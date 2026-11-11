# Phase 6 B Architecture — Read-only Report Data Boundary

## 1. Position in the application

```text
ReportService
└── ReportRepository
    └── Database
```

The data boundary is intentionally separate from exporters. Phase B does not
render or write any report file.

```text
ReportRequest / ReportType / ReportFormat
                 │
                 ▼
          ReportService
   ├─ snapshot policy and data scope
   ├─ authorization / task / finding / evidence statistics
   ├─ evidence managed-path and SHA-256 checks
   └─ warnings and known limitations
                 │
                 ▼
        ReportRepository
   ├─ one Database.connection()
   ├─ PRAGMA query_only = ON
   ├─ BEGIN
   ├─ explicit-column SELECTs filtered by project_id
   ├─ DTO construction inside the read transaction
   └─ rollback + close
                 │
                 ▼
          ProjectSnapshot
```

No UI, scanner, exporter or report-table writer is part of phase B.

## 2. Report DTOs

### Enumerations

- `ReportType`: `vulnerability`, `evidence`, `project_summary`
- `ReportFormat`: `html`, `pdf`, `json`

`ReportFormat` is metadata only in phase B; no export code consumes it yet.

### ReportRequest

```python
@dataclass(frozen=True, slots=True)
class ReportRequest:
    project_id: int
    report_type: ReportType
    report_format: ReportFormat
    title: str = ""
    include_evidence_images: bool = False
    include_notes: bool = True
    requested_at: datetime | None = None
```

### ReportFinding

Fields include identity/project/task, title/category/description, severity and
`severity_source`, confidence, scanner/version, rule/file/line,
recommendation, status/notes, detected/last-seen times, dependency fields,
evidence count and a filtered metadata mapping.

Key truth-preservation rules:

- dependency fields are `None` or empty tuples when absent;
- `vulnerability_id` is only taken from metadata; it does not reuse a Bandit
  or Semgrep rule ID;
- only allowlisted metadata is carried, with `raw_metadata_omitted` marking a
  removed field;
- list metadata values are frozen to tuples.

### ReportEvidence

Fields include evidence/project/finding identity, finding title, type, title,
description, file name/source, database file path, managed path, SHA-256,
timestamps and file verification states.

- `file_exists=None`: no file or not checked;
- `file_exists=False`: checked and missing/outside/unsafe;
- `hash_matches=None`: no stored hash or unreadable;
- `hash_matches=False`: actual SHA-256 differs.

### Other DTOs

- `ReportTaskSummary`: task identity, type, target, status, timestamps,
  summary, error, progress, scanners and current scanner.
- `ReportAuthorizationSummary`: current-time counts and current effective
  count; explicitly marks historical scan-time authorization unavailable.
- `ReportStats`: task/finding/severity/scanner/status/evidence counts and file
  verification counts. Enum-keyed counts include all keys at 0.
- `ReportSnapshot`: immutable aggregate returned by `ReportService`.
- `ReportArtifact`: future exporter result structure only; `path` and
  `sha256` remain `None`; no file is created.

## 3. ReportRepository query scope

`ReportRepository.load_snapshot(project_id,
report_type=ReportType.PROJECT_SUMMARY, *, generated_at=None)`:

1. validates a positive project ID;
2. opens one `Database.connection()`;
3. sets `PRAGMA query_only = ON`;
4. executes `BEGIN`;
5. reads, in that transaction:
   - `projects`
   - `authorizations`
   - `scope_assets`
   - `scan_tasks`
   - `findings` (JOIN `projects`; evidence-count subquery)
   - `evidence` (JOIN `projects`; LEFT JOIN `findings`)
6. constructs the immutable DTOs;
7. rollback in `finally`;
8. closes the connection through the context manager.

Every SQL statement has an explicit column list and a project filter. There is
no `SELECT *`. The repository does not read files or invoke scanners.

## 4. SQLite transaction and snapshot consistency

SQLite does not have `BEGIN READ ONLY`. The connection-level
`PRAGMA query_only = ON` is applied first, so accidental `INSERT`, `UPDATE`,
`DELETE` or DDL on that connection fails. `BEGIN` establishes the explicit
transaction boundary.

The first SELECT establishes the read snapshot. A concurrent writer can commit
new data, but subsequent SELECTs in the same read transaction continue to see
the old snapshot.

Test evidence (`test_read_transaction_consistency_under_concurrent_write`):

```text
before: 1 Finding
concurrent insert committed
after in same read transaction: 1 Finding
new transaction: 2 Findings
```

This was measured against SQLite in WAL mode; it is not inferred merely from
using one connection.

## 5. Report data scope

`ReportService` sets `ReportSnapshot.data_scope`:

- vulnerability: project, current authorization, scan tasks, findings,
  finding stats;
- evidence: project, current authorization, scan tasks, evidence, evidence
  stats, linked findings;
- project summary: project, current authorization, scan tasks, findings,
  evidence, finding stats, evidence stats.

The snapshot currently carries the project's full Finding/Evidence collections
because it is one unified service; exporters must obey `data_scope` and must
not serialize unrelated sections.

## 6. Project isolation

- Every repository query is constrained by `project_id`.
- The project row must exist; otherwise `NotFoundError` is raised.
- No cross-project Finding or Evidence is returned.
- Evidence files are only verified under
  `evidence_root/project_<project_id>/`.
- The service never accepts a second project ID.

Tests cover A/B isolation, nonexistent project, evidence ID separation and
per-project Finding sets.

## 7. Empty data and missing values

- Empty project data returns empty tuples and zero-filled enum counts.
- Missing scan task data produces a warning that the report cannot be treated
  as a scan pass.
- Missing Finding data produces a warning that it does not prove absence of
  vulnerabilities.
- Missing authorization data produces a warning and never invents an
  authorized state.
- Missing dependency fields stay `None`/empty.
- Text evidence has `file_exists=None`, not a fabricated `True`.

## 8. Original data protection

Phase B is read-only:

- `PRAGMA query_only=ON` on the report connection;
- SELECT-only SQL;
- transaction rollback;
- no report-table insert;
- no Finding/Evidence/ScanTask mutation;
- no authorization state change;
- evidence checks open files only for SHA-256 and do not write.

## 9. Known architectural limits

- `ReportSnapshot` is a unified project snapshot, not a per-type SQL query.
- Not wired into `AppContext` in phase B.
- No exporter, report record, HTML/PDF/JSON file, or GUI.
- Current authorization summary is not a historical scan-time snapshot.
- The database has no universal fixture/real-scan provenance flag.
- Raw `ReportEvidence.file_path` is internal; exporters must use managed path.
