"""Persistent source-audit task model."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.models.enums import ScanTaskStatus, ScanTaskType
from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class ScanTask:
    task_id: int
    project_id: int
    task_type: ScanTaskType
    target: str
    status: ScanTaskStatus
    started_at: datetime | None
    finished_at: datetime | None
    result_summary: str
    created_at: datetime
    current_scanner: str
    progress: int
    error_message: str
    scanners: tuple[str, ...]
    cancel_requested: bool
    cancelled_at: datetime | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ScanTask":
        try:
            scanners_raw = json.loads(str(row["scanners_json"] or "[]"))
            scanners = tuple(str(item) for item in scanners_raw)
        except (TypeError, ValueError):
            scanners = ()
        return cls(
            task_id=int(row["task_id"]),
            project_id=int(row["project_id"]),
            task_type=ScanTaskType(str(row["task_type"])),
            target=str(row["target"] or ""),
            status=ScanTaskStatus(str(row["status"])),
            started_at=from_db_time(str(row["started_at"])) if row["started_at"] else None,
            finished_at=from_db_time(str(row["finished_at"])) if row["finished_at"] else None,
            result_summary=str(row["result_summary"] or ""),
            created_at=from_db_time(str(row["created_at"])),
            current_scanner=str(row["current_scanner"] or ""),
            progress=max(0, min(100, int(row["progress"] or 0))),
            error_message=str(row["error_message"] or ""),
            scanners=scanners,
            cancel_requested=bool(row["cancel_requested"]),
            cancelled_at=from_db_time(str(row["cancelled_at"])) if row["cancelled_at"] else None,
        )

    @property
    def status_label(self) -> str:
        return self.status.label

    @property
    def type_label(self) -> str:
        return self.task_type.label
