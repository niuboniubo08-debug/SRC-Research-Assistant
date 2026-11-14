# P6-ACCEPT-01C-A — RC-01 正式关闭条件与批准信息只读复核

- 项目：SRC-Research-Assistant
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 调查类型：READ_ONLY
- 调查日期：2026-11-14（Asia/Shanghai）
- 关联问题：RC-01 pip-audit 假成功/不完整审计被标记为 COMPLETED
- 本步骤结论：技术证据可复核，人工批准证据仅达到 PARTIAL；不创建正式关闭记录

## 0. 结论摘要

```text
P6_ACCEPT_01C_A_STATUS = COMPLETED
RC01_TECHNICAL_EVIDENCE = PASS
RC01_HUMAN_APPROVAL_EVIDENCE = PARTIAL
RC01_CLOSURE_RECORD_READY_FOR_DRAFT = YES
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤没有修改生产代码、测试、数据库、Schema 或已有报告，没有执行 pytest、真实 pip-audit 或网络访问，也没有执行任何 Git 写操作。

## 1. 调查范围与方法

本步骤只做只读核查，不直接引用旧结论作为当前事实。实际执行了：

1. 读取当前 Git 分支、HEAD、工作区状态和最近提交范围；
2. 读取以下五份 RC-01 验收/关闭相关报告的正文：
   - `docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md`
   - `docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md`
   - `docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md`
   - `docs/P6_ACCEPT_01B_RC01_CLOSURE_REVIEW.md`
   - `docs/P6_ACCEPT_01C_PRE_GIT_STATUS_REVIEW.md`
3. 对照报告中与定向测试、完整回归、skip、跨层测试、真实网络 pip-audit 和人工批准有关的原始字段；
4. 检查 RC-01 涉及的代码和测试文件是否在 HEAD 中，以及最近一次改动提交。

本步骤没有重新运行测试。因此，报告中出现的 `12 passed`、`60 passed`、`253 passed / 7 skipped` 均标记为历史执行证据，不是本次新执行结果。

## 2. 当前 Git 状态与基线

### 2.1 实际读取结果

```text
BRANCH = main
HEAD = 79c58bb9ae4158a2638e262c253874cf106fb88d
HEAD_SUBJECT = docs: add pre-closure git status review for RC-01
WORKTREE_STATUS_AT_START = CLEAN
STAGED_FILES = 0
UNSTAGED_FILES = 0
UNTRACKED_FILES_AT_START = 0
```

### 2.2 与用户给出的基线的差异

用户给出的已知基线是：

```text
93d61a814982daf98181138244d4f083833ba3bf
```

实际 HEAD 已前进到：

```text
79c58bb9ae4158a2638e262c253874cf106fb88d
```

差异提交：

```text
79c58bb docs: add pre-closure git status review for RC-01
1 file changed, 211 insertions(+)
A docs/P6_ACCEPT_01C_PRE_GIT_STATUS_REVIEW.md
```

该提交只新增 `docs/P6_ACCEPT_01C_PRE_GIT_STATUS_REVIEW.md`，不包含生产代码、测试、数据库、Schema 或配置。

因此：

```text
USER_STATED_HEAD = 93d61a8...
ACTUAL_HEAD = 79c58bb...
HEAD_MATCHES_USER_STATEMENT = NO
BASELINE_STALE_BY_ONE_DOCS_ONLY_COMMIT = YES
```

不能继续把 `93d61a8` 当作当前 HEAD；但它仍是 01A/01B 报告所在提交，且 01A/01B 及 RC-01 代码仍包含在当前 HEAD 中。

### 2.3 RC-01 代码和测试的提交

以下五个文件的最近一次改动提交均为：

```text
b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
```

文件：

```text
scanners/pip_audit_scanner.py
services/dependency_audit_service.py
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

这五个文件均存在于当前 HEAD：

```text
RC01_CODE_AND_TESTS_IN_CURRENT_HEAD = YES
RC01_CODE_AND_TESTS_UNCOMMITTED_CHANGES = NONE
```

`93d61a8` 和 `79c58bb` 都是文档提交，未改变 RC-01 代码或测试内容。

## 3. 技术证据核对表

### 3.1 定向测试

