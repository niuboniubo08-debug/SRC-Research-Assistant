# Phase 6 B — Phase 5 Historical Archive Difference Investigation

- Investigation date: 2026-11-05 (Asia/Shanghai)
- Project: `D:\挖漏洞\SRC-Research-Assistant`
- Scope: read-only investigation of two phase-5 manifest discrepancies
- Files modified by this investigation: **none**, except this new report
- Phase C: **not started**
- Phase B seal status: **still pending**

> This report is an investigation addendum. It does not repair, restore,
> overwrite or reinterpret the phase-5 archive. The phase-5 manifest was not
> updated to include this report, by explicit instruction not to modify the
> phase-B or phase-5 archive.

## 1. Summary

Two discrepancies were found when
`docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` was checked:

| # | Path | Status | Classification |
|---:|---|---|---|
| 1 | `docs/acceptance/code_quality.json` | hash differs; size same | known generated quality artifact, consistent with phase-B quality-check rerun |
| 2 | `storage/_rebuild_manifest.py` | absent | unresolved missing workspace helper; cause not provable from available evidence |

The phase-5 final directory itself contains 10 files. All nine files other than
the manifest itself are present and match their manifest hashes. The two
discrepancies are **outside** `docs/acceptance/phase5_final/`.

The phase-5 manifest is a **workspace-wide inventory**, not a manifest limited
to `phase5_final/`. It explicitly lists `docs/acceptance/code_quality.json` and
`storage/_rebuild_manifest.py` as project files. Therefore the discrepancies
affect exact manifest verification, even though they do not invalidate the
phase-5 core acceptance material.

## 2. Baseline and scope

### 2.1 Manifest location and coverage

`docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt`:

```text
Generated: 2026-11-05T14:22:49.536482+08:00
Total unique paths: 200
Manifest entry lines: 253
```

Header:

```text
This manifest excludes only __pycache__, .pytest_cache, .tmp,
.screenshot-demo, pytest-of-* and this manifest file itself.
All old snapshots in backups/ are listed.
```

Sections include:

- new phase-5 files;
- modified phase-5 files;
- database backups;
- full project inventory, including `storage/`, `docs/`, tools, tests and
  workspace artifacts.

The phase-5 final directory itself contains 10 files:

```text
PHASE5_ACCEPTANCE.json
phase5_acceptance_evidence.json
PHASE5_ACCEPTANCE_REPORT.md
PHASE5_ARCHITECTURE.md
PHASE5_DATABASE_BACKUP_INFO.md
phase5_evidence_center.png
PHASE5_FILE_MANIFEST.txt
PHASE5_FINAL_SUMMARY.md
PHASE5_TEST_REPORT.md
phase5_vulnerability_management.png
```

Only the manifest itself is excluded from its own manifest. The other nine
files are listed and match.

### 2.2 Current phase-5 core status

| File | Current SHA-256 | Manifest match |
|---|---|---|
| `PHASE5_FINAL_SUMMARY.md` | `645abf1228ec8ca3081ee98e64f34bd4acf75481a1312c62cff7b7d514c74ba6` | yes |
| `PHASE5_ACCEPTANCE.json` | `b133b81ed5727079cf84d02b2dede144a99652f29a1b40aa872618aee2d97f3d` | yes |
| `PHASE5_ACCEPTANCE_REPORT.md` | `589a9a4744fc21fe9d37f439da4e5cd7009673296705da9eb5bd5328ac253ce2` | yes |
| `PHASE5_ARCHITECTURE.md` | `0e9be1d363150aeffbfd88a87dc9220da969f21ae91476dba497ac26d3b26a1c` | yes |
| `PHASE5_DATABASE_BACKUP_INFO.md` | `5b651ee67b52153f755423aeb8a2e8dbe2819bec8c5d2cd843dd2487b5c9401b` | yes |
| `PHASE5_TEST_REPORT.md` | `825821ce7caa457c9e5716e850842dcb2392ec571db06885bf9e60c3e2ada3f6` | yes |
| `phase5_acceptance_evidence.json` | `bc226a9e68ebe6c90e3d6a18b4efe3e0b316df72c36084fa37d28be6fd5b2573` | yes |
| `phase5_vulnerability_management.png` | `f67b1f64c9e570bf38bab5c3d243eb94398371bfdb49cdd9e20a3e1a7a15ce3c` | yes |
| `phase5_evidence_center.png` | `a529ec942b55f4d766f9e42a9bf0795d298da6ccefe8595246e37b57af1569c8` | yes |

