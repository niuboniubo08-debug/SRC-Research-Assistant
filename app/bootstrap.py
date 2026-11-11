"""Composition root for configuration, persistence and services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.config import AppConfig, application_root
from core.logging_setup import configure_logging
from core.timeutil import utc_now
from database.connection import Database
from repositories.evidence_repository import EvidenceRepository
from repositories.report_repository import ReportRepository
from repositories.vulnerability_repository import VulnerabilityRepository
from scanners.bandit_scanner import BanditScanner
from scanners.pip_audit_scanner import PipAuditScanner
from scanners.semgrep_scanner import SemgrepScanner
from security.scope_validator import ScopeValidator
from services.audit_service import AuditLogService
from services.authorization_service import AuthorizationService
from services.dependency_audit_service import DependencyAuditService
from services.evidence_service import EvidenceService
from services.project_service import ProjectService
from services.report_service import ReportService
from services.scan_service import ScanService
from services.scope_asset_service import ScopeAssetService
from services.vulnerability_service import VulnerabilityService


@dataclass(slots=True)
class AppContext:
    config: AppConfig
    database: Database
    audit: AuditLogService
    project_service: ProjectService
    authorization_service: AuthorizationService
    scope_service: ScopeAssetService
    scope_validator: ScopeValidator
    scan_service: ScanService
    dependency_service: DependencyAuditService
    vulnerability_service: VulnerabilityService
    evidence_service: EvidenceService
    report_service: ReportService
    clock: Callable[[], datetime]

    def database_summary(self) -> dict[str, object]:
        healthy, message = self.database.health_check()
        return {
            "healthy": healthy,
            "message": message,
            "path": str(self.config.database_path),
            "schema_version": self.database.schema_version(),
            "tables": self.database.table_names(),
        }


def build_context(
    config_path: str | Path | None = None,
    *,
    clock=utc_now,
    initialize: bool = True,
    expire_overdue: bool = True,
) -> AppContext:
    config = AppConfig.load(config_path)
    config.ensure_directories()
    configure_logging(config.logs_dir)

    database = Database(config.database_path)
    if initialize:
        database.initialize()

    audit = AuditLogService(database, config.logs_dir, clock=clock)
    project_service = ProjectService(database, audit, clock=clock)
    authorization_service = AuthorizationService(database, audit, clock=clock)
    scope_service = ScopeAssetService(
        database, audit, authorization_service, clock=clock
    )
    scope_validator = ScopeValidator(database, audit, clock=clock)
    rules_path = application_root() / "scanners" / "rules" / "python_security.yml"
    scanners = [
        BanditScanner(clock=clock),
        SemgrepScanner(rules_path=rules_path, clock=clock),
    ]
    scan_service = ScanService(
        database,
        audit,
        scope_validator,
        project_service,
        scanners,
        clock=clock,
    )
    pip_audit_scanner = PipAuditScanner(
        cache_dir=config.storage_root / "cache" / "pip-audit",
        temp_dir=config.storage_root / "tmp" / "pip-audit",
        clock=clock,
    )
    dependency_service = DependencyAuditService(
        database,
        audit,
        scope_validator,
        project_service,
        pip_audit_scanner,
        work_dir=config.storage_root / "tmp" / "dependency-audit",
        clock=clock,
    )
    vulnerability_repository = VulnerabilityRepository(database)
    evidence_repository = EvidenceRepository(database)
    vulnerability_service = VulnerabilityService(
        database,
        audit,
        project_service,
        vulnerability_repository,
        evidence_repository,
        clock=clock,
    )
    evidence_service = EvidenceService(
        database,
        audit,
        project_service,
        scope_validator,
        evidence_repository,
        vulnerability_repository,
        config.evidence_dir,
        clock=clock,
    )
    report_repository = ReportRepository(database, clock=clock)
    report_service = ReportService(
        database,
        report_repository,
        evidence_root=config.evidence_dir,
        clock=clock,
    )

    context = AppContext(
        config=config,
        database=database,
        audit=audit,
        project_service=project_service,
        authorization_service=authorization_service,
        scope_service=scope_service,
        scope_validator=scope_validator,
        scan_service=scan_service,
        dependency_service=dependency_service,
        vulnerability_service=vulnerability_service,
        evidence_service=evidence_service,
        report_service=report_service,
        clock=clock,
    )
    if initialize and expire_overdue:
        authorization_service.expire_overdue_authorizations()
    return context
