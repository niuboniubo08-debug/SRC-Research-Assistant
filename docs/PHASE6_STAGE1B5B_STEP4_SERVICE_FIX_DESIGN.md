# Phase 6 Stage 1B-5B — Step 4-R2 DependencyAuditService 最小修复设计（修订版）

> 修订说明：本报告在原 Step 4 设计及 Step 4-R1 修订基础上完成 R2 最小补充。
>
> **原设计保留：**
> - 方案 B：独立 `_validate_statistics()` 私有辅助函数；
> - 统计非法时不进入 Finding 映射/保存；
> - 统计合法但不完整时保留既有 Finding 映射/保存顺序，最终 FAILED；
> - 不扩展 `DependencyAuditOutcome`；
> - 不修改 Scanner、Schema、状态机或 Finding 生命周期。
>
> **R1 修订保留：**
> - 总和校验通过后 `audited != total` 与 `skipped > 0` 的等价关系；
> - 区分预期 `ValidationError` 与意外程序异常；
> - 补齐统计测试矩阵与任务终态验证；
> - 明确“保存 Finding 不等于审计成功”。
>
> **R2 补充：**
> - 增加 `total_dependencies=-1` 独立测试；
> - 确认 `_map_findings()` / `_save_findings()` 已有异常处理位置与行为；
> - 将 Finding 映射/保存异常处理明确排除在本次修改范围之外；
> - 保持既有 Finding 异常处理行为，不与统计校验异常混同。

## 0. 修订后的逻辑基线

在统计全部合法且：

```text
audited_dependencies + skipped_dependencies == total_dependencies
```

成立时：

```text
audited_dependencies != total_dependencies
```

等价于：

```text
skipped_dependencies > 0
```

因此：

- `skipped > 0` 是**合法但不完整**的唯一正常情形；
- `audited != total` 保留为防御性检查，但在总和校验通过后属于冗余保护；
- `audited=1, skipped=0, total=2` **不满足总和关系**，属于**统计非法**，不是合法但不完整。

## 1. 当前 Service 结构及真实接口

### 1.1 主调用链

```text
DependencyAuditService.run_audit()                    :245
  -> discover()                                       :254
  -> _select_file()                                   :255
  -> _create_task()                                   :261
  -> scanner_info()                                   :268
  -> _mark_running()                                  :283
  -> _prepared_input()                                :288
  -> self._scanner.scan()                             :292
  -> int(output.metadata["audited_dependencies"])     :325
  -> audited == 0 失败分支                            :326-338
  -> _map_findings()                                  :340
  -> _save_findings()                                 :341
  -> 成功摘要                                          :356-360
  -> _finish(COMPLETED)                               :361-373
```

### 1.2 当前真实统计读取

```python
# services/dependency_audit_service.py:325
audited = int(output.metadata.get("audited_dependencies") or 0)
```

当前只读取 `audited_dependencies`，没有读取：

```text
skipped_dependencies
total_dependencies
```

唯一完整性检查：

```python
# :326-338
if audited == 0:
    return self._finish(
        ...,
        ScanTaskStatus.FAILED,
        ...,
        ("pip-audit 未审计到任何依赖，不能判定为无漏洞",),
        ...
    )
```

### 1.3 `_finish()` 的真实签名

```python
# services/dependency_audit_service.py:516-531
def _finish(
    self,
    discovery: DependencyDiscovery,
    selected: DependencyFileInfo,
    task_id: int,
    status: ScanTaskStatus,
    findings: tuple[Finding, ...],
    warnings: tuple[str, ...],
    errors: tuple[str, ...],
    audited_dependencies: int,
    skipped: tuple[str, ...],
    *,
    cancelled: bool = False,
    progress: int = 100,
    summary: str = "",
) -> DependencyAuditOutcome:
```

实际行为：

