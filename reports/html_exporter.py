"""Safe, local-only HTML rendering for report snapshots.

The exporter has one security boundary:

    ReportSnapshot
        -> allowlisted view model (no ORM/domain objects)
        -> fixed Jinja2 template with autoescape
        -> UTF-8 HTML
        -> atomic write inside AppConfig.reports_dir

It never imports the database, the repository or a scanner.  It never reads
evidence files.  HTML rendering and file writing are separate functions so a
future GUI can preview a string without writing a file.
"""

from __future__ import annotations

import errno
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

from core.errors import ValidationError
from core.models.enums import (
    EvidenceType,
    FindingStatus,
    ScanTaskStatus,
    Severity,
)
from core.models.report import (
    ReportArtifact,
    ReportAuthorizationSummary,
    ReportEvidence,
    ReportFinding,
    ReportFormat,
    ReportRequest,
    ReportSnapshot,
    ReportStats,
    ReportTaskSummary,
    ReportType,
)
from core.timeutil import ensure_aware_utc

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_TEMPLATE_NAMES = {
    ReportType.VULNERABILITY: "vulnerability.html",
    ReportType.EVIDENCE: "evidence.html",
    ReportType.PROJECT_SUMMARY: "project_summary.html",
}

_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR), encoding="utf-8"),
    autoescape=True,
    auto_reload=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)

_MAX_TITLE = 200
_MAX_FIELD = 2_000
_MAX_PATH = 300
_MAX_LIST_ITEMS = 100
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_INVALID_FILENAME_CHARS = frozenset('?*<>|"')
_WINDOWS_RESERVED_NAMES = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "CLOCK$",
        "CONIN$",
        "CONOUT$",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    }
)


class ReportExportError(RuntimeError):
    """Raised when a snapshot cannot be rendered or written safely."""


@dataclass(frozen=True, slots=True)
class CountView:
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class ProjectView:
    project_id: int
    name: str
    type_label: str
    status_label: str


@dataclass(frozen=True, slots=True)
class AuthorizationView:
    as_of: str
    total_count: int
    effective_count: int
    confirmed_count: int
    expired_count: int
    pending_count: int
    revoked_count: int
    scope_asset_count: int
    active_scope_asset_count: int
    has_effective_authorization: bool
    historical_scan_authorization_available: bool
    note: str


@dataclass(frozen=True, slots=True)
class TaskView:
    task_id: int
    type_label: str
    status_label: str
    started_at: str
    finished_at: str
    created_at: str
    progress: int
    scanners_text: str


@dataclass(frozen=True, slots=True)
class FindingView:
    finding_id: int
    title: str
    category: str
    description: str
    severity_label: str
    severity_source: str
    confidence_label: str
    scanner_text: str
    rule_id: str
    source_path: str
    line_display: str
    recommendation: str
    status_label: str
    manual_notes: str
    detected_at: str
    last_seen_at: str
    dependency_name: str
    dependency_version: str
    vulnerability_id: str
    fix_versions_text: str
    affected_versions: str
    evidence_count: int

    @property
    def has_dependency(self) -> bool:
        return bool(
            self.dependency_name
            or self.dependency_version
            or self.vulnerability_id
            or self.fix_versions_text
            or self.affected_versions
        )


@dataclass(frozen=True, slots=True)
class EvidenceView:
    evidence_id: int
    finding_id: int
    finding_title: str
    type_label: str
    title: str
    description: str
    file_name: str
    file_hash: str
    source_text: str
    captured_at: str
    file_status_note: str
    file_exists_text: str
    hash_matches_text: str

    @property
    def has_file(self) -> bool:
        return bool(self.file_name or self.file_hash or self.file_status_note)

    @property
    def has_finding(self) -> bool:
        return self.finding_id > 0


@dataclass(frozen=True, slots=True)
class StatsView:
    task_count: int
    finding_count: int
    evidence_count: int
    dependency_finding_count: int
    file_evidence_count: int
    missing_evidence_file_count: int
    hash_mismatch_count: int
    task_status_counts: tuple[CountView, ...]
    task_scanner_counts: tuple[CountView, ...]
    severity_counts: tuple[CountView, ...]
    scanner_counts: tuple[CountView, ...]
    finding_status_counts: tuple[CountView, ...]
    evidence_type_counts: tuple[CountView, ...]


