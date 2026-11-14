# Phase 6 Stage 1B-2A：RC-01 精确测试修改范围调查

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：0.5.0
- Schema：v5
- 已批准规则：审计不完整 → FAILED；不得把不完整审计表达为“未发现漏洞”；不新增任务状态；不修改 Schema
- 调查性质：READ_ONLY
- 未修改任何文件（本报告除外）
- 未运行 pytest、pip-audit 或 GUI

## 1. 调查范围、读取文件和结论边界

### 1.1 实际读取

| 文件 | 读取原因 |
|---|---|
| `tests/test_pip_audit_scanner.py` | 解析器直接测试、skipped fixture、错误测试 |
| `tests/test_dependency_audit_service.py` | fake scanner、任务状态、摘要、正常/零审计测试 |
| `tests/test_ui_dependency_audit.py` | 唯一直接 UI 依赖审计测试；回答“是否需要修改 UI 测试” |
| `docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md` | 已批准规则和测试契约 |
| `scanners/pip_audit_scanner.py` | 现有返回值/统计实现，用于预测失败 |
| `services/dependency_audit_service.py` | 现有任务状态和摘要实现，用于预测失败 |

本轮未读取数据库、未执行 SQL、未运行测试、未修改代码。

### 1.2 证据标签

- **CONFIRMED**：当前测试/代码静态可见的事实。
- **PREDICTED**：基于当前代码对测试执行的预测，不是实际运行结果。
- **PROPOSED**：未来测试契约/建议。
- **UNKNOWN**：缺少运行证据。

### 1.3 关键前置条件

当前 `PipAuditScanner.parse_output()` 返回三元组 `(findings, warnings, audited)`，没有 skipped/total 字段。要让测试验证“全部 skipped 不计入 audited”，生产实现必须在未来 Stage 1B 中提供可读取的 `skipped_dependencies`/`total_dependencies`（例如具名解析结果、`ScanOutput.metadata` 或等价的稳定接口）。

本报告假设 Stage 1B 实施会提供这些计数；**如果实施不提供，TC-03/TC-04 无法按契约断言**。该假设是 `PROPOSED`，不是已批准 API。

## 2. 必须修改的现有测试文件及具体断言

### 2.1 `tests/test_pip_audit_scanner.py`

#### 测试：`test_pip_audit_json_parsing_dedupes_and_maps_metadata`

位置：`tests/test_pip_audit_scanner.py:71-94`；fixture 在 `:22-61`。

当前 fixture 包含：

- `requests`：正常，2 个去重后 Finding；
- `safe-package`：正常，0 Finding；
- `skipped-package`：`skip_reason="failed to resolve"`，无有效 version/vulns 语义。

当前断言：

```python
findings, warnings, audited = scanner.parse_output(payload, target, "2.10.1")
assert audited == 3
```

必须改为（`PROPOSED_CONTRACT`）：

```python
result = scanner.parse_output(payload, target, "2.10.1")
assert result.audited == 2
assert result.skipped == 1
assert result.total == 3
assert result.audit_complete is False
assert len(result.findings) == 2
assert "failed to resolve" in " ".join(result.warnings)
```

如果最终实现采用四元组而非具名对象，则解包和属性访问需相应调整；测试不应通过解析 warning 字符串来推断 skipped 数量。**具体 API 是 Stage 1B 实施决策，不应由测试反向妥协统计语义。**

必须改变的断言：

- `audited == 3` → `audited == 2`；
- 增加 `skipped == 1`；
- 增加 `total == 3`；
- 增加 `audit_complete is False`（因为此 fixture 是部分 skipped）；
- 现有 `len(findings) == 2`、metadata、warning、scanner name/version 断言保持不变。

#### 测试：`test_pip_audit_empty_result`

位置：`tests/test_pip_audit_scanner.py:97-104`。

当前解包三元组并断言 `audited == 0`。未来应改为：

```python
result = scanner.parse_output(...)
assert result.findings == []
assert result.warnings == []
assert result.audited == 0
assert result.skipped == 0
assert result.total == 0
assert result.audit_complete is False
```

行为断言（空结果、无 warning、audited=0）保持不变；需要适配返回值形状并增加 `audit_complete=False`。这是 **契约增加**，不是降低原断言。

#### 不需要断言修改的测试

- `test_pip_audit_bad_json`：仍应抛 `ScannerParseError`，无需改断言。
- `test_pip_audit_unavailable_when_module_missing`：不涉及 parse 计数。
- `test_pip_audit_actual_available`：不涉及 parse 计数。
- `test_pip_audit_execution_failure_timeout_and_cancel`：仍应抛执行/超时/取消异常。
- `test_pip_audit_scan_requires_available_tool`：不变。
- `test_pip_audit_severity_mapping`：不变。

