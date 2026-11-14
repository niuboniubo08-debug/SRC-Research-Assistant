# Phase 6 Stage 1B-4A — RC-01 定向测试执行报告

## 1. 执行结论

本次只执行了 RC-01 相关的三个定向测试文件，没有运行全量 pytest、真实 pip-audit 扫描或 GUI 手工测试。

```text
STAGE1B4A_STATUS = COMPLETED
TARGETED_TEST_RESULT = FAIL
TARGETED_TEST_FILES = 3
TOTAL_COLLECTED = 41
TOTAL_PASSED = 26
TOTAL_FAILED = 15
TOTAL_SKIPPED = 0
TOTAL_ERRORS = 0
FAILURES_CONSISTENT_WITH_B2A_PREDICTIONS = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
```

15 个失败全部是断言失败，不是收集错误、测试错误或环境错误。失败集中在当前生产代码仍按旧语义把不完整审计标记为 `COMPLETED`，以及扫描器仍未输出新的统计 metadata；这与 B2A 预测的旧代码行为一致。

本次不能得出 RC-01 已修复的结论；当前结论是：新增测试可以运行，但当前生产代码尚未通过新的 RC-01 合同。

## 2. 执行环境与执行前检查

### 2.1 Python 与 pytest

```text
Python 解释器：D:\挖漏洞\.venv\Scripts\python.exe
Python 版本：3.14.4 (tags/v3.14.4:23116f9, Apr 7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
pytest：9.2.0
pluggy：1.7.0
PySide6：6.12.0
pytest-qt：4.5.0
```

### 2.2 三个测试文件

| 文件 | 存在 | 执行前大小 |
|---|---:|---:|
| `tests/test_pip_audit_scanner.py` | YES | 10,952 bytes |
| `tests/test_dependency_audit_service.py` | YES | 21,410 bytes |
| `tests/test_ui_dependency_audit.py` | YES | 7,855 bytes |

### 2.3 执行前 Git 状态

```text
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
 M tests/test_dependency_audit_service.py
 M tests/test_pip_audit_scanner.py
 M tests/test_ui_dependency_audit.py
?? docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
?? docs/PHASE6_D1B_3_JSON_DECISION.md
?? docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md
?? docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md
?? docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md
?? docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md
?? docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md
?? docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md
?? docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md
?? docs/PHASE6_STAGE1B2A_RC01_TEST_SCOPE_INVESTIGATION.md
?? docs/PHASE6_STAGE1B2B_RC01_DATA_INTERFACE_DESIGN.md
?? docs/PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md
?? docs/PHASE6_STAGE1B3A_RC01_TEST_IMPLEMENTATION_PLAN.md
?? docs/PHASE6_STAGE1B3B_RC01_TEST_IMPLEMENTATION.md
```

