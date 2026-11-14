# Phase 6 Stage 1B-5A — RC-01 生产代码最小修复范围调查

## 0. 调查结论

RC-01 的生产修复范围已经可以确定，且不需要修改数据库 Schema、`ScanTaskStatus`、公共 DTO 或其他扫描器。

核心结论：

```text
STAGE1B5A_STATUS = COMPLETED
RC01_CURRENT_STATUS = CONFIRMED_DEFECT
RC01_FIX_SCOPE = CONFIRMED
PRODUCTION_FILES_TO_CHANGE = 2
TEST_FILES_TO_CHANGE = 3
NEW_MODEL_REQUIRED = NO
NEW_PUBLIC_INTERFACE_REQUIRED = NO
SCHEMA_CHANGE_REQUIRED = NO
NEW_TASK_STATUS_REQUIRED = NO
FIX_IMPLEMENTED = NO
```

需要修改的生产文件只有：

```text
scanners/pip_audit_scanner.py
services/dependency_audit_service.py
```

需要同步调整的测试文件预计为：

```text
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

当前测试文件已经在工作区中修改，但生产代码尚未修复；本报告不修改任何文件。

## 1. 调查范围、方法与事实等级

本次只读取：

```text
scanners/pip_audit_scanner.py
services/dependency_audit_service.py
scanners/base.py
core/models/scan_task.py
core/models/enums.py
ui/dependency_page.py
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md
docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md
docs/PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md
docs/PHASE6_STAGE1B4C_RC01_SERVICE_PARAMETRIZED_TEST.md
```

事实等级：

- **CONFIRMED**：由当前源码、当前测试断言或已执行测试直接证明。
- **INFERRED**：由调用链推导，但本次未运行对应场景。
- **UNKNOWN**：没有当前运行样本或无法从现有代码确定。

本次没有运行 pytest、真实 pip-audit、GUI 或数据库迁移。

## 2. Scanner 调查

### 2.1 当前解析入口和返回结构

`scanners/pip_audit_scanner.py:210-311`：

```text
parse_output(payload_text, target, version)
  -> (list[Finding], list[str], int)
```

当前最后一个返回值是：

```python
return findings, warnings, len(dependencies)   # line 311
```

`scan()` 在 `:194-196` 解包：

```python
findings, warnings, audited = self.parse_output(...)
```

随后只在 `:199-207` 生成：

```python
ScanOutput(
    findings=...,
    warnings=...,
    metadata={
        "returncode": result.returncode,
        "duration_seconds": round(result.duration_seconds, 3),
        "audited_dependencies": audited,
        "vulnerability_service": self.vulnerability_service,
    },
)
```

当前 metadata 没有 `skipped_dependencies` 或 `total_dependencies`。

### 2.2 pip-audit JSON 结构证据

当前项目内可查证据来自 `tests/test_pip_audit_scanner.py:22-61` 的 fixture：

```json
{
  "dependencies": [
    {
      "name": "requests",
      "version": "2.19.0",
      "vulns": [
        {"id": "PYSEC-2018-28", "fix_versions": ["2.20.0"]},
        {"id": "PYSEC-2023-74", "fix_versions": ["2.31.0"]}
      ]
    },
    {
      "name": "safe-package",
      "version": "1.0.0",
      "vulns": []
    },
    {
      "name": "skipped-package",
      "version": "0.1",
      "vulns": [],
      "skip_reason": "failed to resolve"
    }
  ]
}
```

当前解析代码从每条依赖读取：

```text
name
version
skip_reason
vulns
```

`skip_reason` 读取位置：`scanners/pip_audit_scanner.py:229`。

### 2.3 当前统计逻辑

当前流程：

```text
dependencies = payload["dependencies"]
for dependency in dependencies:
    if not isinstance(dependency, dict):
        continue
    name / version / skip_reason
    if skip_reason:
        warnings.append(...)
    vulns = dependency.get("vulns")
    if not isinstance(vulns, list):
        continue
    for vuln in vulns:
        ...生成 Finding...
