"""Typed application configuration loaded from ``config.yaml``."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(RuntimeError):
    """Raised when the application configuration is missing or invalid."""


def application_root() -> Path:
    """Return the writable application directory.

    In a PyInstaller build writable data stays next to the executable.  A source
    checkout uses the repository root.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _require_mapping(raw: Any, key: str) -> dict[str, Any]:
    value = raw.get(key, {}) if isinstance(raw, dict) else {}
    if not isinstance(value, dict):
        raise ConfigError(f"配置项 {key} 必须是对象")
    return value


def _resolve(root: Path, value: Any, default: str) -> Path:
    candidate = Path(str(value or default)).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated, immutable application configuration."""

    name: str
    version: str
    environment: str
    root: Path
    database_path: Path
    storage_root: Path
    projects_dir: Path
    evidence_dir: Path
    reports_dir: Path
    logs_dir: Path
    theme: str
    window_width: int
    window_height: int
    default_remote_access: str
    require_valid_authorization: bool
    allow_wildcard_scope: bool
    allow_redirect_following: bool
    require_exact_remote_match: bool
    config_file: Path

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "AppConfig":
        root = application_root()
        path = Path(config_path).expanduser() if config_path else root / "config.yaml"
        if not path.is_absolute():
            path = (root / path).resolve()
        if not path.is_file():
            raise ConfigError(f"配置文件不存在: {path}")

        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"无法读取配置文件: {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError("配置文件根节点必须是对象")

        base = path.parent
        app = _require_mapping(raw, "app")
        database = _require_mapping(raw, "database")
        storage = _require_mapping(raw, "storage")
        ui = _require_mapping(raw, "ui")
        security = _require_mapping(raw, "security")

        storage_root = _resolve(base, storage.get("root"), "storage")
        database_path = _resolve(base, database.get("path"), "storage/src_research.db")
        projects_dir = _resolve(base, storage.get("projects"), "storage/projects")
        evidence_dir = _resolve(base, storage.get("evidence"), "storage/evidence")
        reports_dir = _resolve(base, storage.get("reports"), "storage/reports")
        logs_dir = _resolve(base, storage.get("logs"), "storage/logs")

        try:
            window_width = int(ui.get("window_width", 1440))
            window_height = int(ui.get("window_height", 900))
        except (TypeError, ValueError) as exc:
            raise ConfigError("窗口尺寸必须是整数") from exc
        if window_width < 960 or window_height < 640:
            raise ConfigError("窗口尺寸不能小于 960x640")

        default_remote_access = str(security.get("default_remote_access", "deny")).lower()
        if default_remote_access != "deny":
            raise ConfigError("安全策略只允许 default_remote_access=deny（默认拒绝）")

        return cls(
            name=str(app.get("name", "SRC Research Assistant")).strip(),
            version=str(app.get("version", "0.5.0")).strip(),
            environment=str(app.get("environment", "local")).strip(),
            root=base,
            database_path=database_path,
            storage_root=storage_root,
            projects_dir=projects_dir,
            evidence_dir=evidence_dir,
            reports_dir=reports_dir,
            logs_dir=logs_dir,
            theme=str(ui.get("theme", "dark")).strip().lower(),
            window_width=window_width,
            window_height=window_height,
            default_remote_access=default_remote_access,
            require_valid_authorization=bool(security.get("require_valid_authorization", True)),
            allow_wildcard_scope=bool(security.get("allow_wildcard_scope", False)),
            allow_redirect_following=bool(security.get("allow_redirect_following", False)),
            require_exact_remote_match=bool(security.get("require_exact_remote_match", True)),
            config_file=path,
        )

    def ensure_directories(self) -> None:
        """Create only application-owned storage directories."""

        for directory in (
            self.storage_root,
            self.projects_dir,
            self.evidence_dir,
            self.reports_dir,
            self.logs_dir,
            self.database_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)
