"""Pure, side-effect-free authorization-scope rules."""

from __future__ import annotations

import ipaddress
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from core.errors import ValidationError
from core.models.enums import AssetType, RemoteOperation

_DOMAIN_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_FORBIDDEN_HOST_CHARS = frozenset("*/\\@?#")


def normalize_domain(value: str) -> str:
    """Return a canonical exact hostname or raise ``ValidationError``.

    Wildcards, URLs, ports, paths, credentials and single-label hosts are
    rejected.  There is deliberately no suffix or wildcard expansion.
    """

    candidate = value.strip().lower()
    if not candidate:
        raise ValidationError("域名不能为空", "asset_value")
    if any(char in candidate for char in _FORBIDDEN_HOST_CHARS) or ":" in candidate:
        raise ValidationError("域名必须是精确主机名，不能包含通配符、协议、端口或路径", "asset_value")
    if candidate.endswith("."):
        candidate = candidate[:-1]
    if not candidate:
        raise ValidationError("域名无效", "asset_value")
    try:
        ascii_host = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValidationError("域名包含无效字符", "asset_value") from exc
    if len(ascii_host) > 253:
        raise ValidationError("域名长度超过 253 个字符", "asset_value")
    try:
        ipaddress.ip_address(ascii_host)
    except ValueError:
        pass
    else:
        raise ValidationError("IP 地址必须使用 IP 资产类型，不能填写为域名", "asset_value")
    labels = ascii_host.split(".")
    if len(labels) < 2:
        raise ValidationError("远程域名必须是至少包含一个点的完整域名", "asset_value")
    if any(not _DOMAIN_LABEL.match(label) for label in labels):
        raise ValidationError("域名标签格式不正确", "asset_value")
    if ascii_host == "localhost" or ascii_host.endswith(".localhost"):
        raise ValidationError("不允许将 localhost 配置为远程授权资产", "asset_value")
    return ascii_host


def normalize_ip(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValidationError("IP 地址不能为空", "asset_value")
    if "*" in candidate or "/" in candidate:
        raise ValidationError("IP 资产必须是单个精确地址，不支持通配符或网段", "asset_value")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError as exc:
        raise ValidationError("IP 地址格式不正确", "asset_value") from exc


def normalize_asset_value(asset_type: AssetType, value: str) -> str:
    if asset_type is AssetType.DOMAIN:
        return normalize_domain(value)
    if asset_type is AssetType.IP:
        return normalize_ip(value)
    return normalize_local_path(value)


def normalize_local_path(value: str) -> str:
    candidate = value.strip().strip('"')
    if not candidate:
        raise ValidationError("本地路径不能为空", "asset_value")
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        raise ValidationError("本地路径必须使用绝对路径", "asset_value")
    resolved = path.resolve(strict=False)
    return os.path.normcase(str(resolved))


def parse_allowed_operations(raw: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(raw, str):
        try:
            values = json.loads(raw or "[]")
        except ValueError as exc:
            raise ValidationError("允许操作格式无效", "allowed_operations") from exc
    else:
        values = list(raw)
    if not isinstance(values, list):
        raise ValidationError("允许操作必须是列表", "allowed_operations")
    supported = {item.value for item in RemoteOperation}
    operations: list[str] = []
    for value in values:
        text = str(value).strip()
        if text not in supported:
            raise ValidationError(f"不支持的远程检测操作: {text}", "allowed_operations")
        if text not in operations:
            operations.append(text)
    return tuple(sorted(operations))


def normalize_operations_for_asset(
    asset_type: AssetType, operations: str | list[str] | tuple[str, ...]
) -> tuple[str, ...]:
    normalized = parse_allowed_operations(operations)
    if asset_type.is_remote and not normalized:
        raise ValidationError("远程资产必须明确选择允许的检测操作", "allowed_operations")
    if not asset_type.is_remote and normalized:
        raise ValidationError("本地资产不能配置远程检测操作", "allowed_operations")
    return normalized


def serialize_allowed_operations(operations: tuple[str, ...]) -> str:
    return json.dumps(list(operations), ensure_ascii=False)


def extract_http_host(url: str) -> tuple[str, str]:
    """Extract ``(scheme, exact_host)`` from an HTTP(S) URL.

    User-info is explicitly rejected, and the host is canonicalised.  The
    caller must still perform an exact scope lookup for the returned host.
    """

    try:
        parsed = urlsplit(url.strip())
    except ValueError as exc:
        raise ValidationError("URL 格式无效", "url") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValidationError("仅支持 HTTP/HTTPS URL", "url")
    if parsed.username or parsed.password:
        raise ValidationError("URL 不允许包含用户凭据", "url")
    hostname = parsed.hostname
    if not hostname:
        raise ValidationError("URL 缺少主机名", "url")
    try:
        return parsed.scheme.lower(), normalize_ip(hostname)
    except ValidationError:
        return parsed.scheme.lower(), normalize_domain(hostname)


def check_resolution_addresses(target: str, resolved_ips: list[str] | tuple[str, ...]) -> list[str]:
    """Validate a DNS-resolution snapshot for a domain.

    All addresses must be globally routable and the snapshot must not be empty.
    Private, loopback, link-local, reserved and multicast answers are rejected
    to reduce DNS-rebinding and SSRF exposure.  The function never resolves DNS
    itself.
    """

    if not resolved_ips:
        raise ValidationError("DNS 复核结果为空，拒绝继续", "resolved_ips")
    errors: list[str] = []
    target_ip: str | None = None
    try:
        target_ip = normalize_ip(target)
    except ValidationError:
        target_ip = None
    addresses: list[str] = []
    for raw in resolved_ips:
        try:
            address = ipaddress.ip_address(str(raw).strip())
        except ValueError:
            errors.append(f"无效 IP: {raw}")
            continue
        if not address.is_global:
            errors.append(f"非公网地址: {address}")
        if target_ip is not None and str(address) != target_ip:
            errors.append(f"解析地址与目标 IP 不一致: {address}")
        addresses.append(str(address))
    if not addresses:
        errors.append("没有有效解析地址")
    if target_ip is not None and target_ip not in addresses:
        errors.append("目标 IP 不在解析结果中")
    return errors
