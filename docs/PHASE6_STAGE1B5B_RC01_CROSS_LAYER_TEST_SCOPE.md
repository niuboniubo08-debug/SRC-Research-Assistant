# Phase 6 Stage 1B-5B — RC-01 跨层回归验证范围调查

## 0. 状态与调查边界

- 调查时间：2026-11-14
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 分支：`main`
- HEAD：`db6a138307cc42e26d1075dbbee161c735ee5d4a`
- 工作区：staged 0；RC-01 相关生产文件和测试文件为未暂存修改；没有执行 Git 写操作。
- 本步骤只读调查，未修改代码、测试、数据库、Schema、Scanner、JSON 或权限配置。
- 本步骤未执行 pytest、真实 pip-audit、GUI 或扫描器。
- 报告性质：测试范围与验收方案，不是 RC-01 最终验收执行。

## 1. RC-01 当前生产代码修改范围

RC-01 至今实际涉及的生产代码只有两个文件：

| 层 | 文件 | 当前大小/行数 | 当前 SHA-256 |
|---|---|---:|---|
| Scanner | `scanners/pip_audit_scanner.py` | 13,391 bytes / 332 lines | `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| Service | `services/dependency_audit_service.py` | 28,981 bytes / 766 lines | `94451DF78D6CE3E85E8E6DA7A7CB1D6F01138C9AF43FECCF2DA3351D3971A4C5` |

Scanner 修改点：

- `scan()` 在 `scanners/pip_audit_scanner.py:194-212` 从统计感知解析入口取得 5 元组，并把 `audited_dependencies`、`skipped_dependencies`、`total_dependencies` 写入 `ScanOutput.metadata`。
- `parse_output()` 在 `:214-220` 保留既有三值公共接口。
- `_parse_with_statistics()` 在 `:222-311` 统一计数：
  - `total` 统计所有 dependency 对象；
  - `skip_reason` 的原始 truthiness 决定 skipped/audited；
  - 跳过记录仍保留 warning，不作为 Finding；
  - Finding 构造与去重逻辑沿用既有行为。

Service 修改点：

- `_validate_statistics()` 在 `services/dependency_audit_service.py:327` 被调用，校验 metadata 三个字段及 `audited + skipped == total` 等不变量。
- 统计非法在 `:328-340` 进入 FAILED，不进入 Finding 映射/保存。
- 统计校验意外异常在 `:341-353` 使用独立文案进入 FAILED。
- 合法但不完整在 `:355-361` 形成 incomplete reason，在 `:369-398` 先按原顺序映射/保存，再以 FAILED 结束。
- 合法完整在 `:400` 之后沿用原成功摘要和 COMPLETED 路径。
- 未修改 `_map_findings()`、`_save_findings()` 的实现和顺序。

其他生产代码：

- RC-01 未修改 GUI、HTML exporter、ReportService、Repository、数据库或 Schema。
- `tests/` 与 `docs/` 不计入生产代码。

## 2. Scanner 层测试范围

测试文件：`tests/test_pip_audit_scanner.py`（10,952 bytes / 317 lines / SHA `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A`）。

共 12 个测试函数：

| 行号 | 测试函数 | 与 RC-01 的关系 |
|---:|---|---|
| 71 | `test_pip_audit_json_parsing_dedupes_and_maps_metadata` | 直接覆盖 audited 语义：2 normal + 1 skipped，期望 audited=2、skipped=1、total=3 |
| 123 | `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | 直接覆盖完整审计元数据 |
| 137 | `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | 直接覆盖完整审计且有 Finding |
| 157 | `test_pip_audit_scan_metadata_partial_skip` | 直接覆盖部分 skip 的 audited/skipped/total |
| 183 | `test_pip_audit_scan_metadata_all_skipped` | 直接覆盖全部 skip |
| 210 | `test_pip_audit_empty_result` | 空 dependencies 的解析边界 |
| 220 | `test_pip_audit_bad_json` | 解析失败边界 |
| 228 | `test_pip_audit_unavailable_when_module_missing` | 可用性边界 |
| 238 | `test_pip_audit_actual_available` | 实际工具可用性；可能受环境影响 |
| 252 | `test_pip_audit_execution_failure_timeout_and_cancel` | 执行/超时/取消边界 |
| 302 | `test_pip_audit_scan_requires_available_tool` | 不可用时拒绝扫描 |
| 311 | `test_pip_audit_severity_mapping` | severity 映射，非统计主路径 |

统计字段的直接覆盖集中在 `:71` 和 `:123-207`。

已知执行结果：

- 最近一次实际运行是 Step 1.8，在 Scanner 修复前：12 collected，7 passed，5 failed，0 skipped，1.22s，exit 1。
- 5 个失败均为预期的旧实现/旧断言冲突：audited=3 vs 2、缺少 `skipped_dependencies`、缺少 `total_dependencies`、全 skip 时 audited=2 vs 0。
- Scanner 修复后尚未重新运行本文件；因此**当前** 12 项是否全绿为 `UNKNOWN`，不能把 Step 1.8 的 7/5 说成当前结果。

## 3. Service 层测试范围

测试文件：`tests/test_dependency_audit_service.py`（31,910 bytes / 871 lines / SHA `1E22EE3A1AC7DF2C982252A2A206FEB6448545E8505EC8AF5E016A77E872FCCF`）。

- 34 个测试函数；参数化展开后为 60 个测试实例。
- 最近一次有效执行：Step 5.2.2，`60 passed in 11.63s`，exit 0，0 failed、0 skipped、0 errors。
- 本步骤不重复执行 pytest；上述 60 passed 是当前 Service 层有效基线。

覆盖分布：

| 覆盖目标 | 代表测试（行号） |
|---|---|
| 完整审计 + Finding | `test_completed_dependency_audit_persists_finding_and_metadata`（188） |
| 完整审计 + 无 Finding | `test_empty_dependency_result_is_completed`（224） |
| 部分 skip | `test_partial_skipped_dependency_audit_fails_without_success_summary`（263） |
| 全部 skip | `test_all_skipped_dependency_audit_fails_without_success`（284） |
| 零 audited | `test_zero_audited_dependencies_is_failure_not_success`（243） |
| 缺失统计 | `test_missing_dependency_statistics_fail_closed`（306） |
| 和不一致 | `test_inconsistent_dependency_statistics_fail_closed`（324） |
| 8 个非法参数 | `test_invalid_dependency_statistics_fail_closed`（415） |
| 非法统计不映射/不保存 | `test_invalid_statistics_skip_finding_mapping_and_saving`（693） |
| 不完整但映射并保存 Finding | `test_incomplete_statistics_map_then_save_and_fail_without_success_summary`（728） |
| ValidationError 路径 | `test_statistics_validation_error_skips_mapping_and_returns_statistics_error`（764） |
| 意外统计异常路径 | `test_statistics_unexpected_exception_is_labeled_and_skips_mapping`（804） |
| Finding 保存异常独立性 | `test_finding_save_exception_is_not_reported_as_statistics_error`（845） |
| 辅助函数契约 | `:585-690` 的统计 helper 测试 |

`60 passed` 适合作为 Service 层最终证据，但最终验收仍应在明确授权的执行步骤中重跑，而不是引用旧输出代替执行。

## 4. Scanner → Service 跨层测试调查

调查结论：

```text
CROSS_LAYER_TEST = NOT_FOUND
```

证据：

- `tests/test_pip_audit_scanner.py` 只导入 `PipAuditScanner`/`map_pip_audit_severity`，不导入 `DependencyAuditService`，只验证 Scanner 解析和元数据。
- `tests/test_dependency_audit_service.py` 使用 `FakePipAuditScanner`，不导入真实 `PipAuditScanner`；Service 测试的 5 个统计字段来自 fake metadata。
- `tests/test_ui_dependency_audit.py` 使用 `DependencyAuditService` + `UiFakeScanner`/`UiIncompleteScanner`，不经过真实 `PipAuditScanner`。
- 因此当前没有测试同时经过：

```text
pip-audit JSON -> 真实 PipAuditScanner._parse_with_statistics
-> ScanOutput.metadata -> DependencyAuditService._validate_statistics
-> ScanTask / Finding
```

- 当前证据只能证明 Scanner 单元契约和 Service 单元/集成契约分别成立，不能单独证明真实 Scanner 输出的 metadata 与 Service 校验器的接口完全一致。

## 5. 推荐分层测试计划

### Level A — Scanner 定向测试

- 命令：`python -m pytest tests/test_pip_audit_scanner.py -q`
- 目的：确认真实解析器产出 `audited_dependencies`、`skipped_dependencies`、`total_dependencies`，且 skip 记录不生成 Finding。
- 预期：12 passed。
- 失败处理：立即停止，保留失败输出，不得用 Service 的 fake 测试替代。
- 分类：**REQUIRED**。

### Level B — Service 定向测试

- 命令：`python -m pytest tests/test_dependency_audit_service.py -q`
- 目的：确认统计校验、非法/不完整/完整路径、Finding 保存异常和状态终态。
- 预期：60 passed。
- 当前基线：60 passed（Step 5.2.2）。
- 失败处理：停止最终验收，优先修复或报告回归。
- 分类：**REQUIRED**。

### Level C — Scanner + Service 跨层测试

- 现状：没有现成测试；`CROSS_LAYER_TEST = NOT_FOUND`。
- 最小方案设计（不实现）：
  1. 新建独立测试文件，例如 `tests/test_rc01_cross_layer.py`。
  2. 使用真实 `PipAuditScanner` 的 `_parse_with_statistics()` 或通过 monkeypatch 的 `run_command` 让真实 `scan()` 解析固定 JSON；不得联网。
  3. 将真实 `PipAuditScanner` 作为 Service 的 scanner，注入临时 Database/项目/Scope；或构造一个只把真实 `ScanOutput` 交给服务的测试适配器。
  4. 至少覆盖：complete/no-vuln、complete/with-vuln、partial-skip、all-skip、统计非法（构造坏 metadata）。
  5. 断言 `ScanTaskStatus`、`error_message`、Finding 数量/项目绑定，以及不出现“未发现已知漏洞”的假成功。
- 该方案需要后续明确授权后实施；本步骤不创建测试。
- 分类：**RECOMMENDED**（若最终验收声称“跨层已验证”，则该结论必须升级为 REQUIRED 并先完成实现与执行；当前不能这样声称）。

### Level D — RC-01 相关更大范围回归

推荐执行：

```text
python -m pytest tests/test_pip_audit_scanner.py tests/test_dependency_audit_service.py tests/test_ui_dependency_audit.py -q
```

- 目的：补上依赖审计页面对 FAILED/不完整状态的实际 UI 行为。
- 当前已知：UI 文件 2 个测试函数；B4A 历史结果为 2 collected / 1 passed / 1 failed，且该结果早于当前修复；当前未重跑，`UNKNOWN`。
- 失败处理：作为回归信号，停止最终验收并报告；不得用旧的 60 passed 覆盖 UI 结果。
- 分类：**RECOMMENDED**。

### 明确排除

- 真实 pip-audit 网络审计：**OUT_OF_SCOPE**（本次验证使用固定 JSON/fake，避免网络不确定性）。
- 全项目 pytest：**OUT_OF_SCOPE**（不能无依据地把全项目回归当作 RC-01 必需项；如发布验收需要，另立授权步骤）。
- Semgrep、PDF、JSON、报告历史、GUI 新功能：**OUT_OF_SCOPE**。

## 6. Windows ACL / 临时目录限制

Step 5.2.2 首次在普通 workspace-write 进程运行 `tests/test_dependency_audit_service.py` 时：

- 全部 60 项在 pytest setup 阶段报错，未进入测试断言；
- 典型异常为 `PermissionError: [WinError 5]`；
- 位置为 `_pytest/tmpdir.py:375 cleanup_dead_symlinks()` → `pathlib.py:398 os.scandir()`；
- 原因是当前 Windows 低完整性/ACL 环境无法读取 pytest 临时目录，不是 RC-01 代码失败。

最终通过方式（项目 C1-R 已记录的方式）：

- 专用临时目录：`D:\挖漏洞\pytest_c1r_tmp`
- `TEMP` / `TMP` / `TMPDIR` / `PYTEST_DEBUG_TEMPROOT` 指向该目录
- `--basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_s522_full`
- 测试进程使用既有 full-access 条件

最终结果：`60 passed in 11.63s`，exit 0。该方式不修改 ACL；最终 RC-01 验收若在同一 Windows 环境执行，需要复用这一已记录的测试环境方式，不能把普通 workspace-write 下的 setup 错误当作产品失败。

## 7. 已知 skip 与环境限制

- `tests/test_evidence_service.py:168 test_symlink_to_outside_is_rejected` 在无符号链接权限的 Windows 环境会 skip，原因 `WinError 1314`。该测试属于 Evidence 路径边界，与 RC-01 的 pip-audit 统计字段无关；RC-01 不应把它计入失败。
- Semgrep 1.183.0 在本 Windows 环境存在 `CertOpenSystemStore returned NULL` 启动限制；当前 RC-01 不依赖 Semgrep。
- 真实 pip-audit 依赖网络/PyPI；RC-01 定向测试不需要真实网络执行，最终验收也不应把网络可用性混同为代码正确性。
- 历史全项目回归的 7 个 skip 均为 Windows 符号链接相关；不要在 RC-01 结论中把它们误报为 RC-01 失败。

## 8. 分类汇总

| 项目 | 分类 | 理由 |
|---|---|---|
| Scanner 定向 12 项 | **REQUIRED** | Scanner 是统计字段的第一生产者 |
| Service 定向 60 项 | **REQUIRED** | 终态、错误文案和 Finding 保存的最终裁决层 |
| Scanner + Service 跨层测试 | **RECOMMENDED** | 当前不存在；没有它不能声称接口已跨层验证 |
| UI 依赖审计 2 项 | **RECOMMENDED** | 验证失败状态不会显示“未发现” |
| 真实 pip-audit 网络审计 | **OUT_OF_SCOPE** | 不应把外部网络作为 RC-01 单元证据 |
| 全项目 pytest | **OUT_OF_SCOPE** | 本步骤未授权，且不是 RC-01 的最小必要证据 |
| Semgrep/PDF/JSON/报告历史 | **OUT_OF_SCOPE** | 与 RC-01 无关或未批准 |

## 9. UNKNOWN 与未验证项

- `SCANNER_TEST_CURRENT_RESULT = UNKNOWN`：Scanner 修复后未重跑；Step 1.8 的 7 passed/5 failed 不是当前结果。
- `UI_TEST_CURRENT_RESULT = UNKNOWN`：B4A 的 1 passed/1 failed 早于当前修复；未重跑。
- `CROSS_LAYER_TEST_CURRENT_RESULT = NOT_FOUND`：不存在现成测试。
- `REAL_PIP_AUDIT_CURRENT_RESULT = NOT_RUN`：本步骤禁止真实 pip-audit；Unit/Service 测试使用固定 JSON/fake。
- `CURRENT_WORKTREE` 中仍保留此前步骤的未暂存生产/测试修改和多份未跟踪报告；本步骤没有修改它们，也没有执行 Git 写操作。
- 没有证据支持把 RC-01 当前状态直接宣布为“最终完成”；本报告只给出测试范围和验收前置条件。

## 10. 最终声明

```text
STEP_6_STATUS = INVESTIGATION_COMPLETED
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_EXECUTED = NO
SCANNER_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
JSON_WORK = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本次唯一新增文件：`docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_TEST_SCOPE.md`。
未执行最终回归测试，未修改权限或系统配置，未执行 Git add/commit/push/reset/restore/clean。