| 证据 | 记录结果 | 来源 | 当前复核判断 |
|---|---:|---|---|
| Scanner 定向测试 | 12 passed / 0 failed / 0 skipped / exit 0 | `docs/PHASE6_STAGE1B5B_STEP1_8_SCANNER_RUNTIME_BASELINE.md` 的后续 Step 7A；`PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md` | HISTORICAL_CONFIRMED；本次未重跑 |
| Service 定向测试 | 60 passed / 0 failed / 0 skipped / exit 0 | Step 7B；`FINAL_ACCEPTANCE_EVIDENCE.md`；`01B` 复核 | HISTORICAL_CONFIRMED；本次未重跑 |
| Scanner 契约测试 | 12 项，含统计字段、skip 行为、invalid 情况 | `tests/test_pip_audit_scanner.py`；`STEP1_8` | HISTORICAL_CONFIRMED |
| Service 契约测试 | 60 个实例，含严格校验、fail-closed、终态、映射/保存边界 | `tests/test_dependency_audit_service.py`；`STEP7B` | HISTORICAL_CONFIRMED |

Scanner 定向证据对应的具体结果来自 Step 7A：

```text
12 passed in 1.37s
exit 0
```

Service 定向证据对应的具体结果来自 Step 7B：

```text
60 passed in 12.85s
exit 0
```

两者都是定向测试，不等于完整回归，也不等于真实 pip-audit 网络执行。

### 3.2 完整项目回归

`docs/P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md` 记录：

```text
执行提交 = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
结果 = 253 passed / 7 skipped / 0 failed / 0 errors
退出码 = 0
耗时 = 61.84s
COLLECTED = 260（由 253 + 7 推导，报告中无显式 collected 行）
```

当前 HEAD 是 `79c58bb`，但仍包含 `b90d234` 的 RC-01 代码和测试；`93d61a8`、`79c58bb` 只增加文档。因此：

```text
FULL_REGRESSION_TESTED_CODE_COMMIT = b90d234
CURRENT_HEAD = 79c58bb
CODE_TEST_TREE_AFTER_B90D234_CHANGED = NO
FULL_REGRESSION_RERUN_IN_THIS_STEP = NO
```

可以认为本步骤的 RC-01 代码树与完整回归时相同，但不能把这表述为“在 79c58bb 上重新执行了 253 项测试”。

### 3.3 七个 skip

完整回归的 7 个 skip 均为 Windows `WinError 1314` 符号链接创建受限：

```text
tests/test_evidence_service.py:184::test_symlink_to_outside_is_rejected
tests/test_report_html.py:577::test_reports_dir_itself_symlink_is_rejected_when_available
tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[False]
tests/test_report_html.py:529::test_internal_file_symlink_leaf_is_rejected[True]
tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[False]
tests/test_report_html.py:529::test_broken_symlink_leaf_is_rejected[True]
tests/test_report_html.py:529::test_external_file_symlink_leaf_is_rejected
```

结论：

```text
SYMLINK_TESTS_SKIPPED = 7
SYMLINK_SKIP_REASON = Windows WinError 1314（当前账户不能创建文件符号链接）
SYMLINK_BRANCHES_ACTUALLY_EXECUTED = NO
```

这不是产品断言失败，也不能被表述为“符号链接分支已验证通过”。

### 3.4 RC-01 契约与失败的关闭状态

五份报告和当前代码/测试共同支持以下契约：

- `PipAuditScanner` 对每个 dependency 分别统计 `audited_dependencies`、`skipped_dependencies`、`total_dependencies`；
- `skip_reason` 的记录不再计入 `audited`，且 skip 记录不生成 Finding；
- Service 在映射/保存 Finding 之前校验统计字段；
- metadata 缺失、非 Mapping、bool、非 int、负数、total<=0、`audited + skipped != total` 均 fail closed；
- 不完整审计最终为 `FAILED`，不显示“无漏洞”；
- 只有统计完整（`skipped == 0` 且 `audited == total`）才允许 `COMPLETED`；
- invalid 统计不映射、不保存 Finding；valid-but-incomplete 可保留已有 Finding，但最终仍 FAILED；
- 既有 Finding 保存异常仍按原行为报告，不伪装成统计错误。

历史 targeted 证据显示：

```text
Scanner = 12 passed
Service = 60 passed
Full suite = 253 passed / 7 skipped / 0 failed
```

本次没有重新执行这些测试，因此它们是 `HISTORICAL_CONFIRMED`，不是本步骤的 `CURRENT_RUNTIME` 结果。

