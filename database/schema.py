"""Database schema and migrations.

Version 1 is the phase-1 foundation (seven tables).  Version 2 adds the
authorization scope, append-only authorization history and a small key/value
settings table.  Version 3 extends scan tasks and findings for local Python
source auditing.  Version 4 adds structured Finding metadata for dependency
vulnerabilities.  Version 5 adds the complete finding workflow, status history
and the evidence fields required by the vulnerability/evidence centers.
Migrations are forward-only and always create a backup first.
"""

from __future__ import annotations

SCHEMA_VERSION = 5

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS projects (
    project_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name    TEXT NOT NULL CHECK(length(trim(project_name)) BETWEEN 1 AND 120),
    project_type    TEXT NOT NULL CHECK(project_type IN ('local_audit', 'authorized_test', 'combined')),
    description     TEXT NOT NULL DEFAULT '',
    local_path      TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'archived')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_status_created
    ON projects(status, created_at DESC);

CREATE TABLE IF NOT EXISTS authorizations (
    authorization_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id            INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    authorization_source  TEXT NOT NULL,
    authorization_document TEXT NOT NULL DEFAULT '',
    start_time            TEXT NOT NULL,
    end_time              TEXT NOT NULL,
    authorization_status  TEXT NOT NULL DEFAULT 'pending'
                          CHECK(authorization_status IN ('pending', 'confirmed', 'expired', 'revoked')),
    notes                 TEXT NOT NULL DEFAULT '',
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    CHECK(end_time >= start_time)
);
CREATE INDEX IF NOT EXISTS idx_authorizations_project
    ON authorizations(project_id, authorization_status, end_time);