### 2.2 `tests/test_dependency_audit_service.py`

#### 2.2.1 `FakePipAuditScanner`（测试 fixture）

位置：`tests/test_dependency_audit_service.py:55-99`。

当前 `scan()` 只写：

```python
metadata={"audited_dependencies": self._audited}
```

必须扩展为可表达完整/不完整：

```python
metadata={
    "audited_dependencies": self._audited,
    "skipped_dependencies": self._skipped,
    "invalid_dependencies": self._invalid,
    "total_dependencies": self._total,
    "audit_complete": self._audit_complete,
}
```

建议构造参数：

```python
audited: int = 3,
skipped: int = 0,
invalid: int = 0,
total: int | None = None,
audit_complete: bool | None = None,
```

默认兼容现有正常场景：`total = audited + skipped + invalid`；`audit_complete = skipped == 0 and invalid == 0 and total > 0`。这样可以避免每个旧测试都被迫改写，同时显式提供 skipped 场景。

该 fixture 修改属于测试基础设施修改，不是降低断言强度。

#### 2.2.2 `test_completed_dependency_audit_persists_finding_and_metadata`

位置：`:173-204`。

- 构造 `FakePipAuditScanner(findings=(make_finding(),), audited=3)`；
- 当前断言 `outcome.audited_dependencies == 3`（`:191`）。

若 fake 默认 `total=3, skipped=0, complete=True`，现有断言 `COMPLETED`、`audited==3`、Finding 持久化、项目/任务 ID 均**不需要改变**。建议增加：

```python
assert outcome.audit_complete is True
assert outcome.skipped_dependencies == 0
```

这是新增契约断言，不是修改已通过的核心行为。

#### 2.2.3 `test_empty_dependency_result_is_completed`

位置：`:207-218`。

当前 `audited=1`、0 Finding，断言 COMPLETED 且摘要含“未发现已知漏洞”。在已批准规则下，这属于“全部正常、0 漏洞”，应继续保持 COMPLETED；断言不需要改变。建议把 fake 明确设为 `total=1, skipped=0, complete=True`，并增加 `audit_complete is True` 断言。

#### 2.2.4 `test_zero_audited_dependencies_is_failure_not_success`

位置：`:221-237`。

当前 `audited=0`，断言 `FAILED` 且错误消息含“未审计到任何依赖”。

这仍然正确；**不应删除或弱化**。但 fake 必须表达 `total=0`/不完整；如果实现把零审计错误文案改为“没有可审计依赖”，应保留“未审计到任何依赖”作为兼容消息，或明确更新此断言。为最小变更，建议保留现有错误文本。

#### 2.2.5 必须新增的服务测试

见第 3 节；这些测试需要修改/扩展本文件。

### 2.3 `tests/test_ui_dependency_audit.py`

见第 6 节。结论：**需要新增一个不完整 UI 测试；现有成功测试的断言可不变，但 fake `UiFakeScanner` 的 metadata 需要补齐。**

## 3. 必须新增的测试场景

### 3.1 Scanner 测试

| 测试名（建议） | 场景 | 核心断言 |
|---|---|---|
| `test_pip_audit_all_skipped_is_not_audited` | D 全部 skipped | `audited=0`、`skipped=N`、`total=N`、`findings=[]`、`audit_complete=False`；warning 含原因 |
| `test_pip_audit_partial_skip_counts_and_findings` | C 部分 skipped | `audited=N-S`、`skipped=S`、`total=N`、Findings 保留、`complete=False` |
| `test_pip_audit_invalid_dependencies_are_not_audited` | 非 dict/缺 `vulns` | `invalid>0`、`audited` 不增加、`complete=False` |
| `test_pip_audit_skip_reason_with_vulns_is_not_audited` | 防御性 skipped + vulns | skipped 优先，不计 audited；不生成不完整 Finding |
| `test_pip_audit_empty_result`（现有测试扩展） | E 空列表 | `total=0`、`audited=0`、`complete=False`，仍 `findings=[]` |

### 3.2 Service 测试