- 暂存区为空。
- `docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 保持既有未暂存修改。
- 三个测试文件的 `M` 状态来自 Stage 1B-3B/R1，本次未修改它们。

### 2.4 执行方式说明

项目在此 Windows 会话中曾出现普通 pytest 临时目录 ACL 限制。本次使用专用临时目录和 full-access 测试进程：

```text
TEMP / TMP / TMPDIR / PYTEST_DEBUG_TEMPROOT = D:\挖漏洞\pytest_c1r_tmp
--basetemp = D:\挖漏洞\pytest_c1r_tmp\bt_b4a_<suite>
QT_QPA_PLATFORM = offscreen
PYTHONDONTWRITEBYTECODE = 1
-p no:cacheprovider
```

这是测试环境隔离措施，不是产品代码修改，也不是测试代码修改。

## 3. 实际执行结果

### 3.1 Scanner 定向测试

实际命令：

```text
D:\挖漏洞\.venv\Scripts\python.exe -m pytest tests\test_pip_audit_scanner.py -v -p no:cacheprovider --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_b4a_scanner
```

实际结果：

```text
collected 12 items
passed 7
failed 5
skipped 0
exit code 1
duration 1.22s
```

失败用例：

1. `test_pip_audit_json_parsing_dedupes_and_maps_metadata`
   - `assert audited == 2`
   - 实际 `3 == 2`
   - 原因：旧 parser 把 `skipped-package` 也计入 audited。

2. `test_pip_audit_scan_metadata_complete_without_vulnerabilities`
   - `output.metadata["skipped_dependencies"]`
   - 实际 `KeyError`
   - 原因：旧 scanner 只输出 `audited_dependencies`，不输出 `skipped_dependencies` 和 `total_dependencies`。

3. `test_pip_audit_scan_metadata_complete_with_vulnerabilities`
   - `output.metadata["skipped_dependencies"]`
   - 实际 `KeyError`
   - 同上。

4. `test_pip_audit_scan_metadata_partial_skip`
   - `assert output.metadata["audited_dependencies"] == 2`
   - 实际 `3 == 2`
   - 原因：旧 parser 把 skipped 依赖计入 audited。

5. `test_pip_audit_scan_metadata_all_skipped`
   - `assert output.metadata["audited_dependencies"] == 0`
   - 实际 `2 == 0`
   - 原因：两条 skipped 依赖被旧 parser 计为已审计。

### 3.2 Service 定向测试

实际命令：

```text
D:\挖漏洞\.venv\Scripts\python.exe -m pytest tests\test_dependency_audit_service.py -v -p no:cacheprovider --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_b4a_service
```

实际结果：

```text
collected 27 items
passed 18
failed 9
skipped 0
exit code 1
duration 6.85s
```

失败用例：

1. `test_partial_skipped_dependency_audit_fails_without_success_summary`
   - 期望 `ScanTaskStatus.FAILED`
   - 实际 `ScanTaskStatus.COMPLETED`
   - 实际 summary 为“已审计 1 个依赖，发现 1 个唯一漏洞”。
   - 说明旧 Service 只判断 `audited > 0`，没有因 `skipped=1` 失败。

2. `test_missing_dependency_statistics_fail_closed`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `raw_metadata` 只有 `audited_dependencies=2`，旧 Service 没有要求 `skipped/total`，仍生成“已审计 2 个依赖，未发现已知漏洞”。

3. `test_inconsistent_dependency_statistics_fail_closed`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `audited=1, skipped=1, total=3` 未通过旧代码的一致性校验。

4. `test_invalid_dependency_statistics_fail_closed[audited-string]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `audited_dependencies="2"` 未被旧 Service 拒绝。

5. `test_invalid_dependency_statistics_fail_closed[audited-negative]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `audited_dependencies=-1` 未被旧 Service 拒绝。

6. `test_invalid_dependency_statistics_fail_closed[total-zero]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `total_dependencies=0` 未被旧 Service 拒绝。

7. `test_invalid_dependency_statistics_fail_closed[skipped-negative]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - `skipped_dependencies=-1` 未被旧 Service 拒绝。

8. `test_invalid_dependency_statistics_fail_closed[audited-bool]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - 布尔 `audited_dependencies=True` 未被旧 Service 拒绝。

9. `test_invalid_dependency_statistics_fail_closed[total-bool]`
   - 期望 `FAILED`
   - 实际 `COMPLETED`
   - 布尔 `total_dependencies=True` 未被旧 Service 拒绝。

说明：

- `test_invalid_dependency_statistics_fail_closed[audited-none]` 通过，原因是旧代码的 `audited=0` 路径本身会失败；这不能证明新校验已实现。
- `test_invalid_dependency_statistics_fail_closed[skipped-bool]` 通过，原因是旧代码在 `audited=0` 时已经失败；这也不能单独证明新统计合同已实现。
- `test_all_skipped_dependency_audit_fails_without_success` 通过，同样是旧代码 `audited == 0` 的既有失败分支；B3B-R 已记录它不是新合同的独立证据。

### 3.3 UI 定向测试

实际命令：

```text
D:\挖漏洞\.venv\Scripts\python.exe -m pytest tests\test_ui_dependency_audit.py -v -p no:cacheprovider --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_b4a_ui
```

实际结果：

```text
collected 2 items
passed 1
failed 1
skipped 0
exit code 1
duration 5.45s
```

失败用例：

