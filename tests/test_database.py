from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.errors import StorageError
from database.connection import Database
from database.schema import MIGRATION_V2, SCHEMA_V1, SCHEMA_VERSION


def test_schema_contains_phase1_and_phase2_tables(db: Database) -> None:
    tables = set(db.table_names())
    assert {
        "projects",
        "authorizations",
        "scan_tasks",
        "findings",
        "evidence",
        "reports",
        "scan_logs",
        "scope_assets",
        "authorization_history",
        "app_settings",
        "finding_status_history",
    } <= tables
    assert db.schema_version() == SCHEMA_VERSION
    finding_columns = {
        str(row["name"]) for row in db.fetch_all("PRAGMA table_info(findings)")
    }
    task_columns = {
        str(row["name"]) for row in db.fetch_all("PRAGMA table_info(scan_tasks)")
    }
    assert {
        "confidence",
        "file_path",
        "line_number",
        "rule_id",
        "scanner_name",
        "scanner_version",
        "detected_at",
        "metadata_json",
        "manual_notes",
        "status_changed_at",
        "last_seen_at",
    } <= finding_columns
    evidence_columns = {
        str(row["name"]) for row in db.fetch_all("PRAGMA table_info(evidence)")
    }
    assert {"evidence_type", "title", "source"} <= evidence_columns
    assert {
        "progress",
        "current_scanner",
        "error_message",
        "scanners_json",
        "cancel_requested",
        "cancelled_at",
    } <= task_columns


def test_v2_database_migrates_to_current_schema_with_backups(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA_V1)
        connection.executescript(MIGRATION_V2)
        connection.execute("PRAGMA user_version = 2")
        connection.commit()
    finally:
        connection.close()

    database = Database(path)
    database.initialize()
    assert database.schema_version() == SCHEMA_VERSION == 5
    columns = {
        str(row["name"]) for row in database.fetch_all("PRAGMA table_info(findings)")
    }
    assert {
        "scanner_name",
        "metadata_json",
        "manual_notes",
        "status_changed_at",
        "last_seen_at",
    } <= columns
    assert database.foreign_keys_enabled() is True
    assert list((tmp_path / "backups").glob("legacy_v2_*.db"))
    assert list((tmp_path / "backups").glob("legacy_v3_*.db"))
    assert list((tmp_path / "backups").glob("legacy_v4_*.db"))


def test_foreign_keys_are_enabled_on_every_connection(db: Database) -> None:
    assert db.foreign_keys_enabled() is True
    with pytest.raises(StorageError):
        db.execute(
            "INSERT INTO authorizations "
            "(project_id, authorization_source, start_time, end_time, created_at, updated_at) "
            "VALUES (9999, 'x', '2030-01-01T00:00:00Z', '2030-02-01T00:00:00Z', "
            "'2030-01-01T00:00:00Z', '2030-01-01T00:00:00Z')"
        )


def test_database_path_failure_is_wrapped(tmp_path: Path) -> None:
    target_directory = tmp_path / "a-directory"
    target_directory.mkdir()
    database = Database(target_directory)
    with pytest.raises(StorageError):
        database.initialize()


def test_project_delete_cascades_authorization_and_scope(
    projects, project, authorizations, confirmed_auth, scopes, db
) -> None:
    scopes.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="example.com",
        authorization_id=confirmed_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    projects.delete_project(project.project_id)
    assert db.fetch_one("SELECT * FROM authorizations") is None
    assert db.fetch_one("SELECT * FROM scope_assets") is None
    # Audit history is retained with project_id set to NULL.
    row = db.fetch_one("SELECT * FROM scan_logs WHERE operation = 'delete_project'")
    assert row is not None
    assert row["project_id"] is None