@dataclass(frozen=True, slots=True)
class ReportView:
    title: str
    report_type_label: str
    project: ProjectView
    authorization: AuthorizationView
    tasks: tuple[TaskView, ...]
    findings: tuple[FindingView, ...]
    evidence: tuple[EvidenceView, ...]
    stats: StatsView
    generated_at: str
    snapshot_id: str
    snapshot_short: str
    schema_version: int
    data_scope: tuple[str, ...]
    warnings: tuple[str, ...]
    known_limitations: tuple[str, ...]
    notes_included: bool
    evidence_images_requested: bool
    evidence_images_embedded: bool
    image_notice: str
    linked_finding_count: int

    @property
    def has_tasks(self) -> bool:
        return bool(self.tasks)

    @property
    def has_findings(self) -> bool:
        return bool(self.findings)

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


def build_report_view_model(
    snapshot: ReportSnapshot,
    request: ReportRequest | None = None,
) -> ReportView:
    """Project a snapshot into the only object templates are allowed to see."""

    if not isinstance(snapshot, ReportSnapshot):
        raise ValidationError("报告快照类型无效")
    if request is not None:
        _validate_request(snapshot, request)

    include_notes = request.include_notes if request is not None else True
    images_requested = (
        bool(request.include_evidence_images) if request is not None else False
    )
    title = _request_title(snapshot, request)
    warnings = list(_bounded_sequence(snapshot.warnings))
    image_notice = ""
    if images_requested:
        image_notice = _bounded_text(
            "本阶段不读取或嵌入证据图片；即使请求了 include_evidence_images，"
            "报告也不会展示原始证据文件。"
        )
        warnings.append(image_notice)
    if not include_notes:
        warnings.append(
            _bounded_text("本报告未包含人工备注（按报告请求的 include_notes=False）。")
        )

    findings = _select_findings(snapshot)
    evidence = _select_evidence(snapshot)
    linked_ids = {item.finding_id for item in evidence if item.finding_id > 0}
    if snapshot.report_type is ReportType.EVIDENCE:
        findings = tuple(
            item for item in snapshot.findings if item.finding_id in linked_ids
        )

    return ReportView(
        title=title,
        report_type_label=snapshot.report_type.label,
        project=_project_view(snapshot.project),
        authorization=_authorization_view(snapshot.authorization),
        tasks=tuple(_task_view(item) for item in snapshot.tasks),
        findings=tuple(_finding_view(item, include_notes=include_notes) for item in findings),
        evidence=tuple(_evidence_view(item) for item in evidence),
        stats=_stats_view(snapshot.stats),
        generated_at=_format_dt(snapshot.generated_at),
        snapshot_id=snapshot.snapshot_id,
        snapshot_short=snapshot.snapshot_id[:12],
        schema_version=snapshot.schema_version,
        data_scope=_bounded_sequence(snapshot.data_scope),
        warnings=_bounded_sequence(warnings),
        known_limitations=_bounded_sequence(snapshot.known_limitations),
        notes_included=include_notes,
        evidence_images_requested=images_requested,
        evidence_images_embedded=False,
        image_notice=image_notice,
        linked_finding_count=len(linked_ids),
    )


def render_html(
    snapshot: ReportSnapshot,
    request: ReportRequest | None = None,
) -> str:
    """Render one snapshot to a UTF-8 HTML string; never writes a file."""

    view = build_report_view_model(snapshot, request)
    try:
        template = _ENV.get_template(_TEMPLATE_NAMES[snapshot.report_type])
        rendered = template.render(view=view)
    except (KeyError, TemplateError) as exc:
        raise ReportExportError(f"HTML 报告渲染失败: {exc}") from exc
    if not isinstance(rendered, str):
        raise ReportExportError("HTML 报告渲染结果不是字符串")
    return rendered


