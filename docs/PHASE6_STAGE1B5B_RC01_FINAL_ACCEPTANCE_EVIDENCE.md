# Phase 6 Stage 1B-5B — RC-01 最终验收证据汇总

## 0. 状态与边界

- 汇总时间：2026-11-14
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 分支：`main`
- HEAD：`db6a138307cc42e26d1075dbbee161c735ee5d4a`
- 工作区：staged 0；此前步骤的未暂存修改和未跟踪报告仍在，本步骤没有改动它们。
- 本步骤只读汇总：未执行 pytest、真实 pip-audit、真实网络访问、GUI、数据库或 Git 写操作。
- 本报告不宣布 `RC-01 = COMPLETED`；最终完成状态由人工审核决定。

## 1. RC-01 原始问题与目标

原始问题（确认自当前实现和历史报告）：

- pip-audit JSON 中的 `skip_reason` 依赖曾被当作已审计依赖；
- 全部/部分依赖被跳过时，Service 仍可能以 `COMPLETED` 结束并显示“未发现已知漏洞”；
- 该行为会把“不完整审计”错误表达为“无漏洞”。

修复目标：

### Scanner 层

正确生成并传递：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

语义要求：

- `total` 包含所有 dependency 对象；
- `skipped` 只统计带真实 `skip_reason` 的对象；
- `audited` 只统计没有 `skip_reason` 的对象；
- `audited + skipped == total`；
- skip 记录不产生 Finding。

### Service 层

- 严格验证三个统计字段；
- 非法统计 fail closed；
- 区分 `ValidationError`（统计非法）与意外异常（统计校验异常）；
- 完整审计才允许 `COMPLETED`；
- 不完整审计即使已保存 Finding，最终仍为 `FAILED`；
- 不生成“未发现已知漏洞”的成功摘要。

## 2. 实际生产代码修改范围

### 2.1 Scanner

文件：`scanners/pip_audit_scanner.py`

```text
13,391 bytes
332 lines
SHA-256 = 5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D
```

RC-01 相关修改目的：

- `scan()` 在 `scanners/pip_audit_scanner.py:194-212` 使用统计感知解析结果，并写入三个 metadata 字段（`:207-209`）；
- `parse_output()` 在 `:214-220` 保持既有三值公共接口；
- `_parse_with_statistics()` 在 `:222-311` 计算 audited/skipped/total，skip 不产生 Finding。

与 RC-01 无关的修改证据：

- 未发现；当前文件的 RC-01 统计逻辑和既有解析/映射逻辑可区分，但精确到提交级的完整 delta 未建立：
  `SCANNER_UNRELATED_CHANGE_EVIDENCE = NOT_FOUND`
  `SCANNER_EXACT_HISTORICAL_DELTA = UNKNOWN`

### 2.2 Service

文件：`services/dependency_audit_service.py`

```text
28,981 bytes
766 lines
SHA-256 = 94451DF78D6CE3E85E8E6DA7A7CB1D6F01138C9AF43FECCF2DA3351D3971A4C5
```

RC-01 相关修改目的：

- `_validate_statistics()`（`:420`）严格校验 metadata；
- `run_audit()` 在 `:327` 调用校验；
- `:328-340` 非法统计 → FAILED，映射/保存前停止；
- `:341-353` 意外统计异常 → FAILED，使用独立文案；
- `:355-398` 合法但不完整 → 先映射/保存，再 FAILED，无成功摘要；
- 合法且完整才走原 COMPLETED 路径。

与 RC-01 无关的修改证据：

- 未发现；`_map_findings()`/`_save_findings()` 的既有实现和顺序未被 RC-01 改造。
- 精确历史 delta 同样未建立：
  `SERVICE_UNRELATED_CHANGE_EVIDENCE = NOT_FOUND`
  `SERVICE_EXACT_HISTORICAL_DELTA = UNKNOWN`

### 2.3 其他生产代码

- RC-01 未修改 GUI、HTML exporter、ReportService、Repository、数据库或 Schema。
- 未修改 PDF/JSON 功能。
- 未因 RC-01 新增生产文件。

## 3. RC-01 测试代码修改范围

测试文件不是生产代码。

### Scanner 测试

文件：`tests/test_pip_audit_scanner.py`

```text
10,952 bytes
317 lines
SHA-256 = B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A
```

当前 12 个测试函数。统计语义直接覆盖：

