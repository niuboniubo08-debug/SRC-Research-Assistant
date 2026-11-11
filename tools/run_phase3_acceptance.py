"""Real local acceptance for phase 3 source auditing.

Uses the actual Bandit executable and the actual installed Semgrep availability
probe.  Semgrep output is never fabricated when the tool is unavailable.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from core.timeutil import to_db_time, utc_now  # noqa: E402

ACCEPTANCE_ROOT = ROOT / "storage" / "phase3_acceptance"
OUTPUT = ROOT / "docs" / "acceptance" / "phase3_acceptance.json"


def _write_config() -> Path:
    if ACCEPTANCE_ROOT.exists():
        shutil.rmtree(ACCEPTANCE_ROOT)
    ACCEPTANCE_ROOT.mkdir(parents=True)
    config = {
        "app": {
            "name": "SRC Phase 3 Acceptance",
            "version": "0.3.0",
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


def _unsafe_source(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "unsafe.py").write_text(
        "import subprocess\n"
        "\n"
        "PASSWORD = 'phase3-acceptance-secret'\n"
        "\n"
        "def execute(user_input):\n"
        "    eval(user_input)\n"
        "    subprocess.run('echo ' + user_input, shell=True)\n"
        "\n"
        "def load(blob):\n"
        "    import pickle\n"
        "    return pickle.loads(blob)\n",
        encoding="utf-8",
    )


def _safe_source(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "safe.py").write_text(
        "import json\n"
        "\n"
        "def parse(payload: str):\n"
        "    return json.loads(payload)\n",
        encoding="utf-8",
    )


def _summary(outcome) -> dict[str, object]:
    return {
        "task_id": outcome.task.task_id,
        "status": outcome.task.status.value,
        "progress": outcome.task.progress,
        "result_summary": outcome.task.result_summary,
        "error_message": outcome.task.error_message,
        "findings_count": len(outcome.findings),
        "findings": [
            {
                "severity": item.severity.value,
                "confidence": item.confidence.value,
                "rule_id": item.rule_id,
                "title": item.title,
                "file": item.file_path,
                "line": item.line_number,
                "scanner": item.scanner_name,
                "scanner_version": item.scanner_version,
            }
            for item in outcome.findings
        ],
        "scanners_run": list(outcome.scanners_run),
        "scanners_skipped": list(outcome.scanners_skipped),
        "warnings": list(outcome.warnings),
        "errors": list(outcome.errors),
    }


def main() -> int:
    config_path = _write_config()
    unsafe_dir = ACCEPTANCE_ROOT / "unsafe_project"
    safe_dir = ACCEPTANCE_ROOT / "safe_project"
    _unsafe_source(unsafe_dir)
    _safe_source(safe_dir)
    context = build_context(config_path, expire_overdue=False)
    projects = context.project_service
    scopes = context.scope_service
    scan_service = context.scan_service

    unsafe = projects.create_project(
        "第三阶段验收 · Unsafe", "local_audit", "实际 Bandit 扫描", str(unsafe_dir), "active"
    )
    safe = projects.create_project(
        "第三阶段验收 · Safe", "local_audit", "空结果验证", str(safe_dir), "active"
    )
    scopes.create_asset(
        unsafe.project_id,
        asset_type="local_project",
        asset_value=str(unsafe_dir),
        notes="阶段三实际扫描验收",
    )
    scopes.create_asset(
        safe.project_id,
        asset_type="local_project",
        asset_value=str(safe_dir),
        notes="空结果验收",
    )
    projects.set_active_project(unsafe.project_id)

    scanner_infos = {
        info.name: {
            "available": info.available,
            "version": info.version,
            "reason": info.reason,
            "command": info.command,
        }
        for info in scan_service.scanner_infos(refresh=True)
    }
    print("SCANNER_INFOS", json.dumps(scanner_infos, ensure_ascii=False))

    semgrep_only = scan_service.run_scan(
        unsafe.project_id, ["semgrep"], timeout_seconds=60
    )
    print("SEMGREP_ONLY", json.dumps(_summary(semgrep_only), ensure_ascii=False))

    safe_bandit = scan_service.run_scan(
        safe.project_id, ["bandit"], timeout_seconds=60
    )
    print("BANDIT_SAFE", json.dumps(_summary(safe_bandit), ensure_ascii=False))

    bandit_unsafe = scan_service.run_scan(
        unsafe.project_id, ["bandit"], timeout_seconds=60
    )
    print("BANDIT_UNSAFE", json.dumps(_summary(bandit_unsafe), ensure_ascii=False))

    combined = scan_service.run_scan(
        unsafe.project_id, ["bandit", "semgrep"], timeout_seconds=60
    )
    print("COMBINED", json.dumps(_summary(combined), ensure_ascii=False))

    # Leave the latest task as the combined run so the GUI acceptance screenshot
    # shows real Bandit findings and the explicit Semgrep unavailability state.
    projects.set_active_project(unsafe.project_id)
    safety = {
        "secret_in_findings": any(
            "phase3-acceptance-secret" in (item.title + item.description)
            for item in bandit_unsafe.findings
        ),
        "semgrep_fabricated_results": (
            semgrep_only.findings != ()
            if not scanner_infos["semgrep"]["available"]
            else False
        ),
        "safe_scan_completed": safe_bandit.success,
        "safe_scan_findings": len(safe_bandit.findings),
        "unsafe_scan_completed": bandit_unsafe.success,
        "combined_completed": combined.success,
        "project_isolation": {
            "safe_tasks": len(scan_service.list_tasks(safe.project_id)),
            "unsafe_tasks": len(scan_service.list_tasks(unsafe.project_id)),
            "safe_findings": len(scan_service.list_findings(safe.project_id)),
        },
    }
    result = {
        "generated_at": to_db_time(utc_now()),
        "database": str(context.config.database_path),
        "project_ids": {"unsafe": unsafe.project_id, "safe": safe.project_id},
        "scanner_infos": scanner_infos,
        "runs": {
            "semgrep_only": _summary(semgrep_only),
            "bandit_safe": _summary(safe_bandit),
            "bandit_unsafe": _summary(bandit_unsafe),
            "combined": _summary(combined),
        },
        "safety": safety,
        "database_counts": {
            "tasks": len(
                context.database.fetch_all("SELECT task_id FROM scan_tasks")
            ),
            "findings": len(context.database.fetch_all("SELECT finding_id FROM findings")),
        },
        "notes": {
            "semgrep": (
                "Semgrep is genuinely unavailable in this Windows session: "
                + scanner_infos["semgrep"]["reason"]
                if not scanner_infos["semgrep"]["available"]
                else "Semgrep executed locally."
            ),
            "network": "No remote target or Internet scan was used.",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ACCEPTANCE_JSON", OUTPUT)
    print(
        "RESULT",
        json.dumps(
            {
                "bandit_unsafe": bandit_unsafe.task.status.value,
                "bandit_findings": len(bandit_unsafe.findings),
                "bandit_safe": safe_bandit.task.status.value,
                "bandit_safe_findings": len(safe_bandit.findings),
                "semgrep": semgrep_only.task.status.value,
                "semgrep_findings": len(semgrep_only.findings),
                "combined": combined.task.status.value,
                **safety,
            },
            ensure_ascii=False,
        ),
    )

    expected = (
        bandit_unsafe.success
        and len(bandit_unsafe.findings) >= 3
        and safe_bandit.success
        and len(safe_bandit.findings) == 0
        and safety["secret_in_findings"] is False
        and safety["semgrep_fabricated_results"] is False
    )
    return 0 if expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
