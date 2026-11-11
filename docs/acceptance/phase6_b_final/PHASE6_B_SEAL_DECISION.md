# Phase 6 B Seal Decision

- Project: `D:\挖漏洞\SRC-Research-Assistant`
- Version: `0.5.0`
- Database schema: `v5`
- Decision date: 2026-11-05 (Asia/Shanghai)
- Decision authority: user-authorized seal with recorded exception
- Phase C: **not started**

## 1. Final decision

```text
phase_b_status          = "sealed_with_recorded_exception"
sealed                  = true
seal_exception_present  = true
phase_c_started         = false
phase_c_allowed         = false
```

Phase B is sealed with the two exceptions below recorded. This does **not**
mean that the phase-5 workspace manifest is fully reproducible, that the
missing helper file is restored or unnecessary, or that its deletion cause is
known.

## 2. Sealed facts

| Item | Result |
|---|---|
| Phase B implementation | passed |
| Tests | 145 collected / 144 passed / 1 skipped / 0 failed |
| Failed tests | 0 |
| Skipped test | existing Windows file-symlink privilege limitation (`WinError 1314`) |
| Schema | v5, unchanged |
| Database integrity | passed; both databases `integrity_check=ok`, `foreign_key_check=0` |
| Phase-5 core archive | complete and hash-matching |
| Phase-5 workspace manifest | not fully reproducible |
| Phase C | not started |

Phase-5 core archive verification:

- `docs/acceptance/phase5_final/` contains 10 files;
- the manifest itself is excluded from its own list;
- the other nine files match their recorded sizes and SHA-256;
- `PHASE5_FINAL_SUMMARY.md` remains
  `645abf1228ec8ca3081ee98e64f34bd4acf75481a1312c62cff7b7d514c74ba6`.

The phase-5 **workspace-wide** manifest covers more than `phase5_final/` and
does not fully reproduce against the current workspace.

## 3. Recorded exceptions

### P6B-EX-001 — explained generated artifact difference

Path:

```text
docs/acceptance/code_quality.json
```

| Property | Value |
|---|---|
| Original size | 9144 |
| Original SHA-256 | `5993473a569adb396d482b354ab21c830be7f557f022bea0c94b79d092d4fbe1` |
| Current size | 9144 |
| Current SHA-256 | `f0d0fca2a1f144d9f44891df76d4bd581b55f52139687c68edfcdc748caf2e59` |
| Old copy | exists in `backups/src-research-assistant_phase5_final.zip` |
| Cause | phase-B quality check regenerated the quality report |
| Observed content difference | `product_file_count: 57 -> 59` |

The old copy in the phase-5 zip has the original size and SHA-256. The current
file has the same size but a different hash. No manual edit or rollback was
performed by this seal step.

This exception is recorded as **explained generated artifact difference**.
The exact process invocation is documented by the stage-B report; no
immutable execution log is available.

### P6B-EX-002 — accepted unresolved historical workspace difference

Path:

```text
storage/_rebuild_manifest.py
```

Original manifest record:

```text
size:   4150
sha256: aed42f24e14aeae1b22a7ef161e15e9a5c19bef9251d2aa6a3573bf61de37d2a
```

Current status:

- the path is absent;
- the phase-5 manifest proves historical existence;
- no same-name file was found in the project;
- no copy was found in available archive/backup zips;
- its purpose and deletion cause cannot be confirmed;
- it was **not** restored, recreated, or deleted by this seal step;
- the phase-5 manifest was not modified.

The user explicitly accepted this as an **unresolved historical workspace
difference**. Acceptance does not mean the file was restored, is unnecessary,
or that its missing cause is known.

## 4. Conditions of this seal

- Phase B implementation and tests are accepted as recorded.
- Schema v5 remains unchanged.
- Database integrity checks remain valid.
- Phase-5 core acceptance archive is complete and hash-matching.
- The phase-5 workspace manifest is not fully reproducible; that limitation is
  recorded in `PHASE6_B_EXCEPTION_REGISTER.md`.
- No production code, test code, database, schema, phase-5 manifest, phase-5
  summary, or existing archive file was modified by this decision step.
- Only this decision and the exception register were added.
- Phase C is not started and is not allowed by this decision.

## 5. Related records

- `docs/acceptance/phase6_b_final/PHASE6_B_EXCEPTION_REGISTER.md`
- `docs/acceptance/phase6_b_final/PHASE6_B_ARCHIVE_DIFFERENCE_INVESTIGATION.md`
- `docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json`
- `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt`

This decision does not overwrite or amend any of those historical records.
