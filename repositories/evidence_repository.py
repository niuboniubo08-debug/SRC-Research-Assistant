"""SQL persistence for project-scoped evidence."""

from __future__ import annotations

from typing import Any

from core.errors import NotFoundError
from core.models import Evidence, EvidenceType
from core.timeutil import to_db_time
from database.connection import Database

_EVIDENCE_SELECT = (
    "SELECT e.*, p.project_name AS project_name, "
    "f.title AS finding_title "
    "FROM evidence e "
    "JOIN projects p ON p.project_id = e.project_id "
    "LEFT JOIN findings f ON f.finding_id = e.finding_id"
)


class EvidenceRepository:
    def __init__(self, database: Database) -> None:
        self._db = database

    def list_evidence(
        self,
        *,
        project_id: int | None = None,
        finding_id: int | None = None,
        evidence_type: str | None = None,
        keyword: str = "",
        limit: int = 1000,
    ) -> list[Evidence]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("e.project_id = ?")
            params.append(int(project_id))
        if finding_id is not None:
            clauses.append("e.finding_id = ?")
            params.append(int(finding_id))
        if evidence_type:
            clauses.append("e.evidence_type = ?")
            params.append(str(evidence_type))
        query = str(keyword or "").strip()
        if query:
            clauses.append(
                "(e.title LIKE ? OR e.description LIKE ? OR e.file_name LIKE ? "
                "OR e.source LIKE ? OR f.title LIKE ? OR p.project_name LIKE ?)"
            )
            pattern = f"%{query}%"
            params.extend([pattern] * 6)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        safe_limit = max(1, min(int(limit), 5000))
        rows = self._db.fetch_all(
            f"{_EVIDENCE_SELECT}{where} "
            "ORDER BY e.created_at DESC, e.evidence_id DESC LIMIT ?",
            (*params, safe_limit),
        )
        return [Evidence.from_row(row) for row in rows]

    def get_evidence(self, project_id: int, evidence_id: int) -> Evidence:
        row = self._db.fetch_one(
            f"{_EVIDENCE_SELECT} WHERE e.project_id = ? AND e.evidence_id = ?",
            (int(project_id), int(evidence_id)),
        )
        if row is None:
            raise NotFoundError("证据不存在或不属于当前项目")
        return Evidence.from_row(row)

    def create_evidence(
        self,
        *,
        project_id: int,
        finding_id: int,
        evidence_type: EvidenceType,
        title: str,
        description: str,
        file_path: str,
        file_name: str,
        file_hash: str,
        captured_at,
        source: str,
        created_at,
    ) -> Evidence:
        stamp_captured = to_db_time(captured_at)
        stamp_created = to_db_time(created_at)
        with self._db.transaction() as conn:
            finding = conn.execute(
                "SELECT finding_id FROM findings WHERE project_id = ? AND finding_id = ?",
                (int(project_id), int(finding_id)),
            ).fetchone()
            if finding is None:
                raise NotFoundError("漏洞不存在或不属于当前项目")
            cursor = conn.execute(
                "INSERT INTO evidence "
                "(project_id, finding_id, evidence_type, title, description, file_path, "
                "file_name, sha256, captured_at, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(project_id),
                    int(finding_id),
                    evidence_type.value,
                    str(title),
                    str(description),
                    str(file_path),
                    str(file_name),
                    str(file_hash),
                    stamp_captured,
                    str(source),
                    stamp_created,
                ),
            )
            evidence_id = int(cursor.lastrowid or 0)
        return self.get_evidence(project_id, evidence_id)

    def delete_evidence(self, project_id: int, evidence_id: int) -> Evidence:
        evidence = self.get_evidence(project_id, evidence_id)
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "DELETE FROM evidence WHERE project_id = ? AND evidence_id = ?",
                (int(project_id), int(evidence_id)),
            )
            if cursor.rowcount == 0:
                raise NotFoundError("证据不存在或不属于当前项目")
        return evidence

    def count(self, project_id: int | None = None, finding_id: int | None = None) -> int:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            params.append(int(project_id))
        if finding_id is not None:
            clauses.append("finding_id = ?")
            params.append(int(finding_id))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self._db.fetch_one(
            f"SELECT COUNT(*) AS count FROM evidence{where}", tuple(params)
        )
        return int(row["count"]) if row else 0
