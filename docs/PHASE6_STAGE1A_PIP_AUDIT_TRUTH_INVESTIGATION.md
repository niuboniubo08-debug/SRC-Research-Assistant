# Phase 6 Stage 1A：pip-audit 扫描结果真实性只读调查

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：0.5.0
- Schema：v5
- 调查性质：只读；未修改生产代码、测试、README、数据库、Schema、Manifest 或 Git
- 调查时间：2026-11-13（Asia/Shanghai）
- 唯一新增文件：`docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md`
- 未运行 pytest、真实 pip-audit、GUI 或扫描器
- 未执行 Git add/commit/push/reset/restore/clean

## 0. 结论摘要

```text
STAGE1A_STATUS = COMPLETED
RC01_STATUS = CONFIRMED
CURRENT_AUDITED_SEMANTICS = INCORRECT
CURRENT_ALL_SKIPPED_RESULT = FALSE_SUCCESS (INFERRED)
FIX_IMPLEMENTED = NO
SCHEMA_CHANGE_REQUIRED = NO
```

RC-01 不是一个“可能”的推测，而是当前解析器、服务层和现有测试共同固定的行为：

1. pip-audit 的 skipped dependency 在 JSON 中只有 `name` 和 `skip_reason`，没有 `version`、`vulns`。
2. `scanners/pip_audit_scanner.py:311` 返回 `audited = len(dependencies)`，把 skipped 记录计入已审计。
3. `services/dependency_audit_service.py:325-338` 只检查 `audited == 0`；全部 skipped 时 `audited > 0`，于是继续保存并返回 `COMPLETED`。
4. 任务摘要写成“已审计 N 个依赖，未发现已知漏洞”，UI 在无 findings 时显示“当前任务未发现已知依赖漏洞。”。
5. `tests/test_pip_audit_scanner.py:53-78` 明确把 skipped 包计入 `audited == 3`，固定了错误语义。

因此，全部依赖被跳过时，当前代码路径会给出**“无漏洞”的假结论**；部分跳过时，也会把“不完整审计”显示成完整审计。该结论在静态代码层面为 `CONFIRMED`；具体运行时的任务落库结果因本轮禁止执行，标为 `INFERRED`。

## 1. 调查范围和实际读取的文件

### 1.1 读取的当前项目文件

| 文件 | 读取目的 |
|---|---|
| `scanners/pip_audit_scanner.py` | JSON 解析、计数、Finding 映射、Scanner 错误 |
| `services/dependency_audit_service.py` | 任务创建、执行、状态、摘要、持久化 |
| `tests/test_pip_audit_scanner.py` | 现有解析测试和固定行为 |
| `tests/test_dependency_audit_service.py` | 服务任务状态测试和 fake scanner |
| `tests/test_ui_dependency_audit.py` | UI 成功状态、空结果文案 |
| `scanners/base.py` | `ScanOutput`、异常层次、扫描器接口 |
| `core/models/enums.py` | `ScanTaskStatus` 及标签 |
| `core/models/scan_task.py` | 任务持久字段和展示字段 |
| `ui/dependency_page.py` | 结果表、空状态、警告、任务摘要 |
| `core/models/finding.py` | Finding 字段与 metadata 传递 |

### 1.2 为确认 `skip_reason` 语义读取的 pip-audit 包源

仅读取已安装 `pip-audit 2.10.1` 的实现，未执行扫描：

| 文件 | 作用 |
|---|---|
| `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_format\json.py` | JSON 输出格式；skipped 记录不包含 version/vulns |
| `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_service\pypi.py` | PyPI 404 -> `SkippedDependency` |
| `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_dependency_source\pip.py` | editable / 无法解析版本 -> skipped |
| `D:\挖漏洞\.venv\Lib\site-packages\pip_audit\_format\columns.py` | skipped 的展示语义 |

### 1.3 本轮未读取/未验证的内容

- 未运行真实 pip-audit，因此没有本轮的新 JSON 样本。
- 未运行 GUI，因此没有本轮 UI 状态截图。
- 未查询数据库当前行数；本报告不把历史数据库状态当作本次运行结果。
- 未验证网络/索引错误时 pip-audit 的具体退出码和 stdout 组合；该部分标为 `UNKNOWN`/`INFERRED`。

