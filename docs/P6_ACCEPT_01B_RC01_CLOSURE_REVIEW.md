# P6-ACCEPT-01B — RC-01 关闭条件审核

## 1. 审核范围与证据来源

本步骤是只读证据审核，不重新执行测试，不修改任何代码、测试、数据库或 Git 状态。

审核对象：

- `docs/PHASE6_CURRENT_STATUS_AFTER_RC01.md`
- `docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md`
- `docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md`
- `docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md`
- RC-01 相关的实施、测试与状态报告
- 当前 Git HEAD 与工作区状态

本步骤没有运行 pytest，没有执行 pip-audit，没有网络访问，没有修改 ACL 或系统权限。

## 2. 当前 Git 状态

```text
HEAD = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
HEAD_ONELINE = b90d234 fix: resolve RC-01 false success vulnerability and finalize TDD tests
BRANCH = main
PRE_REVIEW_GIT_STATUS = ?? docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md
STAGED_FILE_COUNT = 0
```

HEAD commit 实际范围：

```text
17 files changed, 5058 insertions(+), 19 deletions(-)
```

该提交不是 RC-01 专属提交，而是包含 RC-01 生产/测试修复、Stage 1B 报告和此前状态复核报告的综合提交。

### 报告是否已进入 commit

| 报告 | 是否被 Git 跟踪 | 结论 |
|---|---|---|
| `docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md` | 是 | 已包含在当前 HEAD |
| `docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md` | 是 | 已包含在当前 HEAD |
| `docs/PHASE6_CURRENT_STATUS_AFTER_RC01.md` | 是 | 已包含在当前 HEAD |
| `docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md` | 否 | 当前为未跟踪文件 |

因此：

```text
STEP9_REPORT_COMMITTED = YES
STEP8_DECISION_REPORT_COMMITTED = YES
ACCEPT_01A_REPORT_COMMITTED = NO
```

`P6-ACCEPT-01A` 报告本身尚未提交，但它的内容对应本会话中真实执行的完整 pytest 结果；不能因为报告未提交就否定测试执行事实，也不能把报告未提交写成代码未提交。

没有其他未提交的代码、测试或数据库文件。工作区唯一的未跟踪项是 `docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md`。

## 3. 完整回归结果审核

来源：`docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md` 及其对应的实际 pytest 执行。

```text
HEAD = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
PASSED = 253
SKIPPED = 7
FAILED = 0
ERRORS = 0
EXIT_CODE = 0
EXECUTION_TIME = 61.84s
COLLECTED = 260（由 253 + 7 推导；pytest -q 没有单独打印 collected 行）
```

结论：

```text
FULL_PROJECT_REGRESSION = PASS
REAL_PYTEST_EXECUTION_RECORD = PRESENT
TESTED_COMMIT = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
RC01_RELATED_FAILURES = 0
RC01_RELATED_NEW_SKIPS = 0
```

边界：

- 这是当前 HEAD 的完整项目回归，不是 RC-01 专属回归；
- 7 个 skip 不计入 passed；
- `0 failed` 不等于“所有测试都执行”；7 个 symlink 动态测试没有执行；
- 历史完整套件 `210/203/7` 早于 RC-01 测试修改，不能替代本次结果；
- 本步骤没有重新执行 pytest。

## 4. 七个 Skip 的具体名称与分类

| # | 测试位置/测试名称 | 分类 | 原因 |
|---:|---|---|---|
| 1 | `tests/test_evidence_service.py:184::test_symlink_to_outside_is_rejected` | `KNOWN_HISTORICAL_SKIP` | Windows 文件 symlink 创建失败 |
| 2 | `tests/test_report_html.py:577::test_reports_dir_itself_symlink_is_rejected_when_available` | `KNOWN_HISTORICAL_SKIP` | Windows 目录 symlink 创建失败 |
| 3 | `tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[False]` | `KNOWN_HISTORICAL_SKIP` | 文件 symlink helper 失败 |
| 4 | `tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[True]` | `KNOWN_HISTORICAL_SKIP` | 文件 symlink helper 失败 |
| 5 | `tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[False]` | `KNOWN_HISTORICAL_SKIP` | 文件 symlink helper 失败 |
| 6 | `tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[True]` | `KNOWN_HISTORICAL_SKIP` | 文件 symlink helper 失败 |
| 7 | `tests/test_report_html.py:529::test_external_file_symlink_leaf_is_rejected` | `KNOWN_HISTORICAL_SKIP` | 文件 symlink helper 失败 |

共同原因：

```text
[WinError 1314] 客户端没有所需的特权。
```

结论：

```text
KNOWN_HISTORICAL_SKIP = 7
NEW_SKIP = 0
UNKNOWN_SKIP = 0
SKIPPED_COUNTED_AS_PASSED = NO
```

这些 skip 已在此前的 C2A/R1 和 Evidence 测试中记录，不是 RC-01 引入的新 skip。

## 5. RC-01 技术证据核对

### 5.1 定向证据

```text
LEVEL_A_SCANNER = 12 passed
LEVEL_B_SERVICE = 60 passed
```

来源：RC-01 Step 7A / Step 7B 历史定向验收。

本步骤未重新执行，不能把这些数字当作本步骤结果。

### 5.2 Scanner 契约

已核对并确认：