return len(dependencies)
```

由此得到：

| 情形 | 当前是否计入 audited | 是否符合 `audited` 语义 |
|---|---|---|
| 正常依赖，`vulns=[]` | 是，计入对象总数 | 是 |
| 正常依赖，`vulns` 有内容 | 是，计入对象总数 | 是 |
| `skip_reason` 非空 | **是**，仍计入对象总数 | **否** |
| `vulns` 非 list | **是**，仍计入对象总数 | **否** |
| 依赖记录不是 dict | 否，但仍计入 `len(dependencies)` | **否** |
| 依赖记录为空或缺少 name/version | 是，仍计入对象总数 | **否** |
| 重复依赖对象 | 按对象重复计数 | 需按契约决定；当前没有去重 |

关键事实：

```text
CONFIRMED: 当前 audited 实际是 dependencies 列表对象数，不是完成审计的依赖数。
CONFIRMED: skip_reason 只产生 warning，不阻止该对象被计入 audited。
CONFIRMED: skip_reason 记录如果同时带 vulns，当前仍会继续生成 Finding；与“skip_reason 优先”的契约不一致。
CONFIRMED: 当前没有 total_dependencies / skipped_dependencies 字段。
CONFIRMED: 当前没有 invalid_dependencies 契约字段。
```

### 2.4 边界情况

**UNKNOWN / 需要实现时防御**：

- pip-audit 是否会在真实输出中产生非 dict 的 dependencies 元素。
- 是否会输出缺少 `name` 或 `version`、但也没有 `skip_reason` 的记录。
- skipped 记录同时带 `vulns` 的实际频率和形态。
- 重复依赖对象的真实产出方式。

当前代码必须对这些情况 fail-closed；不能因为测试 fixture 没有覆盖就假设不会发生。

## 3. Service 当前执行路径

### 3.1 调用链

`services/dependency_audit_service.py:250-373`：

```text
run_audit()
  -> discover() / _select_file()
  -> _create_task()
  -> scanner.is_available()
  -> _mark_running()
  -> _prepared_input()
  -> self._scanner.scan(...)
  -> audited = int(output.metadata.get("audited_dependencies") or 0)
  -> if audited == 0: FAILED
  -> _map_findings()
  -> _save_findings()
  -> summary "已审计 N 个依赖，发现 ... / 未发现已知漏洞。"
  -> _finish(COMPLETED)
```

关键行：

```text
services/dependency_audit_service.py:325
audited = int(output.metadata.get("audited_dependencies") or 0)

services/dependency_audit_service.py:326
if audited == 0:

services/dependency_audit_service.py:339-341
mapped = self._map_findings(...)
saved = self._save_findings(...)

services/dependency_audit_service.py:356-360
summary = "已审计 {audited} 个依赖，发现 {len(saved)} 个唯一漏洞。"
         或 "已审计 {audited} 个依赖，未发现已知漏洞。"

