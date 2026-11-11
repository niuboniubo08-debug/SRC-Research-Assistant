from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.models import Severity
from scanners.bandit_scanner import BanditScanner
from scanners.base import (
    ScannerAvailability,
    ScannerExecutionError,
    ScannerParseError,
    ScannerTimeoutError,
    ScannerUnavailable,
    ScanOptions,
)
from scanners.process_runner import CommandResult
from services.scan_service import ScanService


@pytest.fixture
def bandit_payload(tmp_path: Path) -> str:
    target = tmp_path / "project"
    target.mkdir(exist_ok=True)
    return json.dumps(
        {
            "results": [
                {
                    "filename": "app.py",
                    "line_number": 4,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "subprocess call with shell=True identified.",
                    "test_id": "B602",
                    "test_name": "subprocess_popen_with_shell_equals_true",
                    "issue_cwe": {"id": 78, "link": "https://cwe.mitre.org/data/definitions/78.html"},
                    "more_info": "https://bandit.readthedocs.io/en/latest/plugins/b602.html",
                },
                {
                    "filename": str(target / "secrets.py"),
                    "line_number": 2,
                    "issue_severity": "LOW",
                    "issue_confidence": "MEDIUM",
                    "issue_text": "Possible hardcoded password: 'super-secret-value'",
                    "test_id": "B105",
                    "test_name": "hardcoded_password_string",
                },
            ],
            "errors": [{"filename": "broken.py", "reason": "syntax error"}],
        }
    )


def test_bandit_json_parsing_to_unified_findings(tmp_path: Path, bandit_payload: str) -> None:
    scanner = BanditScanner()
    target = tmp_path / "project"
    findings, warnings = scanner.parse_output(bandit_payload, target, "1.9.4")
    assert len(findings) == 2
    first = findings[0]
    assert first.file_path == "app.py"
    assert first.line_number == 4
    assert first.severity is Severity.HIGH
    assert first.confidence.value == "high"
    assert first.rule_id == "B602"
    assert first.scanner_name == "bandit"
    assert first.scanner_version == "1.9.4"
    assert first.category == "命令执行"
    assert "shell" in first.recommendation.lower()
    secret = findings[1]
    assert secret.rule_id == "B105"
    assert "super-secret-value" not in secret.title
    assert "super-secret-value" not in secret.description
    assert "具体值未写入结果" in secret.description
    assert any("syntax error" in warning for warning in warnings)


def test_bandit_empty_results_is_not_an_error(tmp_path: Path) -> None:
    scanner = BanditScanner()
    findings, warnings = scanner.parse_output('{"results": []}', tmp_path, "1.9.4")
    assert findings == []
    assert warnings == []


def test_bandit_bad_json_is_reported(tmp_path: Path) -> None:
    scanner = BanditScanner()
    with pytest.raises(ScannerParseError):
        scanner.parse_output("not json", tmp_path, "1.9.4")
    with pytest.raises(ScannerParseError):
        scanner.parse_output('{"errors": []}', tmp_path, "1.9.4")


def test_bandit_unavailable_when_module_missing(monkeypatch) -> None:
    monkeypatch.setattr("scanners.bandit_scanner.importlib.util.find_spec", lambda _name: None)
    scanner = BanditScanner()
    availability = scanner.is_available()
    assert availability.available is False
    assert "未安装" in availability.reason


def test_bandit_execution_failure_and_timeout(monkeypatch, tmp_path: Path) -> None:
    scanner = BanditScanner()
    scanner._availability_cache = ScannerAvailability(True, "1.9.4")  # noqa: SLF001

    def fake_failure(*_args, **_kwargs):
        return CommandResult(
            command=("bandit",),
            returncode=9,
            stdout="",
            stderr="bandit crashed",
            duration_seconds=0.1,
        )

    monkeypatch.setattr("scanners.bandit_scanner.run_command", fake_failure)
    with pytest.raises(ScannerExecutionError):
        scanner.scan(tmp_path, ScanOptions(timeout_seconds=5))

    def fake_timeout(*_args, **_kwargs):
        return CommandResult(
            command=("bandit",),
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=6,
            timed_out=True,
        )

    monkeypatch.setattr("scanners.bandit_scanner.run_command", fake_timeout)
    with pytest.raises(ScannerTimeoutError):
        scanner.scan(tmp_path, ScanOptions(timeout_seconds=5))


def test_bandit_scan_requires_available_tool(monkeypatch, tmp_path: Path) -> None:
    scanner = BanditScanner()
    scanner._availability_cache = ScannerAvailability.unavailable("not available")  # noqa: SLF001
    with pytest.raises(ScannerUnavailable):
        scanner.scan(tmp_path, ScanOptions(timeout_seconds=5))


def test_actual_bandit_scan_persists_results(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    scopes.create_asset(
        local_project.project_id,
        asset_type="local_project",
        asset_value=str(local_source),
    )
    scanner = BanditScanner(clock=clock)
    assert scanner.is_available().available is True
    service = ScanService(
        db, audit, scope_validator, projects, [scanner], clock=clock
    )
    outcome = service.run_scan(
        local_project.project_id, ["bandit"], timeout_seconds=60
    )
    assert outcome.task.status.value == "completed"
    assert outcome.task.progress == 100
    assert len(outcome.findings) >= 3
    rule_ids = {finding.rule_id for finding in outcome.findings}
    assert {"B602", "B307"}.issubset(rule_ids)
    assert all(finding.file_path == "unsafe.py" for finding in outcome.findings)
    combined_text = " ".join(
        finding.title + finding.description for finding in outcome.findings
    )
    assert "should-not-be-persisted" not in combined_text
    stored = service.list_findings(local_project.project_id, task_id=outcome.task.task_id)
    assert len(stored) == len(outcome.findings)
    assert stored[0].task_id == outcome.task.task_id
    assert stored[0].project_id == local_project.project_id