Conclusion: the phase-5 acceptance/report/screenshot/database-info core is
present and hash-matching. The final summary hash also matches the value
recorded during the phase-5 closeout.

## 3. Difference 1 — `docs/acceptance/code_quality.json`

### 3.1 Manifest record

The phase-5 manifest records this file twice (two sections), with identical
values:

```text
path:   docs/acceptance/code_quality.json
size:   9144
sha256: 5993473a569adb396d482b354ab21c830be7f557f022bea0c94b79d092d4fbe1
```

Occurrences:

```text
line 66  (MODIFIED PHASE 5 FILES section)
line 103 (FULL PROJECT INVENTORY section)
```

### 3.2 Current state

```text
exists: yes
size:   9144
sha256: f0d0fca2a1f144d9f44891df76d4bd581b55f52139687c68edfcdc748caf2e59
```

The size is unchanged. The hash differs.

### 3.3 Historical copy found in the phase-5 archive

`backups/src-research-assistant_phase5_final.zip` contains:

```text
entry:  SRC-Research-Assistant/docs/acceptance/code_quality.json
size:   9144
sha256: 5993473a569adb396d482b354ab21c830be7f557f022bea0c94b79d092d4fbe1
```

This byte-for-byte matches the phase-5 manifest. It confirms the old content
is preserved inside the phase-5 release zip, although there is no dedicated
pre-rerun backup next to the current file.

### 3.4 Content difference

Old content was read from the phase-5 zip and compared with current JSON.

Observed differences:

```text
top-level keys: same
product_file_count: 57 -> 59
empty_function_count: 0 -> 0 (same)
pass_count: 19 -> 19 (same)
pass_locations: 19 entries, identical (same)
todo_count: 0 -> 0 (same)
status_literal_count: 27 -> 27 (same)
verdicts: identical all PASS
```

The only scalar difference found is:

```text
product_file_count: 57 -> 59
```

The `pass_locations` file set is identical:
`app/application.py`, `database/connection.py`, `scanners/base.py`,
`scanners/process_runner.py`, `security/scope_rules.py`,
`security/scope_validator.py`, `services/dependency_audit_service.py`,
`services/scan_service.py`, `ui/dependency_page.py`,
`ui/source_audit_page.py`.

### 3.5 Can we confirm the stage-B quality check regenerated it?

**Yes, at the level of documented evidence; not by an immutable execution
log.**

Evidence:

1. `docs/PHASE6_B_REPORT.md` states that
   `docs/acceptance/code_quality.json` was "仅由质量检查工具重新生成" and lists
   the path explicitly.
2. The current file reports `product_file_count=59`, matching the stage-B
   quality-check output (`PRODUCT_FILES=59`) and differing from the phase-5
   snapshot value `57`.
3. The current file timestamp is later than the phase-5 final archive and is
   consistent with the phase-B quality-check activity; the stage-B report was
   written in the same stage.
4. The phase-5 zip preserves the exact expected old hash, so the old content
   and the current rerun can be compared independently.

What cannot be proven from timestamp/JSON alone is which exact process
invocation produced the current file. The stage-B report and matching count
are documentary evidence, not a signed execution log.

### 3.6 Was there a backup before regeneration?

- There is **no dedicated immediate backup** named after this file change.
- The phase-5 release zip does contain the old copy with the expected hash
  `5993473a...`.
