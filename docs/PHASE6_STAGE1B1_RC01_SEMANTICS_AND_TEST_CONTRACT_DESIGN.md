# Phase 6 Stage 1B-1：RC-01 业务语义与测试契约设计

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：0.5.0
- Schema：v5
- 任务性质：READ_ONLY + DESIGN_ONLY
- 前置阶段：Stage 1A = COMPLETED / APPROVED
- 前置报告：`docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md`
- 本报告性质：设计建议，不是产品批准，不是实施记录
- 未修改生产代码、测试、README、数据库、Schema、Manifest 或 Git
- 未运行 pytest、真实 pip-audit 或 GUI

## 1. 任务性质与边界

本任务只回答“pip-audit 结果的正确业务语义是什么”和“未来测试应固定什么契约”，不修复代码。

边界：

- `PRODUCTION_CODE_MODIFIED = NO`
- `TEST_MODIFIED = NO`
- `DATABASE_MODIFIED = NO`
- `SCHEMA_MODIFIED = NO`
- `GIT_MUTATION = NO`
- `TESTS_RUN = NO`
- `REAL_PIP_AUDIT_RUN = NO`
- `GUI_RUN = NO`

证据标签约定：

- **CONFIRMED**：可由当前代码/测试/Schema 静态确认，或 Stage 1A 已确认的当前事实。
- **INFERRED**：由确定的代码路径推导，但未实际运行。
- **PROPOSED**：本报告建议的设计，不是已批准规则。
- **UNKNOWN**：资料或运行证据不足。

所有“当前行为”均指当前 `bffb5ac...` 工作树，不代表历史验收运行结果。

## 2. 实际读取的文件

### 2.1 本轮直接核对

| 文件 | 用途 |
|---|---|
| `docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md` | 复核 RC-01 的已确认事实 |
| `scanners/pip_audit_scanner.py` | 当前解析与计数逻辑 |
| `services/dependency_audit_service.py` | 任务状态、摘要、持久化 |
| `tests/test_pip_audit_scanner.py` | 固定 skipped 行为的测试 |
| `tests/test_dependency_audit_service.py` | 服务层 fake/状态测试 |
| `database/schema.py` | `scan_tasks.status` CHECK 与任务表结构 |
| `core/models/enums.py`、`core/models/scan_task.py`、`core/models/finding.py` | 状态、任务、Finding 字段 |
| `ui/dependency_page.py` | 当前“无漏洞”文案与 warning 展示路径 |
| `tests/test_ui_dependency_audit.py` | UI 空结果覆盖范围 |

Stage 1A 已读取的 pip-audit 包源仍作为 skipped 语义证据：

- `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_format\json.py`
- `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_service\pypi.py`
- `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_dependency_source\pip.py`

本轮未运行任何测试、扫描器、GUI 或数据库查询。

## 3. Stage 1A 事实复核

### 3.1 已确认的 Stage 1A 结论

- `RC01_STATUS = CONFIRMED`（CONFIRMED）
- `CURRENT_AUDITED_SEMANTICS = INCORRECT`（CONFIRMED）
- `FIX_IMPLEMENTED = NO`（CONFIRMED）
- `SCHEMA_CHANGE_REQUIRED = NO`（Stage 1A 的建议结论，非产品批准；PROPOSED）
- 全部 skipped 的当前结果是 `FALSE_SUCCESS`（INFERRED，基于代码路径，未运行）
- Stage 1A 报告存在：25,927 bytes，367 行，SHA-256 `47119199469B5F93A048E3E27493CAA18EF670F285A59CC65E568874C4A12B91`（CONFIRMED）

### 3.2 当前关键事实

