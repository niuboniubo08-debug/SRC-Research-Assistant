# Phase 6 Stage 1B-5B — Step 3 DependencyAuditService 只读调查报告

## 1. 调查文件清单

本次只读检查：

```text
services/dependency_audit_service.py
scanners/pip_audit_scanner.py
scanners/base.py
core/models/scan_task.py
core/models/finding.py
```

为确认调用链，还静态检索了 Service/Scanner 相关调用点。

本次没有修改生产代码、测试、Scanner、Service、Repository、GUI、数据库或 Schema；没有运行 pytest、真实 pip-audit 或 GUI。

当前文件：

```text
services/dependency_audit_service.py
25,953 bytes
D91A328D7E0F65B6ED512C37A86D6F3BA05DFF6D974D1046F0D7DF700DB1E6F9

scanners/pip_audit_scanner.py
13,391 bytes
5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D
```

## 2. 实际函数、方法和调用链

### 2.1 主调用链

```text
DependencyAuditService.run_audit()                    :245
  -> discover()                                       :254
  -> _select_file()                                   :255
  -> _create_task()                                   :261
  -> scanner_info()                                   :268
  -> _mark_running()                                  :283
  -> _prepared_input()                                :288
  -> PipAuditScanner.scan()                           :292
       -> run_command()                               (Scanner 内部)
       -> _parse_with_statistics()                    (Scanner 内部)
  -> int(output.metadata["audited_dependencies"])     :325
  -> audited == 0 失败分支                            :326-338
  -> _map_findings()                                  :340
  -> _save_findings()                                 :341
  -> 成功摘要                                          :356-360
  -> _finish(COMPLETED)                               :361-373
       -> UPDATE scan_tasks
       -> audit.record()
       -> get_task()
       -> list_findings()
```

### 2.2 `DependencyAuditOutcome`

位置：`services/dependency_audit_service.py:69-88`

字段：

```python
task: ScanTask
findings: tuple[Finding, ...]
dependency_file: str
audited_dependencies: int
warnings: tuple[str, ...]
errors: tuple[str, ...]
```

当前 outcome 没有：

```text
skipped_dependencies
total_dependencies
audit_complete
```

`success` 仅判断：

```python
return self.task.status is ScanTaskStatus.COMPLETED
```

## 3. Scanner metadata 的读取

### 3.1 接收输出

`PipAuditScanner.scan()` 返回 `ScanOutput`：

```text
scanners/base.py:66-70
ScanOutput.findings / warnings / metadata
```

Service 在：

```text
services/dependency_audit_service.py:292-298
```

接收：

```python
output = self._scanner.scan(
    prepared,
    ScanOptions(
        timeout_seconds=float(timeout_seconds),
        cancel_event=cancel,
    ),
)
```

### 3.2 读取 metadata

唯一读取统计字段的位置：

```python
# services/dependency_audit_service.py:325
audited = int(output.metadata.get("audited_dependencies") or 0)
```

当前只读取：

```text
audited_dependencies
```

没有读取：

```text
skipped_dependencies
total_dependencies
```

### 3.3 字段缺失与默认值

```text
audited_dependencies 缺失 / None / 0 -> int(... or 0) -> 0
skipped_dependencies 缺失 -> 未读取，无影响
total_dependencies   缺失 -> 未读取，无影响
```

因此 `audited > 0` 时，即使 `skipped_dependencies` 和 `total_dependencies` 完全缺失，Service 仍会继续执行。

### 3.4 类型转换

```python
int(output.metadata.get("audited_dependencies") or 0)
```

当前会隐式接受：

```text
True  -> 1
False -> 0
"2"   -> 2
2.9   -> 2
-1    -> -1
```

当前不会区分 `bool`、字符串、浮点数。

对不可转换值：

```text
"abc"  -> ValueError
[]     -> int([] or 0) -> 0
[2]    -> TypeError
None   -> 0
```

`audited` 的转换发生在扫描 `try/except` 块之外（`try` 位于 `:287-323`，读取位于 `:325`），所以 `ValueError`/`TypeError` 不会被该块捕获。

## 4. 统计数据合法性检查

### 4.1 当前实现与目标契约对照

| 目标检查 | 当前实现 | 结论 |
|---|---|---|
| 三个字段全部存在 | 只读取 `audited_dependencies` | **缺失** |
| 严格为 `int`，拒绝 `bool` | 使用 `int()` 强制转换 | **缺失** |
| 均为非负数 | 无检查 | **缺失** |
| `total_dependencies > 0` | 不读取 `total_dependencies` | **缺失** |
| `audited + skipped == total` | 不读取两者，无检查 | **缺失** |
| 统计合法且完整才成功 | 只检查 `audited != 0` | **缺失** |

