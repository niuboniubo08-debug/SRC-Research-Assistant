"""Unified SQLite connection management.

Every operation opens a short-lived connection.  This is intentional: it keeps
the service layer thread-safe and guarantees that every connection enables
foreign keys.  Transactions use ``BEGIN IMMEDIATE`` and are explicitly rolled
back on error.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.errors import StorageError
from database.schema import (
    MIGRATION_V2,
    FINDINGS_V5_TABLE,
    MIGRATION_V3_INDEXES,
    MIGRATION_V5_BACKFILL,
    MIGRATION_V5_COPY,
    MIGRATION_V5_HISTORY,
    MIGRATION_V5_INDEXES,
    SCHEMA_V1,
    SCHEMA_VERSION,
    V3_COLUMNS,
    V4_COLUMNS,
    V5_EVIDENCE_COLUMNS,
)


class Database:
    """Owns the SQLite file and schema lifecycle."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._initialized = False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=15.0,
            isolation_level=None,
            check_same_thread=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a configured connection and always close it."""

        try:
            connection = self._connect()
        except sqlite3.Error as exc:
            raise StorageError(f"无法连接数据库: {exc}") from exc
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run statements in an immediate transaction."""

        with self.connection() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception as exc:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                if isinstance(exc, StorageError):
                    raise
                if isinstance(exc, sqlite3.Error):
                    raise StorageError(f"数据库操作失败: {exc}") from exc
                raise

    def initialize(self) -> None:
        """Create or forward-migrate the database.

        An existing older database is copied next to itself before the schema is
        changed.  Newer schema versions are refused rather than downgraded.
        """

        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.connection() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if current_version > SCHEMA_VERSION:
                    raise StorageError(
                        f"数据库版本 {current_version} 高于程序支持的 {SCHEMA_VERSION}，"
                        "请升级程序后再打开"
                    )
                if current_version == 0:
                    connection.executescript(SCHEMA_V1)
                    connection.execute(f"PRAGMA user_version = 1")
                    current_version = 1
                if current_version == 1:
                    self._backup_before_migration(1)
                    connection.executescript(MIGRATION_V2)
                    connection.execute("PRAGMA user_version = 2")
                    current_version = 2
                if current_version == 2:
                    self._backup_before_migration(2)
                    for table, columns in V3_COLUMNS.items():
                        existing = {
                            str(row[1])
                            for row in connection.execute(f"PRAGMA table_info({table})")
                        }
                        for name, declaration in columns:
                            if name not in existing:
                                connection.execute(
                                    f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                                )
                    connection.executescript(MIGRATION_V3_INDEXES)
                    connection.execute("PRAGMA user_version = 3")
                    current_version = 3
                if current_version == 3:
                    self._backup_before_migration(3)
                    for table, columns in V4_COLUMNS.items():
                        existing = {
                            str(row[1])
                            for row in connection.execute(f"PRAGMA table_info({table})")
                        }
                        for name, declaration in columns:
                            if name not in existing:
                                connection.execute(
                                    f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                                )
                    connection.execute("PRAGMA user_version = 4")
                    current_version = 4
                if current_version == 4:
                    try:
                        connection.execute("PRAGMA wal_checkpoint(FULL)")
                    except sqlite3.Error:
                        pass
                    self._backup_before_migration(4)
                    self._migrate_v5(connection)
                    current_version = 5
                if current_version != SCHEMA_VERSION:
                    raise StorageError(
                        f"数据库迁移未完成，当前版本 {current_version}，期望 {SCHEMA_VERSION}"
                    )
        except sqlite3.Error as exc:
            raise StorageError(f"数据库初始化失败: {exc}") from exc
        self._initialized = True

    def _migrate_v5(self, connection: sqlite3.Connection) -> None:
        """Rebuild findings and add the phase-5 evidence/history structures.

        The DDL runs in one explicit transaction with foreign keys disabled.
        Any failure rolls every v5 change back to the intact v4 database; the
        pre-migration backup is the second recovery path.
        """

        try:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(FINDINGS_V5_TABLE)
            connection.execute(MIGRATION_V5_COPY)
            connection.execute("DROP TABLE findings")
            connection.execute("ALTER TABLE findings_v5 RENAME TO findings")
            connection.execute(MIGRATION_V5_BACKFILL)
            connection.execute(MIGRATION_V5_HISTORY)
            for table, columns in V5_EVIDENCE_COLUMNS.items():
                existing = {
                    str(row[1])
                    for row in connection.execute(f"PRAGMA table_info({table})")
                }
                for name, declaration in columns:
                    if name not in existing:
                        connection.execute(
                            f"ALTER TABLE {table} ADD COLUMN {name} {declaration}"
                        )
            for statement in MIGRATION_V5_INDEXES:
                connection.execute(statement)
            connection.execute("PRAGMA user_version = 5")
            connection.commit()
        except Exception as exc:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            if isinstance(exc, StorageError):
                raise
            if isinstance(exc, sqlite3.Error):
                raise StorageError(f"数据库 v5 迁移失败: {exc}") from exc
            raise
        finally:
            try:
                connection.execute("PRAGMA foreign_keys = ON")
            except sqlite3.Error:
                pass

    def _backup_before_migration(self, version: int) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        backup_dir = self.path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = backup_dir / f"{self.path.stem}_v{version}_{stamp}.db"
        try:
            shutil.copy2(self.path, target)
        except OSError as exc:
            raise StorageError(f"迁移前数据库备份失败: {exc}") from exc

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        with self.connection() as connection:
            try:
                return connection.execute(sql, tuple(params)).fetchone()
            except sqlite3.Error as exc:
                raise StorageError(f"数据库查询失败: {exc}") from exc

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self.connection() as connection:
            try:
                return list(connection.execute(sql, tuple(params)).fetchall())
            except sqlite3.Error as exc:
                raise StorageError(f"数据库查询失败: {exc}") from exc

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Execute a single write and return the last row id."""

        with self.transaction() as connection:
            cursor = connection.execute(sql, tuple(params))
            return int(cursor.lastrowid or 0)

    def table_names(self) -> list[str]:
        rows = self.fetch_all(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [str(row["name"]) for row in rows]

    def schema_version(self) -> int:
        row = self.fetch_one("PRAGMA user_version")
        return int(row[0]) if row else 0

    def foreign_keys_enabled(self) -> bool:
        row = self.fetch_one("PRAGMA foreign_keys")
        return bool(row and int(row[0]) == 1)

    def health_check(self) -> tuple[bool, str]:
        try:
            row = self.fetch_one("SELECT sqlite_version() AS version")
            version = str(row["version"]) if row else "unknown"
            fk = "ON" if self.foreign_keys_enabled() else "OFF"
            return True, f"SQLite {version} · 外键 {fk}"
        except StorageError as exc:
            return False, str(exc)
