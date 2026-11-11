from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from core.errors import AuthorizationDenied, NotFoundError, StorageError, ValidationError
from core.models import AssetStatus
from security.scope_validator import ScopeValidator


@pytest.fixture
def validator(db, audit, clock) -> ScopeValidator:
    return ScopeValidator(db, audit, clock=clock)


@pytest.fixture
def remote_asset(scopes, project, confirmed_auth):
    return scopes.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="Example.COM",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )


def test_exact_scope_match_allows(validator, project, remote_asset) -> None:
    decision = validator.check_remote_access(
        project.project_id, "example.com", "config_check"
    )
    assert decision.allowed is True
    assert decision.code == "allowed"


def test_unauthorized_target_denied(validator, project, remote_asset) -> None:
    decision = validator.check_remote_access(
        project.project_id, "evil.example.net", "config_check"
    )
    assert decision.allowed is False
    assert decision.code == "target_not_in_scope"
    with pytest.raises(AuthorizationDenied):
        validator.require_remote_access(project.project_id, "evil.example.net", "config_check")


def test_subdomain_is_not_covered_by_parent_domain(validator, project, remote_asset) -> None:
    decision = validator.check_remote_access(
        project.project_id, "sub.example.com", "config_check"
    )
    assert decision.allowed is False
    assert decision.code == "target_not_in_scope"


def test_ip_asset_is_exact_and_not_interchangeable_with_domain(
    scopes, validator, project, confirmed_auth
) -> None:
    scopes.create_asset(
        project.project_id,
        asset_type="ip",
        asset_value="203.0.113.10",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    assert validator.check_remote_access(
        project.project_id, "203.0.113.10", "config_check"
    ).allowed
    assert not validator.check_remote_access(
        project.project_id, "203.0.113.11", "config_check"
    ).allowed


def test_wildcard_scope_is_rejected(scopes, project, confirmed_auth) -> None:
    with pytest.raises(ValidationError):
        scopes.create_asset(
            project.project_id,
            asset_type="domain",
            asset_value="*.example.com",
            authorization_id=confirmed_auth.authorization_id,
            allowed_operations=["config_check"],
        )


def test_expired_authorization_immediately_denies(validator, project, remote_asset, clock) -> None:
    clock.advance(days=40)
    decision = validator.check_remote_access(project.project_id, "example.com", "config_check")
    assert decision.allowed is False
    assert decision.code in {"authorization_expired", "authorization_expired"}


def test_revoked_authorization_immediately_denies(
    validator, project, confirmed_auth, remote_asset, authorizations
) -> None:
    authorizations.revoke_authorization(project.project_id, confirmed_auth.authorization_id)
    decision = validator.check_remote_access(project.project_id, "example.com", "config_check")
    assert decision.allowed is False
    assert decision.code == "authorization_revoked"


def test_pending_authorization_denies(
    scopes, validator, project, clock, authorizations
) -> None:
    pending = authorizations.create_authorization(
        project.project_id,
        authorization_source="待审核",
        authorization_document="",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=3),
        authorization_status="pending",
    )
    with pytest.raises(ValidationError):
        scopes.create_asset(
            project.project_id,
            asset_type="domain",
            asset_value="pending.example.com",
            authorization_id=pending.authorization_id,
            allowed_operations=["config_check"],
        )


def test_operation_must_be_explicit(scopes, validator, project, confirmed_auth) -> None:
    asset = scopes.create_asset(
        project.project_id,
        asset_type="ip",
        asset_value="203.0.113.10",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    assert asset.asset_value == "203.0.113.10"
    decision = validator.check_remote_access(
        project.project_id, "203.0.113.10", "unsupported_op"
    )
    assert decision.allowed is False
    assert decision.code == "unsupported_operation"


def test_asset_must_belong_to_same_project(
    scopes, validator, projects, project, clock, authorizations
):
    other = projects.create_project("项目 X", "authorized_test")
    other_auth = authorizations.create_authorization(
        other.project_id,
        authorization_source="X 授权",
        authorization_document="C:/x.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=5),
        authorization_status="confirmed",
    )
    with pytest.raises(NotFoundError):
        scopes.create_asset(
            project.project_id,
            asset_type="domain",
            asset_value="x.example.com",
            authorization_id=other_auth.authorization_id,
            allowed_operations=["config_check"],
        )


def test_dns_resolution_review_blocks_private_ip(validator, project, remote_asset) -> None:
    decision = validator.check_remote_access(
        project.project_id,
        "example.com",
        "config_check",
        resolved_ips=["127.0.0.1"],
    )
    assert decision.allowed is False
    assert decision.code == "dns_scope_review_failed"


def test_redirect_target_must_also_be_authorized(
    scopes, validator, project, confirmed_auth
) -> None:
    for domain in ("source.example.com", "target.example.com"):
        scopes.create_asset(
            project.project_id,
            asset_type="domain",
            asset_value=domain,
            authorization_id=confirmed_auth.authorization_id,
            allowed_operations=["config_check"],
        )
    allowed = validator.check_redirect_target(
        project.project_id,
        "https://source.example.com/",
        "https://target.example.com/",
        "config_check",
    )
    assert allowed.allowed is True
    denied = validator.check_redirect_target(
        project.project_id,
        "https://source.example.com/",
        "https://unauthorized.example.net/",
        "config_check",
    )
    assert denied.allowed is False
    assert denied.code == "target_not_in_scope"


def test_local_assets_are_separate(scopes, validator, project, confirmed_auth, tmp_path: Path) -> None:
    local_dir = tmp_path / "local-source"
    local_dir.mkdir()
    asset = scopes.create_asset(
        project.project_id,
        asset_type="local_project",
        asset_value=str(local_dir),
    )
    assert asset.authorization_id is None
    assert asset.allowed_operations == ()
    with pytest.raises(ValidationError):
        scopes.create_asset(
            project.project_id,
            asset_type="local_folder",
            asset_value=str(local_dir),
            authorization_id=confirmed_auth.authorization_id,
        )
    decision = validator.check_local_path(project.project_id, str(local_dir))
    assert decision.allowed is True
    remote_decision = validator.check_local_path(project.project_id, str(tmp_path / "other"))
    assert remote_decision.allowed is False


def test_every_check_is_audited(validator, project, remote_asset, audit) -> None:
    validator.check_remote_access(project.project_id, "example.com", "config_check")
    validator.check_remote_access(project.project_id, "not-authorized.example.net", "config_check")
    logs = audit.list_logs(project.project_id, event_prefix="authorization_check")
    assert len(logs) >= 2
    assert {log.decision for log in logs} == {"allow", "deny"}
    lines = [
        line
        for line in audit.audit_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 2


def test_audit_failure_is_fail_closed(monkeypatch, validator, project, remote_asset, audit) -> None:
    def fail_audit(**_kwargs):
        raise StorageError("simulated audit outage")

    monkeypatch.setattr(audit, "record", fail_audit)
    decision = validator.check_remote_access(project.project_id, "example.com", "config_check")
    assert decision.allowed is False
    assert decision.code == "audit_unavailable"


def test_scope_asset_update_and_delete(scopes, project, confirmed_auth) -> None:
    asset = scopes.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="old.example.com",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    updated = scopes.update_asset(
        project.project_id,
        asset.asset_id,
        asset_type="domain",
        asset_value="new.example.com",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
        asset_status="inactive",
        notes="更新",
    )
    assert updated.asset_value == "new.example.com"
    assert updated.asset_status.value == "inactive"
    scopes.delete_asset(project.project_id, asset.asset_id)
    assert scopes.list_assets(project.project_id) == []