1. `scanners/pip_audit_scanner.py:311` 的 `audited = len(dependencies)`（CONFIRMED）。
2. skipped 记录的 JSON 只有 `name` 和 `skip_reason`，没有 `version`、`vulns`（CONFIRMED，Stage 1A 包源证据）。
3. `services/dependency_audit_service.py:325-338` 只有 `audited == 0` 的失败门禁（CONFIRMED）。
4. `tests/test_pip_audit_scanner.py:71-78` 把 `skipped-package` 断言计入 `audited == 3`（CONFIRMED）。
5. `ui/dependency_page.py:708-711` 在 COMPLETED 且无 Finding 时显示“当前任务未发现已知依赖漏洞”（CONFIRMED）。
6. `scan_tasks.status` 的 CHECK 只允许 `pending/running/completed/failed/cancelled/blocked`（CONFIRMED，`database/schema.py:47-53`）。
7. 当前没有 `PARTIAL`、`INCOMPLETE` 或 `COMPLETED_WITH_WARNINGS` 状态（CONFIRMED）。
8. `ScanTask` 没有独立的 `audit_complete`、`skipped_dependencies`、`total_dependencies` 字段（CONFIRMED）。
9. 实际项目类名是 `ScanOutput`，不是 `ScanResult`；没有独立 `ScanResult` 类（CONFIRMED）。
10. `DependencyAuditOutcome` 只有 `audited_dependencies`、`warnings`、`errors`，没有 skipped 计数（CONFIRMED）。

### 3.3 仍不能确认的内容

- 全部 skipped 在真实运行中的最终 UI 呈现（INFERRED；未运行）。
- pip-audit 网络/索引错误的具体 exit code/stdout 组合（UNKNOWN）。
- 真实数据库在全部 skipped 测试后的任务行（本轮禁止写库；INFERRED）。
- 当前完整测试集是否仍全部通过（本轮禁止运行；UNKNOWN）。

## 4. 当前统计语义

### 4.1 当前实际计算

| 概念 | 当前实现 | 语义判断 |
|---|---|---|
| `total_dependencies` | 没有显式变量；使用 `len(payload["dependencies"])` | 不可见、未持久化，且包含非 dict/异常项（CONFIRMED） |
| `audited_dependencies` | `len(dependencies)`（`pip_audit_scanner.py:311`） | 把 skipped、非 dict、缺 `vulns` 的记录计入（CONFIRMED，错误） |
| `skipped_dependencies` | 仅存于 `warnings` 字符串 | 无结构化计数、无门禁（CONFIRMED） |
| `vulnerabilities_found` | `len(saved)`，按 `(name.lower(), vuln_id)` 去重 | 漏洞数量本身正确，但不等同于依赖已审计（CONFIRMED） |
| `audit_complete` | 不存在 | 无法表达“全部应审计依赖均完成”（CONFIRMED） |
| `task_success` | `status == COMPLETED` | 不完整审计也可 COMPLETED（CONFIRMED，代码路径） |
| 空结果文案 | `COMPLETED and not findings` | 不完整审计也会显示“未发现”（CONFIRMED） |

### 4.2 当前统计不一致

- `audited` 是“输入依赖数组长度”，不是“完成查询的依赖数”（CONFIRMED）。
- `vulnerabilities_found` 是“去重 Finding 数量”，可以与 `audited` 无直接关系（CONFIRMED）。
- `skipped` 没有数字，只有 warning（CONFIRMED）。
- `audit_complete` 不存在，因而无法从任务对象可靠计算“不完整”（CONFIRMED）。
- `_finish(..., skipped=...)` 参数存在，但当前调用方传空 tuple，函数体不读取（CONFIRMED）；这等于预留了语义却没有实现。

## 5. 当前任务状态处理

### 5.1 状态链路

```text
PipAuditScanner.scan
  -> parse_output() -> (findings, warnings, len(dependencies))
  -> ScanOutput(metadata.audited_dependencies)
  -> DependencyAuditService.run_audit
  -> _save_findings
  -> _finish
  -> scan_tasks.status
  -> DependencyPage._on_completed / _update_task_display
```

### 5.2 当前场景状态

