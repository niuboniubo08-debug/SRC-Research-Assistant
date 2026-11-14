# Phase 6 Stage 1B-5A-CORRECTION — RC-01 调查报告修正

## 0. 修正结论

本文件是对以下原调查报告的独立修正记录，不重写原报告：

```text
docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

原报告 SHA-256：

```text
57246C2B1CF9C45F5DEC571DDC388C864D6167A5168BEC26F11C0EAF00A29C8D
```

本次只新增本修正记录，不修改原报告、生产代码、测试代码、数据库、Schema、README、Manifest 或历史归档。

```text
STAGE1B5A_CORRECTION_STATUS = COMPLETED
ORIGINAL_REPORT_STATUS = UNCHANGED
FINDING_PARSE_CHANGE = REMOVED_FROM_RC01_MINIMAL_SCOPE
STATISTICS_VALIDATION = SPLIT_INTO_LEGALITY_AND_COMPLETENESS
SKIP_REASON_TYPE_RULE = DEFINED
FIX_IMPLEMENTED = NO
```

本修正记录优先于原报告中关于以下三点的设计表述：

1. `skip_reason` 存在时是否 `continue` 并阻止 Finding 解析；
2. 统计合法性校验与审计完整性判断的边界；
3. `skip_reason` 的类型规则。

## 1. 原调查报告的问题

### 1.1 问题一：建议的 `continue` 可能改变 Finding 解析行为

原报告的最小方案曾建议：

```python
if skip_reason:
    skipped += 1
    warnings.append(...)
    continue
```

这个建议会让带有效 `skip_reason` 的记录直接跳过后续 `vulns` 循环。问题在于：

- 当前生产代码在 `skip_reason` 存在时**没有** `continue`。
- 当前生产代码仍会继续检查 `vulns`，并且如果 `vulns` 列表中存在有效对象，会继续生成 Finding。
- 因此，`continue` 会改变既有 Finding 解析行为，超出了 RC-01 的统计真实性修复范围。

修正原则：

```text
不得仅凭 skip_reason 的存在，擅自改变原有 Finding 解析行为。
RC-01 只修复“不完整审计被错误标记为成功”，不改变 Finding 生成、保留、删除或持久化策略。
```

### 1.2 问题二：原报告没有明确拆分统计合法性与审计完整性

原报告把“字段是否合法”和“审计是否完整”都归入 fail-closed，但没有清晰区分：

- 统计字段非法或互相矛盾；
- 统计字段合法，但审计本身不完整（存在 skipped）；
- 统计合法且完整，才允许成功。

两者都必须 FAILED，但失败原因和校验顺序不同，需要在实现中分开。

### 1.3 问题三：原报告对 `skip_reason` 的类型规则不够明确

当前代码：

```python
skip_reason = str(dependency.get("skip_reason") or "").strip()
```

这行代码会把非字符串值也转换为字符串，例如：

```text
None              -> ""
""                -> ""
"   "             -> ""
"reason"          -> "reason"
123               -> "123"
True              -> "True"
["reason"]        -> "['reason']"
```

因此，如果统计逻辑直接使用转换后的字符串，会把数字、布尔值、列表等异常输入误当成有效跳过原因。原报告没有定义这种情况。

## 2. 修正一：明确 Finding 解析行为边界

### 2.1 当前代码的实际行为

`scanners/pip_audit_scanner.py:224-235`：

```python
for dependency in dependencies:
    if not isinstance(dependency, dict):
        continue
    name = str(dependency.get("name") or "").strip()
    current_version = str(dependency.get("version") or "").strip()
    skip_reason = str(dependency.get("skip_reason") or "").strip()
    if skip_reason:
        warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
    vulns = dependency.get("vulns")
    if not isinstance(vulns, list):
        continue
    for vuln in vulns:
        ...
        findings.append(Finding(...))
