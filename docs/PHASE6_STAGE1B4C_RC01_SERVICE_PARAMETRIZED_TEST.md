# Phase 6 Stage 1B-4C — RC-01 Service 参数化测试验证

## 1. 执行结论

只执行了单个参数化测试函数：

```text
tests/test_dependency_audit_service.py::test_invalid_dependency_statistics_fail_closed
```

实际结果：

```text
collected 8 items
passed 1
failed 7
skipped 0
errors 0
exit code 1
duration 2.23s
```

```text
STAGE1B4C_STATUS = COMPLETED
TARGETED_PARAMETRIZED_RESULT = FAIL
SKIPPED_BOOL_USES_AUDITED_ZERO_FALLBACK = NO
SKIPPED_BOOL_IS_INDEPENDENT_OF_OLD_ZERO_BRANCH = YES
TOTAL_BOOL_IS_INDEPENDENT_OF_OLD_ZERO_BRANCH = YES
PRODUCTION_VALIDATION_IMPLEMENTED = NO
FALSE_POSITIVE_PASS_CASES = audited-none
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_OTHER_FILES_RUN = NO
DATABASE_MODIFIED = NO
GIT_MUTATION = NO
```

## 2. 实际执行命令与环境

### 2.1 Python 环境

```text
解释器：D:\挖漏洞\.venv\Scripts\python.exe
Python：3.14.4
pytest：9.2.0
PySide6：6.12.0
pytest-qt：4.5.0
```

### 2.2 实际命令

```text
D:\挖漏洞\.venv\Scripts\python.exe -m pytest tests\test_dependency_audit_service.py::test_invalid_dependency_statistics_fail_closed -v -p no:cacheprovider --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_b4c_params
```

执行环境：

```text
TEMP / TMP / TMPDIR / PYTEST_DEBUG_TEMPROOT = D:\挖漏洞\pytest_c1r_tmp
QT_QPA_PLATFORM = offscreen
PYTHONDONTWRITEBYTECODE = 1
```

项目当前 Windows 会话需要专用临时目录和 full-access 测试进程；这是测试环境隔离，不是产品修改。

## 3. 8 个参数化用例的实际结果

| # | 参数 id | 输入（audited / skipped / total） | 实际结果 | 测试结果 |
|---:|---|---|---|---|
| 1 | `audited-none` | `None / 0 / 1` | task `FAILED` | **PASSED** |
| 2 | `audited-string` | `"2" / 0 / 2` | task `COMPLETED` | **FAILED** |
| 3 | `audited-negative` | `-1 / 2 / 1` | task `COMPLETED`，summary 含 `已审计 -1 个依赖` | **FAILED** |
| 4 | `total-zero` | `1 / 0 / 0` | task `COMPLETED` | **FAILED** |
| 5 | `skipped-negative` | `2 / -1 / 2` | task `COMPLETED` | **FAILED** |
| 6 | `audited-bool` | `True / 0 / 1` | task `COMPLETED` | **FAILED** |
| 7 | `skipped-bool` | `1 / True / 2` | task `COMPLETED` | **FAILED** |
| 8 | `total-bool` | `1 / 0 / True` | task `COMPLETED` | **FAILED** |

只有 `audited-none` 通过；其余 7 个参数均未达到测试期望的 `FAILED` 状态。

## 4. 完整测试结果输出

```text
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\挖漏洞\SRC-Research-Assistant
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.14.4, qt-4.5.0
collected 8 items

test_invalid_dependency_statistics_fail_closed[audited-none] PASSED
test_invalid_dependency_statistics_fail_closed[audited-string] FAILED
test_invalid_dependency_statistics_fail_closed[audited-negative] FAILED
test_invalid_dependency_statistics_fail_closed[total-zero] FAILED
test_invalid_dependency_statistics_fail_closed[skipped-negative] FAILED
test_invalid_dependency_statistics_fail_closed[audited-bool] FAILED
test_invalid_dependency_statistics_fail_closed[skipped-bool] FAILED
test_invalid_dependency_statistics_fail_closed[total-bool] FAILED

=========================== short test summary info ===========================
FAILED ... [audited-string]
FAILED ... [audited-negative]
FAILED ... [total-zero]
FAILED ... [skipped-negative]
FAILED ... [audited-bool]
FAILED ... [skipped-bool]
FAILED ... [total-bool]
========================= 7 failed, 1 passed in 2.23s =========================
EXIT_CODE=1
```

每个失败用例的实际断言都是：

```text
assert <ScanTaskStatus.COMPLETED: 'completed'> is <ScanTaskStatus.FAILED: 'failed'>
```

失败位置统一为：

```text
tests/test_dependency_audit_service.py:432
```

没有 collection error、测试错误、skip 或临时目录错误。

## 5. `skipped-bool` 执行路径

### 5.1 输入

```text
audited_dependencies = 1
skipped_dependencies = True
total_dependencies = 2
```

### 5.2 当前 Service 实际路径

