"""Bandit adapter producing unified :class:`Finding` objects."""

from __future__ import annotations

import importlib.util
import json
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

_RECOMMENDATIONS = {
    "B102": "避免使用 exec；改用显式、受控的业务逻辑。",
    "B105": "不要硬编码密码；使用环境变量或专用密钥管理。",
    "B106": "不要硬编码密码；使用环境变量或专用密钥管理。",
    "B107": "不要硬编码秘密；使用环境变量或专用密钥管理。",
    "B108": "避免使用可预测的临时文件；使用 tempfile 安全创建。",
    "B201": "生产环境关闭 Flask debug 调试模式。",
    "B301": "不要反序列化不可信 pickle 数据；改用 JSON 等安全格式。",
    "B307": "避免对不可信输入使用 eval；使用显式解析或白名单。",
    "B310": "限制 URL 协议为 http/https，拒绝 file 等危险协议。",
    "B311": "安全用途使用 secrets 模块，而不是可预测的 random。",
    "B324": "使用 SHA-256 或更强哈希；如非安全用途请显式设置 usedforsecurity=False。",
    "B404": "审查 subprocess 的使用，仅允许受控命令和参数。",
    "B506": "使用 yaml.safe_load，并限制输入来源。",
    "B602": "不要使用 shell=True；以参数列表启动进程并校验输入。",
    "B603": "审查子进程命令与参数来源，使用参数列表并设置白名单。",
    "B604": "不要使用 shell=True；以参数列表启动进程并校验输入。",
    "B608": "使用参数化 SQL，禁止把不可信输入拼接到 SQL 字符串。",
    "B701": "关闭 Jinja2 autoescape=False，启用自动转义。",
}

_CATEGORIES = {
    "B102": "代码执行",
    "B105": "凭据管理",
    "B106": "凭据管理",
    "B107": "凭据管理",
    "B201": "安全配置",
    "B301": "反序列化",
    "B307": "代码执行",
    "B310": "网络请求",
    "B311": "密码学",
    "B324": "密码学",
    "B506": "反序列化",
    "B602": "命令执行",
    "B603": "命令执行",
    "B604": "命令执行",
    "B608": "SQL 注入",
    "B701": "模板注入",
}


def map_bandit_severity(value: str) -> Severity:
    normalized = str(value or "").strip().upper()
    return {
        "HIGH": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "LOW": Severity.LOW,
    }.get(normalized, Severity.INFO)