- That zip is a historical snapshot, not a guaranteed pre-rerun backup created
  immediately before the stage-B quality check.

### 3.7 Is the difference known and explainable?

**Known and explainable at the level of the quality report.**

The file is a generated quality-check JSON, not a user-authored acceptance
decision. The old and new reports have the same keys, same 19 pass locations,
same verdicts, same zero empty/todo counts, and differ only in
`product_file_count` (57 → 59). This is consistent with rerunning the quality
check after stage-B files were added. The exact reason the count increased by
two rather than three is **not independently established** by this
investigation; it may depend on the quality tool's product-file classification.
No manual edit of the metrics was found.

The discrepancy still means the phase-5 manifest cannot be exactly re-verified
against the current workspace.

## 4. Difference 2 — `storage/_rebuild_manifest.py`

### 4.1 Manifest record

The phase-5 manifest contains this file once:

```text
path:   storage/_rebuild_manifest.py
size:   4150
sha256: aed42f24e14aeae1b22a7ef161e15e9a5c19bef9251d2aa6a3573bf61de37d2a
line:   171 (FULL PROJECT INVENTORY)
```

### 4.2 Current state

```text
path exists: no
same-name file under project: none found
```

A recursive project search for `_rebuild_manifest.py` returned no file.

### 4.3 Other archive/backup copies

Searched archives:

```text
backups/src-research-assistant_acceptance_final.zip
backups/src-research-assistant_phase2_20261104T145255Z.zip
backups/src-research-assistant_phase3_final.zip
backups/src-research-assistant_phase4_final.zip
backups/src-research-assistant_phase5_final.zip
```

No zip contains `_rebuild_manifest.py`. No other copy was found.

### 4.4 Documentation of purpose

The only project text reference found was:
- the phase-5 manifest entry;
- phase-B archive summaries that repeat the missing-file finding.

No design/runbook/readme explains what `_rebuild_manifest.py` did.

### 4.5 Can it be confirmed as a temporary helper?

**Cannot confirm.**

Its location (`storage/`) and filename (`_rebuild_manifest.py`) are consistent
with a helper script, but the file content is unavailable and no document
states its purpose. This is an inference, not a verified fact.

### 4.6 Can it be confirmed that it was deliberately deleted?

**Cannot confirm.**

There is:

- no deletion log;
- no audit record;
- no backup copy;
- no tombstone or explanation in the phase-5 summary.

The only verifiable fact is that the manifest says it existed at
`2026-11-05T14:22:49+08:00` and the path is absent now.

### 4.7 Is there enough evidence that its absence is reasonable?

**No.**

The manifest proves previous existence but provides no content, purpose,
deletion reason or approved exception. It cannot be reconstructed from the
SHA-256. Its absence is therefore an unresolved historical-manifest gap, not a
proven harmless cleanup.

## 5. Impact on the phase-5 archive

### 5.1 Core phase-5 archive

The core phase-5 acceptance materials are complete:

- all nine non-manifest files in `docs/acceptance/phase5_final/` exist;
- all nine match their recorded sizes and hashes;
- `PHASE5_FINAL_SUMMARY.md` still has the known
  `645abf12...74ba6` hash;
- `PHASE5_ACCEPTANCE.json`, acceptance report, test report, architecture,
  database backup info and both screenshots match.

### 5.2 Do the two differences affect core acceptance material?

**No evidence that the core acceptance content is corrupted.**

- `docs/acceptance/code_quality.json` is an auxiliary generated quality report,
  not the phase-5 acceptance report or database evidence.
- `storage/_rebuild_manifest.py` is a workspace helper, not a phase-5
  acceptance artifact under `phase5_final/`.

However, they do affect **exact manifest completeness** and therefore the
ability to claim the whole historical project inventory is bit-for-bit
unchanged.

### 5.3 Workspace inventory vs sealed archive

The manifest mixes two scopes:

