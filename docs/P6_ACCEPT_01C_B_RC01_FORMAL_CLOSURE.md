# STATUS: DRAFT

# P6-ACCEPT-01C-B — RC-01 正式关闭记录草案

```text
RC01_CLOSURE_DECISION = NOT_YET_APPROVED
RC01_FORMAL_CLOSURE = NOT_CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = PENDING
RECORD_VERSION = 0.1-DRAFT
```

> 本文件是待人工审核的关闭记录草案，不是正式关闭决定。
> 它记录已完成的 RC-01 技术证据、已接受的三项残余验证限制，以及尚待人工批准的关闭决定。
> 不得把本草案表述为 RC-01 已正式关闭，也不得据此宣称 Phase 6 已完成。

## 1. 项目与 Issue 标识

| 字段 | 值 |
|---|---|
| 项目 | SRC-Research-Assistant |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| Issue ID | RC-01 |
| Issue 标题 | pip-audit 不完整审计被错误标记为 COMPLETED（假成功/假“无漏洞”） |
| 问题类别 | 扫描结果真实性、审计完整性、失败关闭 |
| 当前记录状态 | `DRAFT` |
| 记录版本 | `0.1-DRAFT` |
| 正式关闭状态 | `NOT_CLOSED` |
| 人工最终批准 | `PENDING` |

## 2. RC-01 问题背景

修复前的行为链：

1. `PipAuditScanner.parse_output()` 以 dependency 对象总数作为 `audited`；
2. 带 `skip_reason` 的依赖仍被计入 `audited`；
3. `DependencyAuditService.run_audit()` 只在 `audited == 0` 时失败；
4. 全部或部分依赖被跳过时，任务仍可进入 `COMPLETED`；
5. 无 Finding 时，依赖审计页面显示“未发现已知依赖漏洞”。

该行为会把“审计不完整”错误表达为“没有漏洞”，属于扫描结果真实性缺陷，而不是单纯的 UI 文案问题。

RC-01 的修复目标是：

```text
不完整审计 = FAILED
不完整审计不得显示为无漏洞
只有完整审计才允许 COMPLETED
```

## 3. 当前 Git 状态与基线

### 3.1 执行前只读读取结果

```text
BRANCH = main
HEAD = b3ae705b857ef7f722f4a8640529b2ce4eb41076
HEAD_SUBJECT = docs: add RC-01 closure readiness and approval review
WORKTREE_AT_START = CLEAN
STAGED = 0
UNSTAGED = 0
UNTRACKED_AT_START = 0
COMMIT_COUNT = 13
```

历史任务说明给出的 HEAD 是 `79c58bb...`，实际 HEAD 已前进到 `b3ae705...`。实际差异为：

```text
b3ae705 docs: add RC-01 closure readiness and approval review
1 file changed, 489 insertions(+)
A docs/P6_ACCEPT_01C_A_CLOSURE_READINESS_REVIEW.md
```

该提交只新增 01C-A 复核报告，不包含生产代码、测试、数据库、Schema 或配置。

### 3.2 关闭记录基线

```text
CLOSURE_BASELINE_HEAD = b3ae705b857ef7f722f4a8640529b2ce4eb41076
CLOSURE_BASELINE_SUBJECT = docs: add RC-01 closure readiness and approval review
```

如果本草案后续被人工批准并提交，正式记录应使用批准当时的实际 HEAD，而不是机械沿用本草案创建时的 HEAD。

## 4. RC-01 代码与测试提交

RC-01 的代码和测试最近改动提交：

```text
CODE_TEST_COMMIT = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
COMMIT_SUBJECT = fix: resolve RC-01 false success vulnerability and finalize TDD tests
```

该提交是综合提交，涉及 17 个文件，**不得描述为仅包含 RC-01**。

RC-01 相关文件：