### 4.2 逐项源码证据

当前唯一校验：

```python
# :325-338
audited = int(output.metadata.get("audited_dependencies") or 0)
if audited == 0:
    return self._finish(
        ...
        ScanTaskStatus.FAILED,
        ...
        ("pip-audit 未审计到任何依赖，不能判定为无漏洞",),
        ...
    )
```

该分支只处理“审计数为零”，不处理：

```text
skipped_dependencies > 0
total_dependencies <= 0
audited + skipped != total
audited 为负数
audited 为 bool / 字符串 / 浮点数
```

## 5. 审计完整性判断

### 5.1 当前分支

存在：

```text
audited == 0 -> FAILED
```

不存在：

```text
skipped_dependencies > 0 -> FAILED
audited_dependencies != total_dependencies -> FAILED
```

### 5.2 实际处理路径

| 情形 | 当前处理 |
|---|---|
| `audited=0` | FAILED，错误 `pip-audit 未审计到任何依赖…` |
| `audited>0, skipped=0, total=audited` | COMPLETED |
| `audited>0, skipped>0, total=audited+skipped` | **COMPLETED，错误地视为成功** |
| `audited>0, total` 缺失 | **COMPLETED** |
| `audited>0, total=0` | **COMPLETED** |
| `audited>0, audited+skipped != total` | **COMPLETED** |
| 统计合法但 `skipped>0` | **COMPLETED，可能生成无漏洞摘要** |

关键结论：

```text
INCOMPLETE_AUDIT_CAN_REACH_SUCCESS = YES
```

## 6. 成功摘要生成

成功路径位于：

```text
services/dependency_audit_service.py:355-373
```

```python
warnings = list(output.warnings)
summary = (
    f"已审计 {audited} 个依赖，发现 {len(saved)} 个唯一漏洞。"
    if saved
    else f"已审计 {audited} 个依赖，未发现已知漏洞。"
)
return self._finish(
    discovery,
    selected,
    task_id,
    ScanTaskStatus.COMPLETED,
    tuple(saved),
    tuple(warnings),
    (),
    audited,
    (),
    progress=100,
    summary=summary,
)
```

实际控制流：

```text
scanner output
  -> audited = int(...)
  -> audited == 0? --yes--> FAILED
       |
       no
       v
  _map_findings()
  -> _save_findings()
  -> saved
  -> summary "已审计 N ... 未发现..."
  -> _finish(COMPLETED)
  -> UPDATE scan_tasks SET status='completed'
  -> audit.record(COMPLETED)
```

成功摘要生成前的实际检查只有：

```text
audited == 0
```

在生成成功摘要前，未检查：

```text
skipped_dependencies
total_dependencies
audited + skipped == total
```

## 7. FAILED 状态写入

### 7.1 当前会触发 FAILED 的条件

| 条件 | 位置 | 实际错误信息 |
|---|---|---|
| 取消 | `:299-303` | CANCELLED，不是 FAILED |
| 超时 | `:304-308` | `ScannerTimeoutError` 文本 |
| ScannerError | `:309-313` | `str(exc)` |
| OSError / ValidationError | `:314-318` | `str(exc)` |
| 其他 Scanner 异常 | `:319-323` | `依赖审计内部错误：...` |
| audited == 0 | `:326-338` | `pip-audit 未审计到任何依赖，不能判定为无漏洞` |
| Finding 映射/保存失败 | `:339-354` | `依赖审计结果保存失败：...` |

FAILED 最终写入点：

```text
_finish() :516-599
  -> status.value = 'failed'
  -> error_message = "；".join(errors) or "依赖审计失败"
  -> UPDATE scan_tasks ...
  -> audit.record(... 'dependency_audit_failed')
```

### 7.2 统计异常的实际路径

