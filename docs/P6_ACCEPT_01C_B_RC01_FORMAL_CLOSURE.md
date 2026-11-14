# STATUS = APPROVED

# P6-ACCEPT-01C-B — RC-01 正式关闭记录

```text
STATUS = APPROVED
RC01_CLOSURE_DECISION = APPROVED
RC01_FORMAL_CLOSURE = CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = APPROVED
CURRENT_FORMAL_CLOSURE_RECORD_STATUS = CLOSED
RECORD_VERSION = 1.0-APPROVED
```

> 本文件是已按项目负责人正式授权定稿的 RC-01 正式关闭记录。
> 它记录 RC-01 的技术证据、已接受的三项残余验证限制、正式批准依据和关闭结论。
> RC-01 正式关闭不等于 Phase 6 整体完成，也不代表其他阶段或功能自动通过。

## 1. 项目与 Issue 标识

| 字段 | 值 |
|---|---|
| 项目 | SRC-Research-Assistant |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| Issue ID | RC-01 |
| Issue 标题 | pip-audit 不完整审计被错误标记为 COMPLETED（假成功/假“无漏洞”） |
| 问题类别 | 扫描结果真实性、审计完整性、失败关闭 |
| 当前记录状态 | `APPROVED` |
| 记录版本 | `1.0-APPROVED` |
| 正式关闭状态 | `CLOSED` |
| 人工最终批准 | `APPROVED` |

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

### 3.1 定稿前只读读取结果

```text
BRANCH = main
HEAD = de4a639971e790264798db3bf02cf9b5ce8b18b4
HEAD_SUBJECT = docs: add RC-01 post-commit verification report
LATEST_COMMIT_TIME = 2026-11-14T19:55:49+08:00
TASK_STATED_HEAD = 6e615db12ef5019295de2e8b2343756e4cc2e572
HEAD_DRIFT = ONE_DOCS_ONLY_COMMIT
WORKTREE_AT_C1_START = CLEAN
STAGED = 0
UNSTAGED = 0
UNTRACKED_AT_C1_START = 0
```

任务说明给出的 `6e615db...` 已被项目负责人后续提交的 C1 核验报告推进到 `de4a639...`。差异是文档提交，不是生产代码或测试变更：

```text
LATEST_VERIFIED_COMMIT = de4a639971e790264798db3bf02cf9b5ce8b18b4
COMMIT_SUBJECT = docs: add RC-01 post-commit verification report
COMMIT_FILES:
A docs/P6_ACCEPT_01C_C1_POST_COMMIT_VERIFICATION.md
PRIOR_C1_VERIFIED_COMMIT = 6e615db12ef5019295de2e8b2343756e4cc2e572
```

该提交只新增 C1 提交后核验报告。C2 定稿发生在该提交之后，不包含在该提交中；没有虚构新的 commit hash。

### 3.2 关闭记录基线

```text
CLOSURE_BASELINE_HEAD = de4a639971e790264798db3bf02cf9b5ce8b18b4
CLOSURE_BASELINE_SUBJECT = docs: add RC-01 post-commit verification report
PRIOR_C1_VERIFIED_COMMIT = 6e615db12ef5019295de2e8b2343756e4cc2e572
C2_FINALIZATION_AFTER_LATEST_COMMIT = YES
C2_RECORD_IN_LATEST_COMMIT = NO
```

