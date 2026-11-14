# Phase 6 Stage 1B-3A：RC-01 测试实施计划

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：0.5.0；Schema：v5
- 性质：READ_ONLY 测试实施计划
- 数据载体（已批准）：`ScanOutput.metadata`
- 必需统计：`audited_dependencies`、`skipped_dependencies`、`total_dependencies`
- `audit_complete`：由 Service 派生，不写入 metadata
- 未修改任何文件（本报告除外）
- 未运行 pytest、pip-audit 或 GUI

## 1. 已批准的测试契约

本计划只落实以下已批准规则，不重新设计产品接口：

```text
INCOMPLETE_AUDIT_POLICY = FAILED
FALSE_NO_VULNERABILITY_CLAIM = PROHIBITED
DATA_CARRIER = ScanOutput.metadata
REQUIRED_STATISTICS = audited_dependencies, skipped_dependencies, total_dependencies
audit_complete = SERVICE_DERIVED
FAIL_CLOSED = YES
```

统计完整性规则：

```text
total_dependencies > 0
audited_dependencies >= 0
skipped_dependencies >= 0
audited_dependencies + skipped_dependencies == total_dependencies

complete:
    skipped_dependencies == 0
    AND audited_dependencies == total_dependencies
```

统计缺失、非法、负数、矛盾或 `total_dependencies <= 0`：

```text
NOT COMPLETE -> FAILED
```

不新增 `invalid_dependencies`；无 `version`/`vulns` 的对象若不能计为 audited 或 skipped，只能通过总数不一致触发 FAILED，不得宣称完整审计。

## 2. 计划总览

| 项 | 结论 |
|---|---|
| 必须修改的现有测试文件 | 3 个 |
| 必须新增的测试文件 | 0 个（在现有 3 个文件内新增） |
| 计划修改的既有测试数 | 4 个测试（含 fixture-only） |
| 计划新增的测试场景数 | 15 个（按 TC 编号细分见下表） |
| 不需要修改的既有测试 | 见第 5 节 |
| 生产代码修改 | 不属于本计划 |
| pytest | 不运行 |

### 2.1 最小文件集合