- `test_pip_audit_json_parsing_dedupes_and_maps_metadata`（`:71`）：audited 2、含 1 个 skip；
- `test_pip_audit_scan_metadata_complete_without_vulnerabilities`（`:123`）；
- `test_pip_audit_scan_metadata_complete_with_vulnerabilities`（`:137`）；
- `test_pip_audit_scan_metadata_partial_skip`（`:157`）：audited 2/skipped 1/total 3；
- `test_pip_audit_scan_metadata_all_skipped`（`:183`）：audited 0/skipped 2/total 2。

### Service 测试

文件：`tests/test_dependency_audit_service.py`

```text
31,910 bytes
871 lines
SHA-256 = 1E22EE3A1AC7DF2C982252A2A206FEB6448545E8505EC8AF5E016A77E872FCCF
```

34 个测试函数，参数化展开为 60 个实例。RC-01 直接覆盖：

- 非法统计不映射/不保存：`test_invalid_statistics_skip_finding_mapping_and_saving`（`:693`）；
- 不完整审计先映射/保存再 FAILED：`test_incomplete_statistics_map_then_save_and_fail_without_success_summary`（`:728`）；
- ValidationError 路径：`test_statistics_validation_error_skips_mapping_and_returns_statistics_error`（`:764`）；
- 意外统计异常路径：`test_statistics_unexpected_exception_is_labeled_and_skips_mapping`（`:804`）；
- Finding 保存异常独立：`test_finding_save_exception_is_not_reported_as_statistics_error`（`:845`）；
- 旧零审计断言已更新为当前统计非法契约（`:243`）。

## 4. Level A — Scanner 最终证据

仅引用 Step 7A 实际完成结果：

```text
python -m pytest tests/test_pip_audit_scanner.py -q
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_step7a
```

```text
12 passed in 1.37s
exit code 0
```

```text
collected = 12
passed    = 12
failed    = 0
skipped   = 0
errors    = 0
```

说明：

- 这是 Step 7A 的实际结果；
- 本步骤未重新执行 pytest；
- 使用已记录的专用 pytest 临时目录；
- 未修改 ACL 或系统权限；
- 未发生 `WinError 5` setup 错误。

## 5. Level B — Service 最终证据

仅引用 Step 7B 实际完成结果：

```text
python -m pytest tests/test_dependency_audit_service.py -q
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_step7b
```

```text
60 passed in 12.85s
exit code 0
```

```text
collected = 60
passed    = 60
failed    = 0
skipped   = 0
errors    = 0
```

说明：

- 这是 Step 7B 的实际结果；
- 本步骤未重新执行 pytest；
- 测试执行前后 `services/dependency_audit_service.py` 与测试文件 SHA-256 不变；
- 未修改生产代码或测试代码。

## 6. 跨层测试决策

Step 8 已给出明确决定：

```text
DECISION = WAIVE_CROSS_LAYER_TEST
```

豁免依据：

```text
Level A Scanner: 12 passed
Level B Service: 60 passed
FIELD_NAME_MATCH = YES
METADATA_TYPE_MATCH = YES
VALUE_TYPE_MATCH = YES
CONFIRMED_INTERFACE_MISMATCH = NONE
```

理由摘要：

- Scanner 使用真实 `PipAuditScanner.scan()`，仅 mock 外部 subprocess；
- Service 使用同一三个字段契约并经过真实 `_validate_statistics()`；
- 没有证据表明当前接口存在字段名、类型或缺失处理不一致；
- 跨层测试的价值主要是未来漂移防护，不是当前已确认缺陷。

不得夸大的结论：

```text
REAL_SCANNER_TO_REAL_SERVICE_RUNTIME_TEST = NOT_EXECUTED
APP_BOOTSTRAP_REAL_SCANNER_WIRING_TEST = NOT_FOUND
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_EXECUTED
```

跨层豁免不等于上述运行时验证已经完成。

## 7. 环境限制与历史问题

### Windows ACL / WinError 5

- 历史上 Step 5.2.2 首次普通 workspace-write 执行时，pytest 在 setup/cleanup 阶段遇到 Windows ACL 限制，60 项均未进入实际断言；
- 典型异常为 `PermissionError: [WinError 5]`；
- Step 7A/7B 最终执行使用项目已记录的专用临时目录：
  `D:\挖漏洞\pytest_c1r_tmp`；
