# Phase 6 B Test Report

## 1. Historical baseline

The phase-B development report recorded:

```text
phase-B before:
127 collected / 126 passed / 1 skipped / 0 failed

phase-B targeted:
18 passed

phase-B full:
145 collected / 144 passed / 1 skipped / 0 failed
38.44 s
```

The historical skipped test was the phase-5 environment limitation:

```text
test_symlink_to_outside_is_rejected
Windows current session cannot create a file symlink:
[WinError 1314] 客户端没有所需的特权
```

## 2. Current archive-task rerun

Command:

```powershell
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
```

Actual output file:

```text
docs/acceptance/phase6_b_final/PHASE6_B_TEST_OUTPUT.txt
```

Result:

```text
144 passed, 1 skipped in 41.51s
```

- Collected: 145
- Passed: 144
- Failed: 0
- Skipped: 1
- Exit code: 0

The pass/fail/skip counts match the historical record. The wall-clock duration
is different (41.51 s now vs 38.44 s historically); it is recorded, not
rewritten as the historical value.

## 3. Skipped item and cause

```text
tests/test_evidence_service.py:184
test_symlink_to_outside_is_rejected
当前 Windows 会话无法创建符号链接：
[WinError 1314] 客户端没有所需的特权
```

The test was not deleted. Its assertion was not weakened. The directory
junction test and the simulated `is_symlink` branch remain as previously
documented.

## 4. Failure / warning review

- Failures: **0**
- New skips: **0**
- Existing skip: **1** (same Windows symlink privilege)
- No pytest warning was emitted in the recorded output.

## 5. Test scope that remains covered

The 18 phase-B targeted tests cover:

1. three report snapshot types;
2. normal project data;
3. empty project data;
4. missing text/file fields;
5. project isolation;
6. missing project rejection;
7. authorization summaries and missing authorization;
8. Finding statistics;
9. Evidence statistics and SHA-256;
10. ScanTask statistics;
11. original data unchanged;
12. DTO immutability;
13. single-transaction snapshot consistency;
14. concurrent write snapshot behavior;
15. connection release on error;
16. distinction between zero and missing values;
17. default `load_snapshot(project_id)` behavior;
18. report request and artifact stub (no file output).

## 6. Interpretation

The current execution confirms the phase-B test state, but **does not unblock
formal sealing**: the historical-manifest discrepancy described in
`PHASE6_B_FINAL_SUMMARY.md` section 6 is independent of the test result.