- `status=FAILED`：`result_summary` 固定为 `依赖审计失败；已保留 N 个结果。`
- `error_message` 来自 `"；".join(errors)`；
- `audited_dependencies` 写入 outcome 和审计日志；
- `skipped` 参数是 `tuple[str, ...]`，当前未使用；
- `_finish` 负责 `UPDATE scan_tasks`、写审计日志、读取任务和已保存 Finding。

### 1.4 `DependencyAuditOutcome` 当前字段

```python
# :69-76
task: ScanTask
findings: tuple[Finding, ...]
dependency_file: str
audited_dependencies: int
warnings: tuple[str, ...]
errors: tuple[str, ...]
```

没有：

```text
skipped_dependencies
total_dependencies
audit_complete
```

### 1.5 当前调用者

- `DependencyAuditOutcome` 的唯一构造位置是 `_finish()` `:592-599`。
- `ui/dependency_page.py:68` 调用 `run_audit()`，`_on_completed()` 使用 `outcome.task`、`outcome.warnings`。
- `tools/run_phase4_acceptance.py:69` 使用 `outcome.audited_dependencies`。
- 测试使用 `outcome.audited_dependencies`、`outcome.task`、`outcome.warnings` 等。
- 没有调用者依赖 `DependencyAuditOutcome` 的 skipped/total 字段。

## 2. 两种修复方案比较

### 方案 A：最小局部修复

在 `run_audit()` 的原位置直接增加字段读取和判断：

```python
raw_audited = output.metadata.get("audited_dependencies")
raw_skipped = output.metadata.get("skipped_dependencies")
raw_total = output.metadata.get("total_dependencies")

if not (type(raw_audited) is int and type(raw_skipped) is int and type(raw_total) is int):
    return self._finish(... FAILED ...)
if raw_audited < 0 or raw_skipped < 0 or raw_total < 0:
    return self._finish(... FAILED ...)
if raw_total <= 0 or raw_audited + raw_skipped != raw_total:
    return self._finish(... FAILED ...)
```

优点：

- 修改最少；
- 不需要新增辅助类型或接口；
- 所有逻辑在 `run_audit()` 内可见。

缺点：

- `run_audit()` 已有大量失败分支，继续内联会增加分支复杂度；
- 统计校验无法独立测试，只能通过完整 Service 流程测试；
- 容易把“统计非法”和“审计不完整”混在同一层；
- 错误原因需要重复拼接，后续维护风险较高。

### 方案 B：独立统计校验辅助函数（推荐）

在 Service 内增加一个私有辅助函数，例如：

```python
def _validate_statistics(
    self, metadata: Mapping[str, object]
) -> tuple[int, int, int]:
    ...
```

返回：

```text
(audited_dependencies, skipped_dependencies, total_dependencies)
```

非法时抛出项目已有的 `ValidationError`，由 `run_audit()` 捕获并转成 FAILED。

优点：

- 统计规则集中、可独立测试；
- `run_audit()` 只负责控制流，不承担字段解析细节；
- 明确区分“非法统计”与“合法但不完整”；
- 可以稳定生成可区分的错误原因；
- 不改变 Scanner、Schema、状态机或 Finding 业务。

缺点：

- 需要新增一个私有方法；
- 需要为辅助函数补测试，修改面略大于方案 A。

### 2.1 选择

```text
RECOMMENDED_OPTION = B
```

理由：RC-01 的根因是统计契约没有单一校验点；继续内联会把字段检查、错误文本和任务终态逻辑混在 `run_audit()`。方案 B 的额外代码量很小，但明显更适合测试和后续维护。

## 3. 推荐方案的详细控制流

### 3.1 校验顺序

