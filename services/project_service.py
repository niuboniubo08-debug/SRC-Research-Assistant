"""Project lifecycle and active-project management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.errors import NotFoundError, StorageError, ValidationError
from core.models import Project, ProjectStatus, ProjectType
from core.timeutil import to_db_time, utc_now
from database.connection import Database
from services.audit_service import AuditLogService


class ProjectService:
    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._clock = clock

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _coerce_project_type(value: ProjectType | str) -> ProjectType:
        if isinstance(value, ProjectType):
            return value
        try:
            return ProjectType(str(value))
        except ValueError as exc:
            raise ValidationError("项目类型无效", "project_type") from exc

    @staticmethod
    def _coerce_project_status(value: ProjectStatus | str) -> ProjectStatus:
        if isinstance(value, ProjectStatus):
            return value
        try:
            return ProjectStatus(str(value))
        except ValueError as exc:
            raise ValidationError("项目状态无效", "status") from exc

    @staticmethod
    def _validate_name(value: str) -> str:
        name = str(value or "").strip()
        if not name:
            raise ValidationError("项目名称不能为空", "project_name")
        if len(name) > 120:
            raise ValidationError("项目名称不能超过 120 个字符", "project_name")
        return name

    @staticmethod
    def _validate_local_path(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        path = Path(text).expanduser()
        if not path.is_absolute():
            raise ValidationError("本地路径必须是绝对路径", "local_path")
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ValidationError("本地路径不存在或不可访问", "local_path") from exc
        if not resolved.is_dir():
            raise ValidationError("本地路径必须是文件夹", "local_path")
        return os.path.normpath(str(resolved))

    def _row(self, project_id: int, conn=None) -> Any:
        sql = "SELECT * FROM projects WHERE project_id = ?"
        if conn is not None:
            return conn.execute(sql, (project_id,)).fetchone()
        return self._db.fetch_one(sql, (project_id,))

    # ------------------------------------------------------------------ create
    def create_project(
        self,
        project_name: str,
        project_type: ProjectType | str,
        description: str = "",
        local_path: str = "",
        status: ProjectStatus | str = ProjectStatus.ACTIVE,
    ) -> Project:
        name = self._validate_name(project_name)
        kind = self._coerce_project_type(project_type)
        state = self._coerce_project_status(status)
        clean_path = self._validate_local_path(local_path)
        now = to_db_time(self._clock())
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (project_name, project_type, description, local_path, "
                "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, kind.value, str(description or "").strip(), clean_path, state.value, now, now),
            )
            project_id = int(cursor.lastrowid or 0)
            self._audit.record(
                event_type="project_change",
                target=name,
                operation="create_project",
                decision="info",
                message=f"创建项目 #{project_id}",
                details={
                    "project_id": project_id,
                    "project_type": kind.value,
                    "status": state.value,
                },
                project_id=project_id,
                conn=conn,
                created_at=self._clock(),
            )
        return self.get_project(project_id)

    # ------------------------------------------------------------------ update
    def update_project(
        self,
        project_id: int,
        *,
        project_name: str,
        project_type: ProjectType | str,
        description: str = "",
        local_path: str = "",
        status: ProjectStatus | str = ProjectStatus.ACTIVE,
    ) -> Project:
        name = self._validate_name(project_name)
        kind = self._coerce_project_type(project_type)
        state = self._coerce_project_status(status)
        clean_path = self._validate_local_path(local_path)
        now = to_db_time(self._clock())
        with self._db.transaction() as conn:
            old_row = self._row(project_id, conn)
            if old_row is None:
                raise NotFoundError("要修改的项目不存在")
            old = Project.from_row(old_row)
            conn.execute(
                "UPDATE projects SET project_name = ?, project_type = ?, description = ?, "
                "local_path = ?, status = ?, updated_at = ? WHERE project_id = ?",
                (name, kind.value, str(description or "").strip(), clean_path, state.value, now, project_id),
            )
            self._audit.record(
                event_type="project_change",
                target=name,
                operation="update_project",
                decision="info",
                message=f"修改项目 #{project_id}",
                details={
                    "project_id": project_id,
                    "before": {
                        "project_name": old.project_name,
                        "project_type": old.project_type.value,
                        "status": old.status.value,
                        "local_path": old.local_path,
                    },
                    "after": {
                        "project_name": name,
                        "project_type": kind.value,
                        "status": state.value,
                        "local_path": clean_path,
                    },
                },
                project_id=project_id,
                conn=conn,
                created_at=self._clock(),
            )
        return self.get_project(project_id)

    # ------------------------------------------------------------------ delete
    def delete_project(self, project_id: int) -> None:
        with self._db.transaction() as conn:
            row = self._row(project_id, conn)
            if row is None:
                raise NotFoundError("要删除的项目不存在")
            project = Project.from_row(row)
            self._audit.record(
                event_type="project_change",
                target=project.project_name,
                operation="delete_project",
                decision="info",
                message=f"删除项目 #{project_id}（关联授权与资产将级联删除）",
                details={"project_id": project_id, "project_name": project.project_name},
                conn=conn,
                created_at=self._clock(),
            )
            conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM app_settings WHERE setting_key = 'active_project_id' "
                         "AND setting_value = ?", (str(project_id),))

    # ------------------------------------------------------------------ read
    def get_project(self, project_id: int) -> Project:
        row = self._row(int(project_id))
        if row is None:
            raise NotFoundError("项目不存在")
        return Project.from_row(row)

    def list_projects(
        self,
        search: str = "",
        status: ProjectStatus | str | None = None,
        newest_first: bool = True,
    ) -> list[Project]:
        clauses: list[str] = []
        params: list[Any] = []
        query = str(search or "").strip()
        if query:
            clauses.append("(project_name LIKE ? OR description LIKE ? OR local_path LIKE ?)")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])
        if status is not None:
            state = self._coerce_project_status(status)
            clauses.append("status = ?")
            params.append(state.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        direction = "DESC" if newest_first else "ASC"
        rows = self._db.fetch_all(
            f"SELECT * FROM projects {where} ORDER BY created_at {direction}, project_id {direction}",
            params,
        )
        return [Project.from_row(row) for row in rows]

    def count_projects(self) -> int:
        row = self._db.fetch_one("SELECT COUNT(*) AS count FROM projects")
        return int(row["count"]) if row else 0

    def count_by_status(self) -> dict[ProjectStatus, int]:
        rows = self._db.fetch_all("SELECT status, COUNT(*) AS count FROM projects GROUP BY status")
        return {ProjectStatus(str(row["status"])): int(row["count"]) for row in rows}

    # ------------------------------------------------------------------ active
    def set_active_project(self, project_id: int | None) -> Project | None:
        now = to_db_time(self._clock())
        if project_id is None:
            with self._db.transaction() as conn:
                conn.execute("DELETE FROM app_settings WHERE setting_key = 'active_project_id'")
                self._audit.record(
                    event_type="project_change",
                    target="",
                    operation="clear_active_project",
                    decision="info",
                    message="清除当前活动项目",
                    conn=conn,
                    created_at=self._clock(),
                )
            return None
        project = self.get_project(project_id)
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO app_settings (setting_key, setting_value, updated_at) "
                "VALUES ('active_project_id', ?, ?) "
                "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value, "
                "updated_at = excluded.updated_at",
                (str(project.project_id), now),
            )
            self._audit.record(
                event_type="project_change",
                target=project.project_name,
                operation="set_active_project",
                decision="info",
                message=f"设置当前活动项目为 #{project.project_id}",
                project_id=project.project_id,
                conn=conn,
                created_at=self._clock(),
            )
        return project

    def get_active_project(self) -> Project | None:
        row = self._db.fetch_one(
            "SELECT setting_value FROM app_settings WHERE setting_key = 'active_project_id'"
        )
        if row is None:
            return None
        try:
            project_id = int(row["setting_value"])
        except (TypeError, ValueError):
            raise StorageError("当前活动项目配置损坏")
        project_row = self._row(project_id)
        if project_row is None:
            # Fail cleanly: never leave a dangling active project id.
            with self._db.transaction() as conn:
                conn.execute("DELETE FROM app_settings WHERE setting_key = 'active_project_id'")
            return None
        return Project.from_row(project_row)