1. the sealed phase-5 archive directory `docs/acceptance/phase5_final/`;
2. a broad project/workspace inventory including source, tests, docs,
   `storage/`, database backups and old snapshots.

`TOTAL FILES: 200` reflects unique project paths; the 253 manifest lines include
duplicate path entries in the "modified" and "full inventory" sections. This
explains why `code_quality.json` appears twice.

Therefore:

```text
phase5_final/ core directory: complete and hash-matching
whole workspace inventory:     not exactly matching
```

This should not be reported as "the phase-5 archive folder was overwritten."
It should be reported as "the phase-5 manifest covers the workspace, and two
workspace files no longer match that manifest."

## 6. What remains unconfirmed

1. The exact process invocation that rewrote `code_quality.json` cannot be
   reconstructed from an execution log.
2. Why `product_file_count` increased by exactly 2 (not 3) is not independently
   established; only the observed JSON values are confirmed.
3. The purpose, content and deletion reason of `_rebuild_manifest.py` cannot be
   confirmed.
4. No immediate pre-rerun backup of `code_quality.json` exists; only the phase-5
   release zip contains the old copy.
5. No copy of `_rebuild_manifest.py` exists in any available archive.

These are recorded as unresolved, not as facts inferred from filenames.

## 7. Effect on phase-B sealing

The earlier archive check correctly found:

```text
historical_archive_modified = true
```

The present investigation refines the cause:

- one discrepancy is a known generated quality-report update, with the old
  copy preserved in the phase-5 zip;
- one discrepancy is an unresolved missing workspace helper.

Neither discrepancy was repaired. Because the archive rules require the
historical manifest to match before sealing:

```text
phase_b_status = pending
sealed = false
phase_c_started = false
```

The phase-B tests and database remain valid; sealing is withheld only for the
historical manifest reconciliation decision.

## 8. Recommended handling

No repair should be performed without user approval. Recommended options:

1. **Do not edit** `PHASE5_FILE_MANIFEST.txt` or
   `PHASE5_FINAL_SUMMARY.md`.
2. For `code_quality.json`, record a reconciliation addendum that:
   - keeps the original expected hash;
   - records the current hash and observed `57 → 59` content difference;
   - cites the stage-B quality-check report and the old copy in
     `backups/src-research-assistant_phase5_final.zip`;
   - treats the quality JSON as a generated auxiliary artifact.
3. For `storage/_rebuild_manifest.py`, decide explicitly whether:
   - the helper is required historical evidence; if so, recover from an
     external source or recreate it under review; or
   - it can be waived as a non-core temporary helper; if so, document the
     waiver rather than silently accepting the missing file.
4. Keep phase-B status `pending` until the user accepts the reconciliation.
5. Do not start phase C.

Any future fix must be a separate, authorized task; this investigation makes
no changes.

## 9. Evidence index

| Evidence | Location |
|---|---|
| Phase-5 manifest | `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` |
| Phase-5 final summary | `docs/acceptance/phase5_final/PHASE5_FINAL_SUMMARY.md` |
| Phase-5 acceptance JSON | `docs/acceptance/phase5_final/PHASE5_ACCEPTANCE.json` |
| Old code-quality copy | `backups/src-research-assistant_phase5_final.zip` → `SRC-Research-Assistant/docs/acceptance/code_quality.json` |
| Current code-quality JSON | `docs/acceptance/code_quality.json` |
| Stage-B quality-rerun statement | `docs/PHASE6_B_REPORT.md` lines 59–62 |
| Earlier phase-B archive check | `docs/acceptance/phase6_b_final/PHASE6_B_DATABASE_INFO.md` |

## 10. Final statement

The phase-5 **core archive** is complete and hash-matching. The phase-5
**workspace-wide manifest** is not exactly reproducible because of one
explained generated quality-report change and one unexplained missing helper
file. Phase B remains **unsealed/pending**, and phase C remains **not started**.
