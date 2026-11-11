from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from core.errors import AuthorizationDenied, NotFoundError, ValidationError
from repositories.evidence_repository import EvidenceRepository
from repositories.vulnerability_repository import VulnerabilityRepository
from services.evidence_service import EvidenceService
from services.vulnerability_service import VulnerabilityService
from tests.phase5_helpers import insert_finding


def make_services(db, audit, projects, scope_validator, clock, tmp_path):
    findings = VulnerabilityRepository(db)
    evidence_repo = EvidenceRepository(db)
    vulnerabilities = VulnerabilityService(
        db, audit, projects, findings, evidence_repo, clock=clock
    )
    service = EvidenceService(
        db,
        audit,
        projects,
        scope_validator,
        evidence_repo,
        findings,
        tmp_path / "managed-evidence",
        clock=clock,
    )
    return service, vulnerabilities


def test_multiple_text_evidence_rows_attach_to_one_finding(
    db, audit, projects, scope_validator, clock, local_project, local_asset, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="多证据漏洞",
        scanner_name="bandit",
        rule_id="B-MULTI",
    )
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    first = service.add_evidence(
        local_project.project_id,
        finding_id,
        "code_snippet",
        "代码片段一",
        "eval(user_input)",
    )
    second = service.add_evidence(
        local_project.project_id,
        finding_id,
        "manual_note",
        "人工备注",
        "已脱敏复核说明",
    )
    rows = service.list_evidence(
        project_id=local_project.project_id, finding_id=finding_id
    )
    assert {item.evidence_id for item in rows} == {
        first.evidence_id,
        second.evidence_id,
    }
    assert first.finding_id == finding_id
    assert first.file_hash == ""
    assert service.count(local_project.project_id, finding_id) == 2


def test_file_evidence_is_copied_and_hashed_without_changing_source(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="文件证据",
        scanner_name="bandit",
        rule_id="B-FILE",
    )
    source = local_source / "capture.png"
    content = b"\x89PNG\r\n\x1a\nphase5-evidence"
    source.write_bytes(content)
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    evidence = service.add_evidence(
        local_project.project_id,
        finding_id,
        "screenshot",
        "截图证据",
        "已脱敏截图",
        source_path=source,
    )
    expected = hashlib.sha256(content).hexdigest()
    assert evidence.file_hash == expected
    assert evidence.file_name == "capture.png"
    assert evidence.source == "capture.png"
    assert Path(evidence.file_path).is_file()
    assert Path(evidence.file_path).read_bytes() == content
    assert source.read_bytes() == content
    assert Path(evidence.file_path).resolve().is_relative_to(
        (tmp_path / "managed-evidence").resolve()
    )
    assert evidence.file_path != str(source)


def test_duplicate_source_names_create_unique_managed_copies(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="同名证据",
        scanner_name="bandit",
        rule_id="B-DUP",
    )
    source_dir = local_source / "shots"
    source_dir.mkdir()
    first_source = source_dir / "same.txt"
    first_source.write_text("one", encoding="utf-8")
    second_source = local_source / "same.txt"
    second_source.write_text("two", encoding="utf-8")
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    first = service.add_evidence(
        local_project.project_id,
        finding_id,
        "other_file",
        "同名一",
        source_path=first_source,
    )
    second = service.add_evidence(
        local_project.project_id,
        finding_id,
        "other_file",
        "同名二",
        source_path=second_source,
    )
    assert first.file_path != second.file_path
    assert Path(first.file_path).name != Path(second.file_path).name


def test_path_traversal_is_rejected(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="越界证据",
        scanner_name="bandit",
        rule_id="B-TRAVERSAL",
    )
    outside = tmp_path / "secret.txt"
    outside.write_text("outside", encoding="utf-8")
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(ValidationError):
        service.add_evidence(
            local_project.project_id,
            finding_id,
            "other_file",
            "越界",
            source_path=local_source / ".." / "secret.txt",
        )
    assert service.list_evidence(project_id=local_project.project_id) == []


def test_symlink_to_outside_is_rejected(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="符号链接证据",
        scanner_name="bandit",
        rule_id="B-SYMLINK",
    )
    outside = tmp_path / "outside-symlink-target.txt"
    outside.write_text("outside", encoding="utf-8")
    link = local_source / "outside-link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"当前 Windows 会话无法创建符号链接：{exc}")
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(ValidationError):
        service.add_evidence(
            local_project.project_id,
            finding_id,
            "other_file",
            "符号链接",
            source_path=link,
        )
    assert service.list_evidence(project_id=local_project.project_id) == []