### 3.5 跨层测试决策

`docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md` 记录：

```text
CROSS_LAYER_TEST = NOT_FOUND
DECISION = WAIVE_CROSS_LAYER_TEST
CONFIRMED_INTERFACE_MISMATCH = NONE
RESIDUAL_RISK = LOW
```

该决定是明确的人工/设计豁免，不是测试通过。它允许在已有 Scanner 与 Service 定向证据基础上继续关闭评估，但不覆盖真实 CLI 到 Service 的完整运行链。

## 4. 未验证事项与报告一致性

### 4.1 限制事实

```text
REAL_CROSS_LAYER_EXECUTION = NOT_PERFORMED
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_PERFORMED
SYMLINK_TESTS_SKIPPED = 7
```

### 4.2 报告间用词和覆盖范围

| 报告 | 真实跨层执行 | 真实 pip-audit 网络 | 7 个 symlink skip |
|---|---|---|---|
| `PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md` | `CROSS_LAYER_TEST=NOT_FOUND`；`WAIVE` | `REAL_PIP_AUDIT_NETWORK_EXECUTION=NOT_EXECUTED` | 未在该报告逐项列出 |
| `PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md` | `WAIVE_CROSS_LAYER_TEST`；未执行真实跨层 | `NOT_EXECUTED` | 未逐项列出 |
| `P6_ACCEPT_01A_POST_COMMIT_FULL_REGRESSION.md` | 未执行真实跨层 | 未执行真实网络 | 列出 7 个 skip 及 `WinError 1314` |
| `P6_ACCEPT_01B_RC01_CLOSURE_REVIEW.md` | `REAL_CROSS_LAYER_EXECUTION=NOT_PERFORMED` | `REAL_PIP_AUDIT_NETWORK_EXECUTION=NOT_PERFORMED` | 以完整回归 `7 skipped` 记录 |
| `P6_ACCEPT_01C_PRE_GIT_STATUS_REVIEW.md` | 未重新验证 | 未执行 | 未重述 7 个 skip |

### 4.3 一致性判断

事实层面一致：

```text
CROSS_LAYER_RUNTIME_EXECUTED = NO（所有报告一致）
REAL_PIP_AUDIT_NETWORK_EXECUTED = NO（所有报告一致）
SYMLINK_SKIP_COUNT = 7（相关执行报告一致）
```

字段层面不完全统一：

- `REAL_PIP_AUDIT_NETWORK_EXECUTION` 在 Step 8/Step 9 使用 `NOT_EXECUTED`，在 01B 使用 `NOT_PERFORMED`；语义相同，词面不同。
- `REAL_CROSS_LAYER_EXECUTION` 这个精确字段只出现在 01B；Step 8 使用 `CROSS_LAYER_TEST=NOT_FOUND` 和 `WAIVE_CROSS_LAYER_TEST`。
- 精确字段 `SYMLINK_TESTS_SKIPPED=7` 未在这些报告中作为统一字段出现；7 个 skip 在 01A/01B 有执行记录，Step 8/9 未逐项列出。
- 01C_PRE 是 Git 状态报告，不承担技术限制表职责，因此没有重述全部限制，不构成事实冲突，但正式关闭记录必须自行补齐这些字段。

结论：

```text
LIMITATION_FACT_CONSISTENCY = CONSISTENT
LIMITATION_FIELD_NAME_CONSISTENCY = PARTIAL
LIMITATION_FIELD_COVERAGE = PARTIAL
```

不能因为字段未统一，就把未执行的真实网络/跨层验证改写成通过；正式关闭记录应统一使用本报告第 6 节建议的字段。

## 5. 人工批准信息核对

### 5.1 三类批准来源

| 类型 | 当前证据 | 可核验性 | 判断 |
|---|---|---|---|
| A. ChatGPT 会话中的人工技术验收批准 | 用户在本任务说明中陈述此前已由 ChatGPT 人工审核批准 RC-01 技术证据 | 仅有会话陈述；无姓名、身份、精确时间、签名或独立附件 | `SESSION_REPORTED_ONLY` |
| B. 仓库中已存在的人工批准记录 | 01B 与 01C_PRE 均明确记录 `NOT_FOUND`；未发现独立批准文件 | 可检索仓库后仍为 `NOT_FOUND` | `NOT_FOUND` |
| C. 项目负责人对正式关闭记录实施的授权 | 本任务只授权 01C-A 只读复核；未授权创建关闭记录 | 当前任务文本明确 | `NOT_GRANTED` |