本记录基于实际已核验的最新人工提交定稿。C2 定稿产生的文件修改不改变上述提交 hash，也不声称该提交已包含本记录。

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
CROSS_LAYER_INTEGRATION_TEST_IMPLEMENTATION = NOT_FOUND
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
| 草案创建授权 | 已授权并完成 DRAFT 创建 |
| 正式关闭授权 | 项目负责人已明确批准 RC-01 正式关闭 |
| 批准时间 | `2026-11-14T20:00+08:00`（Asia/Shanghai，以本记录定稿时间为准） |
| 批准人姓名/签名 | 未提供；不得补造；仅记录会话身份 |

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
PRE_EXISTING_REPOSITORY_FORMAL_CLOSURE_RECORD = NOT_FOUND
CURRENT_FORMAL_CLOSURE_RECORD_STATUS = CLOSED
```

01B 与 01C_PRE 已记录：仓库内没有独立人工批准/正式关闭记录。本次正式关闭以项目负责人在会话中的明确书面批准为依据；该来源与“仓库内独立批准记录”分开记录，不虚构历史审批文件。

### 12.4 本次记录如何处理这个差异

本记录明确区分：

```text
SESSION_ACCEPTANCE_OF_LIMITATIONS = PRESENT
SESSION_AUTHORIZATION_FOR_DRAFT = PRESENT
SESSION_REPORTED_TECHNICAL_REVIEW = PRESENT
SESSION_AUTHORIZATION_FOR_FORMAL_CLOSURE = PRESENT
REPOSITORY_INDEPENDENT_APPROVAL = NOT_FOUND
FORMAL_CLOSURE_AUTHORIZATION = GRANTED
```

正式批准依据是会话来源的明确书面批准，不是仓库内独立审批记录；两者不得混同。

## 13. 残余风险

1. **真实跨层链路未执行**：Scanner → Service 的完整运行时接口没有被集成测试覆盖。
2. **真实网络 pip-audit 未执行**：真实 PyPI/漏洞服务响应、网络失败和缓存路径未在本环境验证。
3. **七个 symlink 分支未执行**：Windows `WinError 1314` 导致这些测试 skip，不能视为通过。
4. **测试环境依赖**：完整测试需要 dedicated temp 目录和 full-access 测试进程；普通 workspace-write 可能产生 ACL setup 错误。
5. **Finding 保存顺序**：valid-but-incomplete 场景保留既有 Finding 映射/保存顺序，保存成功不等于审计成功。
6. **代码提交范围**：`b90d234` 是综合提交，不是 RC-01-only 提交，关闭记录必须准确说明。
7. **仓库批准缺口**：独立人工批准记录仍为 `NOT_FOUND`；项目负责人已依据会话中的明确书面批准接受该例外并授权正式关闭，本记录如实保留该差异。

## 14. 正式关闭决定

```text
RC01_CLOSURE_DECISION = APPROVED
RC01_FORMAL_CLOSURE = CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = APPROVED
CURRENT_FORMAL_CLOSURE_RECORD_STATUS = CLOSED
```

批准信息：

```text
APPROVED_BY = 项目负责人（会话身份；姓名未提供）
APPROVAL_ROLE = PROJECT_OWNER
APPROVAL_TIME = 2026-11-14T20:00+08:00
APPROVAL_TIME_ZONE = Asia/Shanghai
APPROVAL_TIME_BASIS = 本正式关闭记录定稿时间
APPROVAL_SCOPE = RC-01 technical acceptance and accepted residual limitations
APPROVAL_REFERENCE = 项目负责人在 ChatGPT 会话中的明确书面批准
APPROVAL_DECISION = APPROVED
APPROVAL_BASIS = SESSION_WRITTEN_APPROVAL
REPOSITORY_INDEPENDENT_APPROVAL_RECORD = NOT_FOUND
APPROVAL_NOTES = 项目负责人明确批准 RC-01 正式关闭；未声称仓库此前存在独立人工审批记录，也未补造姓名、签名或审批文件。
```

正式关闭结论：

- RC-01 技术修复已完成；
- 已有测试证据满足本次接受标准；
- 已接受的技术限制作为残余风险保留；
- 项目负责人批准正式关闭；
- RC-01 正式关闭；
- 本次关闭不扩大解释为 Phase 6 整体完成。

本记录是既有 DRAFT 的正式定稿，具有正式关闭记录的效力；其中的 DRAFT 历史字段仅用于追溯草案创建过程。

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
FINAL_APPROVAL_TIME = 2026-11-14T20:00+08:00
FORMALIZED_AT = 2026-11-14T20:00+08:00
FORMALIZED_BY = AGENT_UNDER_PROJECT_OWNER_AUTHORIZATION
```

草案创建时间不是人工批准时间。正式关闭记录的批准时间以本次定稿时间为准，并已标注 Asia/Shanghai 时区。

## 16. 正式关闭声明

```text
RECORD_STATUS = APPROVED
DRAFT_ONLY = NO
FORMAL_CLOSURE_EFFECT = ACTIVE
RC01_CLOSURE_DECISION = APPROVED
RC01_FORMAL_CLOSURE = CLOSED
HUMAN_FINAL_CLOSURE_APPROVAL = APPROVED
CURRENT_FORMAL_CLOSURE_RECORD_STATUS = CLOSED
P6_ACCEPT_01C_B_STATUS = FORMALIZED
PHASE6_OVERALL_COMPLETION = NOT_DECLARED
```

RC-01 已正式关闭。

本记录不代表 Phase 6 整体完成，也不代表其他阶段、其他功能或所有残余风险均已通过。仓库内独立人工批准记录仍为 `NOT_FOUND`；本次批准的来源是项目负责人在 ChatGPT 会话中的明确书面批准，已按会话来源单独记录。