| 测试名（建议） | 场景 | 核心断言 |
|---|---|---|
| `test_all_skipped_dependency_audit_fails_without_no_vuln_claim` | D | `outcome.failed is True`、`status is FAILED`、`success is False`；摘要/错误含“不完整/未审计”；不含“未发现已知漏洞” |
| `test_partial_skipped_dependency_audit_fails_and_keeps_findings` | C | `FAILED`；正常项 Finding 仍持久化；摘要含 `audited/total` 和 skipped；不显示“未发现” |
| `test_completed_audit_summary_reports_audited_and_total` | A/B | `COMPLETED`、`audit_complete=True`；摘要含 N/N；0 漏洞仍可显示“未发现” |
| `test_skipped_count_is_persisted_in_result_summary` | C/D | 重新读取 latest task 后仍能读到 skipped/不完整摘要，不只依赖一次性 warning |
| `test_empty_audit_cannot_be_success` | E | 保持/加强现有 `audited==0` 失败测试；错误不含“未发现漏洞” |
| `test_execution_error_does_not_become_success` | F | FAILED，不含“未发现” |
| `test_parse_error_does_not_become_success` | G | FAILED，无 Finding |

### 3.3 UI 测试

| 测试名（建议） | 场景 | 核心断言 |
|---|---|---|
| `test_incomplete_dependency_audit_does_not_claim_no_vulnerabilities` | C/D | 状态为 FAILED；页面不出现“当前任务未发现已知依赖漏洞”；显示“审计不完整/失败”及 skipped 信息 |
| `test_completed_zero_vulnerability_shows_no_vulnerabilities` | A | COMPLETED + complete + 0 Finding 时才显示“未发现” |
| `test_ui_fake_scanner_metadata_covers_audit_complete` | fixture 前置 | fake metadata 明确 total/skipped/complete，避免依赖生产默认值 |

## 4. 应保持完全不变的测试

### 4.1 Scanner

- `test_pip_audit_bad_json`
- `test_pip_audit_unavailable_when_module_missing`
- `test_pip_audit_actual_available`
- `test_pip_audit_execution_failure_timeout_and_cancel`
- `test_pip_audit_scan_requires_available_tool`
- `test_pip_audit_severity_mapping`

这些测试不涉及“skipped 计入 audited”，不应被本轮修改牵连。

### 4.2 Service

以下测试应保持断言不变：

- `test_requirements_discovery`
- `test_pyproject_discovery`
- `test_both_dependency_files_prefer_requirements`
- `test_no_dependency_file`
- `test_pip_audit_unavailable_marks_task_failed_without_findings`
- `test_execution_failure_and_timeout_are_failed`
- `test_cancelled_dependency_audit_is_not_completed`
- `test_cancel_before_start_marks_cancelled`
- `test_pyproject_is_prepared_as_temporary_requirements_and_cleaned`
- `test_dependency_project_isolation`
- `test_unregistered_path_is_rejected`
- `test_invalid_pyproject_is_not_auditable`

其中 `test_pip_audit_unavailable...` 的 fake fixture 可保持默认 normal counts；不需要新增 skipped。

### 4.3 Service 中只改 fixture、不改核心断言的测试

- `test_completed_dependency_audit_persists_finding_and_metadata`
- `test_empty_dependency_result_is_completed`
- `test_zero_audited_dependencies_is_failure_not_success`

它们可以使用新 fake 构造参数的默认值；核心业务断言保持。允许增加 `audit_complete`/`skipped` 断言，但不得删除现有断言。

### 4.4 UI

- `test_dependency_page_runs_fake_pip_audit_and_displays_result` 的核心断言（COMPLETED、1 Finding、表格内容）保持不变；
- 只允许补齐 fake metadata 以符合新契约。

## 5. 当前生产代码预计会在哪些新测试上失败（PREDICTED）

> 以下全部是 **PREDICTED**，不是本轮实际 pytest 结果；本轮没有运行测试。

| 新/改测试 | 当前生产代码的预测结果 | 原因 |
|---|---|---|
| 修改后的 `test_pip_audit_json_parsing_dedupes_and_maps_metadata` | **FAIL** | 当前 `audited == 3`，新契约期望 `2`；且当前没有 `skipped`/`total`/`audit_complete` 返回字段 |
| 新增 `test_pip_audit_all_skipped_is_not_audited` | **FAIL** | 当前 `audited = len(dependencies) = N`，期望 `0`；无 skipped 计数 |
| 新增 `test_pip_audit_partial_skip_counts_and_findings` | **FAIL** | 当前 `audited=N`，期望 `N-S`；无 `complete=False` |
| 新增 `test_all_skipped_dependency_audit_fails_without_no_vuln_claim` | **FAIL** | 当前 `audited>0`，服务进入 COMPLETED 并写“未发现” |
| 新增 `test_partial_skipped_dependency_audit_fails_and_keeps_findings` | **FAIL** | 当前 COMPLETED；不会按“不完整”失败 |
| 新增 `test_incomplete_dependency_audit_does_not_claim_no_vulnerabilities` | **FAIL** | 当前 UI 在 COMPLETED/0 Finding 时显示“未发现” |
| `test_pip_audit_empty_result`（仅适配新返回值） | 若未来 API 改变，当前三元组会 **FAIL/TYPE ERROR**；若仍用三元组且只改断言，当前行为可通过 | 取决于最终返回值 API |
| `test_pip_audit_bad_json` | PASS（预测） | 当前已有 `ScannerParseError` |
| 现有正常成功/失败、取消、隔离测试 | PAS（预测，前提是 fake 补齐字段） | 业务路径未被 RC-01 破坏 |