def write_html_report(
    snapshot: ReportSnapshot,
    request: ReportRequest,
    reports_dir: str | Path,
    *,
    overwrite: bool = False,
    filename: str | None = None,
) -> ReportArtifact:
    """Render and atomically write one HTML report under ``reports_dir``.

    ``overwrite=False`` is the default and refuses to replace an existing file.
    The caller is responsible for asking the user before passing ``True``.

    The raw leaf is checked for symlink/junction *before* any leaf resolution.
    This prevents a same-directory symlink from redirecting the write to a
    different file (including a broken link's missing target).
    """

    if not isinstance(request, ReportRequest):
        raise ValidationError("报告请求类型无效")
    html = render_html(snapshot, request)
    root = _resolve_reports_root(reports_dir)
    target_name = _validate_filename(filename or _default_filename(snapshot))
    candidate = root / target_name
    if candidate.parent != root:
        raise ValidationError("报告目标必须直接位于 reports_dir")
    try:
        is_link_like = candidate.is_symlink() or getattr(
            candidate, "is_junction", lambda: False
        )()
    except OSError as exc:
        raise ValidationError("无法确认报告目标类型") from exc
    if is_link_like:
        raise ValidationError("报告目标不能是符号链接或 junction")

    # Keep the raw leaf.  Resolving it here would follow an internal symlink
    # and make the atomic writer replace the symlink's target instead.
    target = candidate
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValidationError("报告目标路径越界") from exc
    if target.parent != root:
        raise ValidationError("报告目标必须直接位于 reports_dir")
    if target.exists() and not overwrite:
        raise FileExistsError(f"目标报告已存在，未覆盖: {target}")
    if target.exists() and target.is_dir():
        raise ValidationError("报告目标不是文件")

    payload = html.encode("utf-8")
    sha256 = hashlib.sha256(payload).hexdigest()
    _atomic_write(target, payload, overwrite=overwrite)
    view = build_report_view_model(snapshot, request)
    return ReportArtifact(
        report_type=snapshot.report_type,
        report_format=ReportFormat.HTML,
        project_id=snapshot.project.project_id,
        title=view.title,
        generated_at=snapshot.generated_at,
        snapshot_id=snapshot.snapshot_id,
        path=str(target),
        sha256=sha256,
        warnings=view.warnings,
    )


def _select_findings(snapshot: ReportSnapshot) -> tuple[ReportFinding, ...]:
    if snapshot.report_type is ReportType.EVIDENCE:
        return ()
    return snapshot.findings


def _select_evidence(snapshot: ReportSnapshot) -> tuple[ReportEvidence, ...]:
    if snapshot.report_type is ReportType.VULNERABILITY:
        return ()
    return snapshot.evidence


def _validate_request(snapshot: ReportSnapshot, request: ReportRequest) -> None:
    if request.project_id != snapshot.project.project_id:
        raise ValidationError("报告请求的项目与快照不一致")
    if request.report_type is not snapshot.report_type:
        raise ValidationError("报告请求的类型与快照不一致")
    if request.report_format is not ReportFormat.HTML:
        raise ValidationError("本阶段仅支持 HTML 报告")


def _request_title(snapshot: ReportSnapshot, request: ReportRequest | None) -> str:
    candidate = _single_line_text(request.title if request is not None else "", _MAX_TITLE)
    if candidate:
        return candidate
    return _single_line_text(
        f"{snapshot.report_type.label} · {snapshot.project.project_name}",
        _MAX_TITLE,
    )


def _project_view(project) -> ProjectView:
    return ProjectView(
        project_id=project.project_id,
        name=_bounded_text(project.project_name),
        type_label=project.project_type.label,
        status_label=project.status.label,
    )


def _authorization_view(
    authorization: ReportAuthorizationSummary,
) -> AuthorizationView:
    return AuthorizationView(
        as_of=_format_dt(authorization.as_of),
        total_count=authorization.total_count,
        effective_count=authorization.effective_count,
        confirmed_count=authorization.confirmed_count,
        expired_count=authorization.expired_count,
        pending_count=authorization.pending_count,
        revoked_count=authorization.revoked_count,
        scope_asset_count=authorization.scope_asset_count,
        active_scope_asset_count=authorization.active_scope_asset_count,
        has_effective_authorization=authorization.has_effective_authorization,
        historical_scan_authorization_available=(
            authorization.historical_scan_authorization_available
        ),
        note=_bounded_text(authorization.note),
    )


def _task_view(task: ReportTaskSummary) -> TaskView:
    scanners = ", ".join(str(item) for item in task.scanners if str(item).strip())
    return TaskView(
        task_id=task.task_id,
        type_label=task.task_type.label,
        status_label=task.status.label,
        started_at=_format_dt(task.started_at),
        finished_at=_format_dt(task.finished_at),
        created_at=_format_dt(task.created_at),
        progress=int(task.progress),
        scanners_text=_bounded_text(scanners) or "—",
    )