| 场景 | 当前代码路径 | 当前任务状态 | 证据级别 |
|---|---|---|---|
| A 全部正常，0 漏洞 | `audited=N>0`，0 Finding | COMPLETED | CONFIRMED（静态） |
| B 全部正常，有漏洞 | `audited=N>0`，保存 Finding | COMPLETED | CONFIRMED（静态） |
| C 部分 skipped | `audited=全部 N`，正常项可能有 Finding | COMPLETED | INFERRED（静态推导） |
| D 全部 skipped | `audited=N>0`，0 Finding | COMPLETED，摘要“未发现” | INFERRED |
| E 依赖列表为空 | `audited=0` | FAILED | CONFIRMED（`audited == 0` 门禁） |
| F 执行/网络/索引错误 | 无 JSON/非 0/1 返回 -> 执行失败；若有 skipped JSON 则可能走 C/D | FAILED 或假成功 | UNKNOWN（具体工具输出组合） |
| G JSON 解析失败 | `ScannerParseError` | FAILED，无 Finding | CONFIRMED（异常路径） |

### 5.3 是否可能把不完整审计显示为成功

**是。**（CONFIRMED 静态；D 的最终任务行为为 INFERRED）

具体路径：

1. 全部 skipped 仍然 `audited = len(dependencies) > 0`；
2. 服务不进入 `audited == 0` 失败分支；
3. `_save_findings` 保存 0 条；
4. `_finish(COMPLETED)` 写入摘要“已审计 N 个依赖，未发现已知漏洞”；
5. UI 在 `COMPLETED + 无 Finding` 时显示“当前任务未发现已知依赖漏洞”。

warning 只在 `_on_completed` 中临时显示，`_update_task_display` 重新读取任务后不会持久保留。该“成功后警告消失”的行为为 CONFIRMED（代码路径），实际 UI 运行未验证。

## 6. 七个场景分析

### 场景 A：全部依赖正常审计，0 个漏洞

- **当前**：`audited=total`，0 Finding，COMPLETED，摘要“未发现”。（CONFIRMED 代码；INFERRED 真实运行）
- **问题**：当前统计本身能表达 0 漏洞，但依赖计数定义仍错误（把 skipped 算入）；在 A 中恰好没有 skipped，结果正确。
- **建议**：`audited=total`，`skipped=0`，`invalid=0`，`audit_complete=True`，`vulnerabilities_found=0`，COMPLETED，明确“完成审计且未发现”。

### 场景 B：全部依赖正常审计，发现漏洞

- **当前**：`audited=total`，保存 Finding，COMPLETED。（CONFIRMED 代码）
- **建议**：完整审计 + `vulnerabilities_found=M`，COMPLETED，展示“已审计 N，发现 M”，不得用 M 反推 N。

### 场景 C：部分 skipped，其他正常

- **当前**：`audited=total`（错误），正常项 Finding 可保存；如果正常项 0 漏洞则摘要“未发现”；warning 仅临时显示；任务 COMPLETED。（INFERRED）
- **建议**：`audited=normal`，`skipped>0`，`invalid` 单独计数，`audit_complete=False`，`vulnerabilities_found=正常项发现数`；任务不得被表达为“完整成功”。
- **推荐最小状态**：FAILED（保留已发现 Finding）；理由见第 8 节。

### 场景 D：全部 skipped

- **当前**：`audited=N>0`，0 Finding，COMPLETED，摘要“未发现”。（INFERRED，已由代码路径确定）
- **建议**：`audited=0`，`skipped=total`，`audit_complete=False`，FAILED，明确“没有依赖完成审计，不能判定无漏洞”。

### 场景 E：依赖列表为空

- **当前**：`audited=0`，FAILED，错误“pip-audit 未审计到任何依赖，不能判定为无漏洞”。（CONFIRMED 代码）
- **建议**：`total=0`，`audited=0`，`skipped=0`，`audit_complete=False`，FAILED；禁止用空结果表示“0 漏洞”。

### 场景 F：执行、网络或索引错误

- **当前**：空 stdout/非 0/1 返回码 -> FAILED；但若 pip-audit 输出 skipped JSON 且返回 0/1，可能变成 C/D 的 COMPLETED。（混合：前段 CONFIRMED，后段 UNKNOWN）
- **建议**：任何执行/网络/索引错误都不得完整成功；进入 FAILED，记录错误/警告；若工具返回“部分 skipped”，按 C/D 处理，不得 COMPLETED。
- **说明**：本轮未运行真实 pip-audit，具体输出组合为 UNKNOWN。

