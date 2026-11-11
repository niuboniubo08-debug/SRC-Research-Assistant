"""Project-scoped evidence management with strict local-file validation."""

from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path

from core.errors import AuthorizationDenied, StorageError, ValidationError
from core.models import Evidence, EvidenceType
from core.timeutil import utc_now
from database.connection import Database
from repositories.evidence_repository import EvidenceRepository
from repositories.vulnerability_repository import VulnerabilityRepository
from security.scope_validator import ScopeValidator
from services.audit_service import AuditLogService
from services.project_service import ProjectService

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 20000
MAX_SOURCE_LENGTH = 500
MAX_FILE_BYTES = 50 * 1024 * 1024
SENSITIVE_WARNING = (
    "证据可能包含密钥、凭据、个人信息或客户数据。保存前请人工确认并脱敏；"
    "本软件不会自动上传或执行证据。"
)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class EvidenceService:
    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        project_service: ProjectService,
        scope_validator: ScopeValidator,
        evidence_repository: EvidenceRepository,
        vulnerability_repository: VulnerabilityRepository,
        evidence_root: str | Path,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._projects = project_service
        self._validator = scope_validator
        self._evidence = evidence_repository
        self._findings = vulnerability_repository
        self._root = Path(evidence_root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    @property
    def evidence_root(self) -> Path:
        return self._root

    # ------------------------------------------------------------------ queries
    def list_evidence(
        self,
        *,
        project_id: int | None = None,
        finding_id: int | None = None,
        evidence_type: EvidenceType | str | None = None,
        keyword: str = "",
        limit: int = 1000,
    ) -> list[Evidence]:
        if project_id is not None:
            self._projects.get_project(int(project_id))
        if finding_id is not None:
            if project_id is None:
                raise ValidationError("按漏洞筛选证据时必须指定项目")
            self._findings.get_finding(project_id, finding_id)
        type_value = self._coerce_type_filter(evidence_type)
        query = str(keyword or "").strip()
        if len(query) > 200:
            raise ValidationError("搜索关键词不能超过 200 个字符")
        return self._evidence.list_evidence(
            project_id=project_id,
            finding_id=finding_id,
            evidence_type=type_value,
            keyword=query,
            limit=limit,
        )

    def get_evidence(self, project_id: int, evidence_id: int) -> Evidence:
        self._projects.get_project(int(project_id))
        return self._evidence.get_evidence(project_id, evidence_id)

    def count(self, project_id: int | None = None, finding_id: int | None = None) -> int:
        return self._evidence.count(project_id, finding_id)

    # ------------------------------------------------------------------ writes
    def add_evidence(
        self,
        project_id: int,
        finding_id: int,
        evidence_type: EvidenceType | str,
        title: str,
        description: str = "",
        *,
        source_path: str | Path | None = None,
        source: str = "manual",
    ) -> Evidence:
        kind = self._require_type(evidence_type)
        project = self._projects.get_project(int(project_id))
        self._findings.get_finding(project_id, finding_id)
        clean_title = str(title or "").strip()
        if not clean_title:
            raise ValidationError("证据标题不能为空")
        if len(clean_title) > MAX_TITLE_LENGTH:
            raise ValidationError(f"证据标题不能超过 {MAX_TITLE_LENGTH} 个字符")
        content = str(description or "")
        if len(content) > MAX_DESCRIPTION_LENGTH:
            raise ValidationError(
                f"证据内容不能超过 {MAX_DESCRIPTION_LENGTH} 个字符"
            )
        clean_source = str(source or "manual").strip()[:MAX_SOURCE_LENGTH]
        file_path = ""
        file_name = ""
        file_hash = ""
        copied: Path | None = None
        if kind.requires_file:
            if not source_path:
                raise ValidationError("该证据类型必须选择本地文件")
            source_file, relative = self._validate_source_file(project, Path(source_path))
            copied, file_hash = self._copy_into_evidence_store(
                project.project_id, source_file
            )
            file_path = str(copied)
            file_name = source_file.name
            clean_source = relative.as_posix()[:MAX_SOURCE_LENGTH]
        else:
            if source_path:
                raise ValidationError("文本证据不能同时附加文件")
            clean_source = clean_source or "manual"
        now = self._clock()
        try:
            evidence = self._evidence.create_evidence(
                project_id=project.project_id,
                finding_id=finding_id,
                evidence_type=kind,
                title=clean_title,
                description=content,
                file_path=file_path,
                file_name=file_name,
                file_hash=file_hash,
                captured_at=now,
                source=clean_source,
                created_at=now,
            )
        except Exception:
            if copied is not None:
                self._unlink_managed(copied)
            raise
        self._audit.record(
            event_type="evidence_created",
            target=f"evidence:{evidence.evidence_id}",
            operation="evidence_management",
            decision="info",
            message=f"添加证据：{clean_title}",
            details={
                "evidence_id": evidence.evidence_id,
                "finding_id": finding_id,
                "evidence_type": kind.value,
                "has_file": bool(file_path),
                "file_name": file_name,
                "sha256": file_hash,
                "source": clean_source,
            },
            project_id=project.project_id,
        )
        return evidence

    def delete_evidence(self, project_id: int, evidence_id: int) -> Evidence:
        self._projects.get_project(int(project_id))
        evidence = self._evidence.delete_evidence(project_id, evidence_id)
        removed = False
        if evidence.file_path:
            removed = self._unlink_managed(Path(evidence.file_path))
        self._audit.record(
            event_type="evidence_deleted",
            target=f"evidence:{evidence_id}",
            operation="evidence_management",
            decision="info",
            message=f"删除证据：{evidence.display_title}",
            details={
                "evidence_id": evidence_id,
                "finding_id": evidence.finding_id,
                "file_removed": removed,
                "source_file_untouched": True,
            },
            project_id=project_id,
        )
        return evidence

    # ------------------------------------------------------------------ file security
    def _validate_source_file(self, project, source: Path) -> tuple[Path, Path]:
        if not str(source).strip():
            raise ValidationError("证据文件路径不能为空")
        candidate = source.expanduser()
        if not candidate.is_absolute():
            raise ValidationError("证据文件必须使用绝对路径")
        project_path = str(project.local_path or "").strip()
        if not project_path:
            raise ValidationError("当前项目未配置本地路径，不能导入证据文件")
        decision = self._validator.check_local_path(
            project.project_id, project_path, operation="evidence_import"
        )
        if not decision.allowed:
            raise AuthorizationDenied(
                f"证据文件未通过本地路径校验：{decision.reason}",
                decision.code,
                decision,
            )
        root = Path(decision.target).resolve()
        try:
            if candidate.is_symlink():
                raise ValidationError("不跟随符号链接读取证据文件")
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ValidationError("证据文件不存在或不可访问") from exc
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise ValidationError("证据文件必须位于当前项目授权根目录内") from exc
        if not resolved.is_file():
            raise ValidationError("证据路径必须是文件")
        try:
            size = resolved.stat().st_size
        except OSError as exc:
            raise ValidationError("无法读取证据文件属性") from exc
        if size > MAX_FILE_BYTES:
            raise ValidationError(
                f"证据文件超过 {MAX_FILE_BYTES // (1024 * 1024)} MB 限制"
            )
        return resolved, relative

    def _copy_into_evidence_store(
        self, project_id: int, source: Path
    ) -> tuple[Path, str]:
        project_dir = self._root / f"project_{int(project_id)}"
        try:
            project_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"无法创建证据目录：{exc}") from exc
        safe_name = _SAFE_NAME.sub("_", source.name).strip("._-")[:120] or "evidence"
        target = project_dir / f"{uuid.uuid4().hex}_{safe_name}"
        try:
            shutil.copy2(source, target)
            digest = sha256_file(target)
        except OSError as exc:
            self._unlink_managed(target)
            raise StorageError(f"复制证据文件失败：{exc}") from exc
        if target.parent.resolve() != project_dir.resolve():
            self._unlink_managed(target)
            raise StorageError("证据文件复制目标越界")
        return target.resolve(), digest

    def _unlink_managed(self, path: Path) -> bool:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(self._root)
        except (OSError, ValueError):
            return False
        try:
            if resolved.is_symlink():
                resolved.unlink()
            elif resolved.is_file():
                resolved.unlink()
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _require_type(value: EvidenceType | str) -> EvidenceType:
        try:
            return value if isinstance(value, EvidenceType) else EvidenceType(str(value))
        except ValueError as exc:
            raise ValidationError("证据类型无效") from exc

    @staticmethod
    def _coerce_type_filter(value: EvidenceType | str | None) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            return (
                value if isinstance(value, EvidenceType) else EvidenceType(str(value))
            ).value
        except ValueError as exc:
            raise ValidationError("证据类型筛选值无效") from exc