```text
1. output = scanner.scan()
2. audited, skipped, total = _validate_statistics(output.metadata)
   - metadata 不是 Mapping -> ValidationError
   - 任一字段缺失 -> ValidationError
   - 任一字段 type(value) is not int -> ValidationError
   - 任一字段 < 0 -> ValidationError
   - total <= 0 -> ValidationError
   - 任一字段为 bool/字符串/浮点数 -> ValidationError
   - audited + skipped != total -> ValidationError
3. 统计非法 -> _finish(FAILED)，不进入 Finding 映射/保存
4. 统计合法 -> 进入既有 _map_findings() / _save_findings() 顺序
5. 判断有效性：
   - skipped == 0 且 audited == total -> COMPLETED 成功摘要
   - skipped > 0 -> FAILED，不使用成功摘要
   - audited != total -> 防御性检查；在总和校验通过后与 skipped > 0 等价
```

总和校验通过时，`skipped == 0` 必然推出 `audited == total`；因此不会出现“总和合法、`skipped == 0`、但 `audited != total`”的合法状态。`audited=1, skipped=0, total=2` 不满足总和校验，必须按统计非法处理。

### 3.2 伪代码

```python
output = self._scanner.scan(...)

try:
    audited, skipped, total = self._validate_statistics(output.metadata)
except ValidationError as exc:
    # 预期校验异常：字段缺失、类型错误、负数、total<=0、总和不一致。
    return self._finish(
        discovery, selected, task_id, ScanTaskStatus.FAILED,
        (), output.warnings,
        (f"依赖审计统计非法：{exc}",),
        0, (), progress=100,
    )
except Exception as exc:
    # 意外程序异常：不能伪装成“统计非法”，但仍必须落 FAILED。
    return self._finish(
        discovery, selected, task_id, ScanTaskStatus.FAILED,
        (), output.warnings,
        (f"依赖审计统计校验异常：{exc}",),
        0, (), progress=100,
    )

incomplete_reason = ""
if skipped > 0:
    incomplete_reason = (
        f"pip-audit 审计不完整：总计 {total}，"
        f"已审计 {audited}，跳过 {skipped}；"
        "不判定为无漏洞"
    )
elif audited != total:
    # 防御性检查：总和已校验时正常不可达。
    incomplete_reason = (
        "pip-audit 审计统计关系异常："
        f"总计 {total}，已审计 {audited}，跳过 {skipped}"
    )

# 注意：以下 try/except 是当前 Service :339-354 的既有行为，
# 不属于 Step 4-R2 的实施变更；仅展示其保持不变的调用位置。
# 统计校验异常与 Finding 映射/保存异常使用不同错误文本。
try:
    mapped = self._map_findings(discovery, selected, output.findings)
    saved = self._save_findings(discovery.project_id, task_id, mapped)
except Exception as exc:
    return self._finish(
        discovery, selected, task_id, ScanTaskStatus.FAILED,
        (), output.warnings,
        (f"依赖审计结果保存失败：{exc}",),
        audited, (), progress=100,
    )

if incomplete_reason:
    return self._finish(
        discovery, selected, task_id, ScanTaskStatus.FAILED,
        tuple(saved), output.warnings,
        (incomplete_reason,),
        audited, (), progress=100,
    )

summary = (
    f"已审计 {audited} 个依赖，发现 {len(saved)} 个唯一漏洞。"
    if saved
    else f"已审计 {audited} 个依赖，未发现已知漏洞。"
)
return self._finish(
    discovery, selected, task_id, ScanTaskStatus.COMPLETED,
    tuple(saved), output.warnings, (), audited, (),
    progress=100, summary=summary,
)
```

### 3.3 关键顺序保证

```text
INVALID_STATS_BEFORE_MAPPING = YES
INVALID_STATS_BEFORE_SAVING = YES
INCOMPLETE_STATS_AFTER_MAPPING_SAVING = YES
COMPLETE_STATS_SAME_ORDER_AS_BEFORE = YES
SAVED_FINDING_DOES_NOT_MEAN_SUCCESS = YES
```

- 统计非法：不进入 `_map_findings()` / `_save_findings()`；
- 统计合法但不完整：保留现有 Finding 映射与保存顺序，但最终进入 `FAILED`；
- 统计合法且完整：沿用原成功路径；
- 不改变 `_map_findings()` / `_save_findings()` 内部实现；
- **保存 Finding 不等于审计成功**；FAILED 任务即使保存了部分有效 Finding，也不得生成“未发现已知漏洞”等成功摘要。

