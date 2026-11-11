from __future__ import annotations

import pytest

from core.errors import NotFoundError, ValidationError
from core.models import ProjectStatus


def test_create_project(projects, tmp_path) -> None:
    local = tmp_path / "source"
    local.mkdir()
    project = projects.create_project(
        "  本地 Python 审计  ",
        "local_audit",
        "审计自研应用",
        str(local),
        "active",
    )
    assert project.project_id > 0
    assert project.project_name == "本地 Python 审计"
    assert project.project_type.value == "local_audit"
    assert project.local_path == str(local)
    assert project.status is ProjectStatus.ACTIVE


def test_update_project(projects, project, tmp_path) -> None:
    local = tmp_path / "new-source"
    local.mkdir()
    updated = projects.update_project(
        project.project_id,
        project_name="更新后的项目",
        project_type="combined",
        description="变更说明",
        local_path=str(local),
        status="paused",
    )
    assert updated.project_name == "更新后的项目"
    assert updated.project_type.value == "combined"
    assert updated.status is ProjectStatus.PAUSED
    assert updated.updated_at >= project.updated_at


def test_delete_project(projects, project) -> None:
    projects.set_active_project(project.project_id)
    projects.delete_project(project.project_id)
    with pytest.raises(NotFoundError):
        projects.get_project(project.project_id)
    assert projects.get_active_project() is None


def test_delete_missing_project_raises(projects) -> None:
    with pytest.raises(NotFoundError):
        projects.delete_project(99999)


def test_search_filter_sort_and_active_project(projects) -> None:
    alpha = projects.create_project("Alpha 审计", "local_audit", "第一")
    beta = projects.create_project("Beta 测试", "authorized_test", "第二")
    projects.update_project(
        alpha.project_id,
        project_name="Alpha 审计",
        project_type="local_audit",
        description="第一",
        status="completed",
    )
    assert [p.project_id for p in projects.list_projects(search="Alpha")] == [alpha.project_id]
    assert [p.project_id for p in projects.list_projects(status="active")] == [beta.project_id]
    assert [p.project_id for p in projects.list_projects(newest_first=False)] == [
        alpha.project_id,
        beta.project_id,
    ]
    projects.set_active_project(beta.project_id)
    assert projects.get_active_project().project_id == beta.project_id
    projects.set_active_project(None)
    assert projects.get_active_project() is None


def test_project_validation(projects, tmp_path) -> None:
    with pytest.raises(ValidationError):
        projects.create_project("", "local_audit")
    with pytest.raises(ValidationError):
        projects.create_project("x", "not-a-type")
    with pytest.raises(ValidationError):
        projects.create_project("x", "local_audit", local_path="relative/path")
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationError):
        projects.create_project("x", "local_audit", local_path=str(file_path))


def test_project_isolation_between_authorization_queries(projects, authorizations, project, clock):
    from datetime import timedelta

    other = projects.create_project("另一个项目", "authorized_test")
    auth = authorizations.create_authorization(
        other.project_id,
        authorization_source="另一个授权",
        authorization_document="C:/docs/other.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=1),
        authorization_status="confirmed",
    )
    with pytest.raises(NotFoundError):
        authorizations.get_authorization(project.project_id, auth.authorization_id)