```text
services/dependency_audit_service.py:325
audited = int(output.metadata.get("audited_dependencies") or 0)

services/dependency_audit_service.py:326
if audited == 0:

services/dependency_audit_service.py:340-341
mapped = self._map_findings(...)
saved = self._save_findings(...)

services/dependency_audit_service.py:356-360
summary = "已审计 1 个依赖，未发现已知漏洞。"

services/dependency_audit_service.py:361-373
return self._finish(... ScanTaskStatus.COMPLETED ...)
```

实际结果：

```text
audited = 1
audited == 0  --> false
skipped_dependencies 未被读取
total_dependencies 未被读取
task.status = COMPLETED
result_summary = 已审计 1 个依赖，未发现已知漏洞。
```

结论：`skipped-bool` 已经绕开了旧的 `audited == 0` 分支，真正把 `skipped_dependencies=True` 送入了 Service；但当前生产代码完全不读取该字段，因此任务仍为 `COMPLETED`，测试失败。

该用例不再因旧的零审计分支而假阳性。它的失败是真实的“缺少 skipped 类型校验”。

## 6. `total-bool` 执行路径

### 6.1 输入

```text
audited_dependencies = 1
skipped_dependencies = 0
total_dependencies = True
```

### 6.2 当前 Service 实际路径

```text
services/dependency_audit_service.py:325
audited = int(True for audited_dependencies only? no: audited=1)

services/dependency_audit_service.py:326
if audited == 0:  # false

services/dependency_audit_service.py:355-373
warnings -> summary -> _finish(COMPLETED)
```

实际各字段：

```text
audited_dependencies = 1
skipped_dependencies = 0
total_dependencies = True
```

当前代码只读取 `audited_dependencies`，完全不读取 `total_dependencies`。`total_dependencies=True` 既没有被 `int()` 处理，也没有被类型或一致性校验拒绝。

结论：`total-bool` 独立覆盖了 `total_dependencies` 字段；它失败是因为该字段没有被校验，而不是因为旧的零审计分支。

## 7. 哪些用例真正验证了对应字段

| 参数 | 是否独立于旧的 `audited == 0` 分支 | 实际覆盖的字段 | 验证有效性 |
|---|---|---|---|
| `audited-none` | NO | `audited_dependencies` 缺失 | **假阳性**：通过来自旧 `audited=0` 失败分支 |
| `audited-string` | YES | `audited_dependencies` 字符串 | 有效；当前代码 `int("2")` 强制转换后成功，测试失败 |
| `audited-negative` | YES | `audited_dependencies` 负数 | 有效；当前代码接受 `-1`，并写入“已审计 -1” |
| `total-zero` | YES | `total_dependencies=0` | 有效；当前代码忽略 total，任务成功 |
| `skipped-negative` | YES | `skipped_dependencies=-1` | 有效；当前代码忽略 skipped，任务成功 |
| `audited-bool` | YES | `audited_dependencies=True` | 有效；当前代码通过 `int(True)=1` 接受 |
| `skipped-bool` | YES | `skipped_dependencies=True` | 有效；当前代码忽略 skipped，任务成功 |
| `total-bool` | YES | `total_dependencies=True` | 有效；当前代码忽略 total，任务成功 |

严格来说，除 `audited-none` 外，7 个失败用例都真正触发了对应字段；它们没有通过，因为生产代码尚未实现字段校验。

## 8. 假阳性分析

唯一假阳性通过用例是：

```text
audited-none
```

原因：

```python
audited = int(output.metadata.get("audited_dependencies") or 0)
if audited == 0:
    ... FAILED ...
```

`None` 被转换为 `0`，直接进入旧失败分支，测试因此通过。这不能证明任何严格类型或统计一致性校验已经实现。

`skipped-bool` 在 Stage 1B-4B 修正后使用 `audited=1`，不再经过该分支；它没有假阳性，是有效的 skipped 字段用例。

## 9. 执行前后 Git 状态

### 9.1 执行前

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
?? docs/PHASE6_STAGE1B4B_SKIPPED_BOOL_TEST_CORRECTION.md
```

### 9.2 执行后

测试执行没有改变上述状态；暂存区仍为空：

```text
git diff --cached --name-only
（空）
```

本报告新增后，Git 预期只多出：

```text
?? docs/PHASE6_STAGE1B4C_RC01_SERVICE_PARAMETRIZED_TEST.md
```

没有新增缓存、数据库、日志或测试输出文件进入项目工作区。

## 10. 执行边界确认

```text
ONLY_ONE_TEST_FUNCTION_RUN = YES
OTHER_PYTEST_FILES_RUN = NO
FULL_PYTEST_RUN = NO
REAL_PIP_AUDIT_RUN = NO
GUI_MANUAL_TEST_RUN = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
DOCS_MODIFIED = NO
GIT_ADD_COMMIT_PUSH = NO
GIT_RESET_RESTORE_CLEAN = NO
```

本次没有修复生产代码，没有扩大测试范围，没有进入下一阶段。

等待人工审核。