### 场景 G：JSON 格式错误或解析失败

- **当前**：`ScannerParseError` -> 服务 FAILED，无 Finding。（CONFIRMED 代码）
- **建议**：`audit_complete=False`，FAILED，显示解析错误；不得生成“0 漏洞”。

## 7. 四类候选方案比较

### 方案 1：审计不完整直接 FAILED

设计：

```text
audit_complete = False
-> ScanTaskStatus.FAILED
```

分析：

- **安全性**：高。不会把不能判定为无漏洞的结果展示为成功；符合 fail-closed。
- **用户可理解性**：中等。用户可能把“部分跳过”误认为“工具崩溃”，需要明确 error_message/summary 区分“执行失败”与“审计不完整”。
- **状态模型兼容性**：高。使用现有 FAILED，不需要枚举/Schema 变更。
- **混淆风险**：存在，但可通过文案降低；比假成功风险低。
- **数据保留**：可在保存有效 Finding 后以 FAILED 结束，保留证据，与 SourceAudit 的“失败保留结果”模式一致。
- **标签**：PROPOSED。

### 方案 2：保持 COMPLETED，但标记 audit_complete=False

设计：

```text
TaskStatus = COMPLETED
audit_complete = False
```

分析：

- 当前 `ui/dependency_page.py:708-711` 只在 `COMPLETED + 0 Finding` 时显示“未发现”；如果不改 UI，**仍会误导**。
- 即使增加 `audit_complete`，它没有持久字段（`ScanTask`/DB 无此列）；reload 后只能靠 `result_summary` 解析，可靠性低。
- `COMPLETED` 在现有状态标签中是“已完成”，容易被操作者理解为审计成功。
- 需要额外用户可见字段/摘要/UI 分支；这已经不是“零改动”。
- **结论**：不满足 RC-01 的 fail-closed 目标，不建议作为最小方案。
- **标签**：PROPOSED（分析后不推荐）。

### 方案 3：引入新状态（PARTIAL / INCOMPLETE / COMPLETED_WITH_WARNINGS）

设计：

```text
ScanTaskStatus.PARTIAL
```

分析：

- `core/models/enums.py` 需要新增枚举值。
- `database/schema.py:47-53` 的 `scan_tasks.status` CHECK 需要修改；要迁移/重建表或新增兼容迁移，超出“无 Schema 变更”的最小修复。
- 所有按状态过滤/统计的代码、UI 标签、任务列表、审计日志都需要审查。
- 现有 `ScanTaskStatus` 包含 `blocked`，但它表示授权/阻塞，不是“部分审计”，不能复用。
- 优点：语义最准确，用户能区分执行失败与部分成功。
- 缺点：成本大，超出 RC-01 最小修复；需要独立产品批准和 Schema 版本计划。
- **结论**：作为未来选项保留，不建议本轮实施。
- **标签**：PROPOSED。

### 方案 4：其他合理方案

#### 4a. FAILED + 保留有效 Finding + 明确“不完整”

这是方案 1 的具体实现，推荐作为最小行为。状态仍是 FAILED，但在 `error_message`/`result_summary` 中区分“执行失败”和“审计不完整”。成本最低，不新增 Schema。

#### 4b. 独立 outcome 字段但不进 DB

在 `DependencyAuditOutcome` / `ScanOutput.metadata` 增加 `total/skipped/audit_complete`，任务仍用 FAILED；这些字段只用于 UI/审计日志，不持久化。适用于“需要结构化展示，但暂不迁移数据库”。

#### 4c. COMPLETED + 永久摘要

保持 COMPLETED，在 `result_summary` 永久写“审计不完整：X/Y，跳过 Z”，并修改 UI 禁止显示“未发现”。这避免了 Schema 变更，但状态语义仍可能是“完成”；需要产品明确接受“COMPLETED 不等于完整审计”。不建议作为默认。

## 8. 推荐的最小行为

