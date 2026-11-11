"""Unified, UI-independent scanner interface and shared result types."""

from __future__ import annotations

import importlib.metadata
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Mapping, Sequence

from core.models.finding import Finding
from scanners.process_runner import CommandResult, run_command


class ScannerError(RuntimeError):
    """Base scanner error."""


class ScannerUnavailable(ScannerError):
    pass


class ScannerExecutionError(ScannerError):
    pass


class ScannerParseError(ScannerError):
    pass


class ScannerTimeoutError(ScannerError):
    pass


class ScanCancelled(ScannerError):
    pass


@dataclass(frozen=True, slots=True)
class ScannerAvailability:
    available: bool
    version: str = ""
    reason: str = ""
    command: str = ""

    @classmethod
    def unavailable(
        cls, reason: str, command: str = "", version: str = ""
    ) -> "ScannerAvailability":
        return cls(available=False, version=version, reason=reason, command=command)


@dataclass(slots=True)
class ScanOptions:
    timeout_seconds: float = 180.0
    cancel_event: threading.Event = field(default_factory=threading.Event)
    env_extra: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("扫描超时时间必须大于 0")


@dataclass(frozen=True, slots=True)
class ScanOutput:
    findings: tuple[Finding, ...]
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


class BaseScanner(ABC):
    """Common contract for all local static-analysis tools.

    Scanners return unified :class:`Finding` objects and never import or touch
    the UI.  External calls are made by ``scanners.process_runner`` without a
    shell.
    """

    name: ClassVar[str]
    display_name: ClassVar[str]
    supported_languages: ClassVar[tuple[str, ...]] = ("python",)

    def __init__(self) -> None:
        self._availability_cache: ScannerAvailability | None = None

    @property
    def version(self) -> str:
        availability = self.is_available()
        return availability.version

    @abstractmethod
    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        """Return real availability and version information."""

    @abstractmethod
    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        """Scan a validated local directory and return unified findings."""

    def _metadata_version(self, distribution: str) -> str:
        try:
            return importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            return ""

    def _probe_command(self, command: Sequence[str], timeout: float = 15.0) -> CommandResult:
        """Run a short availability/version probe without a shell."""

        return run_command(
            command,
            cwd=None,
            timeout_seconds=timeout,
            cancel_event=None,
            env_extra={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

    @staticmethod
    def _module_command(module: str, *args: str) -> list[str]:
        return [sys.executable, "-m", module, *args]

    @staticmethod
    def _relative_source(root: Path, filename: str) -> str:
        candidate = Path(filename)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            return ""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"