CREATE TABLE IF NOT EXISTS scan_tasks (
    task_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    task_type       TEXT NOT NULL CHECK(task_type IN ('source_audit', 'dependency_audit', 'config_audit')),
    target          TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'blocked')),
    started_at      TEXT,
    finished_at     TEXT,
    result_summary  TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scan_tasks_project
    ON scan_tasks(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS findings (
    finding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id         INTEGER REFERENCES scan_tasks(task_id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT '',
    risk_level      TEXT NOT NULL DEFAULT 'info'
                    CHECK(risk_level IN ('critical', 'high', 'medium', 'low', 'info')),
    affected_scope  TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    remediation     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open', 'confirmed', 'fixed', 'false_positive', 'accepted_risk')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_project
    ON findings(project_id, risk_level, status);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    finding_id      INTEGER REFERENCES findings(finding_id) ON DELETE SET NULL,
    file_path       TEXT NOT NULL,
    file_name       TEXT NOT NULL,
    sha256          TEXT NOT NULL DEFAULT '',
    captured_at     TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_project
    ON evidence(project_id, finding_id);

CREATE TABLE IF NOT EXISTS reports (
    report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    report_format   TEXT NOT NULL CHECK(report_format IN ('html', 'pdf', 'json')),
    file_path       TEXT NOT NULL,
    generated_at    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reports_project
    ON reports(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS scan_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER REFERENCES projects(project_id) ON DELETE SET NULL,
    task_id         INTEGER REFERENCES scan_tasks(task_id) ON DELETE SET NULL,
    event_type      TEXT NOT NULL,
    target          TEXT NOT NULL DEFAULT '',
    operation       TEXT NOT NULL DEFAULT '',
    decision        TEXT NOT NULL CHECK(decision IN ('allow', 'deny', 'info', 'error')),
    message         TEXT NOT NULL DEFAULT '',
    details_json    TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scan_logs_project_created
    ON scan_logs(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_logs_event
    ON scan_logs(event_type, created_at DESC);
"""

MIGRATION_V2 = """
CREATE TABLE IF NOT EXISTS scope_assets (
    asset_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    asset_type          TEXT NOT NULL CHECK(asset_type IN ('domain', 'ip', 'local_folder', 'local_project')),
    asset_value         TEXT NOT NULL,
    authorization_id    INTEGER REFERENCES authorizations(authorization_id) ON DELETE RESTRICT,
    allowed_operations  TEXT NOT NULL DEFAULT '[]',
    asset_status        TEXT NOT NULL DEFAULT 'active' CHECK(asset_status IN ('active', 'inactive')),
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    UNIQUE(project_id, asset_type, asset_value)
);
CREATE INDEX IF NOT EXISTS idx_scope_assets_project
    ON scope_assets(project_id, asset_status, asset_type);
CREATE INDEX IF NOT EXISTS idx_scope_assets_authorization
    ON scope_assets(authorization_id);

CREATE TABLE IF NOT EXISTS authorization_history (
    history_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    authorization_id    INTEGER REFERENCES authorizations(authorization_id) ON DELETE SET NULL,
    action              TEXT NOT NULL,
    change_summary      TEXT NOT NULL DEFAULT '',
    details_json        TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_authorization_history_project
    ON authorization_history(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_authorization_history_auth
    ON authorization_history(authorization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key     TEXT PRIMARY KEY,
    setting_value   TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

# Phase 3 is additive.  Columns are applied through PRAGMA table_info checks so
# a partially interrupted migration can be retried safely.
V3_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "scan_tasks": (
        ("current_scanner", "TEXT NOT NULL DEFAULT ''"),
        ("progress", "INTEGER NOT NULL DEFAULT 0"),
        ("error_message", "TEXT NOT NULL DEFAULT ''"),
        ("scanners_json", "TEXT NOT NULL DEFAULT '[]'"),
        ("cancel_requested", "INTEGER NOT NULL DEFAULT 0"),
        ("cancelled_at", "TEXT"),
    ),
    "findings": (
        ("confidence", "TEXT NOT NULL DEFAULT 'unknown'"),
        ("file_path", "TEXT NOT NULL DEFAULT ''"),
        ("line_number", "INTEGER"),
        ("rule_id", "TEXT NOT NULL DEFAULT ''"),
        ("scanner_name", "TEXT NOT NULL DEFAULT ''"),
        ("scanner_version", "TEXT NOT NULL DEFAULT ''"),
        ("detected_at", "TEXT"),
    ),
}

MIGRATION_V3_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_findings_task
    ON findings(project_id, task_id, risk_level);
CREATE INDEX IF NOT EXISTS idx_findings_scanner
    ON findings(project_id, scanner_name, risk_level);
CREATE INDEX IF NOT EXISTS idx_scan_tasks_status
    ON scan_tasks(project_id, status, created_at DESC);
"""

# Phase 4 stores dependency names, versions, aliases and fix information without
# creating a second finding table.
V4_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "findings": (
        ("metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
    ),
}

# Phase 5 needs the additional "reviewing" workflow state.  SQLite cannot alter
# a CHECK constraint in place, so v5 rebuilds findings in one transaction and
# copies every existing row by id.  The migration runs with foreign keys off
# because evidence.finding_id references findings.
FINDINGS_V5_TABLE = """
CREATE TABLE findings_v5 (
    finding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    task_id         INTEGER REFERENCES scan_tasks(task_id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT '',
    risk_level      TEXT NOT NULL DEFAULT 'info'
                    CHECK(risk_level IN ('critical', 'high', 'medium', 'low', 'info')),
    affected_scope  TEXT NOT NULL DEFAULT '',
    description     TEXT NOT NULL DEFAULT '',
    remediation     TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open', 'reviewing', 'confirmed',
                                     'false_positive', 'fixed', 'accepted_risk')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    confidence      TEXT NOT NULL DEFAULT 'unknown',
    file_path       TEXT NOT NULL DEFAULT '',
    line_number     INTEGER,
    rule_id         TEXT NOT NULL DEFAULT '',
    scanner_name    TEXT NOT NULL DEFAULT '',
    scanner_version TEXT NOT NULL DEFAULT '',
    detected_at     TEXT,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    manual_notes    TEXT NOT NULL DEFAULT '',
    status_changed_at TEXT,
    last_seen_at    TEXT
);
"""

MIGRATION_V5_INDEXES: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_findings_project "
    "ON findings(project_id, risk_level, status)",
    "CREATE INDEX IF NOT EXISTS idx_findings_task "
    "ON findings(project_id, task_id, risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_findings_scanner "
    "ON findings(project_id, scanner_name, risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_findings_status "
    "ON findings(project_id, status, risk_level)",
    "CREATE INDEX IF NOT EXISTS idx_finding_status_history_finding "
    "ON finding_status_history(project_id, finding_id, changed_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_evidence_finding "
    "ON evidence(project_id, finding_id, created_at DESC)",
)

MIGRATION_V5_COPY = """
INSERT INTO findings_v5 (
    finding_id, project_id, task_id, title, category, risk_level,
    affected_scope, description, remediation, status, created_at, updated_at,
    confidence, file_path, line_number, rule_id, scanner_name, scanner_version,
    detected_at, metadata_json
)
SELECT
    finding_id, project_id, task_id, title, category, risk_level,
    affected_scope, description, remediation, status, created_at, updated_at,
    confidence, file_path, line_number, rule_id, scanner_name, scanner_version,
    detected_at, metadata_json
FROM findings;
"""

MIGRATION_V5_BACKFILL = """
UPDATE findings
SET last_seen_at = COALESCE(detected_at, created_at)
WHERE last_seen_at IS NULL;
"""

MIGRATION_V5_HISTORY = """
CREATE TABLE IF NOT EXISTS finding_status_history (
    history_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    finding_id      INTEGER NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,
    from_status     TEXT NOT NULL,
    to_status       TEXT NOT NULL,
    note            TEXT NOT NULL DEFAULT '',
    changed_by      TEXT NOT NULL DEFAULT 'local_user',
    changed_at      TEXT NOT NULL
);
"""

V5_EVIDENCE_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "evidence": (
        ("evidence_type", "TEXT NOT NULL DEFAULT 'other_file'"),
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("source", "TEXT NOT NULL DEFAULT ''"),
    ),
}