> **PRODUCT_APPROVED = NO**  
> **RECOMMENDATION_STATUS = PROPOSED**

### 8.1 推荐统计定义

```text
total_dependencies
  = dependencies 数组中的总记录数（含 skipped、invalid）

audited_dependencies
  = 有 name、version、vulns 列表、无 skip_reason 的记录数
    （只有这些记录完成了漏洞查询）

skipped_dependencies
  = 有 skip_reason 的记录数

invalid_dependencies
  = 非 dict、缺 name/version/vulns 且无 skip_reason 的记录数

vulnerabilities_found
  = 去重后的 Finding 数，按 (name.lower(), vulnerability_id)

不变量：
  total_dependencies = audited_dependencies
                     + skipped_dependencies
                     + invalid_dependencies

audit_complete
  = total_dependencies > 0
    and skipped_dependencies == 0
    and invalid_dependencies == 0
    and audited_dependencies == total_dependencies
```

解释：

- `skipped_dependencies` **不计入** `audited_dependencies`。
- `vulnerabilities_found` 是漏洞数，不是依赖数；0 漏洞不等于 0 依赖。
- `audit_complete` 只表示依赖审计完整性，不表示“已发现所有漏洞”的绝对保证。
- 空依赖列表 `audit_complete=False`；不能得出“无漏洞”。

### 8.2 推荐状态映射

| 场景 | 推荐统计 | 推荐任务状态 | 用户可见语义 |
|---|---|---|---|
| A 全部正常，0 漏洞 | total=N, audited=N, skipped=0, vulns=0, complete=True | COMPLETED | “已完成 N/N 依赖审计，未发现漏洞” |
| B 全部正常，有漏洞 | total=N, audited=N, skipped=0, vulns=M, complete=True | COMPLETED | “已完成 N/N 依赖审计，发现 M 个漏洞” |
| C 部分 skipped | total=N, audited=A, skipped=S, invalid=I, complete=False | FAILED（保留 Finding） | “审计不完整：A/N，跳过 S，不能判定无漏洞；已保留 M 结果” |
| D 全部 skipped | total=N, audited=0, skipped=N, invalid=0, complete=False | FAILED | “全部依赖未完成审计，不能判定无漏洞” |
| E 空列表 | total=0, audited=0, skipped=0, complete=False | FAILED | “没有可审计依赖，不能判定无漏洞” |
| F 执行/网络/索引错误 | 统计不可靠；complete=False | FAILED | 工具执行错误/不完整；不得显示“无漏洞” |
| G JSON/解析错误 | 统计不可用；complete=False | FAILED | 解析失败；不得显示“无漏洞” |

### 8.3 为什么不会把“不完整审计”错误表达为“未发现漏洞”

1. C/D 不再进入 COMPLETED；FAILED 状态直接阻止“成功”语义。
2. UI 的“未发现”条件收紧为 `COMPLETED and audit_complete and vulnerabilities_found == 0`。
3. C/D 的摘要显式写“审计不完整”“跳过 N”“不能判定无漏洞”，不再复用“未发现”。
4. 空依赖列表单独失败，不能由“0 Finding”冒充“0 漏洞”。
5. 网络/解析错误不会生成统计为完整的成功任务。

### 8.4 推荐方案的风险与代价

- 部分 skipped 显示为 FAILED，可能被误读为“扫描器坏了”；需明确文案。
- 不使用新状态时，执行失败与不完整审计共享 FAILED；只能靠 error/summary 区分。
- 如果不持久化 `audit_complete`，reload 后只能依赖摘要文本；建议把关键计数写入 `result_summary`，不新增 Schema。
- 现有测试 `audited == 3` 必须修正；现有 UI 测试需要新增不完整分支。
- 不解决未来“部分结果应允许成功”的产品需求；需独立批准 PARTIAL。

## 9. `PRODUCT_APPROVED = NO` 声明

本报告的所有推荐均为 `PROPOSED`：

```text
PRODUCT_APPROVED = NO
RECOMMENDATION_STATUS = PROPOSED
```