## 2. Scanner 解析流程

### 2.1 入口

`scanners/pip_audit_scanner.py:126-208` 的 `scan()`：

1. `target_path = Path(target).expanduser().resolve()`；必须是文件，否则 `ScannerExecutionError`。
2. `is_available()` 验证模块、可执行文件、`--version`。
3. 创建 `cache_dir` / `temp_dir`。
4. 构造固定参数列表，`shell=False`，包括 `-r`、`--format json`、`--timeout`、`--desc on`、`--aliases on`、`--vulnerability-service pypi`、`--cache-dir`。
5. 调用 `run_command()`；取消 -> `ScanCancelled`；超时 -> `ScannerTimeoutError`。
6. 空 stdout -> `ScannerExecutionError`。
7. 返回码只接受 `0` 和 `1`；其他值 -> `ScannerExecutionError`。
8. `parse_output()`；输出截断时追加 warning。
9. `ScanOutput.metadata` 只写入 `returncode`、`duration_seconds`、`audited_dependencies`、`vulnerability_service`。

**分类**：`CONFIRMED`（代码路径）。

### 2.2 `parse_output()` 的当前步骤

`scanners/pip_audit_scanner.py:210-311`：

1. `json.loads`；失败 -> `ScannerParseError`。
2. 顶层必须是 dict，且 `dependencies` 是 list；否则 `ScannerParseError`。
3. 遍历 `dependencies`：
   - 非 dict -> 直接 `continue`，但最终计数仍包含它；
   - 读取 `name`、`version`、`skip_reason`；
   - 有 `skip_reason` -> 追加一句 warning，继续；
   - `vulns` 不是 list -> `continue`；
   - 对每个 vuln 构造 Finding；
   - 按 `(name.lower(), vuln_id)` 去重；
   - 无 `severity` / `cvss` / `cvss_score` 时使用 `MEDIUM`，并标记 `severity_source=conservative-default`。
4. 返回 `(findings, warnings, len(dependencies))`。

关键点：`len(dependencies)` 是**输入数组长度**，不是“完成审计的依赖数”。它同时包含：

- 正常解析的依赖；
- 带 `skip_reason` 的依赖；
- 非 dict 的异常项；
- 缺少 `vulns` 的异常项（仍会被计入）。

**分类**：`CONFIRMED`。

### 2.3 `skip_reason` 的真实含义

pip-audit 2.10.1 的 JSON 格式化代码 `_format/json.py:59-74`：

```python
if dep.is_skipped():
    return {
        "name": dep.canonical_name,
        "skip_reason": dep.skip_reason,
    }
```

skipped 记录**没有 `version` 和 `vulns`**。`_service/pypi.py:78-86` 在 PyPI 返回 404 时创建：

```text
Dependency not found on PyPI and could not be audited: <name> (<version>)
```

`_dependency_source/pip.py` 还会因 editable、无法从 URL 推导版本等原因产生 skipped。其共同含义是：**该依赖没有被完整查询漏洞数据，因此不能算已审计**。

**分类**：`CONFIRMED`（包源 + 当前测试样本 `skipped-package`）。

### 2.4 当前 warning 与 Finding

- skipped 只会生成 warning，不会生成 Finding。
- `warnings` 是字符串元组；没有结构化的 `skipped_dependencies` 计数。
- `ScanOutput` 没有 `audit_complete` 字段。
- `Finding.metadata` 里没有 skipped 状态；Finding 只对应实际发现的漏洞。

因此，后续服务层只能看到 `audited` 总数和字符串 warnings，无法可靠区分“正常 0 漏洞”和“所有依赖都跳过”。

## 3. DependencyAuditService 调用链

### 3.1 完整链路