1. `test_incomplete_dependency_audit_does_not_claim_no_vulnerabilities`
   - 期望 `page._task.status is ScanTaskStatus.FAILED`
   - 实际 `ScanTaskStatus.COMPLETED`
   - 实际 `result_summary` 包含“已审计 1 个依赖，未发现已知漏洞”。
   - 说明旧 UI + 旧 Service 仍会把 incomplete 审计展示为成功无漏洞。

通过的 UI 用例：

```text
test_dependency_page_runs_fake_pip_audit_and_displays_result PASSED
```

## 4. 汇总

| 测试文件 | Collected | Passed | Failed | Skipped | Exit |
|---|---:|---:|---:|---:|---:|
| `tests/test_pip_audit_scanner.py` | 12 | 7 | 5 | 0 | 1 |
| `tests/test_dependency_audit_service.py` | 27 | 18 | 9 | 0 | 1 |
| `tests/test_ui_dependency_audit.py` | 2 | 1 | 1 | 0 | 1 |
| **合计** | **41** | **26** | **15** | **0** | **FAIL** |

## 5. 静态检查与执行边界

- 三个测试文件均存在，均被 pytest 收集。
- 没有 collection error。
- 没有 error 条目。
- 没有 skipped 条目。
- 没有真实 pip-audit 扫描。
- 没有 GUI 手工操作；UI 测试使用 pytest-qt/offscreen。
- 没有数据库或 Schema 修改。
- 没有生产代码修改。
- 没有测试代码修改。
- 没有 Git add/commit/push/reset/restore/clean。
- 没有删除、覆盖、移动任何报告。

## 6. 失败性质判定

```text
FAILURE_CLASS = ASSERTION_FAILURE
FAILURE_SOURCE = CURRENT_PRODUCTION_CODE_DOES_NOT_YET_IMPLEMENT_RC01_CONTRACT
TEST_COLLECTION_OK = YES
TEST_RUNTIME_ENVIRONMENT_OK = YES
NEW_TESTS_RUNNABLE = YES
RC01_PRODUCTION_FIX_IMPLEMENTED = NO
```

本次失败不是测试代码语法错误，也不是临时目录权限错误。它们是 B2A 预测的旧代码行为：

- scanner 没有 `skipped_dependencies` / `total_dependencies` metadata；
- scanner 把 skipped 计入 audited；
- service 没有用 total/skipped 一致性校验失败关闭；
- UI 仍显示成功无漏洞。

## 7. 尚未验证的内容

- 未运行全量 pytest。
- 未运行真实 pip-audit 网络扫描。
- 未进行 GUI 手工工作流验证。
- 未验证生产代码修复后的通过情况，因为本次没有修改生产代码。
- 未验证真实 pip-audit JSON 中的 skipped 记录与当前 mock 结构完全一致；这是后续实现阶段需要复核的运行验证项。

## 8. 执行后 Git 状态

```text
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
 M tests/test_dependency_audit_service.py
 M tests/test_pip_audit_scanner.py
 M tests/test_ui_dependency_audit.py
?? docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
?? docs/PHASE6_D1B_3_JSON_DECISION.md
?? docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md
?? docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md
?? docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md
?? docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md
?? docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md
?? docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md
?? docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md
?? docs/PHASE6_STAGE1B2A_RC01_TEST_SCOPE_INVESTIGATION.md
?? docs/PHASE6_STAGE1B2B_RC01_DATA_INTERFACE_DESIGN.md
?? docs/PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md
?? docs/PHASE6_STAGE1B3A_RC01_TEST_IMPLEMENTATION_PLAN.md
?? docs/PHASE6_STAGE1B3B_RC01_TEST_IMPLEMENTATION.md
?? docs/PHASE6_STAGE1B4A_RC01_TARGETED_TEST_EXECUTION.md
```

- 暂存区为空。
- 没有新增未预期文件；新增文件只有本报告。
- 保护文件仍是既有 `M`，没有被暂存、恢复或删除。
- 测试文件的修改仍来自 Stage 1B-3B/R1，不是本次测试执行产生。
- 本次没有真实 Git 变更。

## 9. 下一步边界

本次仅完成定向测试执行和报告：

- 不修复生产代码。
- 不修改测试。
- 不进入全量回归。
- 不执行真实 pip-audit。
- 不进入下一阶段。

等待人工审核后再决定是否实施 RC-01 生产代码修复。