### 5.2 会话批准事实与仓库政策的冲突

用户提供的会话语境称：

```text
RC-01 技术验收已由 ChatGPT 在本会话中人工审核批准
```

但仓库内报告明确记录：

- 01B：`人工最终批准 = UNKNOWN`，仓库内没有人工批准/关闭记录；聊天中的表述不等于仓库记录；
- 01C_PRE：如果 01C-A 需要正式关闭，必须有人工批准的仓库记录，不能以聊天内容替代。

因此不能把会话陈述升级为“仓库已存在正式批准记录”。

### 5.3 汇总结论

```text
RC01_HUMAN_APPROVAL_SOURCE_A = SESSION_REPORTED_ONLY
RC01_HUMAN_APPROVAL_SOURCE_B = NOT_FOUND
RC01_HUMAN_APPROVAL_SOURCE_C = NOT_GRANTED
RC01_HUMAN_APPROVAL_EVIDENCE = PARTIAL
```

`PARTIAL` 的含义是：存在会话来源的技术验收陈述，但没有可独立核验的仓库批准记录，也没有创建正式关闭记录的授权。

不得虚构批准人姓名、身份、时间或签名；如果未来要写入精确时间，必须由批准人补充。

## 6. 建议的正式关闭记录结构

本步骤只提出建议，不创建文件。建议文件名可由用户决定，例如：

```text
docs/P6_ACCEPT_01C_B_RC01_FORMAL_CLOSURE.md
```

建议字段：

1. **项目和 RC-01 标识**
   - `PROJECT = SRC-Research-Assistant`
   - `ISSUE_ID = RC-01`
   - `ISSUE_TITLE = pip-audit 不完整审计假成功`

2. **关闭记录版本**
   - `RECORD_VERSION`
   - `RECORD_STATUS = DRAFT / APPROVED / SUPERSEDED`

3. **当前 Git HEAD**
   - `CLOSURE_BASELINE_HEAD`，按创建时的实际 HEAD 填写，不得沿用旧 HEAD。

4. **RC-01 代码和测试提交**
   - `CODE_TEST_COMMIT = b90d234...`
   - 代码和测试文件清单
   - 说明后续 docs-only 提交不改变代码树。

5. **Scanner 定向验收证据**
   - `SCANNER_TARGETED_RESULT = 12 passed`
   - 执行时间、命令、环境、报告路径
   - 明确 `HISTORICAL_RESULT`，不是关闭记录创建时重跑。

6. **Service 定向验收证据**
   - `SERVICE_TARGETED_RESULT = 60 passed`
   - 执行时间、命令、环境、报告路径
   - 明确 `HISTORICAL_RESULT`。

7. **完整项目回归证据**
   - `FULL_REGRESSION_RESULT = 253 passed / 7 skipped / 0 failed`
   - `TESTED_CODE_COMMIT = b90d234...`
   - 当前 HEAD 与测试提交的 docs-only 差异说明。

8. **7 个 skip 的具体限制**
   - `SYMLINK_TESTS_SKIPPED = 7`
   - 每个测试节点、`WinError 1314` 原因
   - 明确这些分支未实际执行。

9. **跨层测试豁免决定**
   - `CROSS_LAYER_TEST = NOT_FOUND`
   - `DECISION = WAIVE_CROSS_LAYER_TEST`
   - 豁免理由、风险和批准来源
   - 不得写成“跨层测试通过”。

10. **未执行的真实网络 pip-audit 验证**
    - `REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_PERFORMED`
    - 说明测试使用 fake/fixture JSON，未访问真实包索引/漏洞服务。

11. **人工技术验收批准来源**
    - `APPROVAL_SOURCE_TYPE = SESSION_REPORTED / REPOSITORY_RECORD`
    - 若为会话来源，明确 `APPROVAL_SUBJECT = ChatGPT 会话中的人工审核`
    - `APPROVAL_SCOPE = RC-01 技术验收证据`
    - `APPROVAL_TIME = UNKNOWN`（若无法核验）
    - 不得伪造姓名、签名或仓库外记录。