services/dependency_audit_service.py:361-373
return self._finish(... ScanTaskStatus.COMPLETED ...)
```

### 3.2 `int()` 和 `audited == 0` 的影响

当前 Service **没有**读取：

```text
skipped_dependencies
total_dependencies
```

它只读取 `audited_dependencies` 并做 `int()`：

- `"2"` 被转换为 `2`；
- `True` 被转换为 `1`；
- `None` 被转换为 `0`；
- 负数保持负数；
- 缺失键被当作 `0`。

因此：

```text
audited-string      -> int("2") = 2 -> 非零 -> COMPLETED
audited-bool        -> int(True) = 1 -> 非零 -> COMPLETED
audited-negative    -> -1 -> 非零 -> COMPLETED
skipped-bool        -> skipped 完全未读 -> COMPLETED
total-bool          -> total 完全未读 -> COMPLETED
total-zero          -> total 完全未读 -> COMPLETED
```

这解释了 Stage 1B-4C 的实际结果：8 个用例中仅 `audited-none` 通过，其余 7 个失败。

### 3.3 `_finish()` 的 FAILED 摘要机制

`services/dependency_audit_service.py:516-599`：

- `COMPLETED` 才生成成功摘要。
- `FAILED` 摘要固定为：

```text
依赖审计失败；已保留 {len(findings)} 个结果。
```

- `error_message` 由传入的 `errors` 生成；为空时才使用兜底文本。
- `event_type=dependency_audit_failed`，`decision=error`。
- `_finish` 的 `skipped` 参数是 `tuple[str, ...]`，当前实现中没有用于统计或摘要。

因此，只要统计校验发生在 `_finish(COMPLETED)` 之前，就不会出现“未发现已知漏洞”的成功摘要。

## 4. `ScanOutput.metadata` 数据结构

实际定义在 `scanners/base.py:66-70`，不是 `core/models/scan_result.py`：

```python
@dataclass(frozen=True, slots=True)
class ScanOutput:
    findings: tuple[Finding, ...]
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
```

结论：

```text
EXISTING_METADATA_TYPE = Mapping[str, Any]
NEW_MODEL_REQUIRED = NO
NEW_PUBLIC_INTERFACE_REQUIRED = NO
DATABASE_CHANGE_REQUIRED = NO
```

可以在现有 metadata 中增加：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

不需要修改 `ScanOutput` 字段、`Finding`、`ScanTask` 或数据库表。

### 4.1 `ScanTaskStatus.FAILED`

`core/models/enums.py:269-292` 已存在：

```text
ScanTaskStatus.FAILED = "failed"
```

`core/models/scan_task.py:14-31` 已包含：

```text
status
result_summary
error_message
```

不需要新增状态或数据库字段。

## 5. 已批准契约逐项映射

| 契约 | 当前实现 | 结论 |
|---|---|---|
| `INCOMPLETE_AUDIT_POLICY=FAILED` | 全部 skipped 仍可 COMPLETED | **不符，需修复** |
| `FALSE_NO_VULNERABILITY_CLAIM=PROHIBITED` | COMPLETED/no findings 显示“未发现” | **不符** |
| `NEW_TASK_STATUS=NOT_APPROVED` | 未新增状态 | 符合 |
| `SCHEMA_MIGRATION=NOT_REQUIRED` | 不需要迁移 | 符合 |
| metadata 三个字段 | 只有 audited | **缺失** |
| audited 定义 | `len(dependencies)` | **错误** |
| skipped 定义 | 未读取 | **缺失** |
| total 定义 | 未提供 | **缺失** |
| 严格非负整数 | `int()` 强制转换 | **不符** |
| bool 拒绝 | `int(True)=1` | **不符** |
| 缺失/非法/负数 fail-closed | 多数进入 COMPLETED | **不符** |
| `audited + skipped == total` | 无检查 | **不符** |
| `total > 0` | 只有 audited==0 | **不完整** |
| `audit_complete` 由 Service 派生 | 未实现 | **缺失** |
| `invalid_dependencies` 不加入 | 未加入 | 符合 |
| Finding 持久化不新增要求 | 不在本调查要求内 | 保持不扩大 |

## 6. 现有测试覆盖映射

### 6.1 Scanner 测试

`tests/test_pip_audit_scanner.py` 当前有 12 个测试函数：

| 测试 | 覆盖 | 与 RC-01 的关系 |
|---|---|---|
| `test_pip_audit_json_parsing_dedupes_and_maps_metadata` | 2 正常 + 1 skipped；断言 `audited == 2` | 目标断言；当前生产仍返回 3，B4A 失败 |
| `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | 完整 1/0/1 | 已新增目标 metadata 断言 |
| `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | 完整 1/0/1 + Finding | 已新增 |
| `test_pip_audit_scan_metadata_partial_skip` | 2 正常 + 1 skipped | 已新增 2/1/3 断言 |
| `test_pip_audit_scan_metadata_all_skipped` | 2 skipped | 已新增 0/2/2 |
| `test_pip_audit_empty_result` | dependencies=[] | 仅 audited=0，未断言 skipped/total |
| `test_pip_audit_bad_json` | 非法 JSON | 解析失败路径 |
| `test_pip_audit_unavailable_when_module_missing` | 工具不可用 | 状态路径 |
| `test_pip_audit_actual_available` | 当前环境实际可用性 | 环境依赖 |
| `test_pip_audit_execution_failure_timeout_and_cancel` | 进程失败/超时/取消 | 不涉及统计 |
| `test_pip_audit_scan_requires_available_tool` | 未就绪 | 不涉及统计 |
| `test_pip_audit_severity_mapping` | 严重度映射 | 不涉及统计 |

### 6.2 Service 测试

`tests/test_dependency_audit_service.py` 当前有 19 个测试函数，其中与 RC-01 直接相关的包括：

| 测试 | 覆盖 |
|---|---|
| `test_completed_dependency_audit_persists_finding_and_metadata` | 3/0/3，完整成功 |
| `test_empty_dependency_result_is_completed` | 1/0/1，完整无漏洞 |
| `test_zero_audited_dependencies_is_failure_not_success` | 0/0/0，旧零审计失败 |
| `test_partial_skipped_dependency_audit_fails_without_success_summary` | 1/1/2，部分跳过 |
| `test_all_skipped_dependency_audit_fails_without_success` | 0/2/2，全部跳过 |
| `test_missing_dependency_statistics_fail_closed` | 只给 audited，缺 skipped/total |
| `test_inconsistent_dependency_statistics_fail_closed` | 1/1/3，统计矛盾 |
| `test_invalid_dependency_statistics_fail_closed` | 8 个非法参数，含 bool、负数、字符串、零 |
| `test_pip_audit_unavailable_marks_task_failed_without_findings` | 工具不可用 |
| `test_execution_failure_and_timeout_are_failed` | 执行失败/超时 |
| `test_cancelled_dependency_audit_is_not_completed` | 取消 |
| `test_cancel_before_start_marks_cancelled` | 启动前取消 |
| `test_pyproject_is_prepared_as_temporary_requirements_and_cleaned` | 输入准备 |
| `test_dependency_project_isolation` | 项目隔离 |
| `test_unregistered_path_is_rejected` | 路径校验 |
| `test_invalid_pyproject_is_not_auditable` | 无效 pyproject |

### 6.3 UI 测试

`tests/test_ui_dependency_audit.py:105`：

- 完整 2/0/2，显示 Finding，任务 COMPLETED。

`tests/test_ui_dependency_audit.py:171`：

- 不完整 1/1/2，断言 FAILED 且 empty label 不含“未发现”。

### 6.4 覆盖缺口

| 缺口 | 状态 |
|---|---|
| `total_dependencies` 负数 | **缺失** |
| `skipped_dependencies` 字符串 | **缺失** |
| `total_dependencies` 字符串 / 浮点 | **缺失** |
| `skipped_dependencies=None` | **缺失**（缺字段用 missing 测试覆盖） |
| scanner 直接解析 skipped/total 返回值 | 仅 scan metadata 测试覆盖 |
| `audited-none` 的假阳性 | **已确认**：通过来自旧 `audited==0` 分支 |
| Finding 保留/删除 | **不属于 RC-01 契约**，不应作为本轮断言 |

Scanner 的 `test_pip_audit_empty_result` 还需要在实现 5 元返回后补充 skipped/total 断言，或至少更新解包。

## 7. 最小生产修复方案

### 7.1 Scanner 修改

文件：`scanners/pip_audit_scanner.py`

修改位置：

```text
parse_output()  :210-311
scan()          :194-207
```

建议最小实现：

1. 在 `parse_output()` 中先计算：

```python
total = len(dependencies)
audited = 0
skipped = 0
```

2. 对每条记录：

```text
非 dict -> 只计入 total，不计 audited/skipped
skip_reason 非空 -> skipped += 1；追加 warning；continue（skip 优先，不生成 Finding）
name/version 为空或 vulns 非 list -> 不计 audited；由 Service 的 sum 检查 fail-closed
否则 -> audited += 1；再处理 vulns
```

3. 返回值改为：

```python
return findings, warnings, audited, skipped, total
```

4. `scan()` 解包五个值，metadata 增加：

```text
skipped_dependencies
total_dependencies
```

5. `audited_dependencies` 保留原名，不新增 `invalid_dependencies`。

### 7.2 Service 修改

文件：`services/dependency_audit_service.py`

插入位置：

```text
:323-325 之后、:325 的 int() 之前
```

建议新增私有校验函数（模块级或类方法均可）：

```text
_read_dependency_statistics(metadata) -> (audited, skipped, total)
```

严格规则：

```text
type(value) is int
value >= 0
bool 必须被 type(value) is int 排除
三个键都存在
total > 0
audited + skipped == total
skipped == 0
audited == total
```

只要任一条件失败，立即：

```python
return self._finish(
    discovery, selected, task_id, ScanTaskStatus.FAILED,
    (), output.warnings, (reason,), safe_audited, (),
    progress=100,
)
```

错误文本建议：

```text
total == 0 或 audited == 0:
"pip-audit 未审计到任何依赖，不能判定为无漏洞"