- 本报告没有批准任何实现。
- 没有批准新的 `PARTIAL` 状态。
- 没有批准 Schema 变更。
- 没有批准修改代码或测试。
- 没有改变 Stage 1B 的进入条件。
- 任何实施必须等待人工审核和明确批准。

## 10. 未来测试契约

### 10.1 测试契约总表

以下“预期”列是 **PROPOSED_CONTRACT**；“旧代码结果”是 `EXPECTED_OLD_CODE_RESULT`，除非实际运行，否则不得写成运行事实。

| 编号 | 场景 | 输入 | 预期统计（PROPOSED） | 预期状态（PROPOSED） | 用户可见语义（PROPOSED） | CURRENT_BEHAVIOR（当前代码） | EXPECTED_OLD_CODE_RESULT（推断） |
|---|---|---|---|---|---|---|---|
| TC-01 | 全部正常，0 漏洞 | 2 条正常依赖、`vulns=[]` | total=2, audited=2, skipped=0, invalid=0, vulns=0, complete=True | COMPLETED | 已完成 2/2，未发现漏洞 | 同样 COMPLETED，`audited=2` | COMPLETED，正确；INFERRED |
| TC-02 | 全部正常，有漏洞 | 2 条正常，1 条有 1 vuln | total=2, audited=2, skipped=0, invalid=0, vulns=1, complete=True | COMPLETED | 已完成 2/2，发现 1 个漏洞 | COMPLETED，Finding 保存 | COMPLETED，正确；INFERRED |
| TC-03 | 部分 skipped | 3 条：2 正常（1 Finding），1 skip | total=3, audited=2, skipped=1, invalid=0, vulns=1, complete=False | FAILED（保留 Finding） | 审计不完整：2/3，跳过 1；不能判定无漏洞；已保留 1 个结果 | COMPLETED；`audited=3`；warning 临时；摘要可能“发现 1” | COMPLETED，错误；INFERRED |
| TC-04 | 全部 skipped | 2 条均为 `skip_reason` | total=2, audited=0, skipped=2, invalid=0, vulns=0, complete=False | FAILED | 全部依赖未完成审计，不能判定无漏洞 | COMPLETED；`audited=2`；摘要“未发现”；UI“无漏洞” | COMPLETED，假成功；INFERRED |
| TC-05 | 空依赖列表 | `dependencies=[]` | total=0, audited=0, skipped=0, invalid=0, vulns=0, complete=False | FAILED | 没有可审计依赖，不能判定无漏洞 | `audited=0` -> FAILED | FAILED，正确；CONFIRMED 静态 |
| TC-06 | 执行/网络/索引错误 | 空 stdout、非 0/1 返回码；或 skipped JSON | 无可信统计；complete=False | FAILED | 工具执行错误/不完整；不得显示“无漏洞” | 空 stdout/非法返回 -> FAILED；skipped JSON -> 可能 C/D | FAILED 或 FALSE_SUCCESS_IF_SKIPPED_JSON；UNKNOWN 精确组合 |
| TC-07 | JSON/解析错误 | `not-json` 或非 dict/缺 `dependencies` | 统计不可用；complete=False | FAILED | 解析失败；不得显示“无漏洞” | `ScannerParseError` -> FAILED | FAILED，正确；CONFIRMED 静态 |

### 10.2 测试设计原则

- **CURRENT_BEHAVIOR** 是当前代码事实；**PROPOSED_CONTRACT** 是待批准规则；二者不得混在同一个断言里。
- 旧代码测试可以保留为历史证据/回归基线，但不得把旧的 `audited == 3` 当作正确契约。
- 修正旧测试时，必须把期望改为“skipped 不计入 audited”，不得降低“正常依赖仍被审计”的断言。
- 新增测试必须同时断言：
  - 任务状态；
  - `audit_complete`（或等价 summary 标记）；
  - 用户可见文案；
  - 有效 Finding 是否保留；
  - 项目隔离和任务 ID 归属（服务层）。
- 不得只断言 `status == COMPLETED` 而不检查“未发现”文案。

### 10.3 必须新增/调整的测试

