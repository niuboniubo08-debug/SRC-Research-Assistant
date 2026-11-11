"""pip-audit adapter for local Python dependency vulnerability audits."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

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


def map_pip_audit_severity(value: Any) -> Severity:
    """Map optional advisory severity; pip-audit JSON often omits it."""

    if isinstance(value, (int, float)):
        score = float(value)
        if score >= 9.0:
            return Severity.CRITICAL
        if score >= 7.0:
            return Severity.HIGH
        if score >= 4.0:
            return Severity.MEDIUM
        return Severity.LOW
    normalized = str(value or "").strip().lower()
    if normalized in {"critical", "9", "high"}:
        return Severity.CRITICAL if normalized == "critical" else Severity.HIGH
    if normalized in {"high", "important"}:
        return Severity.HIGH
    if normalized in {"medium", "moderate", "warning"}:
        return Severity.MEDIUM
    if normalized in {"low", "minor", "info", "informational"}:
        return Severity.LOW
    return Severity.MEDIUM


class PipAuditScanner(BaseScanner):
    name = "pip-audit"
    display_name = "pip-audit"
    supported_languages = ("python-dependencies",)
    vulnerability_service = "pypi"

    def __init__(
        self,
        cache_dir: str | Path,
        temp_dir: str | Path,
        *,
        clock=utc_now,
    ) -> None:
        super().__init__()
        self.cache_dir = Path(cache_dir).resolve()
        self.temp_dir = Path(temp_dir).resolve()
        self._clock = clock

    def _executable(self) -> str | None:
        found = shutil.which("pip-audit")
        if found:
            return found
        candidate = Path(sys.executable).with_name("pip-audit.exe")
        if candidate.is_file():
            return str(candidate)
        return None

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        if self._availability_cache is not None and not refresh:
            return self._availability_cache
        version = self._metadata_version("pip-audit")
        if importlib.util.find_spec("pip_audit") is None:
            result = ScannerAvailability.unavailable(
                "pip-audit 未安装：缺少 Python 包 pip-audit。", "pip-audit", version
            )
            self._availability_cache = result
            return result
        executable = self._executable()
        if not executable:
            result = ScannerAvailability.unavailable(
                "pip-audit 包已安装，但找不到 pip-audit 可执行文件", "pip-audit", version
            )
            self._availability_cache = result
            return result
        try:
            probe = self._probe_command([executable, "--version"], timeout=20)
        except OSError as exc:
            result = ScannerAvailability.unavailable(
                f"pip-audit 启动失败：{exc}", "pip-audit --version", version
            )
        else:
            if probe.cancelled:
                result = ScannerAvailability.unavailable(
                    "pip-audit 可用性检查被取消", "pip-audit --version", version
                )
            elif probe.timed_out:
                result = ScannerAvailability.unavailable(
                    "pip-audit 版本检查超时", "pip-audit --version", version
                )
            elif probe.returncode != 0:
                detail = (probe.stderr or probe.stdout).strip().splitlines()
                reason = detail[0] if detail else f"退出码 {probe.returncode}"
                result = ScannerAvailability.unavailable(
                    f"pip-audit 已安装但无法运行：{reason}", "pip-audit --version", version
                )
            else:
                result = ScannerAvailability(
                    available=True,
                    version=version or "unknown",
                    reason="",
                    command="pip-audit -r <requirements> --format json",
                )
        self._availability_cache = result
        return result

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        target_path = Path(target).expanduser().resolve()
        if not target_path.is_file():
            raise ScannerExecutionError("pip-audit 输入依赖文件不存在")
        availability = self.is_available()
        if not availability.available:
            from scanners.base import ScannerUnavailable

            raise ScannerUnavailable(availability.reason)
        executable = self._executable()
        if not executable:
            raise ScannerExecutionError("找不到 pip-audit 可执行文件")
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ScannerExecutionError(f"无法创建 pip-audit 工作目录：{exc}") from exc

        socket_timeout = max(1, min(30, int(options.timeout_seconds)))
        command = [
            executable,
            "-r",
            str(target_path),
            "--format",
            "json",
            "--progress-spinner",
            "off",
            "--timeout",
            str(socket_timeout),
            "--desc",
            "on",
            "--aliases",
            "on",
            "--vulnerability-service",
            self.vulnerability_service,
            "--cache-dir",
            str(self.cache_dir),
        ]
        env_extra = {
            "TMP": str(self.temp_dir),
            "TEMP": str(self.temp_dir),
            "PIP_CACHE_DIR": str(self.cache_dir),
            **dict(options.env_extra),
        }
        try:
            result = run_command(
                command,
                cwd=self.temp_dir,
                timeout_seconds=options.timeout_seconds,
                cancel_event=options.cancel_event,
                env_extra=env_extra,
            )
        except OSError as exc:
            raise ScannerExecutionError(f"pip-audit 启动失败：{exc}") from exc
        if result.cancelled:
            raise ScanCancelled("pip-audit 审计已取消")
        if result.timed_out:
            raise ScannerTimeoutError("pip-audit 审计超时")
        if not result.stdout.strip():
            detail = (result.stderr or result.stdout).strip()
            raise ScannerExecutionError(
                f"pip-audit 没有返回 JSON（退出码 {result.returncode}）：{detail[:1000]}"
            )
        if result.returncode not in (0, 1):
            detail = (result.stderr or result.stdout).strip()
            raise ScannerExecutionError(
                f"pip-audit 执行失败（退出码 {result.returncode}）：{detail[:1000]}"
            )
        findings, warnings, audited = self.parse_output(
            result.stdout, target_path, availability.version
        )
        if result.output_truncated:
            warnings.append("pip-audit 输出超过捕获上限，结果可能不完整。")
        return ScanOutput(
            findings=tuple(findings),
            warnings=tuple(warnings),
            metadata={
                "returncode": result.returncode,
                "duration_seconds": round(result.duration_seconds, 3),
                "audited_dependencies": audited,
                "vulnerability_service": self.vulnerability_service,
            },
        )

    def parse_output(
        self, payload_text: str, target: Path, version: str
    ) -> tuple[list[Finding], list[str], int]:
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            raise ScannerParseError(f"pip-audit JSON 解析失败：{exc.msg}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("dependencies"), list):
            raise ScannerParseError("pip-audit JSON 缺少 dependencies 列表")

        findings: list[Finding] = []
        warnings: list[str] = []
        seen: set[tuple[str, str]] = set()
        dependencies = payload.get("dependencies", [])
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            name = str(dependency.get("name") or "").strip()
            current_version = str(dependency.get("version") or "").strip()
            skip_reason = str(dependency.get("skip_reason") or "").strip()
            if skip_reason:
                warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
            vulns = dependency.get("vulns")
            if not isinstance(vulns, list):
                continue
            for vuln in vulns:
                if not isinstance(vuln, dict):
                    continue
                vuln_id = str(vuln.get("id") or "").strip()
                aliases = [
                    str(alias).strip()
                    for alias in vuln.get("aliases", [])
                    if str(alias).strip()
                ] if isinstance(vuln.get("aliases"), list) else []
                if not vuln_id:
                    vuln_id = aliases[0] if aliases else "UNKNOWN"
                dedupe_key = (name.lower(), vuln_id)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                fix_versions = [
                    str(item).strip()
                    for item in vuln.get("fix_versions", [])
                    if str(item).strip()
                ] if isinstance(vuln.get("fix_versions"), list) else []
                description = str(vuln.get("description") or "").strip()
                severity_value = (
                    vuln.get("severity")
                    or vuln.get("cvss")
                    or vuln.get("cvss_score")
                )
                severity_source = "advisory"
                severity = map_pip_audit_severity(severity_value)
                if severity_value is None:
                    severity = Severity.MEDIUM
                    severity_source = "conservative-default"
                alias_text = f"\n别名：{', '.join(aliases)}" if aliases else ""
                affected = (
                    str(vuln.get("affected_versions") or "").strip()
                    or f"当前审计版本 {current_version} 命中；具体受影响范围见漏洞公告"
                )
                recommendation = (
                    f"升级 {name} 至 {' / '.join(fix_versions)} 或更高版本，并重新审计。"
                    if fix_versions
                    else f"暂无已知修复版本；评估替换、隔离或临时缓解 {name}。"
                )
                if not description:
                    description = f"pip-audit 在 {name} {current_version} 中检测到 {vuln_id}。"
                description = (
                    f"依赖 {name} {current_version} 命中 {vuln_id}。\n\n"
                    f"{description}{alias_text}"
                )
                metadata = {
                    "dependency_name": name,
                    "current_version": current_version,
                    "vulnerability_id": vuln_id,
                    "aliases": aliases,
                    "affected_versions": affected,
                    "fix_versions": fix_versions,
                    "source": "pip-audit/PyPI",
                    "vulnerability_service": self.vulnerability_service,
                    "dependency_file": str(target),
                    "severity_source": severity_source,
                }
                findings.append(
                    Finding(
                        title=f"{name} {current_version} · {vuln_id}",
                        category="依赖漏洞",
                        severity=severity,
                        confidence=Confidence.HIGH,
                        description=description,
                        file_path=str(target),
                        line_number=0,
                        rule_id=vuln_id,
                        recommendation=recommendation,
                        scanner_name=self.name,
                        scanner_version=version,
                        detected_at=self._clock(),
                        metadata=metadata,
                    )
                )
        return findings, warnings, len(dependencies)
