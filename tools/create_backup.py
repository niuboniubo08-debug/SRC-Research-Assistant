"""Create a verified, source-only recovery snapshot of this project.

Excludes transient environments, caches and previous backups.  The resulting
archive includes the SQLite database and audit logs so the current state can be
restored before the next development phase.
"""

from __future__ import annotations

import hashlib
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".venv",
    ".tmp",
    ".pytest_cache",
    ".screenshot-demo",
    "__pycache__",
    "backups",
    "build",
    "cache",
    "dist",
    "tmp",
}
EXCLUDED_FILES = {"debug.log"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_PREFIXES = ("pytest-of-", "pytest-")


def should_include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if any(part.startswith(EXCLUDED_PREFIXES) for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> int:
    backup_dir = ROOT / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    requested_name = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if requested_name:
        if Path(requested_name).name != requested_name:
            print("备份文件名不能包含路径", file=sys.stderr)
            return 1
        if not requested_name.lower().endswith(".zip"):
            print("备份文件名必须以 .zip 结尾", file=sys.stderr)
            return 1
        target = backup_dir / requested_name
    else:
        target = backup_dir / f"src-research-assistant_phase2_{stamp}.zip"
    files = sorted(path for path in ROOT.rglob("*") if should_include(path))
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, f"SRC-Research-Assistant/{path.relative_to(ROOT)}")
    with zipfile.ZipFile(target, "r") as archive:
        bad = archive.testzip()
        if bad:
            print(f"备份校验失败: {bad}", file=sys.stderr)
            return 1
        count = len(archive.namelist())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f"备份: {target}")
    print(f"文件数: {count}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