```text
DependencyPage._start_audit
  -> DependencyAuditWorker
  -> DependencyAuditService.run_audit(project_id, dependency_path, timeout)
  -> discover(project_id)
     -> ProjectService.get_project
     -> ScopeValidator.check_local_path(operation="dependency_audit")
     -> requirements.txt / pyproject.toml 发现
  -> _create_task(status='pending')
  -> scanner_info() (pip-audit 可用性)
  -> _mark_running(status='running')
  -> _prepared_input (pyproject -> 临时 requirements)
  -> PipAuditScanner.scan(target, ScanOptions)
     -> run_command
     -> PipAuditScanner.parse_output
     -> ScanOutput(findings, warnings, metadata.audited_dependencies)
  -> _map_findings (相对路径/行号)
  -> _save_findings(project_id, task_id)
  -> _finish(status=COMPLETED, findings, warnings, errors)
     -> UPDATE scan_tasks
     -> AuditLogService.record
  -> DependencyAuditOutcome
  -> UI _on_completed / _update_task_display / _refresh_findings
```

### 3.2 服务层的计数和状态

`services/dependency_audit_service.py:325-338`：

```python
audited = int(output.metadata.get("audited_dependencies") or 0)
if audited == 0:
    return self._finish(..., ScanTaskStatus.FAILED, ..., "pip-audit 未审计到任何依赖，不能判定为无漏洞")
```

`services/dependency_audit_service.py:339-372`：

```python
mapped = self._map_findings(...)
saved = self._save_findings(...)
warnings = list(output.warnings)
summary = (
    f"已审计 {audited} 个依赖，发现 {len(saved)} 个唯一漏洞。"
    if saved
    else f"已审计 {audited} 个依赖，未发现已知漏洞。"
)
return self._finish(..., ScanTaskStatus.COMPLETED, ..., audited, ...)
```

当前只有一条“审计数 == 0”的失败门禁；没有“skipped > 0”或“audit_complete == False”的门禁。

**分类**：`CONFIRMED`。

### 3.3 `_finish()` 的当前行为

`services/dependency_audit_service.py:516-599`：

- `COMPLETED`：摘要使用传入 summary 或默认“已审计 N ...未发现/发现 M”；
- `CANCELLED`：摘要“已取消；保留 N 结果”；
- 其他（含 FAILED）：摘要“失败；保留 N 结果”，`error_message` 来自 errors；audit log decision=`error`；
- 有一个 `skipped: tuple[str, ...]` 参数，但当前调用方全部传空 tuple，函数内部也**没有使用**该参数写入任务或摘要；
- `DependencyAuditOutcome` 只有 `audited_dependencies`、`warnings`、`errors`，没有 `skipped_dependencies`、`total_dependencies`、`audit_complete`。

**分类**：`CONFIRMED`。

### 3.4 状态枚举

`core/models/enums.py:269-286` 只有：

```text
PENDING / RUNNING / COMPLETED / FAILED / CANCELLED / BLOCKED
```

没有 `PARTIAL` 或 `COMPLETED_WITH_WARNINGS`。因此“部分跳过”无法用现有状态精确表达；本报告的推荐方案见第 8 节。

## 4. audited、skipped、vulnerability 的当前计算规则

| 指标 | 当前来源 | 当前语义 | 问题 |
|---|---|---|---|
| `total` | `len(payload["dependencies"])`（隐式） | 数组元素数，含非 dict/异常记录 | 未落库、未展示 |
| `audited` | `len(dependencies)` (`pip_audit_scanner.py:311`) | 数组长度，不是完成审计的依赖数 | 把 skipped/异常算作已审计 |
| `skipped` | 没有结构化计数；只有 warnings 文本 | 仅用于提示 | 无法汇总、无法做门禁 |
| `vulnerabilities` | `len(saved)`，dedupe `(name.lower(), vuln_id)` | 唯一漏洞 Finding 数 | 正确，但不能替代依赖审计完整性 |
| `audit_complete` | 不存在 | 不存在 | 无法区分“0 漏洞”与“未审计” |
| `task_success` | `task.status is COMPLETED` | 只看状态 | 全部 skipped 也是 COMPLETED |
| UI 空结果 | `task.status is COMPLETED and not findings` (`ui/dependency_page.py:708-711`) | 显示“当前任务未发现已知依赖漏洞。” | 不完整审计也显示“无漏洞” |

**分类**：`CONFIRMED`（代码）；具体任务落库为 `INFERRED`（未执行）。

## 5. 全部跳过时的实际任务状态

### 5.1 代码推导

假设 pip-audit JSON：

```json
{
  "dependencies": [
    {"name": "A", "skip_reason": "Dependency not found on PyPI..."},
    {"name": "B", "skip_reason": "failed to resolve"}
  ],
  "fixes": []
}
```