```

**CONFIRMED（静态代码路径）**：

- `skip_reason` 非空时只追加 warning。
- 没有 `continue`。
- 随后仍读取 `vulns`。
- 如果 `vulns` 是 list 且包含有效 vuln 对象，仍会构建并追加 Finding。
- 也就是说，**静态代码允许“skip_reason + 非空 vulns”同时产生 warning 和 Finding**。

### 2.2 真实输出证据

**UNKNOWN**：

- 当前没有真实 pip-audit 运行时输出证明它会在一条记录中同时输出非空 `skip_reason` 和非空 `vulns`。
- 当前项目测试 fixture `tests/test_pip_audit_scanner.py:53-61` 的 `skipped-package` 只有：

```json
{
  "name": "skipped-package",
  "version": "0.1",
  "vulns": [],
  "skip_reason": "failed to resolve"
}
```

- 该 fixture 证明“skip + 空 vulns”可被测试，不证明“skip + 非空 vulns”在真实输出中存在。
- Stage 1A 只做了只读代码/报告调查，没有运行真实 pip-audit 并捕获该组合。

结论：

```text
SKIP_WITH_VULNS_STATIC_CODE_PATH = CONFIRMED
SKIP_WITH_VULNS_REAL_OUTPUT = UNKNOWN
```

不得声称该组合一定存在，也不得声称它一定不存在。

### 2.3 修正后的处理

RC-01 最小修复**不改变** Finding 解析循环的控制流：

- 不新增 `continue` 来阻止 `vulns` 解析。
- 有效 `skip_reason` 的记录仍然照常进入原有 `vulns` 循环。
- 如果原代码会生成 Finding，修复后仍可能生成 Finding；是否保留该 Finding 由既有 Service 流程处理，本修正不新增保留/删除要求。
- 统计上该记录计入 `skipped`，因此即使产生了 Finding，Service 仍因审计不完整返回 FAILED。
- 如果真实输出不会产生这种组合，则该分支在运行时不会触发；这是防御性保留，不是新增业务行为。

### 2.4 不属于 RC-01 的行为

以下均不属于本轮最小修复范围：

```text
Finding 的保留、删除、覆盖或持久化策略
skip_reason 记录的 Finding 是否应被 UI 展示
skip_reason 记录的 Finding 是否应进入漏洞中心
skip_reason 记录的 Finding 去重规则
```

## 3. 修正二：统计合法性与审计完整性分离

实现必须分为两个阶段，顺序不可颠倒。

### 3.1 阶段 A：统计合法性校验

服务必须从 `ScanOutput.metadata` 读取三个字段，并使用严格类型判断：

```text
type(audited_dependencies) is int
type(skipped_dependencies) is int
type(total_dependencies) is int
```

必须拒绝：

- `bool`（`type(True) is bool`，不是 `int`）；
- 字符串、浮点、None、列表、字典等其他类型；
- 负整数；
- 缺失键。

基础约束：

```text
audited_dependencies >= 0
skipped_dependencies >= 0
total_dependencies > 0
audited_dependencies + skipped_dependencies == total_dependencies
```

任一条件不满足：

```text
STATUS = FAILED
```

错误摘要至少应明确“依赖统计无效/缺失”，不得生成成功摘要。

### 3.2 阶段 B：审计完整性判断

只有阶段 A 通过后，才执行：

```text
audit_complete = (
    skipped_dependencies == 0
    and audited_dependencies == total_dependencies
)
```

- `audit_complete` 必须由 Service 派生，**不得写入 metadata**。
- 如果统计合法但 `audit_complete == False`：

```text
STATUS = FAILED
```

- 不能因为 `audited_dependencies > 0` 就进入成功路径。
- 不能因为 `skipped_dependencies > 0` 但仍有 Finding，就进入 COMPLETED。
- `audit_complete == True` 只决定是否允许成功状态和成功摘要，不规定 `_map_findings()` / `_save_findings()` 的调用顺序。
- 统计合法性、审计完整性与 Finding 解析/映射/持久化是不同问题；不得为满足本契约而改变现有 Finding 流程。

### 3.3 三个结果的唯一映射

| 条件 | 任务状态 | 成功摘要 |
|---|---|---|
| 统计非法（类型/负数/缺失/矛盾/`total<=0`） | `FAILED` | 禁止 |
| 统计合法但审计不完整（`skipped>0` 或 `audited<total`） | `FAILED` | 禁止 |
| 统计合法且 `skipped==0` 且 `audited==total` | 允许 `COMPLETED` | 允许 |

上表只约束最终任务状态和成功摘要，不规定 Finding 映射或保存的先后顺序。统计校验结果必须能阻止错误成功，但不得为了满足 FAILED 状态而改变既有 Finding 流程。

### 3.4 当前实现为什么不满足

当前 `services/dependency_audit_service.py:325-338`：

```python
audited = int(output.metadata.get("audited_dependencies") or 0)
if audited == 0:
    ... FAILED ...
