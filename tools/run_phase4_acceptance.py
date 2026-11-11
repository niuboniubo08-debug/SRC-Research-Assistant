"""Real local dependency-audit acceptance for phase 4.

Runs the actual pip-audit executable against isolated local projects with
requirements.txt, pyproject.toml and a no-vulnerability dependency.  The only
network use is pip-audit's public vulnerability service.
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

ACCEPTANCE_ROOT = ROOT / "storage" / "phase4_acceptance"
OUTPUT = ROOT / "docs" / "acceptance" / "phase4_acceptance.json"


def _write_config() -> Path:
    if ACCEPTANCE_ROOT.exists():
        shutil.rmtree(ACCEPTANCE_ROOT)
    ACCEPTANCE_ROOT.mkdir(parents=True)
    config = {
        "app": {
            "name": "SRC Phase 4 Acceptance",
            "version": "0.4.0",
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


def _outcome(outcome) -> dict[str, object]:
    return {
        "task_id": outcome.task.task_id,
        "status": outcome.task.status.value,
        "progress": outcome.task.progress,
        "finished_at": (
            to_db_time(outcome.task.finished_at) if outcome.task.finished_at else None
        ),
        "dependency_file": outcome.dependency_file,
        "audited_dependencies": outcome.audited_dependencies,
        "findings_count": len(outcome.findings),
        "result_summary": outcome.task.result_summary,
        "error_message": outcome.task.error_message,
        "warnings": list(outcome.warnings),
        "errors": list(outcome.errors),
        "findings": [
            {
                "risk": item.severity.value,
                "dependency": item.metadata.get("dependency_name"),
                "current_version": item.metadata.get("current_version"),
                "vulnerability_id": item.rule_id,
                "fix_versions": item.metadata.get("fix_versions"),
                "file": item.file_path,
                "line": item.line_number,
                "source": item.metadata.get("source"),
                "scanner": item.scanner_name,
                "scanner_version": item.scanner_version,
            }
            for item in outcome.findings[:100]
        ],
    }


def main() -> int:
    config_path = _write_config()
    requirements_dir = ACCEPTANCE_ROOT / "requirements_project"
    pyproject_dir = ACCEPTANCE_ROOT / "pyproject_project"
    safe_dir = ACCEPTANCE_ROOT / "safe_project"
    requirements_dir.mkdir()
    pyproject_dir.mkdir()
    safe_dir.mkdir()
    (requirements_dir / "requirements.txt").write_text(
        "requests==2.19.0\n", encoding="utf-8"
    )
    (pyproject_dir / "pyproject.toml").write_text(
        "[project]\n"
        "name = 'phase4-pyproject-example'\n"
        "version = '1.0.0'\n"
        "requires-python = '>=3.10'\n"
        "dependencies = ['requests==2.19.0']\n",
        encoding="utf-8",
    )
    (safe_dir / "requirements.txt").write_text(
        "six==1.16.0\n", encoding="utf-8"
    )

    context = build_context(config_path, expire_overdue=False)
    projects = context.project_service
    scopes = context.scope_service
    service = context.dependency_service

    projects_created = {}
    for key, directory in (
        ("requirements", requirements_dir),
        ("pyproject", pyproject_dir),
        ("safe", safe_dir),
    ):
        project = projects.create_project(
            f"第四阶段验收 · {key}",
            "local_audit",
            "pip-audit 本地验收",
            str(directory),
            "active",
        )
        scopes.create_asset(
            project.project_id,
            asset_type="local_project",
            asset_value=str(directory),
            notes="第四阶段依赖审计验收",
        )
        projects_created[key] = project

    scanner = service.scanner_info(refresh=True)
    print("SCANNER", scanner)
    discoveries = {}
    for key, project in projects_created.items():
        discovery = service.discover(project.project_id)
        discoveries[key] = {
            "message": discovery.message,
            "files": [
                {
                    "file": item.relative_path,
                    "kind": item.kind,
                    "count": item.dependency_count,
                    "supported": item.supported,
                    "reason": item.reason,
                }
                for item in discovery.files
            ],
            "primary": discovery.primary.relative_path if discovery.primary else None,
        }
        print("DISCOVERY", key, json.dumps(discoveries[key], ensure_ascii=False))

    outcomes = {}
    for key in ("requirements", "pyproject", "safe"):
        outcome = service.run_audit(
            projects_created[key].project_id, timeout_seconds=180
        )
        outcomes[key] = _outcome(outcome)
        print("AUDIT", key, json.dumps(outcomes[key], ensure_ascii=False))

    # Make the requirements project current and leave a result task for the GUI.
    projects.set_active_project(projects_created["requirements"].project_id)

    all_findings = context.database.fetch_all(
        "SELECT finding_id, project_id, task_id, metadata_json FROM findings"
    )
    metadata_ok = all(
        bool(row["metadata_json"]) and str(row["metadata_json"]) != "{}"
        for row in all_findings
    )
    result = {
        "generated_at": to_db_time(utc_now()),
        "database": str(context.config.database_path),
        "scanner": {
            "name": scanner.name,
            "version": scanner.version,
            "available": scanner.available,
            "reason": scanner.reason,
        },
        "project_ids": {key: project.project_id for key, project in projects_created.items()},
        "discoveries": discoveries,
        "outcomes": outcomes,
        "database_counts": {
            "tasks": len(context.database.fetch_all("SELECT task_id FROM scan_tasks")),
            "findings": len(all_findings),
            "findings_with_metadata": sum(
                1 for row in all_findings if str(row["metadata_json"]) != "{}"
            ),
        },
        "security": {
            "requirements_has_vulns": outcomes["requirements"]["findings_count"] > 0,
            "pyproject_has_vulns": outcomes["pyproject"]["findings_count"] > 0,
            "safe_has_no_vulns": outcomes["safe"]["findings_count"] == 0,
            "safe_completed": outcomes["safe"]["status"] == "completed",
            "metadata_complete": metadata_ok,
            "remote_scan": False,
            "network_usage": "pip-audit public vulnerability service only",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ACCEPTANCE_JSON", OUTPUT)
    print(
        "RESULT",
        json.dumps(
            {
                "pip_audit": scanner.version,
                "requirements_findings": outcomes["requirements"]["findings_count"],
                "pyproject_findings": outcomes["pyproject"]["findings_count"],
                "safe_findings": outcomes["safe"]["findings_count"],
                "safe_status": outcomes["safe"]["status"],
                "metadata_complete": metadata_ok,
            },
            ensure_ascii=False,
        ),
    )
    success = (
        scanner.available
        and outcomes["requirements"]["status"] == "completed"
        and outcomes["pyproject"]["status"] == "completed"
        and outcomes["requirements"]["findings_count"] > 0
        and outcomes["pyproject"]["findings_count"] > 0
        and outcomes["safe"]["status"] == "completed"
        and outcomes["safe"]["findings_count"] == 0
        and metadata_ok
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