- 测试进程使用既有 full-access 条件；
- 未修改 ACL 或系统权限；
- Step 7A/7B 最终均未发生 ACL setup 错误。

### 已知历史 skip

- `tests/test_evidence_service.py:168 test_symlink_to_outside_is_rejected`
- 原因：Windows 符号链接权限 `WinError 1314`。
- 结论：`OUT_OF_SCOPE_FOR_RC01`，不计入 RC-01 Scanner/Service 定向测试失败。

## 8. 最终完成标准核对表

| 检查项 | 结论 | 依据 |
|---|---|---|
| Scanner 统计契约已修复 | **PASS** | Level A 12 passed；`audited/skipped/total` 测试 |
| Service 统计契约已修复 | **PASS** | Level B 60 passed；统计校验和终态测试 |
| 非法统计 fail closed | **PASS** | 非法统计测试不映射/不保存、FAILED |
| 不完整审计不会误报成功 | **PASS** | 部分/全部 skip 测试 FAILED、无成功摘要 |
| 完整审计保持成功路径 | **PASS** | 有 Finding / 无 Finding 的 COMPLETED 测试 |
| Scanner 定向测试通过 | **PASS** | Step 7A：12 passed，exit 0 |
| Service 定向测试通过 | **PASS** | Step 7B：60 passed，exit 0 |
| 跨层测试决策已完成 | **PASS** | Step 8：`WAIVE_CROSS_LAYER_TEST` |
| 跨层豁免理由已记录 | **PASS** | 字段/类型/值匹配，无当前不一致 |
| 未验证事项已明确 | **PASS** | 见第 9 节 |
| 无数据库/Schema 修改 | **PASS** | 两份报告均记录未修改；本步骤只读 |
| 最终验收期间未修改生产代码 | **PASS** | 当前源文件 SHA 与前序一致 |
| 最终验收期间未修改测试代码 | **PASS** | 当前测试 SHA 与前序一致 |

## 9. UNKNOWN / NOT_EXECUTED / 证据边界

### CONFIRMED

- Scanner 当前实现生成三个统计字段，字段名和值类型符合契约；
- Service 当前实现对非法统计 fail closed，对不完整审计返回 FAILED；
- Level A：12 passed；
- Level B：60 passed；
- Step 8 决策为 `WAIVE_CROSS_LAYER_TEST`；
- 本步骤未执行 pytest、真实 pip-audit、网络、GUI 或数据库操作。

### UNKNOWN / NOT_EXECUTED

```text
REAL_SCANNER_TO_REAL_SERVICE_RUNTIME_TEST = NOT_EXECUTED
APP_BOOTSTRAP_REAL_SCANNER_WIRING_TEST = NOT_FOUND
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_EXECUTED
CURRENT_FULL_SUITE_RESULT = NOT_RUN_IN_THIS_STEP
PRODUCTION_DATABASE_BEHAVIOR = NOT_EXERCISED_IN_THIS_STEP
SCANNER_EXACT_HISTORICAL_DELTA = UNKNOWN
SERVICE_EXACT_HISTORICAL_DELTA = UNKNOWN
```

“没有发现问题”不等于“已经证明不存在问题”。上述未执行项不得被写成已验证。

## 10. 实际文件变化

本步骤只新增：

```text
docs/PHASE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md
```

未修改任何生产代码、测试、现有文档、数据库、Schema、Manifest、GUI 或 JSON。

当前工作区仍有此前步骤留下的未暂存修改和未跟踪报告；它们不是本步骤的修改。

## 11. 最终结论

```text
RC01_EVIDENCE_STATUS = READY_FOR_FINAL_HUMAN_REVIEW
```

不存在阻塞最终人工审核的证据冲突。

但必须保留以下边界：

- 这是“证据汇总完成”，不是“RC-01 = COMPLETED”；
- 跨层测试已豁免，因此不能声称真实 Scanner → 真实 Service 运行时已验证；
- 真实 pip-audit、真实网络、生产数据库行为和完整测试套件未在本步骤执行；
- 最终完成状态由人工审核决定。

```text
STEP_9_STATUS = EVIDENCE_SUMMARY_COMPLETED
RC01_EVIDENCE_STATUS = READY_FOR_FINAL_HUMAN_REVIEW
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
NETWORK_ACCESS = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
JSON_WORK = NO
NEXT_STEP = FINAL_HUMAN_REVIEW_REQUIRED
```