```

问题：

- `int()` 会把 bool、字符串、`None` 转换为整数；
- 不读取 `skipped_dependencies`；
- 不读取 `total_dependencies`；
- 不做严格类型判断；
- 不做 sum 校验；
- 只检查 `audited == 0`；
- `audited=1, skipped=1, total=2` 仍进入 COMPLETED；
- `audited=1, skipped=0, total=True` 仍进入 COMPLETED；
- `audited=1, skipped=True, total=2` 仍进入 COMPLETED。

这与 B4C 实测结果一致：

```text
8 collected / 1 passed / 7 failed
audited-none 通过是旧 audited==0 分支的假阳性
```

## 4. 修正三：`skip_reason` 类型规则

### 4.1 当前代码的类型问题

当前代码先做：

```python
skip_reason = str(dependency.get("skip_reason") or "").strip()
```

这会丢失原始类型，导致：

```text
None          -> ""        （不构成跳过）
""            -> ""        （不构成跳过）
"   "         -> ""        （不构成跳过）
"reason"      -> "reason"  （有效跳过）
123           -> "123"     （异常输入被字符串化）
True          -> "True"    （异常输入被字符串化）
["x"]         -> "['x']"   （异常输入被字符串化）
```

### 4.2 修正后的严格规则

在统计层必须基于**原始值**判断，而不是转换后的字符串：

```text
raw_skip = dependency.get("skip_reason")

有效 skip_reason:
    isinstance(raw_skip, str) and bool(raw_skip.strip())

无效但非异常:
    raw_skip is None
    raw_skip == ""
    raw_skip.strip() == ""

异常输入:
    raw_skip 是非字符串类型（bool、int、list、dict 等）
