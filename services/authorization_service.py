"""Authorization record lifecycle, validity and change history."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from core.errors import ConflictError, NotFoundError, ValidationError
from core.models import Authorization, AuthorizationHistory, AuthStatus
from core.timeutil import ensure_aware_utc, from_db_time, to_db_time, utc_now
from database.connection import Database
from services.audit_service import AuditLogService


class AuthorizationService:
    """All authorization reads and writes are project-scoped.

    ``confirmed`` alone is not enough: an authorization is effective only when
    its status is confirmed and the current time is inside its interval.
    """

    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._clock = clock

    def now(self) -> datetime:
        """Expose the service clock so UI validity labels stay consistent."""

        return self._clock()

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _coerce_status(value: AuthStatus | str) -> AuthStatus:
        if isinstance(value, AuthStatus):
            return value
        try:
            return AuthStatus(str(value))
        except ValueError as exc:
            raise ValidationError("授权状态无效", "authorization_status") from exc

    @staticmethod
    def _normalize_times(
        start_time: datetime, end_time: datetime
    ) -> tuple[datetime, datetime]:
        try:
            start = ensure_aware_utc(start_time)
            end = ensure_aware_utc(end_time)
        except (TypeError, ValueError) as exc:
            raise ValidationError("授权起止时间必须包含时区", "time_range") from exc
        if end <= start:
            raise ValidationError("授权结束时间必须晚于开始时间", "time_range")
        return start, end

    @staticmethod
    def _validate_source(value: str) -> str:
        source = str(value or "").strip()
        if not source:
            raise ValidationError("授权来源不能为空", "authorization_source")
        if len(source) > 500:
            raise ValidationError("授权来源不能超过 500 个字符", "authorization_source")
        return source

    @staticmethod
    def _validate_document(value: str) -> str:
        document = str(value or "").strip()
        if len(document) > 2000:
            raise ValidationError("授权文件路径过长", "authorization_document")
        return document

    def _validate_status_requirements(
        self,
        status: AuthStatus,
        source: str,
        document: str,
        end: datetime,
    ) -> None:
        if status is AuthStatus.CONFIRMED:
            if not source:
                raise ValidationError("确认授权必须填写授权来源", "authorization_source")
            if not document:
                raise ValidationError("确认授权必须填写授权文件路径", "authorization_document")
            if end <= ensure_aware_utc(self._clock()):
                raise ValidationError("不能把已过期的授权设置为已确认", "time_range")

    def _scoped_row(self, conn, project_id: int, authorization_id: int):
        return conn.execute(
            "SELECT * FROM authorizations WHERE authorization_id = ? AND project_id = ?",
            (authorization_id, project_id),
        ).fetchone()

    def _record_history(
        self,
        conn,
        *,
        project_id: int,
        authorization_id: int | None,
        action: str,
        summary: str,
        details: dict[str, Any],
        now: datetime,
    ) -> None:
        conn.execute(
            "INSERT INTO authorization_history "
            "(project_id, authorization_id, action, change_summary, details_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                project_id,
                authorization_id,
                action,
                summary,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                to_db_time(now),
            ),
        )
        self._audit.record(
            event_type="authorization_change",
            target=f"authorization:{authorization_id or 'deleted'}",
            operation=action,
            decision="info",
            message=summary,
            details=details,
            project_id=project_id,
            conn=conn,
            created_at=now,
        )

    # ------------------------------------------------------------------ create
    def create_authorization(
        self,
        project_id: int,
        *,
        authorization_source: str,
        authorization_document: str = "",
        start_time: datetime,
        end_time: datetime,
        authorization_status: AuthStatus | str = AuthStatus.PENDING,
        notes: str = "",
    ) -> Authorization:
        if self._db.fetch_one("SELECT 1 FROM projects WHERE project_id = ?", (project_id,)) is None:
            raise NotFoundError("项目不存在，无法添加授权")
        source = self._validate_source(authorization_source)
        document = self._validate_document(authorization_document)
        start, end = self._normalize_times(start_time, end_time)
        status = self._coerce_status(authorization_status)
        self._validate_status_requirements(status, source, document, end)
        now = self._clock()
        stamp = to_db_time(now)
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO authorizations "
                "(project_id, authorization_source, authorization_document, start_time, end_time, "
                "authorization_status, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    project_id,
                    source,
                    document,
                    to_db_time(start),
                    to_db_time(end),
                    status.value,
                    str(notes or "").strip(),
                    stamp,
                    stamp,
                ),
            )
            authorization_id = int(cursor.lastrowid or 0)
            self._record_history(
                conn,
                project_id=project_id,
                authorization_id=authorization_id,
                action="created",
                summary=f"新增授权 #{authorization_id}（{status.label}）",
                details={
                    "authorization_id": authorization_id,
                    "status": status.value,
                    "start_time": to_db_time(start),
                    "end_time": to_db_time(end),
                },
                now=now,
            )
        return self.get_authorization(project_id, authorization_id)

    # ------------------------------------------------------------------ update
    def update_authorization(
        self,
        project_id: int,
        authorization_id: int,
        *,
        authorization_source: str,
        authorization_document: str = "",
        start_time: datetime,
        end_time: datetime,
        authorization_status: AuthStatus | str,
        notes: str = "",
    ) -> Authorization:
        source = self._validate_source(authorization_source)
        document = self._validate_document(authorization_document)
        start, end = self._normalize_times(start_time, end_time)
        status = self._coerce_status(authorization_status)
        self._validate_status_requirements(status, source, document, end)
        now = self._clock()
        with self._db.transaction() as conn:
            row = self._scoped_row(conn, project_id, authorization_id)
            if row is None:
                raise NotFoundError("授权记录不存在或不属于当前项目")
            old = Authorization.from_row(row)
            if old.authorization_status is AuthStatus.REVOKED:
                raise ConflictError("已撤销的授权不可修改；如需重新授权，请新增授权记录")
            before = {
                "authorization_source": old.authorization_source,
                "authorization_document": old.authorization_document,
                "start_time": to_db_time(old.start_time),
                "end_time": to_db_time(old.end_time),
                "authorization_status": old.authorization_status.value,
                "notes": old.notes,
            }
            after = {
                "authorization_source": source,
                "authorization_document": document,
                "start_time": to_db_time(start),
                "end_time": to_db_time(end),
                "authorization_status": status.value,
                "notes": str(notes or "").strip(),
            }
            conn.execute(
                "UPDATE authorizations SET authorization_source = ?, "
                "authorization_document = ?, start_time = ?, end_time = ?, "
                "authorization_status = ?, notes = ?, updated_at = ? "
                "WHERE authorization_id = ? AND project_id = ?",
                (
                    source,
                    document,
                    to_db_time(start),
                    to_db_time(end),
                    status.value,
                    str(notes or "").strip(),
                    to_db_time(now),
                    authorization_id,
                    project_id,
                ),
            )
            action = "revoked" if status is AuthStatus.REVOKED else "updated"
            summary = (
                f"撤销授权 #{authorization_id}"
                if action == "revoked"
                else f"修改授权 #{authorization_id}"
            )
            self._record_history(
                conn,
                project_id=project_id,
                authorization_id=authorization_id,
                action=action,
                summary=summary,
                details={"before": before, "after": after},
                now=now,
            )
        return self.get_authorization(project_id, authorization_id)

    def revoke_authorization(self, project_id: int, authorization_id: int) -> Authorization:
        auth = self.get_authorization(project_id, authorization_id)
        if auth.authorization_status is AuthStatus.REVOKED:
            raise ConflictError("该授权已撤销")
        return self.update_authorization(
            project_id,
            authorization_id,
            authorization_source=auth.authorization_source,
            authorization_document=auth.authorization_document,
            start_time=auth.start_time,
            end_time=auth.end_time,
            authorization_status=AuthStatus.REVOKED,
            notes=auth.notes,
        )

    # ------------------------------------------------------------------ delete
    def delete_authorization(self, project_id: int, authorization_id: int) -> None:
        now = self._clock()
        with self._db.transaction() as conn:
            row = self._scoped_row(conn, project_id, authorization_id)
            if row is None:
                raise NotFoundError("授权记录不存在或不属于当前项目")
            auth = Authorization.from_row(row)
            asset = conn.execute(
                "SELECT asset_value FROM scope_assets WHERE authorization_id = ? LIMIT 1",
                (authorization_id,),
            ).fetchone()
            if asset is not None:
                raise ConflictError("该授权仍关联授权资产，请先删除或改绑资产后再删除授权")
            self._record_history(
                conn,
                project_id=project_id,
                authorization_id=authorization_id,
                action="deleted",
                summary=f"删除授权 #{authorization_id}",
                details={"authorization_id": authorization_id, "source": auth.authorization_source},
                now=now,
            )
            conn.execute(
                "DELETE FROM authorizations WHERE authorization_id = ? AND project_id = ?",
                (authorization_id, project_id),
            )

    # ------------------------------------------------------------------ query
    def get_authorization(self, project_id: int, authorization_id: int) -> Authorization:
        row = self._db.fetch_one(
            "SELECT * FROM authorizations WHERE authorization_id = ? AND project_id = ?",
            (authorization_id, project_id),
        )
        if row is None:
            raise NotFoundError("授权记录不存在或不属于当前项目")
        return Authorization.from_row(row)

    def list_authorizations(self, project_id: int) -> list[Authorization]:
        rows = self._db.fetch_all(
            "SELECT * FROM authorizations WHERE project_id = ? "
            "ORDER BY end_time DESC, authorization_id DESC",
            (project_id,),
        )
        return [Authorization.from_row(row) for row in rows]

    def list_history(
        self, project_id: int, authorization_id: int | None = None, limit: int = 100
    ) -> list[AuthorizationHistory]:
        safe_limit = max(1, min(int(limit), 500))
        if authorization_id is None:
            rows = self._db.fetch_all(
                "SELECT * FROM authorization_history WHERE project_id = ? "
                "ORDER BY created_at DESC, history_id DESC LIMIT ?",
                (project_id, safe_limit),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM authorization_history WHERE project_id = ? "
                "AND authorization_id = ? ORDER BY created_at DESC, history_id DESC LIMIT ?",
                (project_id, authorization_id, safe_limit),
            )
        return [AuthorizationHistory.from_row(row) for row in rows]

    def is_effective(
        self, project_id: int, authorization_id: int, at: datetime | None = None
    ) -> bool:
        auth = self.get_authorization(project_id, authorization_id)
        return auth.is_effective(at or self._clock())

    def count_effective(self, project_id: int | None = None) -> int:
        moment = to_db_time(self._clock())
        sql = (
            "SELECT COUNT(*) AS count FROM authorizations WHERE authorization_status = 'confirmed' "
            "AND start_time <= ? AND end_time >= ?"
        )
        if project_id is None:
            row = self._db.fetch_one(sql, (moment, moment))
        else:
            row = self._db.fetch_one(sql + " AND project_id = ?", (moment, moment, project_id))
        return int(row["count"]) if row else 0

    def count_expiring_soon(self, days: int = 7, project_id: int | None = None) -> int:
        now = self._clock()
        end = now.timestamp() + max(0, int(days)) * 86400
        end_stamp = to_db_time(datetime.fromtimestamp(end, tz=now.tzinfo))
        now_stamp = to_db_time(now)
        sql = (
            "SELECT COUNT(*) AS count FROM authorizations WHERE authorization_status = 'confirmed' "
            "AND start_time <= ? AND end_time >= ? AND end_time <= ?"
        )
        params: list[Any] = [now_stamp, now_stamp, end_stamp]
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        row = self._db.fetch_one(sql, params)
        return int(row["count"]) if row else 0

    def expire_overdue_authorizations(self, project_id: int | None = None) -> int:
        """Persist ``expired`` for confirmed rows whose end time has passed.

        Remote checks still inspect timestamps themselves; this method keeps the
        UI status aligned with reality and records a history entry.
        """

        now = self._clock()
        stamp = to_db_time(now)
        params: list[Any] = [stamp]
        sql = (
            "SELECT * FROM authorizations WHERE authorization_status = 'confirmed' "
            "AND end_time < ?"
        )
        if project_id is not None:
            sql += " AND project_id = ?"
            params.append(project_id)
        rows = self._db.fetch_all(sql, params)
        if not rows:
            return 0
        with self._db.transaction() as conn:
            for row in rows:
                auth = Authorization.from_row(row)
                conn.execute(
                    "UPDATE authorizations SET authorization_status = 'expired', updated_at = ? "
                    "WHERE authorization_id = ? AND authorization_status = 'confirmed'",
                    (stamp, auth.authorization_id),
                )
                self._record_history(
                    conn,
                    project_id=auth.project_id,
                    authorization_id=auth.authorization_id,
                    action="expired",
                    summary=f"授权 #{auth.authorization_id} 已到期",
                    details={"authorization_id": auth.authorization_id, "end_time": to_db_time(auth.end_time)},
                    now=now,
                )
        return len(rows)

    @staticmethod
    def parse_time(value: str | datetime) -> datetime:
        if isinstance(value, datetime):
            return ensure_aware_utc(value)
        return from_db_time(value)
