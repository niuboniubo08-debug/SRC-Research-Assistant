"""Shared active-project state for all pages."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.models import Project
from services.project_service import ProjectService


class AppState(QObject):
    project_changed = Signal(object)
    projects_changed = Signal()

    def __init__(self, project_service: ProjectService) -> None:
        super().__init__()
        self._projects = project_service
        self._current: Project | None = project_service.get_active_project()

    @property
    def current_project(self) -> Project | None:
        return self._current

    @property
    def current_project_id(self) -> int | None:
        return self._current.project_id if self._current else None

    def reload(self) -> None:
        self._current = self._projects.get_active_project()
        self.project_changed.emit(self._current)

    def set_active_project(self, project_id: int | None) -> Project | None:
        project = self._projects.set_active_project(project_id)
        self._current = project
        self.project_changed.emit(project)
        self.projects_changed.emit()
        return project

    def notify_projects_changed(self) -> None:
        self._current = self._projects.get_active_project()
        self.project_changed.emit(self._current)
        self.projects_changed.emit()
