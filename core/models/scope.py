"""Authorization-scope asset domain model."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.models.enums import AssetStatus, AssetType
from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class ScopeAsset:
    asset_id: int
    project_id: int
    asset_type: AssetType
    asset_value: str
    authorization_id: int | None
    allowed_operations: tuple[str, ...]
    asset_status: AssetStatus
    notes: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ScopeAsset":
        try:
            operations = tuple(json.loads(str(row["allowed_operations"] or "[]")))
        except (ValueError, TypeError):
            operations = ()
        return cls(
            asset_id=int(row["asset_id"]),
            project_id=int(row["project_id"]),
            asset_type=AssetType(str(row["asset_type"])),
            asset_value=str(row["asset_value"]),
            authorization_id=(
                int(row["authorization_id"]) if row["authorization_id"] is not None else None
            ),
            allowed_operations=operations,
            asset_status=AssetStatus(str(row["asset_status"])),
            notes=str(row["notes"] or ""),
            created_at=from_db_time(str(row["created_at"])),
            updated_at=from_db_time(str(row["updated_at"])),
        )

    @property
    def is_remote(self) -> bool:
        return self.asset_type.is_remote

    @property
    def type_label(self) -> str:
        return self.asset_type.label

    @property
    def status_label(self) -> str:
        return self.asset_status.label
