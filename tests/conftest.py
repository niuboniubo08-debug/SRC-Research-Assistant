from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from database.connection import Database  # noqa: E402
from security.scope_validator import ScopeValidator  # noqa: E402
from services.audit_service import AuditLogService  # noqa: E402
from services.authorization_service import AuthorizationService  # noqa: E402
from services.project_service import ProjectService  # noqa: E402
from services.scope_asset_service import ScopeAssetService  # noqa: E402


class MutableClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value

    def set(self, value: datetime) -> None:
        self.value = value

    def advance(self, **kwargs) -> None:
        self.value = self.value + timedelta(**kwargs)


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock(datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc))


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    database.initialize()
    return database


@pytest.fixture
def audit(db: Database, tmp_path: Path, clock: MutableClock) -> AuditLogService:
    return AuditLogService(db, tmp_path / "logs", clock=clock)


@pytest.fixture
def projects(db: Database, audit: AuditLogService, clock: MutableClock) -> ProjectService:
    return ProjectService(db, audit, clock=clock)


@pytest.fixture
def authorizations(
    db: Database, audit: AuditLogService, clock: MutableClock
) -> AuthorizationService:
    return AuthorizationService(db, audit, clock=clock)


@pytest.fixture
def scopes(
    db: Database,
    audit: AuditLogService,
    authorizations: AuthorizationService,
    clock: MutableClock,
) -> ScopeAssetService:
    return ScopeAssetService(db, audit, authorizations, clock=clock)


@pytest.fixture
def project(projects: ProjectService):
    return projects.create_project("测试授权项目", "authorized_test", "单元测试项目")


@pytest.fixture
def scope_validator(
    db: Database, audit: AuditLogService, clock: MutableClock
) -> ScopeValidator:
    return ScopeValidator(db, audit, clock=clock)


@pytest.fixture
def local_source(tmp_path: Path) -> Path:
    path = tmp_path / "local_python_project"
    path.mkdir()
    (path / "unsafe.py").write_text(
        "import subprocess\n"
        "PASSWORD = 'should-not-be-persisted'\n"
        "def run(user_input):\n"
        "    eval(user_input)\n"
        "    subprocess.run('echo ' + user_input, shell=True)\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def local_project(projects: ProjectService, local_source: Path):
    return projects.create_project(
        "本地 Python 审计项目",
        "local_audit",
        "第三阶段测试",
        str(local_source),
        "active",
    )


@pytest.fixture
def local_asset(scopes: ScopeAssetService, local_project, local_source: Path):
    return scopes.create_asset(
        local_project.project_id,
        asset_type="local_project",
        asset_value=str(local_source),
        notes="测试本地源码资产",
    )


@pytest.fixture
def confirmed_auth(authorizations: AuthorizationService, project, clock: MutableClock):
    return authorizations.create_authorization(
        project.project_id,
        authorization_source="客户书面授权 SRC-2026-001",
        authorization_document=str(Path("C:/authorized/scope.pdf")),
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=30),
        authorization_status="confirmed",
        notes="测试授权，不外联",
    )