**重要**：`EXPECTED_OLD_CODE_RESULT` 不是运行事实。尤其 `test_pip_audit_json...` 当前返回 3 是 CONFIRMED 代码事实，但“测试失败”是 PREDICTED。

## 6. 是否需要修改 UI 测试

**需要新增，且现有成功测试可能需要小改 fixture；不需要改现有成功断言。**

### 6.1 现有 `tests/test_ui_dependency_audit.py`

当前 `UiFakeScanner.scan()` 只返回：

```python
metadata={"audited_dependencies": 2}
```

在未来的严格实现中，服务可能要求 `total_dependencies/skipped_dependencies/audit_complete`。为避免测试通过“缺省值猜测”获得错误绿灯，建议改为：

```python
metadata={
    "audited_dependencies": 2,
    "skipped_dependencies": 0,
    "invalid_dependencies": 0,
    "total_dependencies": 2,
    "audit_complete": True,
}
```

现有断言（`COMPLETED`、1 Finding、表格字段）保持不变。该修改是 fixture 完整性，不是降低断言。

### 6.2 必须新增的 UI 测试

至少新增：

```python
def test_incomplete_dependency_audit_does_not_claim_no_vulnerabilities(...)
```

构造：

- fake scanner 返回 `findings=()`；
- `audited=1`, `skipped=1`, `total=2`, `audit_complete=False`；
- 服务按新规则返回 FAILED（保留 0 或 1 个有效 Finding）。

断言：

- `page._task.status is ScanTaskStatus.FAILED`；
- 页面不包含“当前任务未发现已知依赖漏洞”；
- 页面显示“审计不完整”“失败”或等价错误；
- 若保留 Finding，表格/详情仍可见。

另可新增正常 0 漏洞 UI 测试，确保只有 `COMPLETED + audit_complete + 0 Finding` 才显示“未发现”。这不是修改旧断言，而是补足闭环。

### 6.3 UI 测试是否属于最小范围

属于。因为已批准规则包含“不得将不完整审计表达为未发现漏洞”，仅测试 service 状态不足以验证用户可见文案；不增加该 UI 测试，规则没有被完整覆盖。

## 7. 最小测试修改文件集合

必须修改/新增的测试文件恰好三个：

```text
tests/test_pip_audit_scanner.py
tests/test_dependency_audit_service.py
tests/test_ui_dependency_audit.py
```

- `tests/conftest.py`：不需要修改；现有 `db/audit/scopes/projects/local_source` fixture 足够。
- 不需要新增测试文件；测试放在上述三个现有文件内，便于定位。
- 不修改生产代码、模型、Schema、数据库、UI 生产代码、README、Manifest、历史归档。

### 7.1 每个文件的最小改动类型

| 文件 | 改动类型 |
|---|---|
| `tests/test_pip_audit_scanner.py` | 改 1 个既有解析断言；适配空结果 API；新增全部 skipped/partial/invalid 测试 |
| `tests/test_dependency_audit_service.py` | 扩展 `FakePipAuditScanner` metadata/构造参数；新增 all-skip/partial/摘要持久化测试；既有断言不弱化 |
| `tests/test_ui_dependency_audit.py` | 补齐 `UiFakeScanner` metadata；新增 incomplete UI 测试；既有成功断言不变 |

### 7.2 不属于最小范围

- 修改 `tests/conftest.py`（无必要）。
- 修改 Bandit/Semgrep 测试。
- 修改 report center/JSON/PDF 测试。
- 修改数据库测试。
- 修改生产代码来“让测试过”；本任务禁止。

## 8. 最终状态

```text
TEST_SCOPE_INVESTIGATION = COMPLETE
TESTS_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
PYTEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

补充记录：

- 已读文件：`tests/test_pip_audit_scanner.py`、`tests/test_dependency_audit_service.py`、`tests/test_ui_dependency_audit.py`、Stage 1B-1 报告；未读取数据库。
- Git：HEAD `bffb5ac82bbebe7fef5992f87ff90494c9776ace`，branch `main`，staged 0；已有 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 和未跟踪报告保持不变；本报告为唯一新增文件。
- 未运行 pytest、pip-audit 或 GUI。
- 未进入测试修改阶段；等待人工审核。