```

对应处理：

| 原始 `skip_reason` | 是否计入 skipped | 是否作为正常审计记录 | 最终结果 |
|---|---|---|---|
| 非空字符串 | 是 | 不计入 audited | 审计不完整 -> FAILED |
| `None` | 否 | 可进入正常记录判断 | 若完整则允许成功 |
| 空字符串 | 否 | 可进入正常记录判断 | 若完整则允许成功 |
| 仅空白字符串 | 否 | 可进入正常记录判断 | 若完整则允许成功 |
| 非字符串 | **否** | **不计入 audited** | 统计缺口 -> 阶段 A 失败 |
| 缺失 | 否 | 可进入正常记录判断 | 若完整则允许成功 |

### 4.3 不增加 `invalid_dependencies`

不得新增第四个统计字段：

```text
invalid_dependencies = NOT_ALLOWED
```

异常记录只通过以下方式 fail-closed：

- 计入 `total_dependencies`；
- 不计入 `audited_dependencies`；
- 不计入 `skipped_dependencies`；
- 导致 `audited + skipped != total`，阶段 A 失败。

因此，不需要暴露 `invalid_dependencies`，也不需要改 metadata 结构。

### 4.4 Finding 解析保持

对于非字符串 `skip_reason`：

- 不以“有效 skip”处理；
- 不新增 `continue` 来改变 Finding 解析；
- 仍按原有 `vulns` 逻辑处理；
- 统计上不计 audited/skipped，最终 Service FAILED；
- 该记录的 Finding 是否保留不属于 RC-01 契约。

## 5. 修正前后设计差异

| 项目 | 原报告/原建议 | 本修正 |
|---|---|---|
| `skip_reason` + `vulns` | 建议 `continue`，不生成 Finding | **不改变** Finding 解析；仍按原循环处理 |
| 统计校验 | 混合在 fail-closed 中 | 拆成阶段 A 合法性 + 阶段 B 完整性 |
| `bool` 处理 | 强调拒绝，但未按原始值 | 严格 `type(x) is int`，拒绝 bool |
| `skip_reason` 类型 | 未明确 | 原始值必须是字符串；空白/None 无效；非字符串异常 |
| 非字符串 `skip_reason` | 未定义 | 不计 skipped/audited，total 不变，sum 失败 |
| 第四字段 | 明确不加入 | 仍不加入 `invalid_dependencies` |
| `audit_complete` | 由 Service 派生 | 保持 Service 派生，不写入 metadata |
| Finding 持久化 | 明确不属于 | 仍不属于 |
| 生产修复文件 | 2 个 | 仍为 2 个 |
| Schema 修改 | 不需要 | 不需要 |
| 新任务状态 | 未批准 | 不新增 |

## 6. 当前已确认事实与 UNKNOWN

### CONFIRMED

```text
当前 scanner 的 audited 返回 len(dependencies)
当前 scanner 对 skip_reason 只追加 warning，不 continue
当前 scanner 使用 str() 转换 skip_reason，丢失原始类型
当前 Service 使用 int() 并只检查 audited == 0
当前 Service 不读取 skipped/total
当前 COMPLETED/no findings 会显示“未发现已知漏洞”
当前 B4A 定向测试 41/26/15，B4C 8/1/7
当前 parser 测试解包 3 元返回
当前最小生产修复文件为 2 个
当前不需要 Schema/模型/状态变更
```

### UNKNOWN

```text
真实 pip-audit 是否输出 skip_reason + 非空 vulns 组合
真实 skipped 记录是否总是缺少 version/vulns
真实非 dict / 缺字段记录出现频率
非字符串 skip_reason 的真实出现方式
重复依赖名的真实计数语义
```

以上 UNKNOWN 不改变修正后的统计规则；实现时必须 fail-closed，不得假设真实输出一定完整。

## 7. 修正后的最小生产修复范围

### 7.1 Scanner

文件：`scanners/pip_audit_scanner.py`

修改点：

```text
parse_output()  :210-311
scan()          :194-207
```

要求：

1. 读取原始 `raw_skip = dependency.get("skip_reason")`。
2. `total_dependencies = len(dependencies)`。
3. 非 dict：计入 total，不计 audited/skipped。
4. 有效 skip：`isinstance(raw_skip, str) and raw_skip.strip()`；计入 skipped，追加 warning。
5. 有效 skip 也**不 continue**；沿用原 `vulns` 循环，不改变 Finding 解析。
6. None/空字符串/空白字符串：不构成 skip；按正常记录判断。
7. 非字符串 skip_reason：不计 skipped；也不计 audited；total 已计入；最终 sum 不一致，Service 阶段 A 失败。
8. 正常记录需 `name`、`version` 非空且 `vulns` 是 list 才计 audited。
9. `parse_output` 返回 5 元：

```text
findings, warnings, audited, skipped, total
```

10. `scan()` 解包 5 元，metadata 增加：

```text
skipped_dependencies
total_dependencies
```

11. 不新增 `invalid_dependencies`。

### 7.2 Service

文件：`services/dependency_audit_service.py`

修改点：

```text
:325 之前插入统计读取和阶段 A 校验
:325-338 替换为严格校验后的分发
:339-373 统计结果必须能决定最终 status/summary；本契约不规定 map/save 的先后顺序
```

要求：

1. 严格类型：

```python
type(v) is int
```

2. 阶段 A：非负、total>0、sum 相等。
3. 阶段 B：`skipped == 0 and audited == total`。
4. 阶段 A/B 任一失败，最终任务状态必须为 FAILED，且不得产生成功无漏洞摘要。
5. 不规定统计校验与 `_map_findings()` / `_save_findings()` 的先后顺序；不得为了满足 FAILED 状态改变现有 Finding 解析、映射、保存、删除、保留或覆盖行为。
6. 不将 `audit_complete` 写入 metadata。
7. 保留现有 `audited == 0` 的“未审计到任何依赖”错误文本，或统一到统计错误文本；不得生成成功摘要。
8. 不改变 Finding 持久化要求。
9. 如果当前调用链无法在不改变 Finding 行为的情况下实现统计契约，记录冲突并停止，等待人工决策。

### 7.3 UI

生产 UI 不需要修改。

`ui/dependency_page.py:708-711` 只在 `COMPLETED` 且无 findings 时显示“未发现”。修复后的不完整审计为 `FAILED`，不会触发。

### 7.4 测试

已存在的测试文件：

```text
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