### 3.4 Finding 映射/保存异常（既有行为，不纳入本次修改）

当前 Service 已存在异常处理，位置：

```text
services/dependency_audit_service.py:339-354
```

真实代码行为：

```python
try:
    mapped = self._map_findings(discovery, selected, output.findings)
    saved = self._save_findings(discovery.project_id, task_id, mapped)
except Exception as exc:
    return self._finish(
        discovery,
        selected,
        task_id,
        ScanTaskStatus.FAILED,
        (),
        output.warnings,
        (f"依赖审计结果保存失败：{exc}",),
        audited,
        (),
        progress=100,
    )
```

结论：

```text
MAP_SAVE_EXCEPTION_HANDLING_ALREADY_EXISTS = YES
MAP_SAVE_EXCEPTION_HANDLING_CHANGE_IN_RC01 = NO
```

- 该 `try/except` 同时覆盖 `_map_findings()` 和 `_save_findings()`；
- 捕获到异常后调用现有 `_finish(FAILED)`，错误文本为 `依赖审计结果保存失败：...`；
- 该异常与统计校验异常是**不同类别**，不得混用错误文本；
- 如果 `_save_findings()` 已经写入部分记录后失败，现有 `_finish()` 会重新读取已保存记录（`:590-591`），可能返回部分结果；这是既有行为；
- 本设计的实施范围不修改这段代码，也不新增其异常处理。

因此，R2 的变更范围仅为统计校验和统计失败分支；Finding 映射/保存异常处理保持原样。

## 4. 统计非法与审计不完整的处理差异

| 项目 | 统计非法 | 审计不完整 |
|---|---|---|
| 定义 | 字段缺失、类型错误、负数、total 为 0、总和不等 | 三字段合法且总和相等，但 skipped > 0 |
| 示例 | `audited=1, skipped=0, total=2`（总和不相等） | `audited=1, skipped=1, total=2` |
| 是否映射 Finding | **否** | 是，保持原有顺序 |
| 是否保存 Finding | **否** | 是，保持原有顺序 |
| 是否生成成功摘要 | 否 | **否** |
| 终态 | FAILED | FAILED |
| `error_message` | `依赖审计统计非法：...` | `pip-audit 审计不完整：...` |
| `result_summary` | `依赖审计失败；已保留 N 个结果。` | `依赖审计失败；已保留 N 个结果。` |
| 是否可能 COMPLETED | 否 | 否 |

这里刻意区分两类问题：

- **非法统计**意味着 Scanner 契约被破坏，不能相信计数，也不能处理 Finding；
- **不完整统计**意味着计数合法、总和一致，但审计覆盖不足，可以保留有效结果，但绝不能报告成功；
- 保存 Finding 不等于审计成功。FAILED 任务即使保存了部分 Finding，也必须使用失败摘要，不得使用“未发现已知漏洞”。

`audited != total` 在总和校验通过后与 `skipped > 0` 等价，因此它不能单独构成“另一类合法不完整”。如果 `audited != total` 且 `skipped == 0`，则总和必然不相等，属于统计非法。

## 5. `_finish()` 调用设计与任务终态保障

### 5.1 非法统计调用

```python
return self._finish(
    discovery,
    selected,
    task_id,
    ScanTaskStatus.FAILED,
    (),
    output.warnings,
    (f"依赖审计统计非法：{exc}",),
    0,
    (),
    progress=100,
)
```

`_finish()` 会执行：

```text
UPDATE scan_tasks SET status='failed', finished_at=...
result_summary='依赖审计失败；已保留 0 个结果。'
error_message='依赖审计统计非法：...'
```

### 5.2 不完整审计调用