| 输入 | 当前路径 |
|---|---|
| `audited_dependencies` 缺失/None/0 | 转成 0 -> FAILED 分支 |
| `audited_dependencies=True` | 转成 1 -> 可进入成功路径 |
| `audited_dependencies="2"` | 转成 2 -> 可进入成功路径 |
| `audited_dependencies=2.9` | 转成 2 -> 可进入成功路径 |
| `audited_dependencies=-1` | 转成 -1 -> 不等于 0 -> 可进入成功路径 |
| `audited_dependencies="abc"` | `int()` 抛 ValueError；位于扫描 try 块外 -> 调用者收到异常，任务未写入终态 |
| `audited_dependencies=[2]` | `int()` 抛 TypeError；同样未捕获 |
| `skipped_dependencies>0` | 未读取 -> 可进入成功路径 |
| `total_dependencies=0` | 未读取 -> 可进入成功路径 |
| 三项统计不一致 | 仅检查 audited != 0 -> 可进入成功路径 |

### 7.3 异常被捕获后是否仍可能成功

```text
SCANNER_EXCEPTION_HANDLED = YES (:299-323)
STAT_METADATA_EXCEPTION_HANDLED = NO (:325)
STAT_METADATA_EXCEPTION_CAN_LEAVE_TASK_RUNNING = YES
```

`run_audit` 在 `:325` 的统计转换位于所有 `try/except` 之后；转换失败不会进入 `_finish`，任务可能保持 `running`（除非上层调用者另有处理）。

## 8. 已确认的问题

```text
SVC-01 CONFIRMED
只读取 audited_dependencies，未读取 skipped_dependencies/total_dependencies。

SVC-02 CONFIRMED
使用 int() 强制转换，接受 bool、数字字符串、浮点数；未拒绝非法类型。

SVC-03 CONFIRMED
未检查非负数、total > 0、统计总和一致性。

SVC-04 CONFIRMED
只检查 audited == 0；audited > 0 且 skipped > 0 时仍可 COMPLETED 并生成“未发现已知漏洞”摘要。

SVC-05 CONFIRMED
统计转换异常（ValueError/TypeError）位于扫描 try 块之外，可能导致任务停留在 running，未调用 _finish。

SVC-06 CONFIRMED
DependencyAuditOutcome 没有 skipped_dependencies/total_dependencies/audit_complete 字段。

SVC-07 CONFIRMED
_finish() 的 skipped 参数是未使用的 tuple[str, ...]；没有用于完整性判断。
```

## 9. 尚未确认的 UNKNOWN

```text
UNKNOWN
真实 pip-audit 在全部 skipped 场景下产生的 JSON 和退出码，本次未运行真实 pip-audit。

UNKNOWN
上层 GUI 调用者如何展示 run_audit 在 :325 抛出的未捕获异常；本次未运行 GUI，未追踪 UI 异常展示路径。

UNKNOWN
其他调用者是否直接依赖当前 audited==0 的宽松成功行为；本次只读调查未做全项目行为回归。

UNKNOWN
在生产数据库中，是否存在历史任务因该逻辑被错误标记为 COMPLETED；本次未打开数据库。
```

## 10. 最小修复方向建议

以下仅为调查建议，不是本次实施内容：

1. 在 `:325` 前增加独立统计校验函数，读取全部三个字段。
2. 使用严格类型检查，例如 `type(value) is int`，而不是 `int(value or 0)`；显式拒绝 `bool`。
3. 检查：

```text
三个字段都存在
三个字段都是 int 且不是 bool
三个字段都 >= 0
total_dependencies > 0
audited_dependencies + skipped_dependencies == total_dependencies
```

4. 统计非法时，在 Scanner try 块内或紧邻位置安全进入 `_finish(FAILED, errors=(...))`，避免任务停在 running。
5. 统计合法但：

```text
skipped_dependencies > 0
或 audited_dependencies != total_dependencies
```

应进入 `FAILED`，并写入明确错误信息；不得生成“未发现已知漏洞”摘要。
6. 只有在统计合法且 `skipped == 0`、`audited == total` 时，才进入现有成功摘要与 `_finish(COMPLETED)`。
7. 保留现有 Finding 映射/保存顺序和生命周期；不扩大 RC-01 范围，不新增状态或 Schema 迁移。

## 11. 本次边界声明

```text
STEP_3_STATUS = INVESTIGATION_COMPLETED
CODE_MODIFIED = NO
TESTS_EXECUTED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
SERVICE_MODIFIED = NO
REPOSITORY_MODIFIED = NO
SCANNER_MODIFIED = NO
GUI_MODIFIED = NO
JSON_WORK = NO
GIT_MUTATION = NO
REAL_PIP_AUDIT_EXECUTED = NO
```

本报告只基于当前实际源码和静态调用关系；未使用推测代替代码证据，未虚构行号或接口。

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```
