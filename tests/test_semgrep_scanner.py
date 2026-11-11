from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from core.models import Severity
from scanners.base import ScannerParseError
from scanners.semgrep_scanner import SemgrepScanner

RULES = Path(__file__).resolve().parents[1] / "scanners" / "rules" / "python_security.yml"


@pytest.fixture
def semgrep_payload(tmp_path: Path) -> str:
    target = tmp_path / "project"
    target.mkdir(exist_ok=True)
    return json.dumps(
        {
            "results": [
                {
                    "check_id": "src-python-dynamic-exec",
                    "path": str(target / "app.py"),
                    "start": {"line": 9, "col": 5},
                    "end": {"line": 9, "col": 20},
                    "extra": {
                        "message": "Avoid dynamic evaluation of untrusted input with eval/exec.",
                        "severity": "ERROR",
                        "metadata": {
                            "title": "动态代码执行",
                            "category": "代码执行",
                            "confidence": "HIGH",
                            "remediation": "不要对不可信输入使用 eval。",
                            "cwe": "CWE-95",
                            "references": ["https://owasp.org/Top10/A03_2021-Injection/"],
                        },
                    },
                }
            ],
            "errors": [{"message": "one file skipped"}],
        }
    )


def test_semgrep_local_rules_are_repository_owned() -> None:
    data = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    rules = data["rules"]
    assert len(rules) >= 7
    assert len({rule["id"] for rule in rules}) == len(rules)
    assert all(rule["languages"] == ["python"] for rule in rules)
    assert all(rule.get("message") for rule in rules)
    assert all("metadata" in rule for rule in rules)


def test_semgrep_json_parsing_to_unified_findings(
    tmp_path: Path, semgrep_payload: str
) -> None:
    scanner = SemgrepScanner(RULES)
    target = tmp_path / "project"
    findings, warnings = scanner.parse_output(semgrep_payload, target, "1.183.0")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.file_path == "app.py"
    assert finding.line_number == 9
    assert finding.rule_id == "src-python-dynamic-exec"
    assert finding.severity is Severity.HIGH
    assert finding.confidence.value == "high"
    assert finding.category == "代码执行"
    assert finding.recommendation == "不要对不可信输入使用 eval。"
    assert finding.scanner_name == "semgrep"
    assert finding.scanner_version == "1.183.0"
    assert any("one file skipped" in warning for warning in warnings)


def test_semgrep_empty_results(tmp_path: Path) -> None:
    scanner = SemgrepScanner(RULES)
    findings, warnings = scanner.parse_output('{"results": []}', tmp_path, "1.183.0")
    assert findings == []
    assert warnings == []


def test_semgrep_bad_json(tmp_path: Path) -> None:
    scanner = SemgrepScanner(RULES)
    with pytest.raises(ScannerParseError):
        scanner.parse_output("not json", tmp_path, "1.183.0")
    with pytest.raises(ScannerParseError):
        scanner.parse_output('{"version": "1"}', tmp_path, "1.183.0")


def test_semgrep_missing_rules_marks_unavailable(tmp_path: Path) -> None:
    scanner = SemgrepScanner(tmp_path / "missing.yml")
    availability = scanner.is_available()
    assert availability.available is False
    assert "规则文件不存在" in availability.reason


def test_semgrep_missing_module_marks_unavailable(monkeypatch) -> None:
    scanner = SemgrepScanner(RULES)
    monkeypatch.setattr(
        "scanners.semgrep_scanner.importlib.util.find_spec", lambda _name: None
    )
    availability = scanner.is_available()
    assert availability.available is False
    assert "未安装" in availability.reason
