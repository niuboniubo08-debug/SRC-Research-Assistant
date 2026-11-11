"""Authorization-scope asset CRUD with backend ownership checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.errors import ConflictError, NotFoundError, ValidationError
from core.models import (
    AssetStatus,
    AssetType,
    Authorization,
    ScopeAsset,
)
from core.timeutil import to_db_time, utc_now
from database.connection import Database
from security.scope_rules import (
    normalize_asset_value,
    normalize_operations_for_asset,
    serialize_allowed_operations,
)
from services.audit_service import AuditLogService
from services.authorization_service import AuthorizationService


class ScopeAssetService:
    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        authorization_service: AuthorizationService,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._authorizations = authorization_service
        self._clock = clock

    @staticmethod
    def _coerce_type(value: AssetType | str) -> AssetType:
        if isinstance(value, AssetType):
            return value
        try:
            return AssetType(str(value))
        except ValueError as exc:
            raise ValidationError("资产类型无效", "asset_type") from exc

    @staticmethod
    def _coerce_status(value: AssetStatus | str) -> AssetStatus:
        if isinstance(value, AssetStatus):
            return value
        try:
            return AssetStatus(str(value))
        except ValueError as exc:
            raise ValidationError("资产状态无效", "asset_status") from exc

    def _validate(self, project_id: int, asset_type: AssetType, value: str) -> str:
        if self._db.fetch_one("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)) is None:
            raise NotFoundError("项目不存在，无法管理授权资产")
        normalized = normalize_asset_value(asset_type, value)
        if not asset_type.is_remote:
            path = Path(normalized)
            if not path.is_dir():
                raise ValidationError("本地资产路径不存在或不是文件夹", "asset_value")
        return normalized

    def _resolve_remote_authorization(
        self, project_id: int, authorization_id: int | None
    ) -> Authorization:
        if authorization_id is None:
            raise ValidationError("远程资产必须关联授权记录", "authorization_id")
        auth = self._authorizations.get_authorization(project_id, authorization_id)
        if not auth.is_effective(self._clock()):
            raise ValidationError("远程资产必须关联当前有效的已确认授权", "authorization_id")
        return auth

    def _ensure_unique(
        self,
        project_id: int,
        asset_type: AssetType,
        normalized_value: str,
        exclude_asset_id: int | None = None,
    ) -> None:
        sql = (
            "SELECT asset_id FROM scope_assets WHERE project_id = ? AND asset_type = ? "
            "AND asset_value = ?"
        )
        params: list[Any] = [project_id, asset_type.value, normalized_value]
        if exclude_asset_id is not None:
            sql += " AND asset_id <> ?"
            params.append(exclude_asset_id)
        row = self._db.fetch_one(sql, params)
        if row is not None:
            raise ConflictError("同一项目内已存在相同类型和值的授权资产")

    def create_asset(
        self,
        project_id: int,
        *,
        asset_type: AssetType | str,
        asset_value: str,
        authorization_id: int | None = None,
        allowed_operations: tuple[str, ...] | list[str] | str = (),
        asset_status: AssetStatus | str = AssetStatus.ACTIVE,
        notes: str = "",
    ) -> ScopeAsset:
        kind = self._coerce_type(asset_type)
        status = self._coerce_status(asset_status)
        normalized = self._validate(project_id, kind, asset_value)
        operations = normalize_operations_for_asset(kind, allowed_operations)
        if kind.is_remote:
            auth = self._resolve_remote_authorization(project_id, authorization_id)
            auth_id: int | None = auth.authorization_id
        else:
            if authorization_id is not None:
                raise ValidationError("本地资产不应绑定远程授权记录", "authorization_id")
            if operations:
                raise ValidationError("本地资产不能配置远程检测操作", "allowed_operations")
            auth_id = None
        self._ensure_unique(project_id, kind, normalized)
        now = self._clock()
        stamp = to_db_time(now)
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO scope_assets "
                "(project_id, asset_type, asset_value, authorization_id, allowed_operations, "
                "asset_status, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    kind.value,
                    normalized,
                    auth_id,
                    serialize_allowed_operations(operations),
                    status.value,
                    str(notes or "").strip(),
                    stamp,
                    stamp,
                ),
            )
            asset_id = int(cursor.lastrowid or 0)
            self._audit.record(
                event_type="scope_asset_change",
                target=normalized,
                operation="create_scope_asset",
                decision="info",
                message=f"新增授权资产 #{asset_id}（{kind.label}）",
                details={
                    "asset_id": asset_id,
                    "asset_type": kind.value,
                    "authorization_id": auth_id,
                    "operations": list(operations),
                },
                project_id=project_id,
                conn=conn,
                created_at=now,
            )
        return self.get_asset(project_id, asset_id)

    def update_asset(
        self,
        project_id: int,
        asset_id: int,
        *,
        asset_type: AssetType | str,
        asset_value: str,
        authorization_id: int | None = None,
        allowed_operations: tuple[str, ...] | list[str] | str = (),
        asset_status: AssetStatus | str = AssetStatus.ACTIVE,
        notes: str = "",
    ) -> ScopeAsset:
        kind = self._coerce_type(asset_type)
        status = self._coerce_status(asset_status)
        normalized = self._validate(project_id, kind, asset_value)
        operations = normalize_operations_for_asset(kind, allowed_operations)
        if kind.is_remote:
            auth = self._resolve_remote_authorization(project_id, authorization_id)
            auth_id: int | None = auth.authorization_id
        else:
            if authorization_id is not None:
                raise ValidationError("本地资产不应绑定远程授权记录", "authorization_id")
            auth_id = None
        self._ensure_unique(project_id, kind, normalized, exclude_asset_id=asset_id)
        now = self._clock()
        with self._db.transaction() as conn:
            old_row = conn.execute(
                "SELECT * FROM scope_assets WHERE asset_id = ? AND project_id = ?",
                (asset_id, project_id),
            ).fetchone()
            if old_row is None:
                raise NotFoundError("授权资产不存在或不属于当前项目")
            old = ScopeAsset.from_row(old_row)
            conn.execute(
                "UPDATE scope_assets SET asset_type = ?, asset_value = ?, authorization_id = ?, "
                "allowed_operations = ?, asset_status = ?, notes = ?, updated_at = ? "
                "WHERE asset_id = ? AND project_id = ?",
                (
                    kind.value,
                    normalized,
                    auth_id,
                    serialize_allowed_operations(operations),
                    status.value,
                    str(notes or "").strip(),
                    to_db_time(now),
                    asset_id,
                    project_id,
                ),
            )
            self._audit.record(
                event_type="scope_asset_change",
                target=normalized,
                operation="update_scope_asset",
                decision="info",
                message=f"修改授权资产 #{asset_id}",
                details={
                    "asset_id": asset_id,
                    "before": {
                        "asset_type": old.asset_type.value,
                        "asset_value": old.asset_value,
                        "authorization_id": old.authorization_id,
                        "operations": list(old.allowed_operations),
                        "status": old.asset_status.value,
                    },
                    "after": {
                        "asset_type": kind.value,
                        "asset_value": normalized,
                        "authorization_id": auth_id,
                        "operations": list(operations),
                        "status": status.value,
                    },
                },
                project_id=project_id,
                conn=conn,
                created_at=now,
            )
        return self.get_asset(project_id, asset_id)

    def delete_asset(self, project_id: int, asset_id: int) -> None:
        now = self._clock()
        with self._db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM scope_assets WHERE asset_id = ? AND project_id = ?",
                (asset_id, project_id),
            ).fetchone()
            if row is None:
                raise NotFoundError("授权资产不存在或不属于当前项目")
            asset = ScopeAsset.from_row(row)
            self._audit.record(
                event_type="scope_asset_change",
                target=asset.asset_value,
                operation="delete_scope_asset",
                decision="info",
                message=f"删除授权资产 #{asset_id}",
                details={"asset_id": asset_id, "asset_type": asset.asset_type.value},
                project_id=project_id,
                conn=conn,
                created_at=now,
            )
            conn.execute(
                "DELETE FROM scope_assets WHERE asset_id = ? AND project_id = ?",
                (asset_id, project_id),
            )

    def get_asset(self, project_id: int, asset_id: int) -> ScopeAsset:
        row = self._db.fetch_one(
            "SELECT * FROM scope_assets WHERE asset_id = ? AND project_id = ?",
            (asset_id, project_id),
        )
        if row is None:
            raise NotFoundError("授权资产不存在或不属于当前项目")
        return ScopeAsset.from_row(row)

    def list_assets(
        self,
        project_id: int,
        asset_type: AssetType | str | None = None,
        status: AssetStatus | str | None = None,
    ) -> list[ScopeAsset]:
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]
        if asset_type is not None:
            clauses.append("asset_type = ?")
            params.append(self._coerce_type(asset_type).value)
        if status is not None:
            clauses.append("asset_status = ?")
            params.append(self._coerce_status(status).value)
        rows = self._db.fetch_all(
            f"SELECT * FROM scope_assets WHERE {' AND '.join(clauses)} "
            "ORDER BY asset_type, asset_value",
            params,
        )
        return [ScopeAsset.from_row(row) for row in rows]

    def count_assets(self, project_id: int | None = None) -> int:
        if project_id is None:
            row = self._db.fetch_one("SELECT COUNT(*) AS count FROM scope_assets")
        else:
            row = self._db.fetch_one(
                "SELECT COUNT(*) AS count FROM scope_assets WHERE project_id = ?", (project_id,)
            )
        return int(row["count"]) if row else 0

    @staticmethod
    def operations_display(asset: ScopeAsset) -> str:
        if not asset.allowed_operations:
            return "—"
        names = {
            "config_check": "非破坏性配置检查",
        }
        return "、".join(names.get(item, item) for item in asset.allowed_operations)