def test_junction_to_outside_is_rejected(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    """A Windows directory junction is an actual reparse-point traversal test."""

    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="目录联接证据",
        scanner_name="bandit",
        rule_id="B-JUNCTION",
    )
    outside_dir = tmp_path / "outside-junction-target"
    outside_dir.mkdir()
    secret = outside_dir / "secret.txt"
    secret.write_text("outside", encoding="utf-8")
    link_dir = local_source / "linked-outside"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_dir), str(outside_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"当前 Windows 会话无法创建目录联接：{result.stderr.strip()}")
    try:
        service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
        with pytest.raises(ValidationError):
            service.add_evidence(
                local_project.project_id,
                finding_id,
                "other_file",
                "目录联接证据",
                source_path=link_dir / "secret.txt",
            )
        assert service.list_evidence(project_id=local_project.project_id) == []
    finally:
        try:
            os.rmdir(link_dir)
        except OSError:
            pass


def test_symlink_metadata_branch_is_rejected(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path, monkeypatch
) -> None:
    """Unit check for the explicit symlink branch; actual symlink creation is skipped above."""

    source = local_source / "simulated-link.txt"
    source.write_text("inside-looking-link", encoding="utf-8")
    real_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda self: self.name == "simulated-link.txt" or real_is_symlink(self),
    )
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="模拟链接元数据",
        scanner_name="bandit",
        rule_id="B-SYMLINK-META",
    )
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(ValidationError):
        service.add_evidence(
            local_project.project_id,
            finding_id,
            "other_file",
            "模拟链接",
            source_path=source,
        )


def test_evidence_requires_finding_in_same_project(
    db, audit, projects, scope_validator, clock, local_project, local_asset, tmp_path
) -> None:
    other_source = tmp_path / "another"
    other_source.mkdir()
    other = projects.create_project(
        "另一个证据项目", "local_audit", "隔离", str(other_source), "active"
    )
    other_finding = insert_finding(
        db,
        other.project_id,
        title="其他项目漏洞",
        scanner_name="semgrep",
        rule_id="OTHER-1",
    )
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(NotFoundError):
        service.add_evidence(
            local_project.project_id,
            other_finding,
            "manual_note",
            "不应写入",
            "cross project",
        )
    with pytest.raises(NotFoundError):
        service.get_evidence(local_project.project_id, 1)


def test_file_evidence_requires_authorized_project_directory(
    db, audit, projects, scope_validator, clock, tmp_path
) -> None:
    source_dir = tmp_path / "no-asset-project"
    source_dir.mkdir()
    evidence_file = source_dir / "capture.txt"
    evidence_file.write_text("content", encoding="utf-8")
    project = projects.create_project(
        "未登记资产", "local_audit", "路径校验", str(source_dir), "active"
    )
    finding_id = insert_finding(
        db,
        project.project_id,
        title="无资产漏洞",
        scanner_name="bandit",
        rule_id="NOASSET",
    )
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(AuthorizationDenied):
        service.add_evidence(
            project.project_id,
            finding_id,
            "other_file",
            "未授权证据",
            source_path=evidence_file,
        )


def test_delete_evidence_keeps_original_file_and_finding(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="删除证据测试",
        scanner_name="bandit",
        rule_id="B-DELETE",
    )
    source = local_source / "delete-me.png"
    source.write_bytes(b"delete evidence")
    service, vulnerabilities = make_services(
        db, audit, projects, scope_validator, clock, tmp_path
    )
    evidence = service.add_evidence(
        local_project.project_id,
        finding_id,
        "screenshot",
        "待删除截图",
        source_path=source,
    )
    managed = Path(evidence.file_path)
    assert managed.exists()
    service.delete_evidence(local_project.project_id, evidence.evidence_id)
    assert not managed.exists()
    assert source.exists()
    assert service.list_evidence(project_id=local_project.project_id) == []
    detail = vulnerabilities.get_detail(local_project.project_id, finding_id)
    assert detail.finding.finding_id == finding_id
    assert detail.evidence == ()


def test_relative_file_path_is_rejected(
    db, audit, projects, scope_validator, clock, local_project, local_asset, local_source, tmp_path
) -> None:
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="相对路径",
        scanner_name="bandit",
        rule_id="B-REL",
    )
    service, _ = make_services(db, audit, projects, scope_validator, clock, tmp_path)
    with pytest.raises(ValidationError):
        service.add_evidence(
            local_project.project_id,
            finding_id,
            "other_file",
            "相对路径证据",
            source_path=Path("unsafe.py"),
        )