1. `parse_output` 对每条追加 warning；
2. `dependencies` 没有 `vulns`，不会产生 Finding；
3. 返回 `audited = 2`；
4. 服务 `audited != 0`，不进入 FAILED 门禁；
5. 保存 0 条 Finding；
6. `summary = "已审计 2 个依赖，未发现已知漏洞。"`；
7. `status = COMPLETED`；
8. UI 状态为“已完成”，空结果文案为“当前任务未发现已知依赖漏洞。”；
9. `_on_completed` 会把 warnings 放进 `error_label`，但 `_update_task_display` 再次读取任务时只显示 `result_summary`，warning 不再持久存在。

**分类**：`INFERRED`（由静态代码路径推导，未运行）；解析器的 `audited=2` 部分为 `CONFIRMED`。

### 5.2 与真正的“0 个依赖”区分

如果 `dependencies` 是空数组：

- `parse_output` 返回 `audited=0`；
- 服务进入 `if audited == 0`，任务 FAILED，错误为“pip-audit 未审计到任何依赖，不能判定为无漏洞”。

所以当前代码已经区分了“空依赖列表”，但没有区分“有依赖、全部 skipped”。这正是 RC-01 的核心。

### 5.3 部分跳过

部分 skipped 时：

- `audited` 仍等于全部依赖数；
- 若正常依赖有漏洞，summary 写成“已审计 N 个依赖，发现 M 个唯一漏洞”，N 包含 skipped；
- 若正常依赖 0 漏洞，summary 写成“已审计 N 个依赖，未发现已知漏洞”，忽略 skipped；
- 状态仍为 COMPLETED。

**分类**：`INFERRED`。

### 5.4 非 dict / 缺 vulns 项

`parse_output` 对非 dict 直接 `continue`，但最终 `len(dependencies)` 包含它；缺 `vulns` 的 dict 也被计入。结果是：

- `audited` 可能大于实际可审计记录数；
- 不会产生 warning；
- 服务仍可能 COMPLETED。

**分类**：`CONFIRMED`（代码）；实际出现频率 `UNKNOWN`。

## 6. 现有测试的问题及证据

### 6.1 `tests/test_pip_audit_scanner.py:53-78`

fixture 包含：

```python
{
    "name": "skipped-package",
    "version": "0.1",
    "vulns": [],
    "skip_reason": "failed to resolve",
}
```

测试断言：

```python
findings, warnings, audited = scanner.parse_output(payload, target, "2.10.1")
assert audited == 3
```

该断言把 `requests`（正常）、`safe-package`（正常）、`skipped-package`（跳过）三者都算作已审计。它与 pip-audit 的 skipped 语义冲突，**固定了 RC-01 的错误行为**。

**分类**：`CONFIRMED`。

### 6.2 服务层测试没有覆盖真实 skipped

`tests/test_dependency_audit_service.py`：

- `FakePipAuditScanner` 的 `audited` 是人为传入整数（`:67`、`:97-98`）；
- `test_completed_dependency_audit_persists_finding_and_metadata`（`:173-204`）用 `audited=3` 和一个 Finding；
- `test_empty_dependency_result_is_completed`（`:207-218`）用 `audited=1` 和空 findings；
- `test_zero_audited_dependencies_is_failure_not_success`（`:221-237`）只测试 `audited=0`；
- 没有测试“`dependencies` 全部带 `skip_reason` → 服务 FAILED”；
- 没有测试“部分 skip → 不完整/失败/保留 Finding”。

**分类**：`CONFIRMED`（测试静态检查）；没有运行测试。

### 6.3 UI 测试没有覆盖空结果/不完整

`tests/test_ui_dependency_audit.py` 的 fake scanner：

```python
return ScanOutput(
    findings=(finding,),
    metadata={"audited_dependencies": 2},
)
```

它只覆盖有 Finding 的成功场景，没有覆盖：

- 全部 skipped、0 Finding；
- 部分 skipped、仅正常依赖有 Finding；
- 任务摘要为“未发现”但审计不完整；
- UI 的空状态文案。

**分类**：`CONFIRMED`（测试静态检查）。