```python
return self._finish(
    discovery,
    selected,
    task_id,
    ScanTaskStatus.FAILED,
    tuple(saved),
    output.warnings,
    (incomplete_reason,),
    audited,
    (),
    progress=100,
)
```

`_finish()` 会执行：

```text
UPDATE scan_tasks SET status='failed', finished_at=...
result_summary='依赖审计失败；已保留 N 个结果。'
error_message='pip-audit 审计不完整：...'
```

### 5.3 终态保障

当前统计读取在 Scanner `try` 块之外，非法值可能直接抛出 `ValueError`/`TypeError`，导致 `_finish()` 未被调用，任务停留在 `running`。

推荐方案把统计读取放入独立 `try/except`，并严格区分两类异常：

```text
EXPECTED_VALIDATION_EXCEPTION = ValidationError
  -> 说明字段缺失/类型错误/负数/total=0/总和不一致
  -> _finish(FAILED, errors=("依赖审计统计非法：...",))

UNEXPECTED_VALIDATION_EXCEPTION = Exception（非 ValidationError）
  -> 说明校验代码自身发生意外错误
  -> _finish(FAILED, errors=("依赖审计统计校验异常：...",))
  -> 不得伪装成“统计非法”
```

现有异常类来自 `core/errors.py`：

```text
ValidationError(AppError) at core/errors.py:17-21
```

本设计不新增异常类，不修改 `ValidationError`。

对应要求：

```text
EVERY_STATS_FAILURE_REACHES_FINISH = YES
TASK_LEFT_RUNNING_ON_STATS_ERROR = NO
EXPECTED_AND_UNEXPECTED_ERRORS_DISTINGUISHED = YES
UNEXPECTED_EXCEPTION_LABELED_AS_STATS_INVALID = NO
```

如果 `_finish()` 自身数据库写入失败，Service 不能保证终态；这是现有持久化层的共同风险，不在 RC-01 内扩大处理。

## 6. Outcome DTO 兼容性分析

### 6.1 当前构造位置

`DependencyAuditOutcome` 只在 `_finish()` 的 `:592-599` 构造：

```python
return DependencyAuditOutcome(
    task=task,
    findings=tuple(stored),
    dependency_file=selected.relative_path,
    audited_dependencies=audited_dependencies,
    warnings=tuple(warnings),
    errors=tuple(errors),
)
```

### 6.2 调用者需求

- `ui/dependency_page.py` 只使用 `.task`、`.warnings`；
- `tools/run_phase4_acceptance.py` 使用 `.audited_dependencies`；
- 测试使用 `.task`、`.audited_dependencies`、`.warnings`；
- 没有调用者读取 `skipped/total/audit_complete`。

### 6.3 结论

```text
OUTCOME_DTO_EXTENSION_REQUIRED_FOR_RC01 = NO
```

理由：

- 本次修复需要的是任务状态和错误信息，不是新的 Service 公共字段；
- 不完整审计的计数已写入 `error_message`，足够区分失败原因；
- 新增字段会改变 DTO 结构，需要同步所有调用者和测试，扩大范围；
- 当前 `DependencyAuditOutcome` 的 `success`/`failed` 属性仍能正确反映 FAILED/COMPLETED。

如果未来 UI 需要独立展示 skipped/total，应单独提出 DTO 扩展设计，不能混入 RC-01 最小修复。

## 7. 测试用例设计（仅设计，不执行）

目标测试文件：

```text
tests/test_dependency_audit_service.py
```

复用现有 fake Scanner 和项目夹具；不新增生产接口。

### 7.1 统计字段缺失

| 用例 | 输入 | 预期 |
|---|---|---|
| TC-STAT-00 | `metadata=None` / 列表等非 Mapping | FAILED，错误指明 metadata 非 Mapping |
| TC-STAT-01 | 缺 `audited_dependencies` | FAILED，错误指明字段缺失 |
| TC-STAT-02 | 缺 `skipped_dependencies` | FAILED，错误指明字段缺失 |
| TC-STAT-03 | 缺 `total_dependencies` | FAILED，错误指明字段缺失 |
| TC-STAT-01N | `audited_dependencies=None` | FAILED，拒绝 None |
| TC-STAT-02N | `skipped_dependencies=None` | FAILED，拒绝 None |
| TC-STAT-03N | `total_dependencies=None` | FAILED，拒绝 None |