1. 修正 `tests/test_pip_audit_scanner.py:71-78`：`audited == 2`、`skipped == 1`。
2. 新增全部 skipped parser 与 service 测试。
3. 新增部分 skipped + 正常 Finding service 测试（验证 fail-closed 且 Finding 保留）。
4. 新增空依赖列表与“0 Finding 不等于成功”测试。
5. 新增网络/索引/解析错误测试。
6. 新增 UI 不完整文案测试，确保不出现“当前任务未发现已知依赖漏洞”。
7. 保留现有正常 0 漏洞和正常漏洞测试，不降低断言。

## 11. 预计旧代码表现

> 以下均为 **EXPECTED_OLD_CODE_RESULT**，是代码分析预测；除已标注的历史测试事实外，不是本轮实际运行结果。

| 测试 | 旧代码预计结果 | 依据 |
|---|---|---|
| TC-01 | COMPLETED，`audited=2`，0 Finding | `audited>0`，0 Finding；INFERRED |
| TC-02 | COMPLETED，Finding 保存 | 正常映射；INFERRED |
| TC-03 | COMPLETED，`audited=3`，1 Finding；warning 可能显示一次 | `len(dependencies)`；INFERRED |
| TC-04 | COMPLETED，`audited=2`，0 Finding，摘要“未发现”，UI“无漏洞” | `len(dependencies)` + 0 失败门禁；INFERRED |
| TC-05 | FAILED | `audited=0` 门禁；CONFIRMED 静态 |
| TC-06 | 空 stdout/非法返回 -> FAILED；skipped JSON -> 可能假成功 | 混合；UNKNOWN |
| TC-07 | FAILED | `ScannerParseError`；CONFIRMED 静态 |

**现有测试固定错误行为**：`tests/test_pip_audit_scanner.py:71-78` 的 `assert audited == 3` 是 CONFIRMED。该测试当前通过并不能证明语义正确。

## 12. 最小候选修改范围

### A. 必须修改（仅在 Stage 1B 获批后）

| 文件 | 原因 | 说明 |
|---|---|---|
| `scanners/pip_audit_scanner.py` | 当前计数错误 | 分离 total/audited/skipped/invalid；`ScanOutput.metadata` 写入计数和 `audit_complete` |
| `services/dependency_audit_service.py` | 当前只有 `audited==0` 门禁 | 读取 skipped/invalid；C/D/E/F/G fail-closed；保留有效 Finding；把计数写入 `result_summary` |
| `tests/test_pip_audit_scanner.py` | 旧断言固定错误 | 将 skipped 从 audited 中移除；新增场景 |
| `tests/test_dependency_audit_service.py` | 缺少 all-skip/partial | 新增状态与摘要断言 |
| `tests/test_ui_dependency_audit.py` | 缺少“不完整”文案 | 验证不显示“无漏洞” |

### B. 可能需要修改（按触发条件）

| 文件/范围 | 触发条件 | 说明 |
|---|---|---|
| `ui/dependency_page.py` | 如果不完整状态/新摘要需要 UI 分支 | 仅改文案/状态显示，不写文件、不改 SQL |
| `DependencyAuditOutcome`（服务内定义） | 需要向 UI 传递计数 | 仅内存 DTO；不新增 DB 字段 |
| `ScanOutput` / `ScanTask` 模型 | 只有批准持久化 `audit_complete` 时 | 否则用 metadata/summary，不改模型 |
| `core/models/enums.py` + `database/schema.py` | **仅当批准 PARTIAL 新状态** | 超出 RC-01 最小修复；需要 Schema 迁移，不能顺手做 |

### C. 明确不应修改

- 数据库 Schema、迁移、`scan_tasks` CHECK、任何表字段。
- 无关 Scanner（Bandit/Semgrep）和无关漏洞管理/证据中心逻辑。
- JSON 报告、PDF、Report Center、HTML exporter、报告模板。
- Manifest、历史归档、README、备份、旧验收数据库。
- 现有 Finding 字段/风险等级/状态历史。
- 真实扫描数据或历史验收结果。

