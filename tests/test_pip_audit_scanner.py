from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.models import Severity
from scanners.base import (
    ScanCancelled,
    ScannerAvailability,
    ScannerExecutionError,
    ScannerParseError,
    ScannerTimeoutError,
    ScannerUnavailable,
    ScanOptions,
)
from scanners.pip_audit_scanner import PipAuditScanner, map_pip_audit_severity
from scanners.process_runner import CommandResult


@pytest.fixture
def payload() -> str:
    return json.dumps(
        {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.19.0",
                    "vulns": [
                        {
                            "id": "PYSEC-2018-28",
                            "fix_versions": ["2.20.0"],
                            "aliases": ["CVE-2018-18074"],
                            "description": "Authorization header leak on redirect.",
                        },
                        {
                            "id": "PYSEC-2018-28",
                            "fix_versions": ["2.20.0"],
                            "aliases": ["CVE-2018-18074"],
                            "description": "Duplicate advisory representation.",
                        },
                        {
                            "id": "PYSEC-2023-74",
                            "fix_versions": ["2.31.0"],
                            "aliases": ["CVE-2023-32681"],
                            "description": "Proxy-Authorization header leak.",
                        },
                    ],
                },
                {"name": "safe-package", "version": "1.0.0", "vulns": []},
                {
                    "name": "skipped-package",
                    "version": "0.1",
                    "vulns": [],
                    "skip_reason": "failed to resolve",
                },
            ],
            "fixes": [],
        }
    )


def make_scanner(tmp_path: Path) -> PipAuditScanner:
    return PipAuditScanner(
        cache_dir=tmp_path / "cache",
        temp_dir=tmp_path / "temp",
    )


def test_pip_audit_json_parsing_dedupes_and_maps_metadata(
    tmp_path: Path, payload: str
) -> None:
    scanner = make_scanner(tmp_path)
    target = tmp_path / "requirements.txt"
    target.write_text("requests==2.19.0\n", encoding="utf-8")
    findings, warnings, audited = scanner.parse_output(payload, target, "2.10.1")
    assert audited == 3
    assert len(findings) == 2, "duplicate advisory IDs must be deduplicated"
    first = findings[0]
    assert first.title.startswith("requests 2.19.0")
    assert first.category == "依赖漏洞"
    assert first.severity is Severity.MEDIUM
    assert first.rule_id == "PYSEC-2018-28"
    assert first.recommendation.startswith("升级 requests 至 2.20.0")
    assert first.metadata["dependency_name"] == "requests"
    assert first.metadata["current_version"] == "2.19.0"
    assert first.metadata["vulnerability_id"] == "PYSEC-2018-28"
    assert "CVE-2018-18074" in first.metadata["aliases"]
    assert first.metadata["fix_versions"] == ["2.20.0"]
    assert first.metadata["source"] == "pip-audit/PyPI"
    assert "failed to resolve" in " ".join(warnings)
    assert first.scanner_name == "pip-audit"
    assert first.scanner_version == "2.10.1"


def test_pip_audit_empty_result(tmp_path: Path) -> None:
    scanner = make_scanner(tmp_path)
    findings, warnings, audited = scanner.parse_output(
        '{"dependencies": []}', tmp_path / "requirements.txt", "2.10.1"
    )
    assert findings == []
    assert warnings == []
    assert audited == 0


def test_pip_audit_bad_json(tmp_path: Path) -> None:
    scanner = make_scanner(tmp_path)
    with pytest.raises(ScannerParseError):
        scanner.parse_output("not json", tmp_path / "requirements.txt", "2.10.1")
    with pytest.raises(ScannerParseError):
        scanner.parse_output('{"foo": []}', tmp_path / "requirements.txt", "2.10.1")


def test_pip_audit_unavailable_when_module_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "scanners.pip_audit_scanner.importlib.util.find_spec", lambda _name: None
    )
    scanner = make_scanner(tmp_path)
    info = scanner.is_available()
    assert info.available is False
    assert "未安装" in info.reason


def test_pip_audit_actual_available() -> None:
    # The application requirements include pip-audit. This verifies the
    # installed tool rather than assuming availability from source.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        scanner = PipAuditScanner(
            cache_dir=Path(tmp) / "cache", temp_dir=Path(tmp) / "temp"
        )
        info = scanner.is_available()
        assert info.available is True
        assert info.version


def test_pip_audit_execution_failure_timeout_and_cancel(
    monkeypatch, tmp_path: Path
) -> None:
    scanner = make_scanner(tmp_path)
    target = tmp_path / "requirements.txt"
    target.write_text("requests==2.19.0\n", encoding="utf-8")
    scanner._availability_cache = ScannerAvailability(True, "2.10.1")  # noqa: SLF001

    def failure(*_args, **_kwargs):
        return CommandResult(
            command=("pip-audit",),
            returncode=9,
            stdout="",
            stderr="pip-audit crashed",
            duration_seconds=0.1,
        )

    monkeypatch.setattr("scanners.pip_audit_scanner.run_command", failure)
    with pytest.raises(ScannerExecutionError):
        scanner.scan(target, ScanOptions(timeout_seconds=5))

    def timeout(*_args, **_kwargs):
        return CommandResult(
            command=("pip-audit",),
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=5,
            timed_out=True,
        )

    monkeypatch.setattr("scanners.pip_audit_scanner.run_command", timeout)
    with pytest.raises(ScannerTimeoutError):
        scanner.scan(target, ScanOptions(timeout_seconds=5))

    def cancelled(*_args, **_kwargs):
        return CommandResult(
            command=("pip-audit",),
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=0.1,
            cancelled=True,
        )

    monkeypatch.setattr("scanners.pip_audit_scanner.run_command", cancelled)
    with pytest.raises(ScanCancelled):
        scanner.scan(target, ScanOptions(timeout_seconds=5))


def test_pip_audit_scan_requires_available_tool(monkeypatch, tmp_path: Path) -> None:
    scanner = make_scanner(tmp_path)
    target = tmp_path / "requirements.txt"
    target.write_text("requests==2.19.0\n", encoding="utf-8")
    scanner._availability_cache = ScannerAvailability.unavailable("not installed")  # noqa: SLF001
    with pytest.raises(ScannerUnavailable):
        scanner.scan(target, ScanOptions(timeout_seconds=5))


def test_pip_audit_severity_mapping() -> None:
    assert map_pip_audit_severity(None) is Severity.MEDIUM
    assert map_pip_audit_severity(9.5) is Severity.CRITICAL
    assert map_pip_audit_severity(7.2) is Severity.HIGH
    assert map_pip_audit_severity(5.0) is Severity.MEDIUM
    assert map_pip_audit_severity(2.0) is Severity.LOW
    assert map_pip_audit_severity("high") is Severity.HIGH