```text
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

`tests/conftest.py` 不需要修改。没有新增测试文件。

## 3. 精确测试计划表

类型含义：

- `MODIFY_EXISTING`：修改既有测试/其直接 fixture；不得删除断言。
- `ADD_NEW`：新增测试函数或参数化用例。
- `UNCHANGED`：不进入本轮修改集合，但必须继续通过。

“旧代码预测”全部是 **PREDICTED**，不是本轮运行结果。

### 3.1 Scanner：`tests/test_pip_audit_scanner.py`

| Test ID | 文件 | 类型 | 场景 | 输入条件 | 预期结果 | 旧代码预测 |
|---|---|---|---|---|---|---|
| `TC-03-PARSE` | `tests/test_pip_audit_scanner.py` | `MODIFY_EXISTING` | 既有 partial-skip fixture 的 audited 语义 | 现有 fixture：2 个正常依赖 + 1 个 `skip_reason`；`parse_output()` | `audited == 2`；`len(findings) == 2`；warning 含 skip 原因；不把 skipped 计为 audited | **FAIL**：当前 `audited == 3` |
| `TC-01-SCAN` | 同上 | `ADD_NEW` | 完整审计、0 漏洞的 metadata | 一个正常依赖、`vulns=[]`；monkeypatch `run_command` 返回 JSON；`scanner.scan()` | `metadata["audited_dependencies"] == 1`、`skipped == 0`、`total == 1`；`findings == ()` | **FAIL**：当前 metadata 只有 `audited_dependencies`，缺 skipped/total |
| `TC-02-SCAN` | 同上 | `ADD_NEW` | 完整审计、存在漏洞的 metadata | 一个正常依赖、一个 vuln；`scan()` | audited=1、skipped=0、total=1；Finding 正常映射 | **FAIL**：当前 metadata 缺 skipped/total |
| `TC-03-SCAN` | 同上 | `ADD_NEW` | 部分 skipped 的 metadata | 2 正常 + 1 skipped；`scan()` | audited=2、skipped=1、total=3；Finding 2 个；保留 warning | **FAIL**：当前 audited=3，缺 skipped/total |
| `TC-04-SCAN` | 同上 | `ADD_NEW` | 全部 skipped 的 metadata | 2 个对象均有非空 `skip_reason`；`scan()` | audited=0、skipped=2、total=2；findings=()；warning 含原因 | **FAIL**：当前 audited=2，缺 skipped/total |
| `TC-01-EMPTY` | 同上 | `UNCHANGED` | 空依赖列表的 parse | `{"dependencies":[]}`；`parse_output()` | findings=[]、warnings=[]、audited=0 | **PASS（预测）** |

Scanner 测试实现约束：

- 通过 `scanner.scan()` 验证已批准的 `ScanOutput.metadata` 载体；不新增未批准的解析 DTO/返回值协议。
- 旧 `parse_output()` 仍可保持三元组；`TC-03-PARSE` 只改 audited 期望。
- `run_command` monkeypatch 必须返回 `CommandResult(returncode=0, stdout=json.dumps(payload), ...)`，避免真实 pip-audit/网络。
- `scanner._availability_cache` 可按现有测试方式设为 available；不执行真实工具。
- 不测试具体 warning 中文文案，只断言包含 skip 原因文本（fixture 中的英文原因可保留）。

### 3.2 Service：`tests/test_dependency_audit_service.py`

先扩展 `FakePipAuditScanner`（`:55-99`）：

```text
构造参数：audited, skipped, total, (可选) findings/warnings/error
默认：skipped=0; total=audited+skipped
scan().metadata:
    audited_dependencies
    skipped_dependencies
    total_dependencies
