"""Enumerations and Chinese display labels."""

from __future__ import annotations

from enum import Enum


class ProjectType(str, Enum):
    LOCAL_AUDIT = "local_audit"
    AUTHORIZED_TEST = "authorized_test"
    COMBINED = "combined"

    @property
    def label(self) -> str:
        return {
            ProjectType.LOCAL_AUDIT: "本地代码审计",
            ProjectType.AUTHORIZED_TEST: "授权安全测试",
            ProjectType.COMBINED: "综合安全研究",
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "ProjectType"]]:
        return [(item.label, item) for item in cls]


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    @property
    def label(self) -> str:
        return {
            ProjectStatus.ACTIVE: "进行中",
            ProjectStatus.PAUSED: "已暂停",
            ProjectStatus.COMPLETED: "已完成",
            ProjectStatus.ARCHIVED: "已归档",
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "ProjectStatus"]]:
        return [(item.label, item) for item in cls]


class AuthStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    REVOKED = "revoked"

    @property
    def label(self) -> str:
        return {
            AuthStatus.PENDING: "待审核",
            AuthStatus.CONFIRMED: "已确认",
            AuthStatus.EXPIRED: "已过期",
            AuthStatus.REVOKED: "已撤销",
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "AuthStatus"]]:
        return [(item.label, item) for item in cls]


class AssetType(str, Enum):
    DOMAIN = "domain"
    IP = "ip"
    LOCAL_FOLDER = "local_folder"
    LOCAL_PROJECT = "local_project"

    @property
    def label(self) -> str:
        return {
            AssetType.DOMAIN: "域名",
            AssetType.IP: "IP 地址",
            AssetType.LOCAL_FOLDER: "本地文件夹",
            AssetType.LOCAL_PROJECT: "本地源代码项目",
        }[self]

    @property
    def is_remote(self) -> bool:
        return self in (AssetType.DOMAIN, AssetType.IP)

    @classmethod
    def remote_options(cls) -> list[tuple[str, "AssetType"]]:
        return [(item.label, item) for item in cls if item.is_remote]

    @classmethod
    def local_options(cls) -> list[tuple[str, "AssetType"]]:
        return [(item.label, item) for item in cls if not item.is_remote]

    @classmethod
    def options(cls) -> list[tuple[str, "AssetType"]]:
        return [(item.label, item) for item in cls]


class AssetStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

    @property
    def label(self) -> str:
        return {
            AssetStatus.ACTIVE: "启用",
            AssetStatus.INACTIVE: "停用",
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "AssetStatus"]]:
        return [(item.label, item) for item in cls]


class RemoteOperation(str, Enum):
    CONFIG_CHECK = "config_check"

    @property
    def label(self) -> str:
        return {RemoteOperation.CONFIG_CHECK: "非破坏性配置检查"}[self]

    @classmethod
    def options(cls) -> list[tuple[str, "RemoteOperation"]]:
        return [(item.label, item) for item in cls]


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def label(self) -> str:
        return {
            Severity.CRITICAL: "严重",
            Severity.HIGH: "高危",
            Severity.MEDIUM: "中危",
            Severity.LOW: "低危",
            Severity.INFO: "信息",
        }[self]

    @property
    def rank(self) -> int:
        return {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "Severity"]]:
        return [(item.label, item) for item in cls]