需要同步：

- 两处 `parse_output()` 3 元解包改为 5 元；
- Scanner 测试保留 skip + 空 vulns 的现状；
- 不新增“skip + 非空 vulns 必须无 Finding”的断言，因为该行为不属于 RC-01，且真实输出是 UNKNOWN；
- Service 测试继续覆盖合法/非法/不完整；
- 新增 `total-negative`、`skipped-string`、`total-string/float` 等边界（建议，非本任务执行）。

## 8. 不属于 RC-01 的行为

```text
Finding 保留/删除/覆盖/持久化策略
skip_reason 记录的 Finding 是否必须展示
Finding 去重策略的变更
新增 PARTIAL 状态
新增 invalid_dependencies 字段
修改 ScanOutput 公共结构
修改数据库 Schema
修改 UI 生产代码
修改 HTML/PDF/JSON 报告
```

## 9. 执行前后 Git 状态

### 执行前

```text
branch: main
HEAD: bffb5ac82bbebe7fef5992f87ff90494c9776ace
staged: 0
```

工作区：

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
?? docs/PHASE6_STAGE1B4C_RC01_SERVICE_PARAMETRIZED_TEST.md
?? docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

### 执行后

新增：

```text
?? docs/PHASE6_STAGE1B5A_CORRECTION.md
```

其余状态不变；staged 仍为 0。

## 10. 文件 SHA-256

| 文件 | 状态 | SHA-256 |
|---|---|---|
| `docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md` | 原报告，未改 | `57246C2B1CF9C45F5DEC571DDC388C864D6167A5168BEC26F11C0EAF00A29C8D` |
| `docs/PHASE6_STAGE1B5A_CORRECTION.md` | 本修正记录最终文件 | 见 `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` 第 6 节；该节记录的是本文件最终字节的只读 SHA-256 |

### 10.1 自引用哈希限制

本文件不能在自身内容中嵌入自己的最终 SHA-256：任何写入都会改变文件字节，因此不存在可自洽的嵌入方式。本文件不填占位符或推测值；最终文件的实际 SHA-256 由 `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` 的只读校验记录。R1 报告自身也受同一限制，其最终 SHA-256 在本次任务最终响应中记录。

## 11. 边界遵守情况

```text
READ_ONLY = YES
ORIGINAL_REPORT_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
README_MODIFIED = NO
MANIFEST_MODIFIED = NO
OTHER_REPORTS_MODIFIED = NO
GIT_ADD_COMMIT_PUSH = NO
GIT_RESET_RESTORE_CLEAN = NO
PYTEST_RUN = NO
REAL_PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DEPENDENCY_INSTALL = NO
```

本修正记录只覆盖原报告中的相关设计结论；原报告保持原样，等待人工审核。
