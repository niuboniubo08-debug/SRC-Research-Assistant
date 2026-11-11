from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from database.connection import Database
from database.schema import (
    MIGRATION_V2,
    MIGRATION_V3_INDEXES,
    SCHEMA_V1,
    SCHEMA_VERSION,
    V3_COLUMNS,
    V4_COLUMNS,
)


def make_v4_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA_V1)
        connection.executescript(MIGRATION_V2)
        for table, columns in V3_COLUMNS.items():
            existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, declaration in columns:
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                    )
        connection.executescript(MIGRATION_V3_INDEXES)
        connection.execute("PRAGMA user_version = 3")
        for table, columns in V4_COLUMNS.items():
            existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for name, declaration in columns:
                if name not in existing:
                    connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                    )
        connection.execute("PRAGMA user_version = 4")
        now = "2030-01-01T12:00:00Z"
        connection.execute(
            "INSERT INTO projects "
            "(project_name, project_type, description, local_path, status, created_at, updated_at) "
            "VALUES ('v4 project', 'local_audit', 'legacy', '', 'active', ?, ?)",
            (now, now),
        )
        connection.execute(
            "INSERT INTO scan_tasks "
            "(project_id, task_type, target, status, created_at) "
            "VALUES (1, 'source_audit', 'legacy.py', 'completed', ?)",
            (now,),
        )
        connection.execute(
            "INSERT INTO findings "
            "(project_id, task_id, title, category, risk_level, affected_scope, "
            "description, remediation, status, created_at, updated_at, confidence, "
            "file_path, line_number, rule_id, scanner_name, scanner_version, "
            "detected_at, metadata_json) "
            "VALUES (1, 1, 'legacy vuln', 'test', 'high', 'legacy.py', 'desc', "
            "'fix', 'open', ?, ?, 'high', 'legacy.py', 7, 'B-LEGACY', 'bandit', "
            "'1.0', ?, '{\"source\":\"legacy\"}')",
            (now, now, now),
        )
        connection.execute(
            "INSERT INTO evidence "
            "(project_id, finding_id, file_path, file_name, sha256, captured_at, "
            "description, created_at) VALUES "
            "(1, 1, '', 'legacy.txt', '', ?, 'legacy evidence', ?)",
            (now, now),
        )
        connection.commit()
    finally:
        connection.close()


def test_v4_data_migrates_to_v5_and_preserves_rows(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    make_v4_database(path)
    database = Database(path)
    database.initialize()
    assert SCHEMA_VERSION == 5
    assert database.schema_version() == 5
    finding = database.fetch_one("SELECT * FROM findings WHERE finding_id = 1")
    assert finding["title"] == "legacy vuln"
    assert finding["status"] == "open"
    assert finding["metadata_json"] == '{"source":"legacy"}'
    assert finding["last_seen_at"] == "2030-01-01T12:00:00Z"
    evidence = database.fetch_one("SELECT * FROM evidence WHERE evidence_id = 1")
    assert evidence["title"] == ""
    assert evidence["evidence_type"] == "other_file"
    assert evidence["source"] == ""
    assert database.fetch_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='finding_status_history'"
    )
    assert database.foreign_keys_enabled() is True
    assert list((tmp_path / "backups").glob("legacy_v4_*.db"))


def test_v5_migration_failure_rolls_back_and_backup_can_be_restored(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "legacy.db"
    make_v4_database(path)

    def fail_after_partial_ddl(self, connection):
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE _v5_failure_probe (x INTEGER)")
        raise RuntimeError("simulated migration failure")

    monkeypatch.setattr(Database, "_migrate_v5", fail_after_partial_ddl)
    database = Database(path)
    with pytest.raises(RuntimeError):
        database.initialize()

    raw = sqlite3.connect(path)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 4
        assert raw.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == 1
        probe = raw.execute(
            "SELECT name FROM sqlite_master WHERE name = '_v5_failure_probe'"
        ).fetchone()
        assert probe is None
    finally:
        raw.close()
    backups = list((tmp_path / "backups").glob("legacy_v4_*.db"))
    assert backups
    restored = tmp_path / "restored.db"
    shutil.copy2(backups[-1], restored)
    restored_connection = sqlite3.connect(restored)
    try:
        assert restored_connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert restored_connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == 1
    finally:
        restored_connection.close()