### 7.2 类型非法

| 用例 | 输入 | 预期 |
|---|---|---|
| TC-STAT-04 | `audited=True` | FAILED，拒绝 bool |
| TC-STAT-05 | `skipped=True` | FAILED，拒绝 bool |
| TC-STAT-06 | `total=True` | FAILED，拒绝 bool |
| TC-STAT-07 | `audited="2"` | FAILED，拒绝字符串 |
| TC-STAT-08 | `skipped="1"` | FAILED，拒绝字符串 |
| TC-STAT-09 | `total="3"` | FAILED，拒绝字符串 |
| TC-STAT-10 | `audited=2.0` | FAILED，拒绝浮点数 |
| TC-STAT-10A | `skipped=1.0` | FAILED，拒绝浮点数 |
| TC-STAT-10B | `total=3.0` | FAILED，拒绝浮点数 |

### 7.3 数值非法与不一致

| 用例 | 输入 | 预期 |
|---|---|---|
| TC-STAT-11 | `audited=-1` | FAILED，拒绝负数 |
| TC-STAT-12 | `skipped=-1` | FAILED，拒绝负数 |
| TC-STAT-13 | `total=0` | FAILED，拒绝 total 为 0 |
| TC-STAT-13A | `total=-1` | FAILED，明确拒绝负数 total_dependencies |
| TC-STAT-14 | `audited=2, skipped=1, total=4` | FAILED，总和不等 |
| TC-STAT-15 | `audited=5, skipped=0, total=3` | FAILED，审计数大于总数 |
| TC-STAT-19 | `audited=1, skipped=0, total=2` | FAILED，总和不等；**不是合法不完整** |

### 7.4 合法完整

| 用例 | 输入 | 预期 |
|---|---|---|
| TC-STAT-16 | `audited=2, skipped=0, total=2`，有 Finding | COMPLETED，正常成功摘要 |
| TC-STAT-17 | `audited=2, skipped=0, total=2`，无 Finding | COMPLETED，“未发现已知漏洞”仅在完整时出现 |

### 7.5 合法不完整

| 用例 | 输入 | 预期 |
|---|---|---|
| TC-STAT-18 | `audited=1, skipped=1, total=2` | FAILED，不生成成功摘要 |
| TC-STAT-20 | `audited=2, skipped=1, total=3`，有 Finding | FAILED，保留符合现有顺序的结果，但任务不是 COMPLETED |

### 7.6 终态与摘要

| 用例 | 验证 |
|---|---|
| TC-STAT-21 | 统计非法后查询 `scan_tasks.status`，必须为 `failed`，不能为 `running` |
| TC-STAT-21A | 用 monkeypatch 让 `_validate_statistics()` 抛出非 `ValidationError` 的 `RuntimeError`；任务必须 FAILED，错误文本标明“校验异常”，不得标成“统计非法” |
| TC-STAT-22 | 合法不完整任务 `result_summary` 不包含 `未发现已知漏洞` |
| TC-STAT-23 | 合法完整任务仍保留原成功摘要和 COMPLETED |
| TC-STAT-24 | 统计非法任务不产生新的 Finding（或使用现有测试夹具验证映射未执行） |
| TC-STAT-25 | 合法不完整任务查询真实 `scan_tasks.status`，必须为 `failed`，不能为 `running` 或 `completed` |
| TC-STAT-26 | 合法不完整但已保存 Finding 时，任务仍为 FAILED；保存数量不得改变成功/失败结论 |

### 7.7 测试实现注意

