from __future__ import annotations

from datetime import timedelta

import pytest

from core.errors import ConflictError, NotFoundError, ValidationError
from core.models import AuthStatus


def test_create_authorization(authorizations, project, confirmed_auth, clock) -> None:
    assert confirmed_auth.project_id == project.project_id
    assert confirmed_auth.authorization_status is AuthStatus.CONFIRMED
    assert confirmed_auth.is_effective(clock.value)
    history = authorizations.list_history(project.project_id, confirmed_auth.authorization_id)
    assert history[0].action == "created"


def test_confirmed_requires_document(authorizations, project, clock) -> None:
    with pytest.raises(ValidationError):
        authorizations.create_authorization(
            project.project_id,
            authorization_source="口头授权",
            authorization_document="",
            start_time=clock.value - timedelta(days=1),
            end_time=clock.value + timedelta(days=5),
            authorization_status="confirmed",
        )


def test_pending_authorization_is_not_effective(authorizations, project, clock) -> None:
    auth = authorizations.create_authorization(
        project.project_id,
        authorization_source="待审核来源",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=30),
    )
    assert auth.authorization_status is AuthStatus.PENDING
    assert auth.is_effective(clock.value) is False


def test_expiry_is_checked_and_persisted(authorizations, project, confirmed_auth, clock) -> None:
    clock.advance(days=31)
    assert confirmed_auth.is_effective(clock.value) is False
    assert authorizations.is_effective(project.project_id, confirmed_auth.authorization_id) is False
    changed = authorizations.expire_overdue_authorizations(project.project_id)
    assert changed == 1
    refreshed = authorizations.get_authorization(
        project.project_id, confirmed_auth.authorization_id
    )
    assert refreshed.authorization_status is AuthStatus.EXPIRED
    history = authorizations.list_history(project.project_id, confirmed_auth.authorization_id)
    assert any(item.action == "expired" for item in history)


def test_revoke_authorization(authorizations, project, confirmed_auth, clock) -> None:
    revoked = authorizations.revoke_authorization(
        project.project_id, confirmed_auth.authorization_id
    )
    assert revoked.authorization_status is AuthStatus.REVOKED
    assert revoked.is_effective(clock.value) is False
    with pytest.raises(ConflictError):
        authorizations.update_authorization(
            project.project_id,
            confirmed_auth.authorization_id,
            authorization_source=confirmed_auth.authorization_source,
            authorization_document=confirmed_auth.authorization_document,
            start_time=confirmed_auth.start_time,
            end_time=confirmed_auth.end_time,
            authorization_status="confirmed",
            notes="",
        )


def test_authorization_update_records_history(authorizations, project, confirmed_auth) -> None:
    updated = authorizations.update_authorization(
        project.project_id,
        confirmed_auth.authorization_id,
        authorization_source=confirmed_auth.authorization_source,
        authorization_document=confirmed_auth.authorization_document,
        start_time=confirmed_auth.start_time,
        end_time=confirmed_auth.end_time + timedelta(days=5),
        authorization_status="confirmed",
        notes="延长五天",
    )
    assert updated.notes == "延长五天"
    history = authorizations.list_history(project.project_id, confirmed_auth.authorization_id)
    assert history[0].action == "updated"


def test_authorization_delete_blocked_when_asset_is_bound(
    authorizations, project, confirmed_auth, scopes
) -> None:
    scopes.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="example.com",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    with pytest.raises(ConflictError):
        authorizations.delete_authorization(project.project_id, confirmed_auth.authorization_id)
    scopes.delete_asset(
        project.project_id,
        scopes.list_assets(project.project_id)[0].asset_id,
    )
    authorizations.delete_authorization(project.project_id, confirmed_auth.authorization_id)
    with pytest.raises(NotFoundError):
        authorizations.get_authorization(project.project_id, confirmed_auth.authorization_id)


def test_cross_project_authorization_cannot_be_modified(authorizations, projects, project, clock):
    other = projects.create_project("项目 B", "authorized_test")
    auth = authorizations.create_authorization(
        other.project_id,
        authorization_source="B 的授权",
        authorization_document="C:/b.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=10),
        authorization_status="confirmed",
    )
    with pytest.raises(NotFoundError):
        authorizations.revoke_authorization(project.project_id, auth.authorization_id)