def _finding_view(finding: ReportFinding, *, include_notes: bool) -> FindingView:
    scanner = " ".join(
        item
        for item in (finding.scanner_name.strip(), finding.scanner_version.strip())
        if item
    )
    return FindingView(
        finding_id=finding.finding_id,
        title=_bounded_text(finding.title),
        category=_bounded_text(finding.category),
        description=_bounded_text(finding.description),
        severity_label=finding.severity.label,
        severity_source=_bounded_text(finding.severity_source),
        confidence_label=finding.confidence.label,
        scanner_text=_bounded_text(scanner) or "—",
        rule_id=_bounded_text(finding.rule_id) or "—",
        source_path=_safe_relative_path(finding.file_path) or "—",
        line_display=finding.line_display,
        recommendation=_bounded_text(finding.recommendation),
        status_label=finding.status.label,
        manual_notes=(
            _bounded_text(finding.manual_notes) if include_notes else ""
        ),
        detected_at=_format_dt(finding.detected_at),
        last_seen_at=_format_dt(finding.last_seen_at),
        dependency_name=_bounded_text(finding.dependency_name or ""),
        dependency_version=_bounded_text(finding.dependency_version or ""),
        vulnerability_id=_bounded_text(finding.vulnerability_id or ""),
        fix_versions_text=_bounded_text(", ".join(finding.fix_versions)),
        affected_versions=_bounded_text(finding.affected_versions or ""),
        evidence_count=int(finding.evidence_count),
    )


def _evidence_view(evidence: ReportEvidence) -> EvidenceView:
    return EvidenceView(
        evidence_id=evidence.evidence_id,
        finding_id=evidence.finding_id,
        finding_title=_bounded_text(evidence.finding_title),
        type_label=evidence.evidence_type.label,
        title=_bounded_text(evidence.display_title),
        description=_bounded_text(evidence.description),
        file_name=_safe_file_name(evidence.file_name),
        file_hash=_bounded_text(evidence.file_hash),
        source_text=_safe_relative_path(evidence.source),
        captured_at=_format_dt(evidence.captured_at),
        file_status_note=_bounded_text(evidence.file_status_note),
        file_exists_text=_optional_bool_label(evidence.file_exists),
        hash_matches_text=_optional_bool_label(evidence.hash_matches),
    )


def _stats_view(stats: ReportStats | None) -> StatsView:
    data = stats or ReportStats()
    return StatsView(
        task_count=int(data.task_count),
        finding_count=int(data.finding_count),
        evidence_count=int(data.evidence_count),
        dependency_finding_count=int(data.dependency_finding_count),
        file_evidence_count=int(data.file_evidence_count),
        missing_evidence_file_count=int(data.missing_evidence_file_count),
        hash_mismatch_count=int(data.hash_mismatch_count),
        task_status_counts=_count_views(data.task_status_counts, ScanTaskStatus),
        task_scanner_counts=_named_count_views(data.task_scanner_counts),
        severity_counts=_count_views(data.severity_counts, Severity),
        scanner_counts=_named_count_views(data.scanner_counts),
        finding_status_counts=_count_views(data.finding_status_counts, FindingStatus),
        evidence_type_counts=_count_views(data.evidence_type_counts, EvidenceType),
    )


def _count_views(
    values: Mapping[str, int],
    enum_type: type,
    *,
    include_zero: bool = True,
) -> tuple[CountView, ...]:
    result: list[CountView] = []
    known: set[str] = set()
    for item in enum_type:
        known.add(item.value)
        count = _int_value(values.get(item.value, 0))
        if include_zero or count:
            result.append(CountView(item.label, count))
    for key in sorted(set(values) - known):
        count = _int_value(values.get(key, 0))
        if include_zero or count:
            result.append(CountView(str(key), count))
    return tuple(result)


def _named_count_views(values: Mapping[str, int]) -> tuple[CountView, ...]:
    return tuple(
        CountView(str(key), _int_value(values.get(key, 0)))
        for key in sorted(values)
        if _int_value(values.get(key, 0))
    )


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    try:
        moment = ensure_aware_utc(value)
    except (TypeError, ValueError):
        return "—"
    return moment.strftime("%Y-%m-%d %H:%M:%S UTC")


def _optional_bool_label(value: bool | None) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    return "未校验"


def _bounded_text(value: Any, limit: int = _MAX_FIELD) -> str:
    text = _CONTROL_CHARS_RE.sub("", str(value or "")).strip()
    if len(text) > limit:
        return text[: max(0, limit - 1)] + "…"
    return text


def _single_line_text(value: Any, limit: int = _MAX_TITLE) -> str:
    text = _bounded_text(value, limit)
    return re.sub(r"\s+", " ", text).strip()


