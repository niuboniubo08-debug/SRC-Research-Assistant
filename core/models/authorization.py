"""Authorization and authorization-history domain models."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.models.enums import AuthStatus
from core.timeutil import ensure_aware_utc, from_db_time, utc_now


@dataclass(frozen=True, slots=True)
class Authorization:
    authorization_id: int
    project_id: int
    authorization_source: str
    authorization_document: str
    start_time: datetime
    end_time: datetime
    authorization_status: AuthStatus
    notes: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Authorization":
        return cls(
            authorization_id=int(row["authorization_id"]),
            project_id=int(row["project_id"]),
            authorization_source=str(row["authorization_source"]),
            authorization_document=str(row["authorization_document"] or ""),
            start_time=from_db_time(str(row["start_time"])),
            end_time=from_db_time(str(row["end_time"])),
            authorization_status=AuthStatus(str(row["authorization_status"])),
            notes=str(row["notes"] or ""),
            created_at=from_db_time(str(row["created_at"])),
            updated_at=from_db_time(str(row["updated_at"])),
        )

    def is_expired(self, at: datetime | None = None) -> bool:
        moment = ensure_aware_utc(at or utc_now())
        return moment > self.end_time

    def is_in_window(self, at: datetime | None = None) -> bool:
        moment = ensure_aware_utc(at or utc_now())
        return self.start_time <= moment <= self.end_time

    def is_effective(self, at: datetime | None = None) -> bool:
        moment = ensure_aware_utc(at or utc_now())
        return (
            self.authorization_status is AuthStatus.CONFIRMED
            and self.start_time <= moment <= self.end_time
        )

    def validity_label(self, at: datetime | None = None) -> str:
        moment = ensure_aware_utc(at or utc_now())
        if self.authorization_status is AuthStatus.REVOKED:
            return "已撤销"
        if self.authorization_status is AuthStatus.PENDING:
            return "待审核"
        if self.authorization_status is AuthStatus.EXPIRED or moment > self.end_time:
            return "已过期"
        if moment < self.start_time:
            return "未生效"
        if self.authorization_status is AuthStatus.CONFIRMED:
            return "有效"
        return self.authorization_status.label

    @property
    def status_label(self) -> str:
        return self.authorization_status.label


@dataclass(frozen=True, slots=True)
class AuthorizationHistory:
    history_id: int
    project_id: int
    authorization_id: int | None
    action: str
    change_summary: str
    details_json: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AuthorizationHistory":
        return cls(
            history_id=int(row["history_id"]),
            project_id=int(row["project_id"]),
            authorization_id=(
                int(row["authorization_id"]) if row["authorization_id"] is not None else None
            ),
            action=str(row["action"]),
            change_summary=str(row["change_summary"] or ""),
            details_json=str(row["details_json"] or "{}"),
            created_at=from_db_time(str(row["created_at"])),
        )