class BanditScanner(BaseScanner):
    name = "bandit"
    display_name = "Bandit"
    supported_languages = ("python",)

    def __init__(self, clock=utc_now) -> None:
        super().__init__()
        self._clock = clock

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        if self._availability_cache is not None and not refresh:
            return self._availability_cache
        if importlib.util.find_spec("bandit") is None:
            result = ScannerAvailability.unavailable(
                "Bandit 未安装：缺少 Python 包 bandit。请执行 pip install bandit。",
                "python -m bandit",
            )
            self._availability_cache = result
            return result
        version = self._metadata_version("bandit")
        command = self._module_command("bandit", "--version")
        try:
            probe = self._probe_command(command, timeout=20)
        except OSError as exc:
            result = ScannerAvailability.unavailable(
                f"Bandit 启动失败：{exc}", "python -m bandit --version"
            )
        else:
            if probe.cancelled:
                result = ScannerAvailability.unavailable(
                    "Bandit 可用性检查被取消", "python -m bandit --version"
                )
            elif probe.timed_out:
                result = ScannerAvailability.unavailable(
                    "Bandit 版本检查超时", "python -m bandit --version"
                )
            elif probe.returncode != 0:
                detail = (probe.stderr or probe.stdout).strip().splitlines()
                reason = detail[0] if detail else f"退出码 {probe.returncode}"
                result = ScannerAvailability.unavailable(
                    f"Bandit 已安装但无法运行：{reason}", "python -m bandit --version"
                )
            else:
                result = ScannerAvailability(
                    available=True,
                    version=version or "unknown",
                    reason="",
                    command="python -m bandit",
                )
        self._availability_cache = result
        return result

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        root = Path(target).expanduser().resolve()
        if not root.is_dir():
            raise ScannerExecutionError("Bandit 扫描目标不是有效文件夹")
        availability = self.is_available()
        if not availability.available:
            from scanners.base import ScannerUnavailable

            raise ScannerUnavailable(availability.reason)

        excludes = ".venv,.git,__pycache__,venv,env,node_modules,build,dist"
        command = [
            sys.executable,
            "-m",
            "bandit",
            "-r",
            str(root),
            "-x",
            excludes,
            "-f",
            "json",
            "-q",
        ]
        try:
            result = run_command(
                command,
                cwd=root,
                timeout_seconds=options.timeout_seconds,
                cancel_event=options.cancel_event,
                env_extra=options.env_extra,
            )
        except OSError as exc:
            raise ScannerExecutionError(f"Bandit 启动失败：{exc}") from exc
        if result.cancelled:
            raise ScanCancelled("Bandit 扫描已取消")
        if result.timed_out:
            raise ScannerTimeoutError("Bandit 扫描超时")
        if result.returncode not in (0, 1):
            detail = (result.stderr or result.stdout).strip()
            raise ScannerExecutionError(
                f"Bandit 执行失败（退出码 {result.returncode}）：{detail[:1000]}"
            )
        if not result.stdout.strip():
            raise ScannerParseError("Bandit 未返回 JSON 输出")
        findings, warnings = self.parse_output(
            result.stdout, root, availability.version
        )
        if result.output_truncated:
            warnings = (*warnings, "Bandit 输出超过捕获上限，结果可能不完整。")
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
            raise ScannerParseError(f"Bandit JSON 解析失败：{exc.msg}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise ScannerParseError("Bandit JSON 缺少 results 列表")

        findings: list[Finding] = []
        warnings: list[str] = []
        for item in payload.get("results", []):
            if not isinstance(item, dict):
                continue
            rule_id = str(item.get("test_id") or "")
            filename = self._relative_source(target, str(item.get("filename") or ""))
            if not filename:
                warnings.append("忽略不在扫描根目录内的 Bandit 结果")
                continue
            sensitive_rule = rule_id in {"B105", "B106", "B107"}
            issue_text = (
                "Bandit 检测到可能的硬编码凭据。具体值未写入结果。"
                if sensitive_rule
                else str(item.get("issue_text") or "").strip()
            )
            title = issue_text.splitlines()[0][:180] if issue_text else (
                str(item.get("test_name") or rule_id) or "Bandit finding"
            )
            line_value = item.get("line_number")
            try:
                line_number = int(line_value or 0)
            except (TypeError, ValueError):
                line_number = 0
            cwe = item.get("issue_cwe")
            cwe_text = ""
            if isinstance(cwe, dict) and cwe.get("id"):
                cwe_text = f" CWE-{cwe.get('id')}。"
            more_info = str(item.get("more_info") or "").strip()
            description = issue_text or title
            if rule_id or item.get("test_name"):
                description += f"\n\n规则：{rule_id} ({item.get('test_name') or 'unknown'})"
            if cwe_text:
                description += f"\n风险分类：{cwe_text.strip()}"
            if more_info:
                description += f"\n参考：{more_info}"
            findings.append(
                Finding(
                    title=title,
                    category=_CATEGORIES.get(rule_id, "不安全代码模式"),
                    severity=map_bandit_severity(str(item.get("issue_severity") or "")),
                    confidence=Confidence.from_external(
                        str(item.get("issue_confidence") or "")
                    ),
                    description=description,
                    file_path=filename,
                    line_number=line_number,
                    rule_id=rule_id,
                    recommendation=_RECOMMENDATIONS.get(
                        rule_id,
                        "审查该不安全模式，改用标准库中的安全 API，并补充输入校验与回归测试。",
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
                    reason = str(error.get("reason") or error.get("message") or "").strip()
                    if reason:
                        warnings.append(f"Bandit: {reason[:300]}")
                elif error:
                    warnings.append(f"Bandit: {str(error)[:300]}")
        return findings, warnings
