"""Append-only audit logging.

Security-relevant decisions are written to both SQLite (``scan_logs``) and a
JSON-lines file.  A failure to write is surfaced as ``StorageError`` so that a
caller can fail closed instead of silently authorizing an operation.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from core.errors import StorageError
from core.models.system import ScanLog
from core.timeutil import to_db_time, utc_now
from database.connection import Database

_ALLOWED_DECISIONS = {"allow", "deny", "info", "error"}


class AuditLogService:
    def __init__(
        self,
        database: Database,
        logs_dir: str | Path,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._logs_dir = Path(logs_dir)
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._lock = threading.Lock()

    @property
    def audit_file(self) -> Path:
        return self._logs_dir / "audit.jsonl"

    def record(
        self,
        *,
        event_type: str,
        target: str = "",
        operation: str = "",
        decision: str = "info",
        message: str = "",
        details: dict[str, Any] | None = None,
        project_id: int | None = None,
        task_id: int | None = None,
        conn: sqlite3.Connection | None = None,
        created_at: datetime | None = None,
    ) -> int:
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError(f"无效审计结论: {decision}")
        if not event_type.strip():
            raise ValueError("审计事件类型不能为空")
        timestamp = created_at or self._clock()
        stamp = to_db_time(timestamp)
        payload = json.dumps(details or {}, ensure_ascii=False, sort_keys=True, default=str)
        event = {
            "created_at": stamp,
            "event_type": event_type.strip(),
            "project_id": project_id,
            "task_id": task_id,
            "target": target.strip(),
            "operation": operation.strip(),
            "decision": decision,
            "message": message.strip(),
            "details": details or {},
        }
        try:
            with self._lock:
                with self.audit_file.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, default=str))
                    handle.write("\n")
                    handle.flush()
        except OSError as exc:
            raise StorageError(f"审计日志文件写入失败: {exc}") from exc

        sql = (
            "INSERT INTO scan_logs (project_id, task_id, event_type, target, operation, "
            "decision, message, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            project_id,
            task_id,
            event["event_type"],
            event["target"],
            event["operation"],
            decision,
            event["message"],
            payload,
            stamp,
        )
        try:
            if conn is not None:
                cursor = conn.execute(sql, params)
                return int(cursor.lastrowid or 0)
            return self._db.execute(sql, params)
        except (sqlite3.Error, StorageError) as exc:
            raise StorageError(f"审计日志数据库写入失败: {exc}") from exc

    def list_logs(
        self,
        project_id: int | None = None,
        limit: int = 300,
        event_prefix: str | None = None,
    ) -> list[ScanLog]:
        safe_limit = max(1, min(int(limit), 1000))
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(project_id)
        if event_prefix:
            clauses.append("event_type LIKE ?")
            params.append(f"{event_prefix}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._db.fetch_all(
            f"SELECT * FROM scan_logs {where} ORDER BY created_at DESC, log_id DESC LIMIT ?",
            (*params, safe_limit),
        )
        return [ScanLog.from_row(row) for row in rows]

    def count(self, project_id: int | None = None) -> int:
        if project_id is None:
            row = self._db.fetch_one("SELECT COUNT(*) AS count FROM scan_logs")
        else:
            row = self._db.fetch_one(
                "SELECT COUNT(*) AS count FROM scan_logs WHERE project_id = ?", (project_id,)
            )
        return int(row["count"]) if row else 0
