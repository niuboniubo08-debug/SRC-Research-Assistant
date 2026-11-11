"""Fail-closed authorization scope validation.

Every call records an ``authorization_check`` event.  If audit storage is
unavailable the result is converted to a denial, including for otherwise
allowed requests.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from core.errors import AuthorizationDenied, StorageError, ValidationError
from core.models import AssetStatus, AssetType, AuthStatus, RemoteOperation
from core.timeutil import ensure_aware_utc, from_db_time, local_display, utc_now
from database.connection import Database
from security.scope_rules import (
    check_resolution_addresses,
    extract_http_host,
    normalize_domain,
    normalize_ip,
    normalize_local_path,
)
from services.audit_service import AuditLogService


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    code: str
    reason: str
    project_id: int | None
    target: str
    operation: str
    checked_at: datetime
    asset_id: int | None = None
    authorization_id: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def checked_at_display(self) -> str:
        return local_display(self.checked_at, with_seconds=True)


class ScopeValidator:
    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._clock = clock

    # ------------------------------------------------------------------ utilities
    @staticmethod
    def _target_kind(target: str) -> tuple[AssetType, str]:
        raw = str(target or "").strip()
        if not raw:
            raise ValidationError("检测目标不能为空", "target")
        if "://" in raw:
            raise ValidationError("检测目标必须是精确主机名或 IP，不能是 URL", "target")
        try:
            return AssetType.IP, normalize_ip(raw)
        except ValidationError:
            pass
        try:
            return AssetType.DOMAIN, normalize_domain(raw)
        except ValidationError as exc:
            raise ValidationError(f"检测目标无效: {exc.message}", "target") from exc

    def _finish(
        self,
        decision: AccessDecision,
        *,
        log_project_id: int | None,
        extra: dict[str, Any] | None = None,
    ) -> AccessDecision:
        details = {
            "code": decision.code,
            "asset_id": decision.asset_id,
            "authorization_id": decision.authorization_id,
            "target": decision.target,
            "operation": decision.operation,
            "checked_at": decision.checked_at.isoformat(),
        }
        details.update(extra or {})
        try:
            self._audit.record(
                event_type="authorization_check",
                target=decision.target,
                operation=decision.operation,
                decision="allow" if decision.allowed else "deny",
                message=decision.reason,
                details=details,
                project_id=log_project_id,
                created_at=decision.checked_at,
            )
        except StorageError:
            if decision.allowed:
                return replace(
                    decision,
                    allowed=False,
                    code="audit_unavailable",
                    reason="审计日志不可用，按默认拒绝策略终止操作",
                )
        return decision

    def _deny(
        self,
        *,
        code: str,
        reason: str,
        project_id: int | None,
        target: str,
        operation: str,
        at: datetime,
        asset_id: int | None = None,
        authorization_id: int | None = None,
        log_project_id: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AccessDecision:
        decision = AccessDecision(
            allowed=False,
            code=code,
            reason=reason,
            project_id=project_id,
            target=target,
            operation=operation,
            checked_at=at,
            asset_id=asset_id,
            authorization_id=authorization_id,
        )
        return self._finish(decision, log_project_id=log_project_id, extra=extra)

    # ------------------------------------------------------------------ remote
    def check_remote_access(
        self,
        project_id: int,
        target: str,
        operation: str,
        *,
        at: datetime | None = None,
        resolved_ips: list[str] | tuple[str, ...] | None = None,
    ) -> AccessDecision:
        moment = ensure_aware_utc(at or self._clock())
        clean_target = str(target or "").strip()[:512]
        clean_operation = str(operation or "").strip()
        project_row = self._db.fetch_one(
            "SELECT project_id FROM projects WHERE project_id = ?", (int(project_id),)
        )
        if project_row is None:
            return self._deny(
                code="project_not_found",
                reason="项目不存在，拒绝执行",
                project_id=int(project_id),
                target=clean_target,
                operation=clean_operation,
                at=moment,
                log_project_id=None,
                extra={"requested_project_id": int(project_id)},
            )
        actual_project_id = int(project_row["project_id"])

        try:
            remote_operation = RemoteOperation(clean_operation)
        except ValueError:
            return self._deny(
                code="unsupported_operation",
                reason="未支持的检测操作，拒绝执行",
                project_id=actual_project_id,
                target=clean_target,
                operation=clean_operation,
                at=moment,
                log_project_id=actual_project_id,
            )

        try:
            asset_kind, normalized_target = self._target_kind(clean_target)
        except ValidationError as exc:
            return self._deny(
                code="invalid_target",
                reason=exc.message,
                project_id=actual_project_id,
                target=clean_target,
                operation=remote_operation.value,
                at=moment,
                log_project_id=actual_project_id,
            )

        rows = self._db.fetch_all(
            "SELECT * FROM scope_assets WHERE project_id = ? AND asset_value = ? "
            "AND asset_type IN ('domain', 'ip')",
            (actual_project_id, normalized_target),
        )
        if not rows:
            return self._deny(
                code="target_not_in_scope",
                reason="目标不在该项目的明确授权资产范围内",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                log_project_id=actual_project_id,
            )

        asset = None
        for row in rows:
            if str(row["asset_type"]) == asset_kind.value:
                asset = row
                break
        if asset is None:
            return self._deny(
                code="target_not_in_scope",
                reason="目标类型与已授权资产不匹配",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                log_project_id=actual_project_id,
            )
        if str(asset["asset_status"]) != AssetStatus.ACTIVE.value:
            return self._deny(
                code="asset_inactive",
                reason="授权资产已停用，拒绝执行",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=int(asset["asset_id"]),
                log_project_id=actual_project_id,
            )

        authorization_id = (
            int(asset["authorization_id"]) if asset["authorization_id"] is not None else None
        )
        if authorization_id is None:
            return self._deny(
                code="missing_authorization",
                reason="授权资产未绑定授权记录，拒绝执行",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=int(asset["asset_id"]),
                log_project_id=actual_project_id,
            )

        auth_row = self._db.fetch_one(
            "SELECT * FROM authorizations WHERE authorization_id = ? AND project_id = ?",
            (authorization_id, actual_project_id),
        )
        asset_id = int(asset["asset_id"])
        if auth_row is None:
            return self._deny(
                code="authorization_not_found",
                reason="关联的授权记录不存在或不属于当前项目，拒绝执行",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=asset_id,
                authorization_id=authorization_id,
                log_project_id=actual_project_id,
            )

        status = AuthStatus(str(auth_row["authorization_status"]))
        source = str(auth_row["authorization_source"] or "").strip()
        document = str(auth_row["authorization_document"] or "").strip()
        start_time = from_db_time(str(auth_row["start_time"]))
        end_time = from_db_time(str(auth_row["end_time"]))
        base_extra = {
            "authorization_status": status.value,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "asset_type": str(asset["asset_type"]),
        }
        if status is AuthStatus.REVOKED:
            code, reason = "authorization_revoked", "授权已撤销，立即拒绝远程检测"
        elif status is AuthStatus.PENDING:
            code, reason = "authorization_pending", "授权尚待审核，不得执行远程检测"
        elif status is AuthStatus.EXPIRED or moment > end_time:
            code, reason = "authorization_expired", "授权已过期，拒绝远程检测"
        elif moment < start_time:
            code, reason = "authorization_not_started", "授权尚未生效，拒绝远程检测"
        elif not source or not document:
            code, reason = "authorization_incomplete", "授权来源或授权文件缺失，拒绝远程检测"
        else:
            code, reason = "", ""

        if code:
            return self._deny(
                code=code,
                reason=reason,
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=asset_id,
                authorization_id=authorization_id,
                log_project_id=actual_project_id,
                extra=base_extra,
            )

        try:
            allowed_operations = tuple(json.loads(str(asset["allowed_operations"] or "[]")))
        except (ValueError, TypeError):
            allowed_operations = ()
        if remote_operation.value not in allowed_operations:
            return self._deny(
                code="operation_not_allowed",
                reason="该资产未明确授权此检测操作，拒绝执行",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=asset_id,
                authorization_id=authorization_id,
                log_project_id=actual_project_id,
                extra=base_extra,
            )

        dns_errors: list[str] = []
        if resolved_ips is not None:
            try:
                dns_errors = check_resolution_addresses(normalized_target, resolved_ips)
            except ValidationError as exc:
                dns_errors = [exc.message]
        if dns_errors:
            return self._deny(
                code="dns_scope_review_failed",
                reason="DNS/IP 复核未通过，拒绝执行",
                project_id=actual_project_id,
                target=normalized_target,
                operation=remote_operation.value,
                at=moment,
                asset_id=asset_id,
                authorization_id=authorization_id,
                log_project_id=actual_project_id,
                extra={**base_extra, "dns_errors": dns_errors,
                       "resolved_ips": list(resolved_ips or [])},
            )

        allowed = AccessDecision(
            allowed=True,
            code="allowed",
            reason="目标在明确授权范围内，授权有效",
            project_id=actual_project_id,
            target=normalized_target,
            operation=remote_operation.value,
            checked_at=moment,
            asset_id=asset_id,
            authorization_id=authorization_id,
            details={
                "authorization_status": status.value,
                "dns_reviewed": resolved_ips is not None,
            },
        )
        return self._finish(
            allowed,
            log_project_id=actual_project_id,
            extra={
                **base_extra,
                "dns_reviewed": resolved_ips is not None,
                "resolved_ips": list(resolved_ips or []),
            },
        )

    def require_remote_access(
        self,
        project_id: int,
        target: str,
        operation: str,
        *,
        at: datetime | None = None,
        resolved_ips: list[str] | tuple[str, ...] | None = None,
    ) -> AccessDecision:
        decision = self.check_remote_access(
            project_id, target, operation, at=at, resolved_ips=resolved_ips
        )
        if not decision.allowed:
            raise AuthorizationDenied(decision.reason, decision.code, decision)
        return decision

    # ------------------------------------------------------------------ redirects
    def check_redirect_target(
        self,
        project_id: int,
        source_url: str,
        redirect_url: str,
        operation: str,
        *,
        at: datetime | None = None,
    ) -> AccessDecision:
        """Validate both sides of a redirect.

        This app never follows redirects automatically.  A future HTTP checker
        must call this method and stop when either decision is a denial.
        """

        try:
            _, source_host = extract_http_host(source_url)
        except ValidationError as exc:
            return self._deny(
                code="invalid_redirect_source",
                reason=f"重定向来源无效: {exc.message}",
                project_id=int(project_id),
                target=source_url[:512],
                operation=operation,
                at=ensure_aware_utc(at or self._clock()),
                log_project_id=None,
            )
        source_decision = self.check_remote_access(project_id, source_host, operation, at=at)
        if not source_decision.allowed:
            return source_decision
        try:
            _, target_host = extract_http_host(redirect_url)
        except ValidationError as exc:
            return self._deny(
                code="invalid_redirect_target",
                reason=f"重定向目标无效: {exc.message}",
                project_id=int(project_id),
                target=redirect_url[:512],
                operation=operation,
                at=ensure_aware_utc(at or self._clock()),
                log_project_id=int(project_id),
            )
        # The redirect destination must pass exactly the same scope checks.
        return self.check_remote_access(project_id, target_host, operation, at=at)

    # ------------------------------------------------------------------ local
    def check_local_path(
        self,
        project_id: int,
        path: str,
        operation: str = "local_audit",
        *,
        at: datetime | None = None,
    ) -> AccessDecision:
        moment = ensure_aware_utc(at or self._clock())
        project_row = self._db.fetch_one(
            "SELECT project_id FROM projects WHERE project_id = ?", (int(project_id),)
        )
        if project_row is None:
            return self._deny(
                code="project_not_found",
                reason="项目不存在，拒绝执行",
                project_id=int(project_id),
                target=str(path or "")[:512],
                operation=operation,
                at=moment,
                log_project_id=None,
            )
        try:
            normalized = normalize_local_path(path)
        except ValidationError as exc:
            return self._deny(
                code="invalid_local_path",
                reason=exc.message,
                project_id=int(project_id),
                target=str(path or "")[:512],
                operation=operation,
                at=moment,
                log_project_id=int(project_id),
            )
        candidate = Path(normalized)
        try:
            if not candidate.exists():
                return self._deny(
                    code="local_path_not_found",
                    reason="本地路径不存在，拒绝扫描",
                    project_id=int(project_id),
                    target=normalized,
                    operation=operation,
                    at=moment,
                    log_project_id=int(project_id),
                )
            if not candidate.is_dir():
                return self._deny(
                    code="local_path_not_directory",
                    reason="本地扫描目标必须是文件夹",
                    project_id=int(project_id),
                    target=normalized,
                    operation=operation,
                    at=moment,
                    log_project_id=int(project_id),
                )
            if not os.access(candidate, os.R_OK):
                return self._deny(
                    code="local_path_permission_denied",
                    reason="没有读取本地路径的权限，拒绝扫描",
                    project_id=int(project_id),
                    target=normalized,
                    operation=operation,
                    at=moment,
                    log_project_id=int(project_id),
                )
        except OSError:
            return self._deny(
                code="local_path_inaccessible",
                reason="本地路径不可访问，拒绝扫描",
                project_id=int(project_id),
                target=normalized,
                operation=operation,
                at=moment,
                log_project_id=int(project_id),
            )

        row = self._db.fetch_one(
            "SELECT * FROM scope_assets WHERE project_id = ? AND asset_value = ? "
            "AND asset_type IN ('local_folder', 'local_project')",
            (int(project_id), normalized),
        )
        if row is None:
            return self._deny(
                code="local_target_not_in_scope",
                reason="本地路径不在该项目已授权的本地资产范围内",
                project_id=int(project_id),
                target=normalized,
                operation=operation,
                at=moment,
                log_project_id=int(project_id),
            )
        if str(row["asset_status"]) != AssetStatus.ACTIVE.value:
            return self._deny(
                code="asset_inactive",
                reason="本地授权资产已停用，拒绝执行",
                project_id=int(project_id),
                target=normalized,
                operation=operation,
                at=moment,
                asset_id=int(row["asset_id"]),
                log_project_id=int(project_id),
            )
        decision = AccessDecision(
            allowed=True,
            code="allowed",
            reason="本地路径在明确授权范围内",
            project_id=int(project_id),
            target=normalized,
            operation=operation,
            checked_at=moment,
            asset_id=int(row["asset_id"]),
            details={"local": True},
        )
        return self._finish(decision, log_project_id=int(project_id), extra={"local": True})
