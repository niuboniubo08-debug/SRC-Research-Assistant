from __future__ import annotations

from datetime import datetime, timezone

from core.models import Confidence, Finding, Severity
from scanners.bandit_scanner import map_bandit_severity
from scanners.semgrep_scanner import map_semgrep_severity


def _finding() -> Finding:
    return Finding(
        title="测试问题",
        category="代码执行",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        description="说明",
        file_path="src/app.py",
        line_number=12,
        rule_id="TEST-001",
        recommendation="修复",
        scanner_name="bandit",
        scanner_version="1.9.4",
        detected_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        project_id=3,
        task_id=4,
    )


def test_finding_model_required_fields() -> None:
    finding = _finding()
    assert finding.project_id == 3
    assert finding.task_id == 4
    assert finding.risk_level == "high"
    assert finding.severity_label == "高危"
    assert finding.confidence_label == "高"
    assert finding.line_display == "12"
    assert finding.rule_id == "TEST-001"
    assert finding.scanner_name == "bandit"
    assert finding.detected_at.tzinfo is not None


def test_severity_mappings_are_unified() -> None:
    assert map_bandit_severity("HIGH") is Severity.HIGH
    assert map_bandit_severity("MEDIUM") is Severity.MEDIUM
    assert map_bandit_severity("LOW") is Severity.LOW
    assert map_bandit_severity("UNKNOWN") is Severity.INFO
    assert map_semgrep_severity("ERROR") is Severity.HIGH
    assert map_semgrep_severity("WARNING") is Severity.MEDIUM
    assert map_semgrep_severity("INFO") is Severity.LOW
    assert map_semgrep_severity("CRITICAL") is Severity.CRITICAL


def test_confidence_mapping() -> None:
    assert Confidence.from_external("HIGH") is Confidence.HIGH
    assert Confidence.from_external("moderate") is Confidence.MEDIUM
    assert Confidence.from_external("low") is Confidence.LOW
    assert Confidence.from_external("something-else") is Confidence.UNKNOWN
