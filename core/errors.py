"""Application-specific exceptions.

Service and UI layers translate these into Chinese messages.  Security checks
never catch ``AuthorizationDenied`` and continue; callers must treat it as a
hard stop.
"""

from __future__ import annotations

from typing import Any


class AppError(RuntimeError):
    """Base class for expected application errors."""


class ValidationError(AppError):
    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(AppError):
    def __init__(self, message: str = "记录不存在") -> None:
        super().__init__(message)
        self.message = message


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StorageError(AppError):
    """A database or audit-storage failure."""


class AuthorizationDenied(AppError):
    """Raised when a remote/local operation is not explicitly authorized."""

    def __init__(self, reason: str, code: str = "denied", decision: Any | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.code = code
        self.decision = decision
