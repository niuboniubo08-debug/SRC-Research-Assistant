"""Semgrep adapter for repository-owned local Python security rules."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

from core.models import Confidence, Finding, Severity
from core.timeutil import utc_now
from scanners.base import (
    BaseScanner,
    ScanCancelled,
    ScannerAvailability,
    ScannerExecutionError,
    ScannerParseError,
    ScannerTimeoutError,
    ScanOptions,
    ScanOutput,
)
from scanners.process_runner import run_command


def map_semgrep_severity(value: str) -> Severity:
    normalized = str(value or "").strip().upper()
    return {
        "CRITICAL": Severity.CRITICAL,
        "ERROR": Severity.HIGH,
        "HIGH": Severity.HIGH,
        "WARNING": Severity.MEDIUM,
        "MEDIUM": Severity.MEDIUM,
        "INFO": Severity.LOW,
        "LOW": Severity.LOW,
    }.get(normalized, Severity.INFO)


class SemgrepScanner(BaseScanner):
    name = "semgrep"
    display_name = "Semgrep"
    supported_languages = ("python",)

    def __init__(self, rules_path: str | Path, clock=utc_now) -> None:
        super().__init__()
        self.rules_path = Path(rules_path).resolve()
        self._clock = clock

    def _executable(self) -> str | None:
        found = shutil.which("semgrep")
        if found:
            return found
        candidate = Path(sys.executable).with_name("semgrep.exe")
        if candidate.is_file():
            return str(candidate)
        return None

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        if self._availability_cache is not None and not refresh:
            return self._availability_cache
        version = self._metadata_version("semgrep")
        if not self.rules_path.is_file():
            result = ScannerAvailability.unavailable(
                f"Semgrep 本地规则文件不存在：{self.rules_path}",
                "semgrep",
                version,
            )
            self._availability_cache = result
            return result
        if importlib.util.find_spec("semgrep") is None:
            result = ScannerAvailability.unavailable(
                "Semgrep 未安装：缺少 Python 包 semgrep。", "semgrep", version
            )
            self._availability_cache = result
            return result
        executable = self._executable()
        if not executable:
            result = ScannerAvailability.unavailable(
                "Semgrep 包已安装，但找不到 semgrep 可执行文件",
                "semgrep",
                version,
            )
            self._availability_cache = result
            return result
        try:
            probe = self._probe_command([executable, "--version"], timeout=20)
        except OSError as exc:
            result = ScannerAvailability.unavailable(
                f"Semgrep 启动失败：{exc}", "semgrep --version", version
            )
        else:
            if probe.cancelled:
                result = ScannerAvailability.unavailable(
                    "Semgrep 可用性检查被取消", "semgrep --version", version
                )
            elif probe.timed_out:
                result = ScannerAvailability.unavailable(
                    "Semgrep 版本检查超时", "semgrep --version", version
                )
            elif probe.returncode != 0:
                detail = (probe.stderr or probe.stdout).strip().splitlines()
                reason = detail[0] if detail else f"退出码 {probe.returncode}"
                result = ScannerAvailability.unavailable(
                    f"Semgrep 已安装但当前环境无法运行：{reason}",
                    "semgrep --version",
                    version,
                )
            else:
                result = ScannerAvailability(
                    available=True,
                    version=version or "unknown",
                    reason="",
                    command="semgrep --config <local-rules> --json",
                )
        self._availability_cache = result
        return result

    def _command(self, target: Path) -> list[str]:
        executable = self._executable()
        if not executable:
            raise ScannerExecutionError("找不到 semgrep 可执行文件")
        return [
            executable,
            "--config",
            str(self.rules_path),
            "--json",
            "--quiet",
            "--metrics=off",
            "--disable-version-check",
            "--exclude",
            ".venv",
            "--exclude",
            ".git",
            "--exclude",
            "__pycache__",
            "--exclude",
            "node_modules",
            "--exclude",
            "build",
            "--exclude",
            "dist",
            str(target),
        ]

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        root = Path(target).expanduser().resolve()
        if not root.is_dir():
            raise ScannerExecutionError("Semgrep 扫描目标不是有效文件夹")
        availability = self.is_available()
        if not availability.available:
            from scanners.base import ScannerUnavailable

            raise ScannerUnavailable(availability.reason)
        try:
            result = run_command(
                self._command(root),
                cwd=root,
                timeout_seconds=options.timeout_seconds,
                cancel_event=options.cancel_event,
                env_extra={
                    "SEMGREP_SEND_METRICS": "off",
                    "SEMGREP_ENABLE_VERSION_CHECK": "0",
                    **dict(options.env_extra),
                },
            )
        except OSError as exc:
            raise ScannerExecutionError(f"Semgrep 启动失败：{exc}") from exc
        if result.cancelled:
            raise ScanCancelled("Semgrep 扫描已取消")
        if result.timed_out:
            raise ScannerTimeoutError("Semgrep 扫描超时")
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise ScannerExecutionError(
                f"Semgrep 执行失败（退出码 {result.returncode}）：{detail[:1000]}"
            )
        if not result.stdout.strip():
            raise ScannerParseError("Semgrep 未返回 JSON 输出")
        findings, warnings = self.parse_output(
            result.stdout, root, availability.version
        )
        if result.output_truncated:
            warnings = (*warnings, "Semgrep 输出超过捕获上限，结果可能不完整。")
        return ScanOutput(
            findings=tuple(findings),
            warnings=tuple(warnings),
            metadata={
                "returncode": result.returncode,
                "duration_seconds": round(result.duration_seconds, 3),
            },
        )

    def parse_output(
        self, payload_text: str, target: Path, version: str
    ) -> tuple[list[Finding], list[str]]:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ScannerParseError(f"Semgrep JSON 解析失败：{exc.msg}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ScannerParseError("Semgrep JSON 缺少 results 列表")

        findings: list[Finding] = []
        warnings: list[str] = []
        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            filename = self._relative_source(target, str(item.get("path") or ""))
            if not filename:
                warnings.append("忽略不在扫描根目录内的 Semgrep 结果")
                continue
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            metadata = extra.get("metadata") if isinstance(extra.get("metadata"), dict) else {}
            start = item.get("start") if isinstance(item.get("start"), dict) else {}
            try:
                line_number = int(start.get("line") or 0)
            except (TypeError, ValueError):
                line_number = 0
            message = str(extra.get("message") or "").strip()
            rule_id = str(item.get("check_id") or "")
            title = str(metadata.get("title") or "").strip()
            if not title:
                title = (message.splitlines()[0] if message else rule_id)[:180]
            references = metadata.get("references")
            reference_lines: list[str] = []
            if isinstance(references, list):
                reference_lines = [str(url).strip() for url in references if str(url).strip()]
            description = message or title
            if rule_id:
                description += f"\n\n规则：{rule_id}"
            if metadata.get("cwe"):
                cwe_value = str(metadata["cwe"]).strip()
                cwe_text = cwe_value if cwe_value.upper().startswith("CWE-") else f"CWE-{cwe_value}"
                description += f"\n风险分类：{cwe_text}"
            if reference_lines:
                description += "\n参考：" + "，".join(reference_lines[:5])
            findings.append(
                Finding(
                    title=title,
                    category=str(metadata.get("category") or "静态规则"),
                    severity=map_semgrep_severity(
                        str(extra.get("severity") or item.get("severity") or "")
                    ),
                    confidence=Confidence.from_external(
                        str(metadata.get("confidence") or "")
                    ),
                    description=description,
                    file_path=filename,
                    line_number=line_number,
                    rule_id=rule_id,
                    recommendation=str(
                        metadata.get("remediation")
                        or "复核该规则命中，按安全编码规范修复并补充测试。"
                    ),
                    scanner_name=self.name,
                    scanner_version=version,
                    detected_at=self._clock(),
                    affected_scope=str(target),
                )
            )
        errors = payload.get("errors")
        if isinstance(errors, list):
            for error in errors[:20]:
                if isinstance(error, dict):
                    reason = str(error.get("message") or error.get("type") or "").strip()
                    if reason:
                        warnings.append(f"Semgrep: {reason[:300]}")
                elif error:
                    warnings.append(f"Semgrep: {str(error)[:300]}")
        return findings, warnings
