"""Test-only sealed data builders for phase-5 service and UI tests.

These helpers insert deterministic fixture rows into a temporary database. They
are not scanner integrations and must never be described as real scan results.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.bootstrap import AppContext, build_context


def make_context(tmp_path: Path) -> AppContext:
    config = {
        "app": {
            "name": "SRC Research Assistant",
            "version": "0.5.0",
            "environment": "test",
        },
        "database": {"path": "storage/test.db"},
        "storage": {
            "root": "storage",
            "projects": "storage/projects",
            "evidence": "storage/evidence",
            "reports": "storage/reports",
            "logs": "storage/logs",
        },
        "ui": {"theme": "dark", "window_width": 1440, "window_height": 900},
        "security": {
            "default_remote_access": "deny",
            "require_valid_authorization": True,
            "allow_wildcard_scope": False,
            "allow_redirect_following": False,
            "require_exact_remote_match": True,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return build_context(
        path,
        clock=lambda: datetime(2030, 1, 1, 12, tzinfo=timezone.utc),
        expire_overdue=False,
    )


def create_project(
    context: AppContext,
    tmp_path: Path,
    *,
    name: str,
    directory_name: str,
    with_asset: bool = True,
):
    source = tmp_path / directory_name
    source.mkdir(parents=True, exist_ok=True)
    (source / "unsafe.py").write_text(
        "import subprocess\n"
        "def run(value):\n"
        "    eval(value)\n"
        "    subprocess.run('echo ' + value, shell=True)\n",
        encoding="utf-8",
    )
    project = context.project_service.create_project(
        name, "local_audit", "第五阶段测试项目", str(source), "active"
    )
    if with_asset:
        context.scope_service.create_asset(
            project.project_id,
            asset_type="local_project",
            asset_value=str(source),
        )
    return project


def insert_task(
    db,
    project_id: int,
    *,
    task_type: str = "source_audit",
    target: str = "unsafe.py",
    status: str = "completed",
) -> int:
    now = "2030-01-01T12:00:00Z"
    with db.transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO scan_tasks "
            "(project_id, task_type, target, status, started_at, finished_at, "
            "result_summary, created_at, progress, scanners_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 100, ?)",
            (
                project_id,
                task_type,
                target,
                status,
                now,
                now,
                "测试任务",
                now,
                json.dumps(["bandit"]),
            ),
        )
        return int(cursor.lastrowid or 0)


def insert_finding(
    db,
    project_id: int,
    *,
    title: str,
    scanner_name: str,
    rule_id: str,
    severity: str = "medium",
    confidence: str = "high",
    category: str = "测试分类",
    file_path: str = "unsafe.py",
    line_number: int = 1,
    status: str = "open",
    metadata: dict | None = None,
    task_id: int | None = None,
    detected_at: str = "2030-01-01T12:00:00Z",
) -> int:
    payload = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
    with db.transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO findings "
            "(project_id, task_id, title, category, risk_level, affected_scope, "
            "description, remediation, status, created_at, updated_at, confidence, "
            "file_path, line_number, rule_id, scanner_name, scanner_version, "
            "detected_at, metadata_json, manual_notes, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?)",
            (
                project_id,
                task_id,
                title,
                category,
                severity,
                file_path,
                f"{title} 的测试说明",
                "测试修复建议",
                status,
                detected_at,
                detected_at,
                confidence,
                file_path,
                line_number,
                rule_id,
                scanner_name,
                "1.0-test",
                detected_at,
                payload,
                detected_at,
            ),
        )
        return int(cursor.lastrowid or 0)


def three_scanner_findings(db, project_id: int) -> dict[str, int]:
    task_id = insert_task(db, project_id)
    return {
        "bandit": insert_finding(
            db,
            project_id,
            title="Bandit: eval 使用",
            scanner_name="bandit",
            rule_id="B307",
            severity="high",
            category="代码执行",
            file_path="unsafe.py",
            line_number=3,
            task_id=task_id,
            metadata={"bandit_test_id": ["B307"], "source": "fixture"},
        ),
        "semgrep": insert_finding(
            db,
            project_id,
            title="Semgrep: subprocess shell",
            scanner_name="semgrep",
            rule_id="python.subprocess-shell",
            severity="medium",
            category="命令执行",
            file_path="unsafe.py",
            line_number=5,
            metadata={"semgrep_check_id": "python.subprocess-shell"},
        ),
        "pip_audit": insert_finding(
            db,
            project_id,
            title="requests 2.19.0 · PYSEC-TEST-1",
            scanner_name="pip-audit",
            rule_id="PYSEC-TEST-1",
            severity="medium",
            confidence="high",
            category="依赖漏洞",
            file_path="requirements.txt",
            line_number=1,
            metadata={
                "dependency_name": "requests",
                "current_version": "2.19.0",
                "vulnerability_id": "PYSEC-TEST-1",
                "aliases": ["CVE-TEST-1"],
                "affected_versions": "当前审计版本 2.19.0 命中",
                "fix_versions": ["9.9.9"],
                "source": "pip-audit/PyPI",
                "severity_source": "conservative-default",
            },
        ),
    }
