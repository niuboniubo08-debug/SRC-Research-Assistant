"""Phase 6C-2A tests: safe HTML report rendering and atomic writing.

These tests use an immutable in-memory ReportSnapshot fixture.  They do not
touch the application database, a scanner, a remote target, or evidence files.
"""

from __future__ import annotations

import errno
import hashlib
import os
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.errors import ValidationError
from core.models.enums import (
    Confidence,
    EvidenceType,
    FindingStatus,
    ProjectStatus,
    ProjectType,
    ScanTaskStatus,
    ScanTaskType,
    Severity,
)
from core.models.project import Project
from core.models.report import (
    ReportAuthorizationSummary,
    ReportEvidence,
    ReportFinding,
    ReportFormat,
    ReportRequest,
    ReportSnapshot,
    ReportStats,
    ReportTaskSummary,
    ReportType,
)
from reports import html_exporter


NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def _project() -> Project:
    return Project(
        project_id=7,
        project_name="中文 😀 项目",
        project_type=ProjectType.LOCAL_AUDIT,
        description="PROJECT_DESCRIPTION_SENTINEL",
        local_path="C:\\secret\\local-path-sentinel",
        status=ProjectStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def _task() -> ReportTaskSummary:
    return ReportTaskSummary(
        task_id=3,
        project_id=7,
        task_type=ScanTaskType.SOURCE_AUDIT,
        target="C:\\secret\\task-target-sentinel",
        status=ScanTaskStatus.COMPLETED,
        started_at=NOW,
        finished_at=NOW,
        created_at=NOW,
        result_summary="TASK_RESULT_SENTINEL",
        error_message="TASK_ERROR_SENTINEL",
        progress=100,
        scanners=("bandit", "semgrep"),
        current_scanner="bandit",
    )


def _finding() -> ReportFinding:
    return ReportFinding(
        finding_id=11,
        project_id=7,
        task_id=3,
        title="<script>alert(1)</script> 恶意标题 & 中文",
        category="代码执行",
        description='<img src=x onerror=alert(1)> " onmouseover=alert(2)',
        severity=Severity.HIGH,
        severity_source="scanner",
        confidence=Confidence.HIGH,
        scanner_name="bandit",
        scanner_version="1.9.4",
        rule_id="B307",
        file_path="unsafe.py",
        line_number=4,
        recommendation="使用安全的替代方案 <b>不要执行这里</b>",
        status=FindingStatus.CONFIRMED,
        manual_notes="NOTE_SENTINEL 中文备注",
        detected_at=NOW,
        last_seen_at=NOW,
        dependency_name="requests",
        dependency_version="2.19.0",
        vulnerability_id="PYSEC-2018-28",
        fix_versions=("2.20.0",),
        affected_versions="<2.20.0",
        evidence_count=2,
        metadata={"source": "fixture", "password": "META_SECRET_SENTINEL"},
    )


def _evidence() -> ReportEvidence:
    return ReportEvidence(
        evidence_id=5,
        project_id=7,
        finding_id=11,
        finding_title="<script>alert(1)</script> 恶意标题 & 中文",
        evidence_type=EvidenceType.SCREENSHOT,
        title="证据 <img src=x onerror=alert(1)>",
        description="证据说明中文 😀",
        file_name="C:\\secret\\evidence-file-sentinel.png",
        source="C:\\secret\\evidence-source-sentinel",
        file_path="C:\\secret\\evidence-raw-path-sentinel.png",
        managed_path="project_7/managed-path-sentinel.png",
        file_hash="a" * 64,
        captured_at=NOW,
        created_at=NOW,
        file_exists=False,
        hash_matches=None,
        file_status_note="EVIDENCE_STATUS_SENTINEL",
    )


def _stats(
    *,
    finding_count: int,
    evidence_count: int,
    task_count: int,
) -> ReportStats:
    return ReportStats(
        task_count=task_count,
        task_status_counts={"completed": task_count, "failed": 0},
        task_scanner_counts={"bandit": task_count},
        finding_count=finding_count,
        severity_counts={"high": finding_count} if finding_count else {},
        scanner_counts={"bandit": finding_count} if finding_count else {},
        finding_status_counts={"confirmed": finding_count} if finding_count else {},
        dependency_finding_count=finding_count,
        evidence_count=evidence_count,
        evidence_type_counts={"screenshot": evidence_count} if evidence_count else {},
        file_evidence_count=evidence_count,
        missing_evidence_file_count=1 if evidence_count else 0,
        hash_mismatch_count=0,
    )


def _snapshot(
    report_type: ReportType = ReportType.PROJECT_SUMMARY,
    *,
    findings: tuple[ReportFinding, ...] | None = None,
    evidence: tuple[ReportEvidence, ...] | None = None,
    tasks: tuple[ReportTaskSummary, ...] | None = None,
    warnings: tuple[str, ...] = ("报告警告中文 😀",),
    limitations: tuple[str, ...] = ("已知限制：Semgrep 当前不可用。",),
) -> ReportSnapshot:
    finding_items = (_finding(),) if findings is None else findings
    evidence_items = (_evidence(),) if evidence is None else evidence
    task_items = (_task(),) if tasks is None else tasks
    return ReportSnapshot(
        snapshot_id="0123456789abcdef0123456789abcdef",
        report_type=report_type,
        project=_project(),
        authorization=ReportAuthorizationSummary(
            as_of=NOW,
            total_count=1,
            effective_count=1,
            confirmed_count=1,
            expired_count=0,
            pending_count=0,
            revoked_count=0,
            scope_asset_count=2,
            active_scope_asset_count=1,
            historical_scan_authorization_available=False,
            note="当前授权按生成时刻计算。",
        ),
        tasks=task_items,
        findings=finding_items,
        evidence=evidence_items,
        stats=_stats(
            finding_count=len(finding_items),
            evidence_count=len(evidence_items),
            task_count=len(task_items),
        ),
        generated_at=NOW,
        schema_version=5,
        data_scope=("project", "findings", "evidence"),
        warnings=warnings,
        known_limitations=limitations,
    )


def _request(
    report_type: ReportType,
    *,
    title: str = "",
    include_notes: bool = True,
    include_evidence_images: bool = False,
    report_format: ReportFormat = ReportFormat.HTML,
) -> ReportRequest:
    return ReportRequest(
        project_id=7,
        report_type=report_type,
        report_format=report_format,
        title=title,
        include_notes=include_notes,
        include_evidence_images=include_evidence_images,
    )


@pytest.mark.parametrize("report_type", list(ReportType))
def test_three_report_types_render_utf8_and_print_css(report_type: ReportType) -> None:
    html = html_exporter.render_html(_snapshot(report_type), _request(report_type))

    assert html.startswith("<!DOCTYPE html>")
    assert 'lang="zh-CN"' in html
    assert 'charset="utf-8"' in html
    assert "@media print" in html
    assert "中文 😀" in html
    assert "<html" in html and "<head" in html and "<body" in html
    assert "报告警告中文 😀" in html
    assert "已知限制：Semgrep 当前不可用。" in html
    assert "<script" not in html.lower()
    assert "<img" not in html.lower()
    assert 'src="http' not in html.lower()
    assert 'href="http' not in html.lower()
    assert "@import" not in html.lower()


def test_report_type_specific_sections() -> None:
    vulnerability = html_exporter.render_html(
        _snapshot(ReportType.VULNERABILITY),
        _request(ReportType.VULNERABILITY),
    )
    evidence = html_exporter.render_html(
        _snapshot(ReportType.EVIDENCE),
        _request(ReportType.EVIDENCE),
    )
    summary = html_exporter.render_html(
        _snapshot(ReportType.PROJECT_SUMMARY),
        _request(ReportType.PROJECT_SUMMARY),
    )

    assert "漏洞与风险记录" in vulnerability
    assert "证据记录" not in vulnerability
    assert "证据记录" in evidence
    assert "关联漏洞摘要" in evidence
    assert "漏洞与风险记录" not in evidence
    assert "漏洞与风险摘要" in summary
    assert "证据摘要" in summary


def test_malicious_text_is_escaped_in_text_and_attributes() -> None:
    html = html_exporter.render_html(
        _snapshot(ReportType.VULNERABILITY),
        _request(ReportType.VULNERABILITY),
    )

    assert "&lt;script&gt;" in html
    assert "&lt;img" in html
    assert "<script>" not in html
    assert "<img" not in html
    assert '" onmouseover=alert(2)' not in html
    assert "&#34;" in html or "&#x27;" in html
    assert "&lt;b&gt;" in html


def test_sensitive_fields_are_not_in_html() -> None:
    snapshot = _snapshot(ReportType.PROJECT_SUMMARY)
    snapshot = replace(
        snapshot,
        findings=(
            replace(snapshot.findings[0], file_path="C:\\secret\\absolute-source.py"),
        ),
    )
    html = html_exporter.render_html(
        snapshot,
        _request(ReportType.PROJECT_SUMMARY),
    )

    for sentinel in (
        "C:\\secret\\local-path-sentinel",
        "PROJECT_DESCRIPTION_SENTINEL",
        "C:\\secret\\task-target-sentinel",
        "TASK_RESULT_SENTINEL",
        "TASK_ERROR_SENTINEL",
        "C:\\secret\\evidence-raw-path-sentinel.png",
        "project_7/managed-path-sentinel.png",
        "C:\\secret\\evidence-source-sentinel",
        "C:\\secret\\absolute-source.py",
        "META_SECRET_SENTINEL",
    ):
        assert sentinel not in html


def test_manual_notes_can_be_excluded_by_request() -> None:
    included = html_exporter.render_html(
        _snapshot(ReportType.VULNERABILITY),
        _request(ReportType.VULNERABILITY, include_notes=True),
    )
    excluded = html_exporter.render_html(
        _snapshot(ReportType.VULNERABILITY),
        _request(ReportType.VULNERABILITY, include_notes=False),
    )

    assert "NOTE_SENTINEL 中文备注" in included
    assert "NOTE_SENTINEL 中文备注" not in excluded
    assert "本报告未包含人工备注" in excluded


def test_evidence_images_are_not_embedded_or_read() -> None:
    request = _request(
        ReportType.EVIDENCE,
        include_evidence_images=True,
    )
    view = html_exporter.build_report_view_model(
        _snapshot(ReportType.EVIDENCE),
        request,
    )
    html = html_exporter.render_html(_snapshot(ReportType.EVIDENCE), request)

    assert view.evidence_images_requested is True
    assert view.evidence_images_embedded is False
    assert "本阶段不读取或嵌入证据图片" in html
    assert "<img" not in html.lower()
    assert "data:image" not in html.lower()


def test_empty_findings_use_neutral_language() -> None:
    snapshot = _snapshot(
        ReportType.VULNERABILITY,
        findings=(),
        warnings=("项目没有 Finding；不能据此推断不存在漏洞。",),
    )
    html = html_exporter.render_html(
        snapshot,
        _request(ReportType.VULNERABILITY),
    )

    assert "当前报告快照中未包含漏洞记录" in html
    assert "系统安全" not in html
    assert "项目没有 Finding；不能据此推断不存在漏洞。" in html


def test_request_validation() -> None:
    snapshot = _snapshot(ReportType.VULNERABILITY)
    with pytest.raises(ValidationError):
        html_exporter.render_html(
            snapshot,
            _request(ReportType.VULNERABILITY, report_format=ReportFormat.PDF),
        )
    with pytest.raises(ValidationError):
        html_exporter.render_html(
            snapshot,
            ReportRequest(
                project_id=99,
                report_type=ReportType.VULNERABILITY,
                report_format=ReportFormat.HTML,
            ),
        )
    with pytest.raises(ValidationError):
        html_exporter.render_html(
            snapshot,
            _request(ReportType.PROJECT_SUMMARY),
        )


def test_atomic_write_is_utf8_and_returns_artifact(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    request = _request(ReportType.PROJECT_SUMMARY, title="验收报告 😀")

    artifact = html_exporter.write_html_report(
        _snapshot(ReportType.PROJECT_SUMMARY),
        request,
        output_dir,
    )

    path = Path(artifact.path or "")
    assert path.is_file()
    assert path.parent == output_dir.resolve()
    payload = path.read_bytes()
    assert b"<html" in payload
    assert "中文 😀".encode("utf-8") in payload
    assert artifact.sha256 == hashlib.sha256(payload).hexdigest()
    assert artifact.report_format is ReportFormat.HTML
    assert not list(output_dir.glob("*.tmp"))
    assert not list(output_dir.glob(".*.tmp"))


def test_write_refuses_overwrite_and_preserves_old_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    snapshot = _snapshot(ReportType.PROJECT_SUMMARY)
    first = html_exporter.write_html_report(
        snapshot,
        _request(ReportType.PROJECT_SUMMARY, title="旧报告"),
        output_dir,
    )
    old_bytes = Path(first.path or "").read_bytes()

    with pytest.raises(FileExistsError):
        html_exporter.write_html_report(
            snapshot,
            _request(ReportType.PROJECT_SUMMARY, title="新报告"),
            output_dir,
        )

    assert Path(first.path or "").read_bytes() == old_bytes
    assert not list(output_dir.glob(".*.tmp"))

    second = html_exporter.write_html_report(
        snapshot,
        _request(ReportType.PROJECT_SUMMARY, title="新报告"),
        output_dir,
        overwrite=True,
    )
    assert Path(second.path or "").read_bytes() != old_bytes


@pytest.mark.parametrize("overwrite", [False, True])
def test_write_rejects_existing_directory_target(
    tmp_path: Path, overwrite: bool
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"
    target.mkdir()

    with pytest.raises(FileExistsError if not overwrite else ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
            overwrite=overwrite,
        )

    assert target.is_dir()
    assert list(target.iterdir()) == []
    assert not list(output_dir.glob(".*.tmp"))


@pytest.mark.parametrize(
    "filename",
    ["../escape.html", "C:\\outside.html", "subdir/inside.html", "report.txt"],
)
def test_write_rejects_path_escape_and_non_html(
    tmp_path: Path, filename: str
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename=filename,
        )
    assert not (tmp_path / "escape.html").exists()


def test_failed_replace_preserves_old_file_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    snapshot = _snapshot(ReportType.PROJECT_SUMMARY)
    first = html_exporter.write_html_report(
        snapshot,
        _request(ReportType.PROJECT_SUMMARY, title="保留旧报告"),
        output_dir,
    )
    old_bytes = Path(first.path or "").read_bytes()

    def fail_replace(src, dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(html_exporter.os, "replace", fail_replace)
    with pytest.raises(OSError):
        html_exporter.write_html_report(
            snapshot,
            _request(ReportType.PROJECT_SUMMARY, title="失败的新报告"),
            output_dir,
            overwrite=True,
        )

    assert Path(first.path or "").read_bytes() == old_bytes
    assert not list(output_dir.glob(".*.tmp"))


def test_templates_have_no_safe_markup_or_remote_or_script() -> None:
    template_dir = Path(__file__).resolve().parents[1] / "reports" / "templates"
    for template in template_dir.glob("*.html"):
        text = template.read_text(encoding="utf-8")
        lowered = text.lower()
        assert "|safe" not in text
        assert "markup" not in lowered
        assert "<script" not in lowered
        assert 'src="http' not in lowered
        assert 'href="http' not in lowered
        assert "@import" not in lowered


def _make_windows_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        pytest.skip(f"当前环境无法创建 Windows junction: {detail}")
    assert link.is_junction()


def _make_file_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"当前环境无法创建 Windows 文件符号链接: {exc}")
    assert link.is_symlink()


def test_normal_real_reports_dir_still_exports(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()

    artifact = html_exporter.write_html_report(
        _snapshot(ReportType.PROJECT_SUMMARY),
        _request(ReportType.PROJECT_SUMMARY),
        output_dir,
        filename="normal.html",
    )

    artifact_path = Path(artifact.path or "")
    assert artifact_path.is_file()
    assert artifact_path.parent == output_dir.resolve()
    assert artifact.sha256 is not None


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
def test_reports_dir_itself_junction_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    reports_link = tmp_path / "reports_link"
    _make_windows_junction(reports_link, outside)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            reports_link,
            filename="root.html",
        )

    assert list(outside.iterdir()) == []


def test_reports_dir_itself_symlink_is_rejected_when_available(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    reports_link = tmp_path / "reports_link"
    try:
        os.symlink(outside, reports_link, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"当前环境无法创建 Windows 符号链接: {exc}")

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            reports_link,
            filename="root.html",
        )

    assert list(outside.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
def test_external_junction_leaf_is_rejected(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    escape_link = output_dir / "escape.html"
    _make_windows_junction(escape_link, outside)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="escape.html",
        )

    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("overwrite", [False, True])
def test_internal_file_symlink_leaf_is_rejected(
    tmp_path: Path, overwrite: bool
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "target.html"
    target.write_text("ORIGINAL_TARGET", encoding="utf-8")
    link = output_dir / "alias.html"
    _make_file_symlink_or_skip(link, target)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="alias.html",
            overwrite=overwrite,
        )

    assert target.read_text(encoding="utf-8") == "ORIGINAL_TARGET"
    assert link.is_symlink()
    assert not list(output_dir.glob(".*.tmp"))


@pytest.mark.parametrize("overwrite", [False, True])
def test_broken_symlink_leaf_is_rejected(
    tmp_path: Path, overwrite: bool
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    missing_target = output_dir / "missing.html"
    link = output_dir / "alias.html"
    _make_file_symlink_or_skip(link, missing_target)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="alias.html",
            overwrite=overwrite,
        )

    assert not missing_target.exists()
    assert link.is_symlink()
    assert not list(output_dir.glob(".*.tmp"))


def test_external_file_symlink_leaf_is_rejected(tmp_path: Path) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_target = outside / "secret.html"
    outside_target.write_text("OUTSIDE_SECRET", encoding="utf-8")
    link = output_dir / "escape.html"
    _make_file_symlink_or_skip(link, outside_target)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="escape.html",
            overwrite=True,
        )

    assert outside_target.read_text(encoding="utf-8") == "OUTSIDE_SECRET"
    assert link.is_symlink()
    assert not list(output_dir.glob(".*.tmp"))


def test_leaf_type_check_oserror_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"
    real_is_symlink = Path.is_symlink

    def failing_is_symlink(self: Path) -> bool:
        if self == target:
            raise OSError("simulated leaf stat failure")
        return real_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", failing_is_symlink)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert not target.exists()
    assert not list(output_dir.glob(".*.tmp"))


def test_overwrite_false_race_is_rejected_by_exclusive_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"
    real_link = html_exporter.os.link

    def racing_link(src, dst, *args, **kwargs):
        Path(dst).write_text("concurrent winner", encoding="utf-8")
        return real_link(src, dst, *args, **kwargs)

    def forbidden_replace(*args, **kwargs):
        raise AssertionError("overwrite=False must not use os.replace")

    monkeypatch.setattr(html_exporter.os, "link", racing_link)
    monkeypatch.setattr(html_exporter.os, "replace", forbidden_replace)

    with pytest.raises(FileExistsError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert target.read_text(encoding="utf-8") == "concurrent winner"
    assert not list(output_dir.glob(".*.tmp"))


def test_no_overwrite_fails_closed_without_hardlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"

    def unsupported_link(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, "hard links unsupported")

    def forbidden_replace(*args, **kwargs):
        raise AssertionError("overwrite=False must not fall back to os.replace")

    monkeypatch.setattr(html_exporter.os, "link", unsupported_link)
    monkeypatch.setattr(html_exporter.os, "replace", forbidden_replace)

    with pytest.raises(html_exporter.ReportExportError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert not target.exists()
    assert not list(output_dir.glob(".*.tmp"))


def test_keyboard_interrupt_cleans_temp_and_preserves_old_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    snapshot = _snapshot(ReportType.PROJECT_SUMMARY)
    first = html_exporter.write_html_report(
        snapshot,
        _request(ReportType.PROJECT_SUMMARY, title="旧报告"),
        output_dir,
    )
    old_bytes = Path(first.path or "").read_bytes()

    def interrupt_replace(src, dst):
        raise KeyboardInterrupt()

    monkeypatch.setattr(html_exporter.os, "replace", interrupt_replace)
    with pytest.raises(KeyboardInterrupt):
        html_exporter.write_html_report(
            snapshot,
            _request(ReportType.PROJECT_SUMMARY, title="中断的新报告"),
            output_dir,
            overwrite=True,
        )

    assert Path(first.path or "").read_bytes() == old_bytes
    assert not list(output_dir.glob(".*.tmp"))


def test_untrusted_text_fields_are_bounded_and_control_chars_removed() -> None:
    long_text = "x" * 2_500
    snapshot = replace(
        _snapshot(ReportType.PROJECT_SUMMARY),
        warnings=(f"warning\x00\x01\t{long_text}",),
        data_scope=(f"scope\x02\t{long_text}",),
        known_limitations=(f"limitation\x1f\t{long_text}",),
    )
    request = _request(
        ReportType.PROJECT_SUMMARY,
        title=f"\x00\x01Title{long_text}\nsecond line",
    )

    view = html_exporter.build_report_view_model(snapshot, request)

    assert len(view.title) <= 200
    assert view.title.startswith("Title")
    assert "\n" not in view.title
    assert len(view.warnings) == 1
    assert len(view.warnings[0]) <= 2_000
    assert len(view.data_scope[0]) <= 2_000
    assert len(view.known_limitations[0]) <= 2_000
    for text in (
        view.title,
        *view.warnings,
        *view.data_scope,
        *view.known_limitations,
    ):
        assert "\x00" not in text
        assert "\x01" not in text
        assert "\x02" not in text
        assert "\x1f" not in text
        assert "\t" not in text
        assert "\n" not in text


def test_warning_list_is_bounded() -> None:
    snapshot = replace(
        _snapshot(ReportType.PROJECT_SUMMARY),
        warnings=tuple(f"warning-{index}" for index in range(105)),
    )

    view = html_exporter.build_report_view_model(snapshot)

    assert len(view.warnings) == 100


@pytest.mark.parametrize(
    "filename",
    [
        "NUL.html",
        "nul.html",
        "CON.html",
        "PRN.html",
        "AUX.html",
        "COM1.html",
        "LPT9.html",
        "CONIN$.html",
        "report?.html",
        "report*.html",
        "report<.html",
        "report>.html",
        "report|.html",
        'report".html',
    ],
)
def test_write_rejects_windows_reserved_names_and_invalid_chars(
    tmp_path: Path, filename: str
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename=filename,
        )

    assert not any(output_dir.iterdir())