skipped > 0:
"pip-audit 存在 {skipped} 个未完成审计的依赖，不能判定为无漏洞"

字段缺失/类型非法/负数/统计矛盾:
"pip-audit 依赖统计无效，不能判定为无漏洞"
```

校验必须在 `_map_findings()` 和 `_save_findings()` 之前，确保不会走到 `_finish(COMPLETED)` 或成功摘要。对 Finding 的保存/删除/保留不作额外契约要求；本方案只保证不产生假成功。

### 7.3 UI 修改

生产 UI 不需要修改。

`ui/dependency_page.py:708-711` 只在：

```text
task.status is COMPLETED and not findings
```

时显示“当前任务未发现已知依赖漏洞”。新 Service 对不完整审计返回 FAILED，因此该文案不会出现。

## 8. 文件修改清单

### 生产代码（本轮未修改，仅建议）

| 文件 | 位置 | 目的 |
|---|---|---|
| `scanners/pip_audit_scanner.py` | `:194-207`, `:210-311` | 增加 skipped/total 统计与 metadata |
| `services/dependency_audit_service.py` | `:323-373` | 严格校验统计，fail-closed |

### 测试代码（已在工作区修改，待生产修复后验证）

| 文件 | 已有测试 | 需要同步 |
|---|---|---|
| `tests/test_pip_audit_scanner.py` | metadata 4 个场景 | 更新 `parse_output` 两处 3 元解包为 5 元 |
| `tests/test_dependency_audit_service.py` | 完整/部分/全部/缺失/矛盾/非法 | 生产修复后应通过；建议补 `total-negative`、`skipped-string` |
| `tests/test_ui_dependency_audit.py` | 完整/不完整 | 无需新增生产路径 |

### 不需要修改

```text
core/models/scan_result.py      （不存在；实际 ScanOutput 在 scanners/base.py）
core/models/scan_task.py
core/models/enums.py
database/schema.py
repositories/*
ui/dependency_page.py
其他 Scanner
```

## 9. 兼容性和回归风险

### 9.1 其他扫描器

`ScanOutput.metadata` 是共享的，但 Bandit/Semgrep 不读取 pip-audit 统计键；只改 PipAuditScanner 的 metadata 不会改变它们的行为。

### 9.2 GUI

GUI 通过 `ScanTaskStatus` 和 findings 判断，不直接读取统计 metadata；FAILED 时不会显示“未发现”。不需要 UI 代码修改。

### 9.3 测试

- Scanner 测试中 4 个 metadata 场景目前已经写了目标断言，但生产未实现，B4A 失败。
- Service 测试中 8 个参数化用例只有 `audited-none` 通过；修复后应全部通过。
- `parse_output` 从 3 元改为 5 元会影响两个直接调用测试（`:77`、`:212`），必须同步更新；没有其他生产调用者。

### 9.4 风险

- `total` 包含非 dict / 无效记录时，`audited + skipped != total`，会 fail-closed；这是有意行为，不是漏报。
- 部分审计即使包含有效 Finding，也会因不完整而 FAILED；Finding 持久化不属于本轮契约，不要求保留或删除。
- 真实 pip-audit 的 skipped 记录形态仍需实现时用真实输出验证；当前仅以项目测试 fixture 和 Stage 1A 的包源证据为依据。

## 10. 尚无法确认的事项（UNKNOWN）

```text
UNKNOWN: 当前环境真实 pip-audit 全 skipped 输出（未运行）
UNKNOWN: skipped 记录是否总是缺少 version/vulns
UNKNOWN: 非 dict / 缺字段记录在真实输出中的概率
UNKNOWN: skipped 同时带 vulns 的真实行为是否出现
UNKNOWN: 重复依赖名在真实 pip-audit 输出中的计数语义
```

这些不改变批准的三字段契约，但实现时应以防御性方式处理，不能假设记录一定完整。

## 11. 执行前后 Git 状态

### 执行前

```text
branch: main
staged: 空

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
```

### 执行后

除本报告新增：

```text
?? docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

没有其他工作区变化。暂存区仍为空。

## 12. 边界遵守情况

```text
READ_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
README_MODIFIED = NO
MANIFEST_MODIFIED = NO
GIT_ADD_COMMIT_PUSH = NO
GIT_RESET_RESTORE_CLEAN = NO
PYTEST_RUN = NO
REAL_PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DEPENDENCY_INSTALL = NO
```

本报告只新增调查文件，没有开始修复，也没有进入 Stage 1B-5B。

等待人工审核。