## 13. 明确禁止修改的范围

本轮及 Stage 1B-1 不修改：

```text
database/             （含 schema.py 与迁移）
core/models/          （模型不改；本报告只读）
scanners/             （含 pip_audit_scanner.py）
services/             （含 dependency_audit_service.py）
ui/                   （含 dependency_page.py）
tests/                （含三个相关测试文件）
reports/              （JSON/PDF/HTML）
README.md
docs/                 （除本报告外）
Manifest / 历史归档 / 备份 / 数据库
```

此外不执行：

- `git add`
- `git commit`
- `git push`
- `git reset`
- `git restore`
- `git clean`
- `git add .` / `git add -A`

## 14. Git 状态

调查时只读记录：

```text
BRANCH = main
HEAD = bffb5ac82bbebe7fef5992f87ff90494c9776ace
COMMIT_COUNT = 8
STAGED = 0
UNSTAGED = M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
AHEAD = 5
BEHIND = 0
```

已有未跟踪报告：

- `docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`
- `docs/PHASE6_D1B_3_JSON_DECISION.md`
- `docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md`
- `docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md`
- `docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md`
- `docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md`
- `docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md`
- `docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md`

本报告新增后预计变为 9 个未跟踪报告；未修改已有 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`。**本任务未执行任何 Git 写操作。**

## 15. 文件变化

本次仅新增：

```text
docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md
```

- 生产代码：NO
- 测试：NO
- README/其他文档：NO
- 数据库/Schema：NO
- Manifest/历史归档/备份：NO
- 本次没有修改 Stage 1A 报告或任何已有未跟踪报告。

## 16. 数据库状态

- 本任务没有打开、查询或写入数据库。
- 没有执行迁移。
- 没有修改 `scan_tasks`、`findings`、`reports` 或历史验收库。
- 当前 Schema 保持 v5。
- 未来最小修复**不需要**新字段；如果决定持久化 `audit_complete`/skipped 计数，必须先单独设计 Schema 迁移，不得在本任务或 RC-01 最小修复中顺手完成。

## 17. 未确认事项

| 事项 | 状态 | 说明 |
|---|---|---|
| 真实 all-skipped 运行后的数据库任务行 | INFERRED | 代码路径确定，但未运行真实 pip-audit |
| 网络/索引错误时 pip-audit 的精确输出组合 | UNKNOWN | 本轮禁止运行真实 pip-audit |
| 部分 skipped 的最终 UI 呈现 | INFERRED | 代码路径可推导，未启动 GUI |
| 当前完整 pytest 是否通过 | UNKNOWN | 本轮禁止运行测试 |
| 现有数据库当前行数 | UNKNOWN | 本轮未打开数据库 |
| 产品是否接受“不完整 = FAILED” | UNKNOWN | 需要人工产品决策 |
| 是否未来批准 PARTIAL 状态 | UNKNOWN | 不在本任务范围 |
| 历史真实验收数据是否可重复 | HISTORICAL_ONLY | 不能作为当前运行结果 |

## 18. 最终状态

```text
STAGE1B1_STATUS = DESIGN_COMPLETE
PRODUCT_APPROVAL = PENDING
RECOMMENDATION_STATUS = PROPOSED
PRODUCT_APPROVED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
TESTS_RUN = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

推荐行为摘要（**PROPOSED，未批准**）：

- A/B：审计完整，COMPLETED；A 显示 0 漏洞，B 显示发现漏洞。
- C：部分 skipped，`audit_complete=False`，建议 FAILED，保留有效 Finding。
- D：全部 skipped，FAILED，禁止显示“未发现漏洞”。
- E：空依赖列表，FAILED，禁止显示“0 漏洞”。
- F：执行/网络/索引错误，FAILED；若工具返回部分 skipped，按 C/D 处理。
- G：JSON/解析错误，FAILED，无结果。

不新增 Schema 字段、不新增状态、不修改代码。等待人工审核后再决定是否进入 Stage 1B-2；不得自行进入 Stage 1B-2 或 Stage 1C。
