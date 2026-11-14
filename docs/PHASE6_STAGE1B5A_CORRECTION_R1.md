# Phase 6 Stage 1B-5A-CORRECTION-R1 — RC-01 修正记录二次修订

## 0. 执行结论

本任务只修改：

```text
docs/PHASE6_STAGE1B5A_CORRECTION.md
```

并新增本记录：

```text
docs/PHASE6_STAGE1B5A_CORRECTION_R1.md
```

没有修改原始调查报告、生产代码、测试代码、数据库、Schema、README、Manifest 或其他历史归档。

```text
STAGE1B5A_CORRECTION_R1_STATUS = COMPLETED
CORRECTION_FILE_MODIFIED = YES
ORIGINAL_REPORT_MODIFIED = NO
FINDING_ORDER_CONSTRAINT = REMOVED
CORE_STATISTICS_CONTRACT = RETAINED
FIX_IMPLEMENTED = NO
```

## 1. 原修正记录中的契约冲突

原修正记录以下两处把“统计完整性与 Finding 映射/保存”绑定在一起：

### 冲突文字 A

```text
只有 audit_complete == True，才允许进入
_map_findings() / _save_findings() / 成功摘要路径。
```

问题：

- RC-01 只要求不完整审计最终不能被标记为成功，且不能产生“未发现漏洞”摘要。
- 它没有授权把 `_map_findings()` / `_save_findings()` 设为成功状态的前置条件。
- 把 Finding 映射和持久化顺序绑定到 `audit_complete`，扩大了契约范围。

### 冲突文字 B

```text
阶段 A/B 任一失败，在 _map_findings() / _save_findings() 之前返回 FAILED。
```

问题：

- 这也是对 Finding 流程的强制顺序要求。
- 统计合法性、审计完整性和 Finding 映射/持久化是不同问题。
- 不允许为了满足 FAILED 状态擅自改变现有 Finding 流程。

## 2. 修改前后关键文字

### 2.1 第 3.2 节

**修改前：**

```text
只有 audit_complete == True，才允许进入
_map_findings() / _save_findings() / 成功摘要路径。
```

**修改后：**

```text
audit_complete == True 只决定是否允许成功状态和成功摘要，
不规定 _map_findings() / _save_findings() 的调用顺序。

统计合法性、审计完整性与 Finding 解析/映射/持久化是不同问题；
不得为满足本契约而改变现有 Finding 流程。
```

### 2.2 第 3.3 节

新增：

```text
上表只约束最终任务状态和成功摘要，不规定 Finding 映射或保存的先后顺序。
统计校验结果必须能阻止错误成功，但不得为了满足 FAILED 状态而改变既有
Finding 流程。
```

### 2.3 第 7.2 节

**修改前：**

```text
:339-373 仅在 audit_complete 后执行 map/save/COMPLETED

4. 阶段 A/B 任一失败，在 _map_findings() / _save_findings()
   之前返回 FAILED。
```

**修改后：**

```text
:339-373 统计结果必须能决定最终 status/summary；
本契约不规定 map/save 的先后顺序。

4. 阶段 A/B 任一失败，最终任务状态必须为 FAILED，且不得产生
   成功无漏洞摘要。

5. 不规定统计校验与 _map_findings() / _save_findings() 的先后顺序；
   不得为了满足 FAILED 状态改变现有 Finding 解析、映射、保存、删除、
   保留或覆盖行为。
```

## 3. Finding 流程边界修正结果

修正后的边界：

- 统计非法：最终任务状态 FAILED。
- 统计合法但审计不完整：最终任务状态 FAILED。
- 统计合法且完整：允许进入正常成功路径。
- 上述三条只约束最终任务状态和成功摘要。
- 不规定 `_map_findings()` / `_save_findings()` 的调用时机。
- 不新增 Finding 解析、映射、保存、删除、保留或覆盖要求。
- 不为了满足 FAILED 状态改变现有 Finding 流程。
- 如果当前调用链无法在不改变 Finding 行为的情况下实现统计契约，必须记录冲突并停止，等待人工决策。

本次没有运行代码，也没有验证当前调用链能否无冲突实现；这是实现阶段必须复核的事项。

## 4. 核心统计契约保持情况

以下内容未改变：

```text
INCOMPLETE_AUDIT_POLICY = FAILED
FALSE_NO_VULNERABILITY_CLAIM = PROHIBITED
NEW_TASK_STATUS = NOT_APPROVED
SCHEMA_MIGRATION = NOT_REQUIRED
FINDING_PERSISTENCE_POLICY = OUT_OF_CURRENT_RC01_CONTRACT
```

统计合法性：

```text
type(audited_dependencies) is int
type(skipped_dependencies) is int
type(total_dependencies) is int

audited_dependencies >= 0
skipped_dependencies >= 0
total_dependencies > 0
audited_dependencies + skipped_dependencies == total_dependencies
```

拒绝 bool、字符串、浮点、None、缺失、负数、统计矛盾和 `total <= 0`。

审计完整性：

```text
audit_complete = (
    skipped_dependencies == 0
    and audited_dependencies == total_dependencies
)
```

`audit_complete` 仍由 Service 派生，不写入 metadata。

## 5. 原报告是否保持不变

原调查报告：

```text
docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

- 未修改。
- SHA-256 仍为：

```text
57246C2B1CF9C45F5DEC571DDC388C864D6167A5168BEC26F11C0EAF00A29C8D
```

本任务只修改独立修正记录，并新增本 R1 记录。

## 6. 被修正文件最终 SHA-256

被修改文件：

```text
docs/PHASE6_STAGE1B5A_CORRECTION.md
```

最终只读校验结果：

```text
BYTES = 19049
H2_SECTIONS = 12
SHA256 = C02E7D226B28D3062DD9DCB5E468BA687098E9599793FF90E0F823C3DEB9A1D9
```

该值对应完成 R1 修改后、本 R1 文件写入前的最终修正记录字节；后续未再修改该文件。

## 7. R1 报告自身 SHA-256

R1 报告不能在自身内容中嵌入自己的最终 SHA-256：写入哈希字段会改变文件字节，导致记录的哈希不再对应最终文件。这是自引用哈希的固有限制，不是缺少校验。

因此：

```text
R1_REPORT_SELF_SHA256 = EXTERNAL_ONLY
R1_REPORT_SELF_SHA256_REASON = 自引用哈希无法在文件内部自洽
```

本 R1 文件的最终 SHA-256 在本次任务最终响应中记录；报告内容不填写推测值或伪哈希。

## 8. 执行前后 Git 状态

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
?? docs/PHASE6_STAGE1B5A_CORRECTION.md
?? docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

### 执行后

新增：

```text
?? docs/PHASE6_STAGE1B5A_CORRECTION_R1.md
```

其余文件状态不变。`staged` 仍为 0。

## 9. 所有实际文件变化

| 文件 | 变化 | 说明 |
|---|---|---|
| `docs/PHASE6_STAGE1B5A_CORRECTION.md` | 修改 | 删除 Finding 映射/持久化的强制顺序约束，加入自引用哈希限制说明 |
| `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` | 新增 | 本记录 |

没有其他文件变化。

## 10. 边界遵守情况

```text
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

本任务不开始 Stage 1B-5B。等待人工审核。
