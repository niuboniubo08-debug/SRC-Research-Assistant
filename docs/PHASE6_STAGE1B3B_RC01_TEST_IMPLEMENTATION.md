# Phase 6 Stage 1B-3B：RC-01 实际测试修改

## 0. 状态摘要

```text
STAGE1B3B_TEST_IMPLEMENTATION = COMPLETE
TESTS_MODIFIED = YES
PRODUCTION_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤只按照已审核的 Stage 1B-3A 计划修改测试。没有修改生产代码，没有运行 pytest、pip-audit 或 GUI，也没有修改数据库、Schema 或 Git 状态。

## 1. 实际修改文件

| 文件 | 修改前 | 修改后 | 行数 | SHA-256 |
|---|---:|---:|---:|---|
| `tests/test_pip_audit_scanner.py` | 7,245 B | 10,952 B | 317 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |
| `tests/test_dependency_audit_service.py` | 14,929 B | 20,966 B | 553 | `003F1F9EE570F6081ACA4904123E319F45883CEAC41DCFF637F509CCB81751D1` |
| `tests/test_ui_dependency_audit.py` | 5,269 B | 7,855 B | 223 | `06A24F9F016FCCBA1F7EA770CDBCDAC365523453884F0A9D12009548832A9FD5` |

新增报告：

- `docs/PHASE6_STAGE1B3B_RC01_TEST_IMPLEMENTATION.md`

没有新增测试文件。没有修改其它测试辅助文件；`FakePipAuditScanner` 和 `UiFakeScanner` 的调整均位于上述允许修改的测试文件内。

## 2. 逐项测试修改与场景对应

### 2.1 扫描器解析层

文件：`tests/test_pip_audit_scanner.py`

修改已有测试：

- `test_pip_audit_json_parsing_dedupes_and_maps_metadata:71`
  - 旧断言：`audited == 3`（2 个正常、1 个 skipped）。
  - 新断言：`audited == 2`。
  - 对应：B2C 契约中 `audited_dependencies` 不含 skipped 依赖。

新增测试：

| 测试 | 行 | 对应场景 |
|---|---:|---|
| `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | 123 | TC-01-SCAN：完整、无漏洞，metadata 应为 audited=1/skipped=0/total=1 |
| `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | 137 | TC-02-SCAN：完整、有漏洞，metadata 应为 audited=1/skipped=0/total=1 |
| `test_pip_audit_scan_metadata_partial_skip` | 157 | TC-03-SCAN：部分 skipped，metadata 应为 audited=2/skipped=1/total=3 |
| `test_pip_audit_scan_metadata_all_skipped` | 183 | TC-04-SCAN：全部 skipped，metadata 应为 audited=0/skipped=2/total=2 |

这些测试通过 `scan()` 的公开入口验证 `ScanOutput.metadata`，并使用 `monkeypatch` 替换 `run_command`，不执行真实 pip-audit。

### 2.2 服务层

文件：`tests/test_dependency_audit_service.py`

测试辅助调整：

- `FakePipAuditScanner` 增加 `skipped`、`total`、`raw_metadata` 参数。
- 标准 metadata 现在包含：
  - `audited_dependencies`
  - `skipped_dependencies`
  - `total_dependencies`
- `raw_metadata` 用于构造缺失、矛盾或非法统计的测试输入。
- 已有成功测试显式传入完整统计（audited/skipped/total），不改变其成功语义。

新增测试：

| 测试 | 行 | 对应场景 |
|---|---:|---|
| `test_partial_skipped_dependency_audit_fails_without_success_summary` | 262 | TC-03-SVC：部分 skipped -> FAILED，且不得出现“未发现已知漏洞” |
| `test_all_skipped_dependency_audit_fails_without_success` | 283 | TC-04-SVC：全部 skipped -> FAILED，不得形成成功语义 |
| `test_missing_dependency_statistics_fail_closed` | 305 | TC-05-SVC：缺少必需统计 -> FAILED |
| `test_inconsistent_dependency_statistics_fail_closed` | 323 | TC-06-SVC：`audited + skipped != total` -> FAILED |
| `test_invalid_dependency_statistics_fail_closed` | 398 | TC-07-SVC：六种非法/边界统计 -> FAILED |

`test_invalid_dependency_statistics_fail_closed` 的参数化用例：

1. `audited=None`
2. `audited="2"`（非整数）
3. `audited=-1`（负数）
4. `total_dependencies=0`
5. `skipped_dependencies=-1`（负数）
6. `audited=True`（布尔值不得当作整数统计）

按照已审核的测试计划，部分 skipped 与全部 skipped 测试只断言任务状态和禁止错误成功结论，不强制规定 Finding 的保留、删除或持久化策略。

### 2.3 UI 层

文件：`tests/test_ui_dependency_audit.py`

测试辅助调整：

- `UiFakeScanner` 的 metadata 增加 `skipped_dependencies=0` 和 `total_dependencies=2`。
- 新增 `UiIncompleteScanner`，返回 `audited_dependencies=1 / skipped_dependencies=1 / total_dependencies=2`，无 findings。

新增测试：

| 测试 | 行 | 对应场景 |
|---|---:|---|
| `test_incomplete_dependency_audit_does_not_claim_no_vulnerabilities` | 171 | UI 不完整审计 -> 任务 FAILED，且不得显示“未发现已知依赖漏洞” |

该测试通过真实 `MainWindow`/`DependencyPage` 路径启动 fake 扫描任务，但不启动真实 pip-audit。

## 3. 未修改的允许文件

Stage 1B-3A 允许的三个测试文件均已修改，没有“允许但未修改”的文件。没有新增测试文件。

以下内容没有修改：

- 生产代码：`scanners/pip_audit_scanner.py`
- 生产代码：`services/dependency_audit_service.py`
- 生产代码：`ui/dependency_page.py`
- `reports/html_exporter.py` 及其模板
- README、配置、数据库、Schema、Manifest、历史报告
- 已有文档或归档

## 4. 生产代码未修改

本步骤没有修改任何生产代码或业务接口。`ScanOutput.metadata` 的字段扩展、Service 的完整审计判断和 UI 的错误展示仍属于后续生产修复步骤。

## 5. 未运行 pytest

本步骤没有执行：

- `pytest`
- `python -m pytest`
- pip-audit
- GUI 手工测试
- 任何测试收集或测试子集

只执行了不导入测试模块的 AST 语法检查：

```text
AST_OK=3
```

该检查只确认三个测试文件能被 Python 解析，不代表测试通过。

## 6. 数据库与 Schema 未修改

没有打开数据库执行写操作，没有运行迁移，没有修改 Schema，也没有创建或删除数据库文件。

## 7. PREDICTED 旧代码失败

以下均为静态推断，标记为 **PREDICTED**，不是实际运行结果。

| 场景 | 旧生产代码的预期行为 | 新测试预期 |
|---|---|---|
| 解析层 audited 计数 | 返回 3，包含 skipped | 断言 2，预期失败 |
| 扫描器 metadata 字段 | 只有 `audited_dependencies`，缺少 skipped/total | 访问缺失键，预期失败 |
| 部分 skipped（服务） | `audited=1`，任务 COMPLETED，可能出现“未发现” | 断言 FAILED，预期失败 |
| 全部 skipped（服务） | `audited=0`，旧代码已经 FAILED | 状态可能通过；本测试仍作为禁止成功语义的契约保护 |
| 缺少必需统计（服务） | `audited=2`，任务 COMPLETED | 断言 FAILED，预期失败 |
| 统计矛盾（服务） | `audited=1`，任务 COMPLETED | 断言 FAILED，预期失败 |
| `audited=None` | 旧代码按 0 处理，FAILED | 作为契约保护；状态可能通过 |
| `audited="2"` | 旧代码转成 2，COMPLETED | 断言 FAILED，预期失败 |
| `audited=-1` | 旧代码非 0，COMPLETED | 断言 FAILED，预期失败 |
| `total=0` 且 `audited=1` | 旧代码忽略 total，COMPLETED | 断言 FAILED，预期失败 |
| `skipped=-1` 且 `audited=2` | 旧代码忽略 skipped，COMPLETED | 断言 FAILED，预期失败 |
| `audited=True` | 旧代码按 1 处理，COMPLETED | 断言 FAILED，预期失败 |
| UI 不完整审计 | 任务 COMPLETED，显示“当前任务未发现已知依赖漏洞” | 断言 FAILED 且不显示该文案，预期失败 |

已有完整审计成功测试继续保留，用于确认未来生产修复不能把正常成功路径改坏。

## 8. 当前工作区状态

本步骤开始前已有、且本步骤未处理的变更：

```text
M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
```

本步骤修改的测试文件：

```text
M tests/test_pip_audit_scanner.py
M tests/test_dependency_audit_service.py
M tests/test_ui_dependency_audit.py
```

本步骤新增的报告为未跟踪文件。没有执行 Git add、commit、push、reset、restore 或 clean。

## 9. 下一步

本步骤只完成测试修改。测试执行、失败证据采集和生产修复需要人工审核后另行授权。

```text
STAGE1B3B_TEST_IMPLEMENTATION = COMPLETE
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```