- pip-audit JSON 的 dependency 对象被区分处理；
- `skip_reason` 依赖计入 skipped，不计入 audited；
- 输出包含 `audited_dependencies`、`skipped_dependencies`、`total_dependencies`；
- `total` 覆盖所有 dependency 对象；
- `audited + skipped == total`；
- skip 记录不生成 Finding；
- 非 dict / 异常结构能被计数或进入失败路径，不会被当作正常已审计依赖。

状态：

```text
SCANNER_STATISTICS_CONTRACT = PASS
```

### 5.3 Service 严格校验

已核对并确认：

- `_validate_statistics(metadata)` 要求 Mapping；
- 三个统计字段必须存在；
- 每个字段必须是严格 `int`，拒绝 bool/string/float/None；
- 每个字段非负；
- `total > 0`；
- `audited + skipped == total`；
- 非法统计在 `_map_findings()` / `_save_findings()` 之前失败；
- 不完整审计最终 `FAILED`；
- 完整审计才保持 `COMPLETED`；
- Finding 保存顺序保持既有边界；
- 保存 Finding 不等于成功；
- 保存异常不会被误分类为统计校验异常；
- 不完整审计不生成“未发现已知漏洞”的成功摘要。

状态：

```text
SERVICE_STRICT_STATISTICS_VALIDATION = PASS
INVALID_STATISTICS_FAIL_CLOSED = PASS
INCOMPLETE_AUDIT_FINAL_STATUS_FAILED = PASS
COMPLETE_AUDIT_COMPLETED_PATH = PASS
FINDING_SAVE_ORDER_AND_EXCEPTION_BOUNDARY = PASS
```

### 5.4 跨层测试决策

Step 8 报告：

```text
CROSS_LAYER_TEST = NOT_FOUND
DECISION = WAIVE_CROSS_LAYER_TEST
CONFIRMED_INTERFACE_MISMATCH = NONE
RESIDUAL_INTERFACE_RISK = LOW
```

该决策明确保留了以下边界：

- 真实 Scanner → 真实 Service 的跨层运行时未执行；
- 真实 pip-audit 网络执行未验证；
- 不能把 WAIVE 写成“跨层已验证”。

状态：

```text
CROSS_LAYER_DECISION = PASS
REAL_CROSS_LAYER_EXECUTION = NOT_PERFORMED
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_PERFORMED
```

## 6. RC-01 关闭条件逐项核对

| 条件 | 状态 | 依据 |
|---|---|---|
| Scanner 修复完成 | **PASS** | Scanner 12 passed；统计字段/skip 行为已核对 |
| Service 修复完成 | **PASS** | Service 60 passed；严格校验/fail-closed 已核对 |
| Level A 定向验收 | **PASS** | 12 passed，历史定向证据 |
| Level B 定向验收 | **PASS** | 60 passed，历史定向证据 |
| 跨层测试决策 | **PASS** | `WAIVE_CROSS_LAYER_TEST`，接口冲突 `NONE`，风险记录为 LOW |
| 完整项目回归 | **PASS** | 当前 HEAD：253 passed / 7 skipped / 0 failed / exit 0 |
| Git commit 证据 | **PASS** | RC-01 生产/测试文件已包含在 `b90d234` |
| 人工最终批准 | **UNKNOWN** | 仓库内没有人工批准/关闭记录；聊天中的表述不等于仓库记录 |
| 未验证事项明确记录 | **PASS** | Step 9、Step 8 和 01A 报告均记录了未执行项 |

### 条件解释

- `Git commit 证据 = PASS` 指 RC-01 代码和测试已提交；不表示 `P6-ACCEPT-01A` 报告已提交。
- `人工最终批准 = UNKNOWN` 是唯一未能闭环的条件。
- 7 个 skip 不影响 `0 failed`，但意味着 7 个动态 symlink 测试未执行。

## 7. 最终决策

```text
DECISION = RC01_CLOSURE_BLOCKED
```

### 阻塞证据

```text
BLOCKER_1 = 仓库内不存在人工最终批准记录
BLOCKER_2 = 不存在正式的 RC-01 关闭记录
```

这两项是流程/治理阻塞，不是代码缺陷：

- 技术条件全部 PASS；
- Scanner/Service/定向/跨层/完整回归均有证据；
- 但“人工最终批准”和“正式关闭记录”不能在只读审核中推断或伪造；
- 聊天中的批准不能替代仓库内的关闭记录。

因此不能输出 `RC-01 = COMPLETED`。

### 如果后续要转为 READY

需要人工完成并留下可核验记录：

1. 明确批准 RC-01 技术验收结果；
2. 记录批准人、时间、批准范围和证据引用；
3. 创建正式 RC-01 关闭记录；
4. 决定并处理 `P6_ACCEPT_01A` 报告的提交；
5. 确认关闭记录不把 7 个 skip 写成 passed；
6. 确认关闭记录保留 `REAL_CROSS_LAYER_EXECUTION=NOT_PERFORMED` 和 `REAL_PIP_AUDIT_NETWORK_EXECUTION=NOT_PERFORMED`。

## 8. 最终状态

```text
P6_ACCEPT_01B_STATUS = COMPLETED
RC01_CLOSURE_DECISION = BLOCKED
RC01_CLOSURE_READY = NO
RC01_TECHNICAL_EVIDENCE = COMPLETE
RC01_FORMAL_APPROVAL_RECORD = NOT_FOUND
RC01_FORMAL_CLOSURE_RECORD = NOT_FOUND

CODE_MODIFIED = NO
TEST_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
PYTEST_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
NETWORK_ACCESS = NO
GIT_WRITE = NO

NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤只新增本报告；没有修改代码、测试、数据库、Schema、ACL 或 Git 状态。