### 6.4 目前正确的测试

`test_pip_audit_empty_result`（`:97-104`）对空列表 `audited == 0` 正确；`test_zero_audited_dependencies_is_failure_not_success` 对服务层 `audited=0` 正确；`test_pip_audit_bad_json`（`:107-112`）正确断言 parse error。这些测试不需要降低强度，只需补充 skipped 语义。

## 7. 六种场景：当前行为与建议行为

| 场景 | 当前实际（代码推导） | 当前问题 | 建议语义 | 建议任务状态 |
|---|---|---|---|---|
| **A. 全部正常审计，0 漏洞** | `audited=total`、findings=0，COMPLETED，摘要“未发现已知漏洞” | 语义正确 | `audited=total`，`skipped=0`，`audit_complete=True`，`vulnerability_count=0` | COMPLETED |
| **B. 全部正常审计，有漏洞** | `audited=total`，findings>0，COMPLETED，摘要“发现 M” | 语义正确 | 同上，`vulnerability_count=M` | COMPLETED |
| **C. 部分 skip，其他正常** | `audited=total`（错），findings 取决于正常项，COMPLETED；warning 只显示一次 | 不完整审计被当完整成功 | `audited=normal`、`skipped>0`、`audit_complete=False`、`vulnerability_count=正常项发现数` | 推荐 `FAILED`（保留可验证 Finding）；或经批准新增 `PARTIAL` 状态 |
| **D. 全部 skip** | `audited=total>0`，findings=0，COMPLETED，摘要“未发现”，UI“无漏洞” | **假成功** | `audited=0`、`skipped=total`、`audit_complete=False` | `FAILED` |
| **E. pip-audit 网络/索引错误** | 空 stdout 或返回码不在 0/1 -> `ScannerExecutionError` -> FAILED；若 pip-audit 输出“skipped”且返回 0/1，则走 C/D | 错误是否被吞掉取决于工具输出；`UNKNOWN` | 不把任何 skipped/网络失败当完整审计；记录 warning/错误 | FAILED（或明确的不完整失败） |
| **F. JSON 格式错误/解析失败** | `ScannerParseError` -> 服务 `ScannerError` -> FAILED，无 Finding | 正确 | `parse_error` -> `audit_complete=False`；不保存伪结果 | FAILED |

**重点**：当前 A/B 是正确的；C/D 是错误的“COMPLETED”；E/F 大体是 FAILED，但 E 的 skipped 分支可能退化为 D。

## 8. 建议的最小修复范围

### 8.1 设计原则

1. **只有真正完成漏洞查询的依赖才算 audited**：有 version、有 `vulns` 列表、无 `skip_reason`。
2. **skipped 必须结构化计数**，不能只放在字符串 warning 里。
3. **audit_complete 必须独立于 vulnerability_count**：0 Finding 不等于完整审计。
4. **不新增数据库字段/Schema**；使用 `ScanOutput.metadata`、`DependencyAuditOutcome` 和 `result_summary` 承载。
5. **默认 fail-closed**：不完整审计不得显示“无漏洞”；推荐直接 FAILED，保留已发现的有效 Finding。
6. 不改变 Finding 的漏洞字段和去重规则。

### 8.2 Scanner 层

`scanners/pip_audit_scanner.py`：

- 在遍历时分别计数：
  - `total_dependencies`：所有 dict 记录；
  - `skipped_dependencies`：有 `skip_reason` 的记录；
  - `audited_dependencies`：无 skip、有 version、有 `vulns` 列表的记录；
  - `invalid_dependencies`：非 dict、缺 name/version/vulns 且无 skip 的记录。
- `parse_output()` 返回结构化结果（推荐小 dataclass `PipAuditParseResult`，或至少增加 skipped/total 两个返回值）。为最小改动可保留三元组并在 `ScanOutput.metadata` 写四个计数，但测试可读性较差。
- `ScanOutput.metadata` 增加：
  - `audited_dependencies`
  - `skipped_dependencies`
  - `total_dependencies`
  - `audit_complete`
- warnings 保留具体 skip 原因，但不再承担计数职责。

**不需要**新表、新列或迁移。

### 8.3 Service 层

`services/dependency_audit_service.py`：

