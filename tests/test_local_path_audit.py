from __future__ import annotations

from pathlib import Path


def test_existing_local_asset_is_allowed(
    scope_validator, local_project, local_asset, local_source
) -> None:
    decision = scope_validator.check_local_path(
        local_project.project_id, str(local_source), operation="source_audit"
    )
    assert decision.allowed is True
    assert decision.code == "allowed"
    assert decision.asset_id == local_asset.asset_id


def test_missing_local_path_is_rejected(scope_validator, local_project, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    decision = scope_validator.check_local_path(
        local_project.project_id, str(missing), operation="source_audit"
    )
    assert decision.allowed is False
    assert decision.code == "local_path_not_found"


def test_file_path_is_not_a_valid_scan_root(
    scope_validator, local_project, tmp_path: Path
) -> None:
    file_path = tmp_path / "single.py"
    file_path.write_text("print('x')\n", encoding="utf-8")
    decision = scope_validator.check_local_path(
        local_project.project_id, str(file_path), operation="source_audit"
    )
    assert decision.allowed is False
    assert decision.code == "local_path_not_directory"


def test_traversal_outside_registered_scope_is_rejected(
    scope_validator, local_project, local_asset, local_source, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    traversal = local_source / ".." / "outside"
    decision = scope_validator.check_local_path(
        local_project.project_id, str(traversal), operation="source_audit"
    )
    assert decision.allowed is False
    assert decision.code == "local_target_not_in_scope"
    assert Path(decision.target).resolve() == outside.resolve()


def test_permission_denied_is_rejected(
    monkeypatch, scope_validator, local_project, local_asset, local_source
) -> None:
    monkeypatch.setattr("security.scope_validator.os.access", lambda *_args, **_kwargs: False)
    decision = scope_validator.check_local_path(
        local_project.project_id, str(local_source), operation="source_audit"
    )
    assert decision.allowed is False
    assert decision.code == "local_path_permission_denied"


def test_invalid_path_is_rejected(scope_validator, local_project) -> None:
    decision = scope_validator.check_local_path(
        local_project.project_id, "relative/path", operation="source_audit"
    )
    assert decision.allowed is False
    assert decision.code == "invalid_local_path"


def test_path_checks_are_audited(
    scope_validator, local_project, local_asset, local_source, audit
) -> None:
    scope_validator.check_local_path(
        local_project.project_id, str(local_source), operation="source_audit"
    )
    logs = audit.list_logs(local_project.project_id, event_prefix="authorization_check")
    assert any(log.target.endswith("local_python_project") for log in logs)