12. **正式关闭决定**
    - `RC01_CLOSURE_DECISION = APPROVED / BLOCKED / CONDITIONAL`
    - 明确是技术关闭还是正式管理关闭
    - 不得在授权缺失时写 `APPROVED`。

13. **已知遗留风险**
    - 真实跨层链路未执行
    - 真实网络 pip-audit 未执行
    - 7 个 symlink 测试未执行
    - 测试环境依赖 dedicated temp/full-access
    - Finding 保存顺序的既有异常边界

14. **证据文件路径**
    - Step 8 决策
    - Step 9 证据摘要
    - 01A 完整回归
    - 01B 关闭审核
    - 01C_PRE Git 状态
    - 本 01C-A 复核报告

15. **关闭记录创建时间**
    - 使用实际创建时间，带时区
    - 不得沿用本报告日期作为关闭时间

建议同时增加：

```text
APPROVAL_RECORD_PRESENT = YES / NO
FORMAL_CLOSURE_AUTHORIZED = YES / NO
RECORD_CREATED_BY = HUMAN / AGENT_UNDER_HUMAN_AUTHORIZATION
```

## 7. 尚需用户决定的事项

以下事项不能由本步骤代替决定：

1. **是否接受现有跨层测试豁免**
   - 接受：在正式记录中保留 `WAIVE_CROSS_LAYER_TEST` 和残余风险；
   - 不接受：必须先设计并执行真实 Scanner→Service 集成测试，再关闭。

2. **是否接受 7 个 symlink 测试暂时跳过**
   - 接受：记录 `WinError 1314` 限制，不声称这些分支已验证；
   - 不接受：需要在具备符号链接权限的 Windows/Linux 环境补跑。

3. **是否接受真实 pip-audit 网络执行未验证**
   - 接受：记录为 `NOT_PERFORMED`，不声称端到端网络链路已验证；
   - 不接受：必须在受控环境执行真实 pip-audit 并保存输出。

4. **是否批准创建正式 RC-01 关闭记录**
   - 本步骤只建议结构，不创建；
   - 需要明确授权后才能进入 01C-B。

5. **是否要求正式关闭记录单独提交 Git**
   - 若不要求：记录可作为工作区文件保留；
   - 若要求：需要单独、精确路径的 `git add`/`commit`，不得夹带其他未审文件。

6. **是否接受“会话来源批准”作为正式批准的替代**
   - 这是最关键的未决事项；
   - 现有 01B/01C_PRE 报告明确要求仓库内人工批准记录，且写明聊天内容不能替代；
   - 若项目负责人决定接受会话来源，必须在关闭记录中显式记录这一例外及其依据；否则应先补可核验的仓库批准记录。

## 8. 是否建议进入 01C-B

技术上：

```text
RC01_TECHNICAL_EVIDENCE = PASS
```

人工批准上：

```text
RC01_HUMAN_APPROVAL_EVIDENCE = PARTIAL
```

因此建议：

```text
RC01_CLOSURE_RECORD_READY_FOR_DRAFT = YES
01C_B_RECOMMENDATION = CONDITIONAL_GO_FOR_DRAFT_ONLY
01C_B_AUTHORIZED_NOW = NO
```

理由：

- Scanner/Service 定向证据、完整回归、7 个 skip 的具体原因、跨层豁免和未执行网络验证均有可追溯记录；
- 当前 HEAD 与测试代码树的差异仅为 docs-only，RC-01 代码/测试未变；
- 但人工批准只有会话陈述，仓库内 `NOT_FOUND`，且用户尚未授权创建正式记录；
- 因此可以起草关闭记录，但不能在本步骤或未经授权时宣布正式关闭。

## 9. 停止状态

```text
P6_ACCEPT_01C_A_STATUS = COMPLETED
RC01_TECHNICAL_EVIDENCE = PASS
RC01_HUMAN_APPROVAL_EVIDENCE = PARTIAL
RC01_CLOSURE_RECORD_READY_FOR_DRAFT = YES
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

明确未执行：

```text
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
EXISTING_DOCS_MODIFIED = NO
FORMAL_CLOSURE_RECORD_CREATED = NO
PYTEST_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
NETWORK_ACCESS = NO
GIT_WRITE = NO
RC01_CLOSURE_DECISION = NOT_DECLARED
```

本报告不创建正式关闭记录，不进入 01C-B，不宣布 RC-01 或 Phase 6 完成。等待人工审核和明确授权。