- 读取三个计数，不再只读 `audited`。
- 新增门禁：
  - `total == 0`：FAILED（现有 `audited == 0` 保留）。
  - `skipped > 0` 或 `audit_complete == False`：不得 COMPLETED。
  - `audited == 0`：FAILED。
- 推荐策略（无 Schema 变更）：
  - **C/D 全部映射为 FAILED**，错误写“审计不完整：已审计 X/Y，跳过 Z，不能判定为无漏洞”。
  - 对有正常 Finding 的 C，先保存有效 Finding，再以 FAILED 结束；UI 显示失败但保留结果，符合现有 SourceAudit 的“失败保留结果”模式。
  - 如果产品明确希望“部分成功”，再单独批准 `PARTIAL`/`COMPLETED_WITH_WARNINGS` 状态；不在本最小修复内做。
- `DependencyAuditOutcome` 增加（仅内存）：
  - `total_dependencies`
  - `skipped_dependencies`
  - `audit_complete`
- `_finish()` 中未使用的 `skipped` 参数改为实际使用，或删除以避免误导；audit log details 增加 `skipped_dependencies`/`audit_complete`。
- `result_summary` 统一写成：
  - A/B：`已审计 {audited}/{total} 个依赖，发现 {n} 个唯一漏洞。`
  - C/D：`审计不完整：已审计 {audited}/{total}，跳过 {skipped}，不能判定为无漏洞。`

### 8.4 UI 层

`ui/dependency_page.py`：

- 空结果文案只在 `status == COMPLETED and audit_complete and not findings` 时显示“未发现”。
- FAILED 或 `audit_complete == False` 时显示“审计不完整/未完成”，不得显示“当前任务未发现已知依赖漏洞”。
- warning 不能只放在 `_on_completed` 的临时 `error_label`；`result_summary` 必须持久化计数，reload 后仍能看到“跳过 N”。
- 仍保留现有状态标签；不需要新的数据库列。

### 8.5 最小修改文件

| 文件 | 修改 |
|---|---|
| `scanners/pip_audit_scanner.py` | 计数 + 结构化 metadata |
| `services/dependency_audit_service.py` | 门禁、摘要、outcome、audit details |
| `ui/dependency_page.py` | 空状态/不完整文案 |
| `tests/test_pip_audit_scanner.py` | 修正旧的 `audited == 3` 断言 |
| `tests/test_dependency_audit_service.py` | all-skip/partial/正常/网络/解析用例 |
| `tests/test_ui_dependency_audit.py` | 不完整结果 UI 文案用例 |

**不修改**：数据库 Schema、`scan_tasks` 表、`findings` 表、README、Manifest、报告核心、PDF/JSON。

## 9. 建议新增或调整的测试

### 9.1 Parser 测试

1. 更新 `test_pip_audit_json_parsing_dedupes_and_maps_metadata`：
   - `audited == 2`（requests、safe-package）；
   - `skipped == 1`（skipped-package）；
   - `warnings` 含 `failed to resolve`。
2. 新增全部 skip：`dependencies` 两条带 `skip_reason`、无 `vulns` -> `audited=0`、`skipped=2`、`audit_complete=False`。
3. 新增部分 skip：正常有 Finding + skipped -> `audited=1`、`skipped=1`，Finding 保留。
4. 新增非 dict/缺 `vulns`：`total`、`invalid` 计数明确，不混入 audited。
5. 新增 `{"dependencies":[]}` -> `audited=0`，保持现有空结果语义。
6. 新增 `skip_reason` 但 `vulns` 存在（防御性）-> 不计 audited，记录 warning。

### 9.2 Service 测试

1. 全部 skip -> `status is FAILED`，`error_message` 含“不完整/未审计到任何依赖”，无“未发现”摘要。
2. 部分 skip -> 推荐 FAILED；若产品改为 PARTIAL，则测试不完整标志与 Finding 保留。
3. 正常 0 漏洞 -> COMPLETED，summary 含 `audited/total`，无 skipped。
4. 正常有漏洞 -> COMPLETED，Finding 持久化、项目隔离。
5. 网络错误/空 stdout -> FAILED，无“成功”。
6. 解析错误 -> FAILED。
7. `test_zero_audited` 保留，并增加真实 skipped 数据，而不是只传 fake `audited=0`。