- 通过现有 fake Scanner 的 `raw_metadata` 注入各字段；
- 对统计非法用例直接查询 Service 的 `get_task()`；
- 对不完整用例避免断言 Finding 生命周期细节，只断言任务终态、错误文本和成功摘要不存在；
- 所有“总和不一致”输入（包括 `audited=1, skipped=0, total=2`）必须归入统计非法，不得归入合法不完整；
- 合法不完整只使用总和相等且 `skipped > 0` 的输入；
- 意外校验异常测试只 monkeypatch `_validate_statistics()` 的异常行为，不修改生产代码或测试文件；
- 不修改 `_map_findings()` / `_save_findings()` 的既有测试。

## 8. 修改文件预估清单

### 8.1 生产代码

```text
services/dependency_audit_service.py
```

预计新增：

- `_validate_statistics()` 私有辅助函数；
- `run_audit()` 中统计读取、异常捕获和完整性判断；
- 两处 `_finish()` 调用分支（非法统计、不完整统计）。

明确不新增：

- 不新增 `_map_findings()` / `_save_findings()` 的异常处理；
- 不改变 `:339-354` 的既有 try/except；
- 不新增异常类；
- 不改变 Finding 生命周期或保存顺序。

不修改：

```text
scanners/pip_audit_scanner.py
scanners/base.py
services/report_service.py
ui/dependency_page.py
database/schema.py
repositories/*
```

### 8.2 测试代码

```text
tests/test_dependency_audit_service.py
```

只增加 RC-01 统计校验测试和结果状态测试；不修改 Scanner 测试、UI 测试、Finding 生命周期测试。

### 8.3 文档

```text
docs/PHASE6_STAGE1B5B_STEP4_SERVICE_FIX_DESIGN.md
```

本报告本身。

## 9. 风险与 UNKNOWN

### 9.1 设计风险

```text
RISK-01
在统计非法路径中不映射/保存 Finding；这是有意的 fail-closed 行为，可能与“尽量保留结果”的直觉不同。

RISK-02
不完整审计保留既有 Finding 映射/保存；如果未来产品要求失败任务不得保留 Finding，需要单独批准并修改契约。

RISK-03
_finish() 自身数据库写入失败时，仍不能保证终态；这是现有持久化层风险，不在 RC-01 内解决。

RISK-04
调用方 UI 通过 completed 信号接收 FAILED Outcome 时显示任务失败，但仍刷新 findings；本设计不修改 UI。

RISK-05
意外校验异常与统计非法异常必须使用不同错误文本；如果把两者都归类为“统计非法”，会掩盖程序缺陷。本设计明确区分。

RISK-06
`_map_findings()` / `_save_findings()` 已有 try/except；本次不修改它。统计校验修复不应顺带改变其异常分类或部分保存行为。
```

### 9.2 UNKNOWN

```text
UNKNOWN
真实 pip-audit 在 skipped 场景下的实际 metadata 结构和退出码；本次只设计，未运行真实 pip-audit。

UNKNOWN
生产数据库中是否已有历史 COMPLETED 任务受旧逻辑影响；本次未打开数据库。

UNKNOWN
未来是否需要将 skipped/total/audit_complete 暴露到 DependencyAuditOutcome 或 UI；本次明确不作为 RC-01 要求。

UNKNOWN
统计非法时 _finish() 自身的数据库异常行为；现有实现未提供额外补偿。
```

## 10. 边界声明

```text
STEP_4_R2_STATUS = DESIGN_REVISED
STEP_4_R1_STATUS = DESIGN_REVISED
ORIGINAL_OPTION_B_RETAINED = YES
STATISTICS_CONTRACT_CHANGED = NO
MAP_SAVE_EXCEPTION_HANDLING_CHANGE = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
SCANNER_MODIFIED = NO
SERVICE_CODE_MODIFIED = NO
REPOSITORY_MODIFIED = NO
GUI_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
JSON_WORK = NO
TESTS_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本报告只提出设计方案，没有将方案描述为已实现；所有行号和接口均来自当前源码。