def _bounded_sequence(
    values: Any,
    *,
    limit: int = _MAX_FIELD,
    max_items: int = _MAX_LIST_ITEMS,
) -> tuple[str, ...]:
    result: list[str] = []
    for item in values or ():
        text = _single_line_text(item, limit)
        if text:
            result.append(text)
        if len(result) >= max_items:
            break
    return tuple(result)


def _safe_relative_path(value: Any) -> str:
    """Return a relative display path, or empty for absolute/traversal paths."""

    text = _bounded_text(value, _MAX_PATH).replace("\\", "/")
    if not text:
        return ""
    if text.startswith("/") or text.startswith("//"):
        return ""
    if ":" in text.split("/", 1)[0]:
        return ""
    if any(part == ".." for part in text.split("/")):
        return ""
    return text


def _safe_file_name(value: Any) -> str:
    text = _bounded_text(value, _MAX_PATH).replace("\\", "/")
    if not text:
        return ""
    name = text.rsplit("/", 1)[-1].strip()
    if name in {"", ".", ".."}:
        return ""
    return name[:200]


def _resolve_reports_root(reports_dir: str | Path) -> Path:
    root = Path(reports_dir).expanduser()
    if not root.is_absolute():
        raise ValidationError("报告输出目录必须是绝对路径")
    if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
        raise ValidationError("报告输出目录不能是符号链接或 junction")
    root = root.resolve()
    if root.exists() and not root.is_dir():
        raise ValidationError("报告输出目录不是目录")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportExportError(f"无法创建报告输出目录: {exc}") from exc
    return root


def _validate_filename(filename: str) -> str:
    name = str(filename).strip()
    if not name:
        raise ValidationError("报告文件名不能为空")
    if any(char in name for char in ("/", "\\", ":")):
        raise ValidationError("报告文件名不能包含路径分隔符")
    if any(char in _INVALID_FILENAME_CHARS for char in name):
        raise ValidationError("报告文件名包含 Windows 非法字符")
    if name in {".", ".."}:
        raise ValidationError("报告文件名无效")
    if not name.lower().endswith(".html"):
        raise ValidationError("HTML 报告文件名必须以 .html 结尾")
    if len(name) > 180:
        raise ValidationError("报告文件名过长")
    if re.search(r"[\x00-\x1f\x7f]", name):
        raise ValidationError("报告文件名包含非法字符")
    device_stem = name.split(".", 1)[0].rstrip(" .").upper()
    if device_stem in _WINDOWS_RESERVED_NAMES:
        raise ValidationError("报告文件名不能使用 Windows 保留设备名")
    return name


def _default_filename(snapshot: ReportSnapshot) -> str:
    safe_snapshot = "".join(
        char for char in snapshot.snapshot_id if char.isalnum()
    )[:12]
    return (
        f"project_{snapshot.project.project_id}_"
        f"{snapshot.report_type.value}_{safe_snapshot}.html"
    )


def _publish_exclusive(temporary: Path, target: Path) -> None:
    """Publish ``temporary`` without ever replacing an existing target.

    ``os.link`` is used because both POSIX ``link(2)`` and Windows
    ``CreateHardLinkW`` fail atomically when the target already exists.  It is
    intentionally not followed by an unsafe ``os.replace`` fallback: if the
    platform or filesystem cannot create a hard link, the export fails closed.
    """

    if not hasattr(os, "link"):
        raise ReportExportError(
            "当前平台不支持安全的原子排他发布（硬链接）；报告未写入"
        )
    try:
        os.link(temporary, target)
    except FileExistsError as exc:
        raise FileExistsError(f"目标报告已存在，未覆盖: {target}") from exc
    except OSError as exc:
        if exc.errno == errno.EEXIST or getattr(exc, "winerror", None) in (80, 183):
            raise FileExistsError(f"目标报告已存在，未覆盖: {target}") from exc
        raise ReportExportError(
            "无法在不覆盖现有文件的前提下原子创建报告；"
            "当前平台或文件系统不支持硬链接排他发布，报告未写入。"
        ) from exc


def _atomic_write(target: Path, payload: bytes, *, overwrite: bool) -> None:
    fd: int | None = None
    temporary: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=str(target.parent),
        )
        temporary = Path(temporary_name)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, target)
            temporary = None
        else:
            _publish_exclusive(temporary, target)
            try:
                temporary.unlink()
            except OSError:
                pass
            temporary = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