### 9.3 UI 测试

1. 全部 skip：状态不是“已完成”，空状态不是“未发现已知依赖漏洞”，显示不完整/失败。
2. 部分 skip + 正常 Finding：状态/摘要明确“不完整”，Finding 仍可见。
3. 正常 0 漏洞：才显示“未发现已知依赖漏洞”。
4. reload 后摘要仍保留 skipped 计数（不是只依赖一次性 warning）。

### 9.4 测试约束

- 不降低现有断言强度；只修正错误期望。
- 不删除 `test_zero_audited_dependencies_is_failure_not_success`。
- 不把 skip 测试改成无条件 skip；如 Windows 权限限制，只对 symlink 相关测试 skip。

## 10. 未确认事项和证据限制

| 事项 | 结论 | 原因 |
|---|---|---|
| 全部 skip 的实际数据库状态 | `INFERRED` | 未运行真实 pip-audit；静态路径确定但未执行 |
| 网络/索引错误时的 pip-audit exit/stdout 组合 | `UNKNOWN` | 依赖 pip-audit 版本、网络、索引；本轮禁止运行 |
| 部分 skip 的 UI 实际显示 | `INFERRED` | 代码路径明确，但未启动 GUI |
| `skipped_dependencies` 是否应持久化到 tasks 表 | `UNKNOWN`/设计选择 | 本报告建议不新增 Schema；可用 summary/details |
| 历史真实 19 个漏洞回归 | `HISTORICAL_ONLY` | 不能当作本轮扫描结果 |
| 现有全量测试当前是否通过 | `UNKNOWN` | 本轮禁止运行 pytest |
| `skip_reason` 的具体种类覆盖 | `CONFIRMED`（已读包源） | PyPI 404、editable、URL/版本不可解析等可能 |
| 是否存在其他路径把 skipped 算入 audited | `UNKNOWN` | 只检查了 pip-audit scanner 和 dependency service |

## 11. 本次文件变化

- 新增：`docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md`。
- 生产代码：未修改。
- 测试：未修改。
- README/配置/数据库/Schema/Manifest/历史归档：未修改。
- 未运行 pytest、真实 pip-audit、GUI、扫描器。
- 未执行 Git add/commit/push/reset/restore/clean；未暂存任何文件。

## 12. Git 状态和数据库状态

### 12.1 Git 只读记录

报告生成前：

```text
BRANCH=main
HEAD=bffb5ac82bbebe7fef5992f87ff90494c9776ace
COMMIT_COUNT=8
STAGED=0
UNSTAGED=M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
AHEAD=5
BEHIND=0
```

未跟踪报告（报告生成前 7 个，生成后 8 个）：

- `docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`
- `docs/PHASE6_D1B_3_JSON_DECISION.md`
- `docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md`
- `docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md`
- `docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md`
- `docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md`
- `docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md`
- 本报告（新增）

**分类**：`CONFIRMED`（只读 Git 命令）。

### 12.2 数据库

- 未打开、未查询、未写入数据库；本轮没有新的 DB 行数/完整性结果。
- 未执行 Schema 迁移；v5 保持不变。
- 未修改 `scan_tasks`、`findings` 或任何历史验收库。
- 未来修复不需要新增数据库字段；如实现时决定持久化 skipped/total，必须另立 Schema 设计任务，不能顺手迁移。

### 12.3 最终状态

```text
PIP_AUDIT_TRUTH_INVESTIGATION = COMPLETED
RC01_DEFECT_CONFIRMED = YES
CURRENT_ALL_SKIPPED_RESULT = FALSE_SUCCESS (INFERRED)
RECOMMENDED_POLICY = FAIL_CLOSED_ON_INCOMPLETE_AUDIT
CODE_MODIFIED = NO
TEST_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
TESTS_RUN = NO
GIT_MUTATION = NO
```

**结论**：RC-01 已确认。当前最小修复方向是“把 skipped 从 audited 中剥离、增加 audit_complete 门禁、在无 Schema 变更的前提下 fail-closed”，而不是继续把 `len(dependencies)` 当作已审计数量。等待人工审核后再决定是否进入 Stage 1B 实施。