```

默认值只服务既有正常测试；新增场景显式传参，不通过生产代码的缺省猜测获得 PASS。

| Test ID | 文件 | 类型 | 场景 | 输入条件 | 预期结果 | 旧代码预测 |
|---|---|---|---|---|---|---|
| `TC-01-SVC` | `tests/test_dependency_audit_service.py` | `MODIFY_EXISTING` | 完整审计、0 漏洞 | 修改现有 `test_empty_dependency_result_is_completed` 的 fake metadata 为 audited=1/skipped=0/total=1 | `COMPLETED`；`findings == ()`；无错误；该场景允许“未发现已知漏洞”成功语义 | **PASS**：旧 Service 读 audited=1 即 COMPLETED |
| `TC-02-SVC` | 同上 | `MODIFY_EXISTING` | 完整审计、有漏洞 | 修改 `test_completed_dependency_audit_persists_finding_and_metadata` fake 为 audited=3/skipped=0/total=3，保留 1 Finding | `COMPLETED`；Finding 持久化；project_id/task_id 正确；`audited_dependencies == 3` | **PASS**：旧 Service 读 audited=3 即 COMPLETED |
| `TC-03-SVC` | 同上 | `ADD_NEW` | 部分 skipped | fake：audited=1/skipped=1/total=2；可含 1 个已解析 Finding（仅作输入） | `FAILED`；`success is False`；摘要/错误含不完整信息；不显示“未发现漏洞成功”；**不将 Finding 保留/删除/持久化作为断言**（`OUT_OF_CURRENT_RC01_CONTRACT`） | **FAIL**：旧 Service 见 audited=1，返回 COMPLETED |
| `TC-04-SVC` | 同上 | `ADD_NEW` | 全部 skipped | fake：audited=0/skipped=2/total=2；findings=() | `FAILED`；无“未发现”成功摘要 | **PASS（弱）**：旧 Service 因 audited==0 本就 FAILED；此测试不能单独抓住旧 parser 的假成功，必须与 `TC-04-SCAN` 配套 |
| `TC-05-SVC` | 同上 | `ADD_NEW` | metadata 缺失 | fake 只给 `audited_dependencies=2`，缺 skipped/total；findings=() | `FAILED`；不显示“未发现” | **FAIL**：旧 Service 只读 audited，返回 COMPLETED |
| `TC-06-SVC` | 同上 | `ADD_NEW` | 统计矛盾 | fake：audited=1/skipped=1/total=3（1+1 != 3） | `FAILED`；不做成功摘要 | **FAIL**：旧 Service 仍 COMPLETED |
| `TC-07A-SVC` | 同上 | `ADD_NEW` | `audited=None` | fake：audited=None/skipped=0/total=1 | `FAILED`；fail-closed | **PASS（预测）**：旧 Service 将 None 转为 0 后 FAILED；该 case 不单独证明旧缺陷 |
| `TC-07B-SVC` | 同上 | `ADD_NEW` | audited 为非整数字符串 | fake：audited="2"/skipped=0/total=2 | `FAILED`；不得用 `int("2")` 接受 | **FAIL**：旧 Service `int("2")` 得 2 -> COMPLETED |
| `TC-07C-SVC` | 同上 | `ADD_NEW` | 负数 | fake：audited=-1/skipped=2/total=1 | `FAILED`；负 audited 非法 | **FAIL**：旧 Service 得 -1，非 0 -> COMPLETED |
| `TC-07D-SVC` | 同上 | `ADD_NEW` | `total <= 0` | fake：audited=1/skipped=0/total=0 | `FAILED`；total 必须 > 0 | **FAIL**：旧 Service 忽略 total -> COMPLETED |
| `TC-07E-SVC` | 同上 | `ADD_NEW` | skipped 为负数 | fake：audited=2/skipped=-1/total=2 | `FAILED`；负 skipped 非法 | **FAIL**：旧 Service 忽略 skipped -> COMPLETED |
| `TC-07F-SVC` | 同上 | `ADD_NEW` | bool 冒充整数 | fake：audited=True/skipped=0/total=1 | `FAILED`；bool 不是合法计数 | **FAIL**：旧 Service `int(True)=1` -> COMPLETED |

Service 测试实现约束：

- 每个不完整场景都断言 `outcome.task.status is ScanTaskStatus.FAILED`，而不是只断言 `failed`/`success`。
- `FINDING_PERSISTENCE_POLICY = OUT_OF_CURRENT_RC01_CONTRACT`。RC-01 当前只验证：不完整审计 → `FAILED`；不得形成“审计成功”语义；不得形成“未发现漏洞”的错误成功结论。Finding 的保留、删除或持久化策略不属于本轮 RC-01 测试契约，不得作为 `TC-03-SVC` 的强制断言。
- “不显示未发现”通过任务摘要/错误文本检查；不固定新的失败中文文案，只禁止成功结论。
- 旧 `test_zero_audited_dependencies_is_failure_not_success` 保持；可复用其错误语义，但不以它替代 TC-04。
- 不添加新任务状态；不修改 schema；不新增数据库列。

### 3.3 UI：`tests/test_ui_dependency_audit.py`

| Test ID | 文件 | 类型 | 场景 | 输入条件 | 预期结果 | 旧代码预测 |
|---|---|---|---|---|---|---|
| `TC-01-UI` | `tests/test_ui_dependency_audit.py` | `MODIFY_EXISTING` | 现有成功路径的 fake metadata 补齐 | 修改 `UiFakeScanner` metadata 为 audited=2/skipped=0/total=2；Finding 不变 | 现有 `COMPLETED`、1 Finding、表格/详情断言全部保持 | **PASS**：旧 UI 接受额外 metadata，核心路径不变 |
| `TC-03-UI` | 同上 | `ADD_NEW` | 不完整审计不得显示成功/“未发现” | fake：audited=1/skipped=1/total=2；findings=()；等待任务结束 | `page._task.status is ScanTaskStatus.FAILED`；页面状态/错误非成功；不出现“当前任务未发现已知依赖漏洞”这一成功结论 | **FAIL**：旧 Service 返回 COMPLETED，旧 UI 显示“未发现” |

UI 测试约束：

- 直接复用现有 `DependencyAuditService` + `MainWindow` + `DependencyPage` 的真实 UI 路径，不 mock 页面内部方法。
- 不断言新失败文案的具体中文句子；只断言 FAILED、错误/状态非成功，以及禁止的成功结论。
- 现有 `TC-01-UI` 仅补 fake metadata；不修改既有表格/详情断言。
- **`TC-04-UI` 不纳入最小计划**：它与 `TC-03-UI` 走完全相同的 UI 分支；全部 skipped 的解析错误由 `TC-04-SCAN` 捕获，旧 Service 在正确 `audited=0` 时已会 FAILED，单独 UI 测试不能增加有效区分度。若未来 UI 对“all skipped”有独立文案，再单独增加。

## 4. 必测场景覆盖矩阵

| TC | 场景 | Scanner | Service | UI |
|---|---|---|---|---|
| TC-01 | 完整、0 漏洞 | `TC-01-SCAN` | `TC-01-SVC` | `TC-01-UI` |
| TC-02 | 完整、有漏洞 | `TC-02-SCAN` | `TC-02-SVC` | 既有成功 UI 覆盖 |
| TC-03 | 部分 skipped | `TC-03-PARSE`、`TC-03-SCAN` | `TC-03-SVC` | `TC-03-UI` |
| TC-04 | 全部 skipped | `TC-04-SCAN` | `TC-04-SVC`（弱） | 不单独增加，见 3.3 |
| TC-05 | metadata 缺失 | 不适用 | `TC-05-SVC` | 不适用 |
| TC-06 | 统计不一致 | 不适用 | `TC-06-SVC` | 不适用 |
| TC-07 | 非法统计 | 不适用 | `TC-07A`～`TC-07F` | 不适用 |

覆盖说明：

- TC-05/06/07 是 Service 契约边界，不应强塞给 Scanner；Scanner 只负责产出计数。
- TC-04 的旧 bug 根源在 Scanner 的 audited 计算，`TC-04-SCAN` 是关键回归；Service/UI 测试不能替代。
- TC-01/02 的 Service 测试使用 fake metadata，Scanner 测试使用真实 `scan()` + fake `run_command`，分工明确。

## 5. 不需要修改的测试

以下测试不在修改集合中；Stage 1B 实施后必须继续通过：

### 5.1 `tests/test_pip_audit_scanner.py`

- `test_pip_audit_empty_result`（`TC-01-EMPTY`，parse 仍返回 audited=0）
- `test_pip_audit_bad_json`
- `test_pip_audit_unavailable_when_module_missing`
- `test_pip_audit_actual_available`
- `test_pip_audit_execution_failure_timeout_and_cancel`
- `test_pip_audit_scan_requires_available_tool`
- `test_pip_audit_severity_mapping`

### 5.2 `tests/test_dependency_audit_service.py`

- `test_requirements_discovery`
- `test_pyproject_discovery`
- `test_both_dependency_files_prefer_requirements`
- `test_no_dependency_file`
- `test_zero_audited_dependencies_is_failure_not_success`
- `test_pip_audit_unavailable_marks_task_failed_without_findings`
- `test_execution_failure_and_timeout_are_failed`
- `test_cancelled_dependency_audit_is_not_completed`
- `test_cancel_before_start_marks_cancelled`
- `test_pyproject_is_prepared_as_temporary_requirements_and_cleaned`
- `test_dependency_project_isolation`
- `test_unregistered_path_is_rejected`
- `test_invalid_pyproject_is_not_auditable`

其中 fake 构造默认值变化属于测试辅助代码修改，不改变这些测试的业务断言。

### 5.3 `tests/test_ui_dependency_audit.py`

- `test_dependency_page_runs_fake_pip_audit_and_displays_result` 的现有业务断言保持不变；仅 `UiFakeScanner` metadata 补齐（`TC-01-UI`）。

### 5.4 明确不修改

- `tests/conftest.py`（现有 fixture 足够）
- 所有 Bandit/Semgrep 测试
- 所有报告中心/HTML/JSON/PDF 测试
- 任何数据库 Schema/迁移测试

## 6. 旧代码预测汇总（PREDICTED）

> 未运行 pytest；以下不是实际测试结果。

| 预测结果 | 测试 |
|---|---|
| **FAIL** | `TC-03-PARSE`（audited 3 vs 2） |
| **FAIL** | `TC-01-SCAN`、`TC-02-SCAN`、`TC-03-SCAN`、`TC-04-SCAN`（缺 skipped/total，counts 错误） |
| **FAIL** | `TC-03-SVC`（旧 Service COMPLETED） |
| **FAIL** | `TC-05-SVC`（缺统计仍 COMPLETED） |
| **FAIL** | `TC-06-SVC`（矛盾仍 COMPLETED） |
| **FAIL** | `TC-07B/C/D/E/F-SVC`（非法统计被接受/错误处理） |
| **FAIL** | `TC-03-UI`（旧 UI 显示“未发现”） |
| **PASS（预测）** | `TC-01-SVC`、`TC-02-SVC`、`TC-04-SVC（弱）`、`TC-07A-SVC` |
| **PASS（预测）** | `TC-01-EMPTY`、`TC-01-UI` 及第 5 节不变测试 |

关键限制：

- `TC-04-SVC` 使用正确的 `audited=0` fake 时，旧 Service 已经会 FAILED；因此它**不能单独证明**旧 bug。必须保留 `TC-04-SCAN`，由 Scanner 的 audited=2 暴露根因。
- `TC-07A-SVC` 的 `None` 被旧 Service 转为 0，旧代码碰巧 FAILED；该 case 用于新契约的 fail-closed 覆盖，不用于证明旧缺陷。
- `TC-07B` 使用 `"2"` 会触发旧 Service 的 `int()` 接受路径；`True` 触发 bool 接受路径。这两个 case 才直接证明旧实现的宽松转换。

## 7. UI 测试范围结论

- **需要修改 UI 测试**：是，但只新增 `TC-03-UI`，并补齐既有 fake metadata。
- **是否需要修改 UI 生产代码**：不属于本测试计划；本计划只定义测试预期。
- **是否锁定具体失败文案**：否。只要求任务状态 FAILED、页面不显示成功结论；新增失败文案由实现决定。
- **是否覆盖全部 skipped 的 UI**：不作为最小要求；相同 UI 分支由 `TC-03-UI` 覆盖，全部 skipped 的根因由 `TC-04-SCAN` 覆盖。

## 8. 实施顺序（供下一步使用，不在本轮执行）

1. 先改 `FakePipAuditScanner` 和 `UiFakeScanner` 的 metadata 能力（只测试辅助代码）。
2. 添加/修改 Scanner 的 `TC-03-PARSE` 与 `TC-01`～`TC-04` scan metadata 测试。
3. 添加 Service `TC-03`～`TC-07`；修改 TC-01/02 的 fake metadata。
4. 添加 UI `TC-03-UI`；修改 `TC-01-UI` 的 fake metadata。
5. 运行定向测试：scanner + service + UI dependency tests；预测旧代码在指定用例失败。
6. 生产实现完成后，再运行定向测试和完整回归；本计划不执行这些步骤。

## 9. 最终状态

```text
TEST_IMPLEMENTATION_PLAN = COMPLETE
TESTS_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
PYTEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

补充：

- 只读检查了三个测试文件及其直接 fake/fixture，以及已批准的 RC-01 设计报告。
- 未读取数据库、未运行 pytest/pip-audit/GUI。
- 未修改生产代码、测试、Schema、数据库或 Git 状态。
- 本报告为唯一新增文件；HEAD 与工作区既有修改保持不变。
