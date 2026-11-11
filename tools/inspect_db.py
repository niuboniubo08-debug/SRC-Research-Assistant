"""Read-only database structure diagnostics."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "storage" / "src_research.db"


def main() -> int:
    path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DB
    if not path.is_file():
        print(f"数据库不存在: {path}", file=sys.stderr)
        return 1
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        fk_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        print(f"path={path}")
        print(f"schema_version={version}")
        print(f"foreign_keys_reported={fk_enabled} (per-connection pragma)")
        print(f"foreign_key_violations={len(violations)}")
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for table in tables:
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            print(f"table={table} rows={count}")
        indexes = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' "
            "AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
        print(f"indexes={indexes}")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
