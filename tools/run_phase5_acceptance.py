"""Real local phase-5 acceptance data builder.

The source findings in this script come from an actual Bandit run on a local
authorized test project. Dependency findings are inherited from the phase-4
acceptance database, which was produced by a real pip-audit run. Evidence is a
real local file copied through EvidenceService with SHA-256 verification.
Semgrep is intentionally not simulated here; its Windows runtime limitation is
retained from phase 3.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from core.models import FindingStatus  # noqa: E402
from core.timeutil import to_db_time, utc_now  # noqa: E402

ACCEPTANCE_ROOT = ROOT / "storage" / "phase5_acceptance"
PHASE4_DB = ROOT / "storage" / "phase4_acceptance" / "acceptance.db"
OUTPUT = ROOT / "docs" / "acceptance" / "phase5_acceptance.json"


def _config() -> Path:
    ACCEPTANCE_ROOT.mkdir(parents=True, exist_ok=True)
    config = {
        "app": {
            "name": "SRC Phase 5 Acceptance",
            "version": "0.5.0",
            "environment": "acceptance",
        },
        "database": {"path": "acceptance.db"},
        "storage": {
            "root": ".",
            "projects": "projects",
            "evidence": "evidence",
            "reports": "reports",
            "logs": "logs",
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
    path = ACCEPTANCE_ROOT / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


def main() -> int:
    if not PHASE4_DB.is_file():
        raise SystemExit(f"missing phase-4 acceptance database: {PHASE4_DB}")
    config_path = _config()
    evidence_root = ACCEPTANCE_ROOT / "evidence"
    if evidence_root.exists():
        shutil.rmtree(evidence_root)
    target_db = ACCEPTANCE_ROOT / "acceptance.db"
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(target_db) + suffix)
        if candidate.exists():
            candidate.unlink()
    shutil.copy2(PHASE4_DB, target_db)
    context = build_context(config_path, expire_overdue=False)
    print("SCHEMA", context.database.schema_version())
    project = context.project_service.get_project(1)
    project_dir = Path(project.local_path)
    if not project_dir.is_dir():
        raise SystemExit(f"missing phase-4 local project: {project_dir}")

    demo_file = project_dir / "phase5_demo_source.py"
    demo_file.write_text(
        "import subprocess\n"
        "def run(value):\n"
        "    eval(value)\n"
        "    subprocess.run('echo ' + value, shell=True)\n",
        encoding="utf-8",
    )
    source_outcome = context.scan_service.run_scan(
        project.project_id, ["bandit"], timeout_seconds=120
    )
    print(
        "BANDIT_TASK",
        source_outcome.task.task_id,
        source_outcome.task.status.value,
        len(source_outcome.findings),
    )
    all_findings = context.vulnerability_service.list_findings(
        project_id=project.project_id, limit=1000
    )
    by_scanner = {}
    for item in all_findings:
        by_scanner.setdefault(item.scanner_name, 0)
        by_scanner[item.scanner_name] += 1
    print("FINDINGS", len(all_findings), by_scanner)

    pip_finding = next(
        (item for item in all_findings if item.scanner_name == "pip-audit"),
        None,
    )
    bandit_finding = next(
        (item for item in all_findings if item.scanner_name == "bandit"),
        None,
    )
    if pip_finding is None or bandit_finding is None:
        raise SystemExit("acceptance requires both pip-audit and Bandit findings")

    screenshot_source = ROOT / "docs" / "acceptance" / "phase4_dependency_audit.png"
    screenshot_copy = project_dir / "phase5_evidence_screenshot.png"
    shutil.copy2(screenshot_source, screenshot_copy)
    file_evidence = context.evidence_service.add_evidence(
        project.project_id,
        pip_finding.finding_id,
        "screenshot",
        "依赖漏洞验收截图",
        "本地验收截图副本，仅用于第五阶段证据中心验证。",
        source_path=screenshot_copy,
        source="phase5_acceptance",
    )
    text_evidence = context.evidence_service.add_evidence(
        project.project_id,
        pip_finding.finding_id,
        "dependency_info",
        "依赖漏洞摘要",
        "依赖：requests 2.19.0\n来源：pip-audit 真实验收数据\n"
        "说明：本阶段不改写 pip-audit 的 severity/affected range 处理方式。",
        source="phase4_acceptance",
    )
    context.evidence_service.add_evidence(
        project.project_id,
        bandit_finding.finding_id,
        "code_snippet",
        "Bandit 源码片段",
        "import subprocess\nsubprocess.run('echo ' + value, shell=True)",
        source="phase5_bandit_acceptance",
    )
    context.vulnerability_service.change_status(
        project.project_id,
        pip_finding.finding_id,
        FindingStatus.REVIEWING,
        note="第五阶段验收：进入人工复核",
    )
    context.vulnerability_service.change_status(
        project.project_id,
        bandit_finding.finding_id,
        FindingStatus.CONFIRMED,
        note="第五阶段验收：确认本地测试问题",
    )
    context.vulnerability_service.update_notes(
        project.project_id,
        pip_finding.finding_id,
        "已在本地验收中人工复核；仅保存脱敏证据。",
    )
    context.project_service.set_active_project(project.project_id)

    evidence_rows = context.evidence_service.list_evidence(
        project_id=project.project_id
    )
    status_counts = context.vulnerability_service.status_counts(project.project_id)
    tasks = context.database.fetch_all(
        "SELECT task_id, task_type, status FROM scan_tasks "
        "WHERE project_id = ? ORDER BY task_id",
        (project.project_id,),
    )
    evidence_payload = [
        {
            "evidence_id": item.evidence_id,
            "type": item.evidence_type.value,
            "title": item.title,
            "finding_id": item.finding_id,
            "file_name": item.file_name,
            "file_hash": item.file_hash,
            "source": item.source,
        }
        for item in evidence_rows
    ]
    result = {
        "generated_at": to_db_time(utc_now()),
        "phase4_source_db": str(PHASE4_DB),
        "database": str(context.config.database_path),
        "schema_version": context.database.schema_version(),
        "project_id": project.project_id,
        "project_name": project.project_name,
        "source_scan": {
            "scanner": "bandit",
            "task_id": source_outcome.task.task_id,
            "status": source_outcome.task.status.value,
            "findings": len(source_outcome.findings),
            "error": source_outcome.task.error_message,
        },
        "finding_counts_by_scanner": by_scanner,
        "total_findings": len(all_findings),
        "status_counts": status_counts,
        "tasks": [dict(row) for row in tasks],
        "evidence": evidence_payload,
        "evidence_sha256": {
            "file": file_evidence.file_path,
            "source": screenshot_copy.name,
            "hash": file_evidence.file_hash,
            "expected": hashlib.sha256(screenshot_copy.read_bytes()).hexdigest(),
        },
        "text_evidence_id": text_evidence.evidence_id,
        "semgrep": "not run: retained Windows CA-store limitation from phase 3",
        "network": "no remote targets; phase-5 acceptance only read local data and copied a local file",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("EVIDENCE", len(evidence_rows), evidence_payload)
    print("STATUS", status_counts)
    print("ACCEPTANCE_JSON", OUTPUT)
    success = (
        result["schema_version"] == 5
        and source_outcome.task.status.value == "completed"
        and len(source_outcome.findings) > 0
        and by_scanner.get("pip-audit", 0) > 0
        and by_scanner.get("bandit", 0) > 0
        and len(evidence_rows) >= 3
        and result["evidence_sha256"]["hash"] == result["evidence_sha256"]["expected"]
        and status_counts.get("reviewing", 0) >= 1
        and status_counts.get("confirmed", 0) >= 1
    )
    print("SUCCESS", success)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