class FindingStatus(str, Enum):
    OPEN = "open"
    REVIEWING = "reviewing"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    FIXED = "fixed"
    ACCEPTED_RISK = "accepted_risk"

    @property
    def label(self) -> str:
        return {
            FindingStatus.OPEN: "待处理",
            FindingStatus.REVIEWING: "审核中",
            FindingStatus.CONFIRMED: "已确认",
            FindingStatus.FALSE_POSITIVE: "误报",
            FindingStatus.FIXED: "已修复",
            FindingStatus.ACCEPTED_RISK: "接受风险",
        }[self]

    @property
    def is_terminal(self) -> bool:
        return self in {
            FindingStatus.FALSE_POSITIVE,
            FindingStatus.FIXED,
            FindingStatus.ACCEPTED_RISK,
        }

    @classmethod
    def from_external(cls, value: str | None) -> "FindingStatus":
        normalized = str(value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            return cls.OPEN

    @classmethod
    def options(cls) -> list[tuple[str, "FindingStatus"]]:
        return [(item.label, item) for item in cls]


class EvidenceType(str, Enum):
    CODE_SNIPPET = "code_snippet"
    SCANNER_SUMMARY = "scanner_summary"
    DEPENDENCY_INFO = "dependency_info"
    SCREENSHOT = "screenshot"
    MANUAL_NOTE = "manual_note"
    OTHER_FILE = "other_file"

    @property
    def label(self) -> str:
        return {
            EvidenceType.CODE_SNIPPET: "代码片段",
            EvidenceType.SCANNER_SUMMARY: "扫描器结果摘要",
            EvidenceType.DEPENDENCY_INFO: "依赖漏洞信息",
            EvidenceType.SCREENSHOT: "截图",
            EvidenceType.MANUAL_NOTE: "人工备注",
            EvidenceType.OTHER_FILE: "其他本地证据文件",
        }[self]

    @property
    def requires_file(self) -> bool:
        return self in {EvidenceType.SCREENSHOT, EvidenceType.OTHER_FILE}

    @property
    def is_text(self) -> bool:
        return not self.requires_file

    @classmethod
    def from_external(cls, value: str | None) -> "EvidenceType":
        normalized = str(value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError:
            return cls.OTHER_FILE

    @classmethod
    def options(cls) -> list[tuple[str, "EvidenceType"]]:
        return [(item.label, item) for item in cls]


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

    @property
    def label(self) -> str:
        return {
            Confidence.HIGH: "高",
            Confidence.MEDIUM: "中",
            Confidence.LOW: "低",
            Confidence.UNKNOWN: "未知",
        }[self]

    @classmethod
    def from_external(cls, value: str | None) -> "Confidence":
        normalized = str(value or "").strip().lower()
        if normalized in {"high", "certain"}:
            return cls.HIGH
        if normalized in {"medium", "moderate"}:
            return cls.MEDIUM
        if normalized in {"low", "tentative"}:
            return cls.LOW
        return cls.UNKNOWN

    @classmethod
    def options(cls) -> list[tuple[str, "Confidence"]]:
        return [(item.label, item) for item in cls]


class ScanTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

    @property
    def label(self) -> str:
        return {
            ScanTaskStatus.PENDING: "等待中",
            ScanTaskStatus.RUNNING: "扫描中",
            ScanTaskStatus.COMPLETED: "已完成",
            ScanTaskStatus.FAILED: "失败",
            ScanTaskStatus.CANCELLED: "已取消",
            ScanTaskStatus.BLOCKED: "已阻止",
        }[self]

    @property
    def is_terminal(self) -> bool:
        return self in {
            ScanTaskStatus.COMPLETED,
            ScanTaskStatus.FAILED,
            ScanTaskStatus.CANCELLED,
            ScanTaskStatus.BLOCKED,
        }

    @classmethod
    def options(cls) -> list[tuple[str, "ScanTaskStatus"]]:
        return [(item.label, item) for item in cls]


class ScanTaskType(str, Enum):
    SOURCE_AUDIT = "source_audit"
    DEPENDENCY_AUDIT = "dependency_audit"
    CONFIG_AUDIT = "config_audit"

    @property
    def label(self) -> str:
        return {
            ScanTaskType.SOURCE_AUDIT: "源代码审计",
            ScanTaskType.DEPENDENCY_AUDIT: "依赖漏洞检查",
            ScanTaskType.CONFIG_AUDIT: "安全配置检查",
        }[self]


def enum_by_label(enum_type: type[Enum], label: str) -> Enum:
    """Resolve one of the enums above by its Chinese label."""

    for item in enum_type:  # type: ignore[attr-defined]
        if getattr(item, "label", None) == label:
            return item
    raise ValueError(f"未知选项: {label}")