```text
scanners/pip_audit_scanner.py
services/dependency_audit_service.py
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

验证：

```text
RC01_CODE_AND_TESTS_PRESENT_IN_CURRENT_HEAD = YES
RC01_CODE_AND_TESTS_UNCOMMITTED_AT_DRAFT_START = NO
```

后续提交 `93d61a8`、`79c58bb`、`b3ae705` 均为 docs-only，未改变上述 RC-01 代码和测试内容。

## 5. 修复后的核心契约

### 5.1 统计字段

```text
audited_dependencies = 正常审计完成的依赖数
skipped_dependencies = 带有效 skip_reason 的依赖数
total_dependencies   = payload.dependencies 的条目总数
```

约束：

```text
audited + skipped == total
total > 0
所有字段必须存在
所有字段必须是严格 int（拒绝 bool、string、float、None）
所有字段必须 >= 0
```

### 5.2 Service 状态规则

| 场景 | 结果 |
|---|---|
| 统计字段完整，`skipped == 0`，`audited == total` | `COMPLETED` |
| 存在 skipped 依赖 | `FAILED`；不得显示无漏洞 |
| 统计字段缺失/非法/不一致 | `FAILED`；不映射、不保存 Finding |
| 数据有效但不完整 | `FAILED`；可保留已存在的有效 Finding，但不显示成功摘要 |
| Finding 保存异常 | 保持既有异常处理，不伪装成统计校验错误 |

### 5.3 Finding 边界

- invalid 统计：在 `_map_findings()` / `_save_findings()` 之前失败；
- valid-but-incomplete：保留既有 Finding 映射/保存顺序，然后 `FAILED`；
- 保存 Finding 不等于审计成功；
- 不新增 `PARTIAL` 状态，不修改 `ScanTaskStatus` 枚举，不迁移 Schema。

## 6. Scanner 定向测试证据

```text
SCANNER_TARGETED_RESULT = 12 passed / 0 failed / 0 skipped
SCANNER_TARGETED_EXIT_CODE = 0
SCANNER_TARGETED_TIME = 1.37s
SCANNER_TARGETED_EXECUTION = HISTORICAL
```

来源：

- `docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md`
- `docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md`
- `tests/test_pip_audit_scanner.py`

本次草案创建**没有重新运行** Scanner 测试。上述结果是历史执行证据，不是本次新执行结果。

## 7. Service 定向测试证据

```text
SERVICE_TARGETED_RESULT = 60 passed / 0 failed / 0 skipped
SERVICE_TARGETED_EXIT_CODE = 0
SERVICE_TARGETED_TIME = 12.85s
SERVICE_TARGETED_EXECUTION = HISTORICAL
```

来源：

- `docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md`
- `docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md`
- `tests/test_dependency_audit_service.py`

覆盖内容包括：

- 统计字段完整性；
- 缺失/非法/负数/零 total/和不等；
- bool/string/float/None 拒绝；
- partial-skip、all-skipped、invalid 的 FAILED；
- valid-but-incomplete 的映射/保存顺序与失败摘要；
- 既有 Finding 保存异常不被统计错误覆盖。

本次草案创建**没有重新运行** Service 测试。

## 8. 完整项目回归证据

```text
FULL_REGRESSION_RESULT = 253 passed / 7 skipped / 0 failed / 0 errors
FULL_REGRESSION_EXIT_CODE = 0
FULL_REGRESSION_TIME = 61.84s
FULL_REGRESSION_TESTED_CODE_COMMIT = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
FULL_REGRESSION_EXECUTED_ON_CURRENT_HEAD = NO
```

来源：`docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md`

测试执行时对应 RC-01 代码提交为 `b90d234...`。之后的 `93d61a8`、`79c58bb`、`b3ae705` 均为 docs-only，当前 HEAD 包含同一 RC-01 代码树，但不得声称完整回归是在 `b3ae705` 上重新执行的。

报告中 `COLLECTED=260` 是从 `253 passed + 7 skipped` 推导出的观察值，原报告没有单独输出 collected 行。

## 9. 七项 symlink 测试跳过事实

```text
SYMLINK_TESTS_SKIPPED = 7
SYMLINK_SKIP_REASON = Windows WinError 1314（当前账户不能创建文件符号链接）
SYMLINK_BRANCHES_ACTUALLY_EXECUTED = NO
```

跳过的测试节点：

```text
tests/test_evidence_service.py:184::test_symlink_to_outside_is_rejected
tests/test_report_html.py:577::test_reports_dir_itself_symlink_is_rejected_when_available
tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[False]
tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[True]
tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[False]
tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[True]
tests/test_report_html.py:529::test_external_file_symlink_leaf_is_rejected
```

必须明确：

- `7 skipped` 不等于 `7 passed`；
- 对应的 symlink 分支没有在当前 Windows 环境得到实际验证；
- 不得把这些 skip 隐去，也不得表述为“符号链接安全已全部验证”。

项目负责人在本次对话中已明确接受“7 个 symlink 测试因 Windows `WinError 1314` 暂时跳过”的残余验证限制。

## 10. 跨层测试豁免

```text
CROSS_LAYER_TEST = NOT_FOUND
CROSS_LAYER_TEST_DECISION = WAIVE_CROSS_LAYER_TEST
REAL_CROSS_LAYER_EXECUTION = NOT_PERFORMED
CONFIRMED_INTERFACE_MISMATCH = NONE
RESIDUAL_INTERFACE_RISK = LOW
```

含义：

- 没有现成的 Scanner → Service 运行时集成测试；
- 项目负责人接受该跨层测试豁免；
- 该豁免不等于跨层测试通过；
- 现有证据是 Scanner 与 Service 的定向测试，加上完整项目回归，不是真实 CLI 到 Service 的端到端运行。

## 11. 真实 pip-audit 网络验证未执行

```text
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_PERFORMED
REAL_PIP_AUDIT_EXECUTED = NO
```

测试使用固定的 fake/fixture JSON，没有访问真实包索引或漏洞服务。不得把模拟 JSON 测试描述为真实网络 pip-audit 验证。

历史报告对该限制使用的字段名不完全统一：

- Step 8 / Step 9 使用 `NOT_EXECUTED`
- 01B 使用 `NOT_PERFORMED`

语义相同；本草案统一采用任务要求的 `NOT_PERFORMED`。

项目负责人在本次对话中已明确接受“真实 pip-audit 网络执行未验证”的残余验证限制。

## 12. 人工批准与授权来源

### 12.1 本次对话中的授权

| 项目 | 记录 |
|---|---|
| 三项技术限制接受 | 项目负责人在本次对话中明确接受 |
| 草案创建授权 | 已授权，仅限创建 DRAFT |
| 正式关闭授权 | 未授权 |
| 授权时间 | 会话时间可追溯，但未提供精确审批时间；不得补造 |
| 授权人姓名/签名 | 未提供；不得补造 |

### 12.2 ChatGPT 技术审核

```text
CHATGPT_TECHNICAL_REVIEW = SESSION_REPORTED_ONLY
CHATGPT_REVIEW_SCOPE = 01C-A 调查报告的技术审核认可
CHATGPT_REVIEW_IS_REPOSITORY_APPROVAL = NO
```

该审核认可来自会话，不是仓库内独立审批文件。不得把它写成仓库正式批准记录。

### 12.3 仓库内人工批准记录

```text
REPOSITORY_HUMAN_APPROVAL_RECORD = NOT_FOUND
REPOSITORY_FORMAL_CLOSURE_RECORD = NOT_FOUND
```

01B 与 01C_PRE 已记录：仓库内没有独立人工批准/正式关闭记录，聊天中的表述此前不能替代仓库记录。

### 12.4 本次记录如何处理这个差异

本草案明确区分：

```text
SESSION_ACCEPTANCE_OF_LIMITATIONS = PRESENT
SESSION_AUTHORIZATION_FOR_DRAFT = PRESENT
SESSION_REPORTED_TECHNICAL_REVIEW = PRESENT
REPOSITORY_INDEPENDENT_APPROVAL = NOT_FOUND
FORMAL_CLOSURE_AUTHORIZATION = NOT_GRANTED
```

正式批准栏保持空白/待审批，不把会话来源自动升级为仓库正式批准。

## 13. 残余风险

1. **真实跨层链路未执行**：Scanner → Service 的完整运行时接口没有被集成测试覆盖。
2. **真实网络 pip-audit 未执行**：真实 PyPI/漏洞服务响应、网络失败和缓存路径未在本环境验证。
3. **七个 symlink 分支未执行**：Windows `WinError 1314` 导致这些测试 skip，不能视为通过。
4. **测试环境依赖**：完整测试需要 dedicated temp 目录和 full-access 测试进程；普通 workspace-write 可能产生 ACL setup 错误。
5. **Finding 保存顺序**：valid-but-incomplete 场景保留既有 Finding 映射/保存顺序，保存成功不等于审计成功。
6. **代码提交范围**：`b90d234` 是综合提交，不是 RC-01-only 提交，关闭记录必须准确说明。
7. **仓库批准缺口**：独立人工批准记录仍为 `NOT_FOUND`；正式关闭前必须由人工决定是否补记录或接受会话来源例外。

## 14. 正式关闭决定（待审批）

```text
RC01_CLOSURE_DECISION = NOT_YET_APPROVED
RC01_FORMAL_CLOSURE = NOT_CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = PENDING
```

待审批栏：

```text
APPROVED_BY = ____________________
APPROVAL_ROLE = ___________________
APPROVAL_TIME = ___________________
APPROVAL_SCOPE = RC-01 technical acceptance and residual limitations
APPROVAL_REFERENCE = ______________
APPROVAL_DECISION = APPROVED / REJECTED / DEFERRED
APPROVAL_NOTES = __________________
```

在人工填写并审核前，本文件不具备正式关闭效力。

## 15. 证据文件路径与记录时间

### 15.1 证据路径

```text
docs/PHASE6_CURRENT_STATUS_AFTER_RC01.md
docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md
docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md
docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md
docs/P6_ACCEPT_01B_RC01_CLOSURE_REVIEW.md
docs/P6_ACCEPT_01C_PRE_GIT_STATUS_REVIEW.md
docs/P6_ACCEPT_01C_A_CLOSURE_READINESS_REVIEW.md
```

### 15.2 记录时间

```text
DRAFT_CREATED_AT = 2026-11-14（Asia/Shanghai）
DRAFT_CREATED_BY = AGENT_UNDER_SESSION_AUTHORIZATION
FINAL_APPROVAL_TIME = UNKNOWN
```

草案创建时间不是人工批准时间，也不是正式关闭时间。

## 16. 草案声明

```text
RECORD_STATUS = DRAFT
DRAFT_ONLY = YES
FORMAL_CLOSURE_EFFECT = NONE
RC01_CLOSURE_DECISION = NOT_YET_APPROVED
RC01_FORMAL_CLOSURE = NOT_CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = PENDING
P6_ACCEPT_01C_B_STATUS = DRAFT_CREATED
```

本草案等待项目负责人和后续独立审核。未经人工批准，不得将 RC-01 标记为正式关闭，不得将本文件作为已生效的关闭决定使用。
