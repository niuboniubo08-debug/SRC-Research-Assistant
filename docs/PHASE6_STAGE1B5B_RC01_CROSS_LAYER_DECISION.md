# Phase 6 Stage 1B-5B — RC-01 跨层验证必要性与最小方案调查

## 0. 状态与调查边界

- 调查时间：2026-11-14
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 分支：`main`
- HEAD：`db6a138307cc42e26d1075dbbee161c735ee5d4a`
- 工作区：staged 0；此前步骤留下的生产/测试/文档修改未由本步骤改动。
- 本步骤只读调查：未执行 pytest、真实 pip-audit、真实网络访问、GUI、数据库或 Git 写操作。
- 已确认的 Level A/B 当前结果（来自前序执行，不是本步骤重跑）：
  - Level A：`12 passed in 1.37s`，exit 0；
  - Level B：`60 passed in 12.85s`，exit 0。

## 1. 当前源码实际调查范围

实际读取并核对：

| 文件 | 作用 | 当前 SHA-256 |
|---|---|---|
| `scanners/pip_audit_scanner.py` | 真实 pip-audit 适配器 | `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| `services/dependency_audit_service.py` | 依赖审计编排和统计校验 | `94451DF78D6CE3E85E8E6DA7A7CB1D6F01138C9AF43FECCF2DA3351D3971A4C5` |
| `tests/test_pip_audit_scanner.py` | Scanner 定向测试 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |
| `tests/test_dependency_audit_service.py` | Service 定向测试 | `1E22EE3A1AC7DF2C982252A2A206FEB6448545E8505EC8AF5E016A77E872FCCF` |
| `tests/test_ui_dependency_audit.py` | UI 层 fake scanner 集成测试 | `06A24F9F016FCCBA1F7EA770CDBCDAC365523453884F0A9D12009548832A9FD5` |

说明：用户描述中的 `DependencyAuditOutput` 在当前代码中不存在同名类；实际返回对象是 `DependencyAuditOutcome`（`services/dependency_audit_service.py:70-89`）。Scanner 侧输出对象是 `ScanOutput`（`scanners/base.py:66-70`）。

## 2. Scanner → Service 真实接口链路

实际数据流：

```text
PipAuditScanner.scan()
  scanners/pip_audit_scanner.py:126
        ↓
PipAuditScanner._parse_with_statistics()
  scanners/pip_audit_scanner.py:222
        ↓
ScanOutput(findings, warnings, metadata)
  scanners/base.py:66-70
        ↓
BaseScanner 注入 DependencyAuditService
  services/dependency_audit_service.py:95-111
        ↓
DependencyAuditService.run_audit()
  services/dependency_audit_service.py:246
        ↓
DependencyAuditService._validate_statistics(metadata)
  services/dependency_audit_service.py:420
        ↓
ScanTask / Finding
```

具体接口：

1. **Scanner 输入**：`scan(target: str | Path, options: ScanOptions) -> ScanOutput`。
2. **Scanner 输出**：`ScanOutput(findings: tuple[Finding,...], warnings: tuple[str,...], metadata: Mapping[str, Any])`。
3. **Service 输入 Scanner**：`BaseScanner` 实例，构造参数为 `scanner: BaseScanner`（`services/dependency_audit_service.py:101`）。
4. **Service 读取 metadata**：`output.metadata`，经 `_validate_statistics()` 解包为 `(audited, skipped, total)`（`:327`）。
5. **Service 输出**：`DependencyAuditOutcome`，其中 `task: ScanTask`、`findings: tuple[Finding,...]`、`audited_dependencies: int`、`warnings`、`errors`。
6. **最终状态**：由 `run_audit()` 的 `_finish()` 写入 `ScanTaskStatus.COMPLETED` 或 `FAILED`，Finding 通过 `_map_findings()`/`_save_findings()` 持久化。

没有 adapter、DTO 转换层或独立 pipeline；Scanner 的 `ScanOutput` 被 Service 直接使用。

## 3. metadata 类型和字段契约

### 3.1 Scanner 实际写入

`scanners/pip_audit_scanner.py:204-211` 返回普通 `dict`：

```python
metadata={
    "returncode": result.returncode,
    "duration_seconds": round(result.duration_seconds, 3),
    "audited_dependencies": audited,
    "skipped_dependencies": skipped,
    "total_dependencies": total,
    "vulnerability_service": self.vulnerability_service,
}
```

关键字段：

- `audited_dependencies` 位于 `:207`；
- `skipped_dependencies` 位于 `:208`；
- `total_dependencies` 位于 `:209`。

计数逻辑位于 `_parse_with_statistics()` `:235-252`：

- `total` 对所有 dependency 对象递增；
- `bool(dependency.get("skip_reason"))` 为真时 `skipped += 1`，否则 `audited += 1`；
- skip 仍可生成 warning，但不构造 Finding；
- 三个值始终是 `int`。

### 3.2 Service 实际读取

`services/dependency_audit_service.py:420` 的 `_validate_statistics(metadata: object)`：

- 要求 `metadata` 是 `Mapping`；
- 要求三个字段全部存在；
- 使用 `type(value) is int`，拒绝 bool/string/float/None；
- 拒绝负数和 `total <= 0`；
- 要求 `audited + skipped == total`；
- 返回 `(audited, skipped, total)`。

`ScanOutput.metadata` 的声明类型是 `Mapping[str, Any]`；Scanner 实际传入 `dict`，Service 的 `isinstance(metadata, Mapping)` 检查可接受它。没有类型转换缺口。

### 3.3 字段对照结论

```text
FIELD_NAME_MATCH = YES
METADATA_TYPE_MATCH = YES (dict -> Mapping)
VALUE_TYPE_MATCH = YES (int)
MISSING_FIELD_BEHAVIOR = FAIL CLOSED
CONFIRMED_INTERFACE_MISMATCH = NONE
```

## 4. Level A/B 已覆盖的内容

### Level A — Scanner 定向

`tests/test_pip_audit_scanner.py` 12 项，当前 `12 passed`：

- `:71` 解析和去重，`audited == 2`，含 1 个 skip；
- `:123` 完整、无漏洞，断言三个 metadata 字段；
- `:137` 完整、有漏洞，断言三个 metadata 字段和 Finding；
- `:157` 部分 skip，`audited=2/skipped=1/total=3`，skip 不产生 Finding；
- `:183` 全部 skip，`audited=0/skipped=2/total=2`，无 Finding；
- 其余测试覆盖空结果、坏 JSON、可用性、执行失败/超时/取消、severity、必须可用。

这些测试通过 `_scan_with_dependencies()` 在 `:97-120` mock 了 `scanners.pip_audit_scanner.run_command`，因此测试的是**真实 `PipAuditScanner.scan()` 和真实解析器**，没有网络调用。

### Level B — Service 定向

`tests/test_dependency_audit_service.py` 60 个实例，当前 `60 passed`：

- 非法统计：FAILED，不进入映射/保存，不产生 Finding（`:693`）；
- 不完整统计：`map -> save` 后仍 FAILED，保留 Finding，不生成成功摘要（`:728`）；
- 完整统计：有 Finding 和无 Finding 均 COMPLETED（`:188`、`:224`）；
- ValidationError 和意外统计异常分别使用 `依赖审计统计非法：...` / `依赖审计统计校验异常：...`（`:764`、`:804`）；
- Finding 保存异常独立显示 `依赖审计结果保存失败：...`（`:845`）；
- 8 个非法参数覆盖 bool/string/negative/zero/sum 错误（`:415`）。

Service 测试使用 `FakePipAuditScanner`（`:55-114`），但其 metadata 字段名与真实 Scanner 完全一致，且 `_validate_statistics()` 是当前生产实现。

## 5. 尚存接口风险

### 5.1 已消除的风险

- 字段名：Scanner 与 Service 两侧均使用 `audited_dependencies`、`skipped_dependencies`、`total_dependencies`，静态核对一致。
- 类型：Scanner 写入 `dict`/`int`；Service 接受 `Mapping` 并严格要求 `type(value) is int`。
- 缺字段：Service fail-closed，不会把缺失统计当成成功。
- 计数语义：skip_reason 的原始 truthiness、total 统计、skip 不生成 Finding，均有 Level A 覆盖。

### 5.2 尚未被跨层测试覆盖的风险

`RESIDUAL_INTERFACE_RISK = LOW`，不是“零风险”：

1. **未来漂移风险**：如果以后只改 Scanner 的字段名或 Service 的读取名，Level A/B 的 mock/fake 数据可能被同步修改，真实接口仍可能不一致；跨层测试会直接捕获该问题。
2. **应用装配风险**：当前测试没有验证 `app/bootstrap.py` 用真实 `PipAuditScanner` 构造 `DependencyAuditService` 的实际装配；该路径不是 RC-01 修改点，但属于完整运行时链路。
3. **真实工具输出形态风险**：Scanner 测试使用固定 JSON，未覆盖真实 pip-audit 在极端字段组合下的输出；不过 `_parse_with_statistics()` 的结构校验已覆盖主要形态。

当前没有“已确认的字段/类型不一致”：
`CONFIRMED_INTERFACE_MISMATCH = NONE`。

## 6. 方案 A：不新增跨层测试

支持理由：

- Level A 已使用真实 `PipAuditScanner.scan()` 和真实解析器，并 mock 外部 subprocess；它不是纯 fake。
- Level B 已完整覆盖 Service 对统计字段的校验、状态、Finding 保存顺序和异常分支。
- 两侧字段名、类型和缺失行为已静态核对一致。
- RC-01 当前风险主要是“未来漂移”，不是当前实现错误。

代价：

- `CROSS_LAYER_TEST=NOT_FOUND` 保持；
- 不能声称“真实 Scanner → 真实 Service”已由测试端到端验证；
- 若后续修改接口，需要人工记住同时更新两侧测试。

## 7. 方案 B：新增最小跨层测试

可行方案（设计级，不实施）：

- 新文件：`tests/test_rc01_cross_layer.py`；
- 2 个测试，不凑第三个：
  1. 完整审计：真实 `PipAuditScanner.scan()` + 真实 `DependencyAuditService.run_audit()`，mock `run_command` 返回完整 JSON；预期 COMPLETED。
  2. 部分 skip：真实 Scanner + 真实 Service，mock `run_command` 返回 `audited=1/skipped=1/total=2`；预期 FAILED、Finding 可按既有行为保存、无成功摘要。
- mock 边界：只替换 `scanners.pip_audit_scanner.run_command` 和必要的 `is_available`/`_executable`；不 mock `_parse_with_statistics()`、不 mock `_validate_statistics()`、不 mock `_map_findings()`/`_save_findings()`。
- 不需要真实网络、不需要真实 pip-audit 执行、不修改生产代码。
- 可复用 `tests/conftest.py` 的数据库/项目/授权/Scope 夹具；需要为真实 Scanner 设置 `cache_dir`/`temp_dir`，可复用 `tmp_path`；不需要新 fixture 类型。
- 新增文件/测试数量可控，不改变生产接口。

它能消除：

- 真实 Scanner metadata 到真实 Service 校验器的装配断点；
- 字段名/类型在真实对象上的集成错误；
- 未来只改单侧字段名的回归。

它不能消除：

- 真实 pip-audit 网络/外部服务差异；
- 应用生产数据库的实际运行；
- TOCTOU/路径等非 RC-01 问题。

## 8. 最小跨层测试可行性

可行性：**YES**。

现有基础设施已经足够：

- `tests/test_pip_audit_scanner.py:97-120` 已证明可以 mock `run_command` 并驱动真实 `PipAuditScanner.scan()`；
- `tests/test_dependency_audit_service.py:117-125` 已提供 `make_service` 的注入方式；
- `tests/conftest.py` 已有 `db`、`audit`、`projects`、`scopes`、`scope_validator`、`local_project`、`local_source`；
- 真实 `PipAuditScanner` 构造只需 `cache_dir`/`temp_dir`，可在 `tmp_path` 下创建；
- 不需要新依赖，不需要网络。

若未来实施，建议测试只覆盖 2 个核心场景，不添加第三个“非法 Scanner 输出”场景，因为当前真实 Scanner 的计数逻辑始终生成合法整数；非法 metadata 已由 Level B 的 Service 测试覆盖，重复测试没有实际价值。

## 9. 最终决策

```text
DECISION = WAIVE_CROSS_LAYER_TEST
```

理由：

1. 当前没有已确认的字段名、嵌套层级、类型或缺失处理不一致；静态接口与 Level A/B 双侧测试已对齐。
2. Level A 已经是“真实 Scanner + mock 外部进程”，不是纯 Scanner 字符串解析测试。
3. Level B 已覆盖 Service 对真实字段契约的消费、FAILED/COMPLETED 和 Finding 保存语义。
4. 跨层测试的价值主要是未来漂移防护，而不是当前 RC-01 正确性缺口；在没有真实装配失败证据时新增测试，收益低于维护成本。
5. 因而本次 RC-01 最终验收不把跨层测试列为必需项；但不得声称“跨层运行时验证已完成”。

保留条件：

- 若后续修改三个 metadata 字段、`ScanOutput.metadata` 类型、Service 的统计读取逻辑或 `app/bootstrap.py` 的 Scanner 装配，则必须重新评估并新增跨层测试。
- 若最终验收要求“真实 Scanner + 真实 Service”证据，应将该测试作为独立授权步骤实施，不作为本次静默补充。

## 10. UNKNOWN

```text
REAL_SCANNER_TO_REAL_SERVICE_RUNTIME_TEST = NOT_EXECUTED
APP_BOOTSTRAP_REAL_SCANNER_WIRING_TEST = NOT_FOUND
REAL_PIP_AUDIT_NETWORK_EXECUTION = NOT_EXECUTED
CURRENT_FULL_SUITE_RESULT = NOT_RUN_IN_THIS_STEP
PRODUCTION_DATABASE_BEHAVIOR = NOT_EXERCISED_IN_THIS_STEP
```

以上未知项不影响“当前字段契约静态一致”的结论，但限制了对端到端运行时的更强声明。

## 11. 声明

本步骤：

- 未修改生产代码；
- 未修改测试代码；
- 未新增/删除测试；
- 未执行 pytest；
- 未执行真实 pip-audit；
- 未访问真实网络；
- 未修改 Scanner、Service、数据库、Schema、GUI 或 JSON；
- 未修改 ACL 或系统权限；
- 未执行 Git add/commit/push/reset/restore/clean。

只新增本报告：

```text
docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md
```

最终状态：

```text
STEP_8_STATUS = INVESTIGATION_COMPLETED
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
NETWORK_ACCESS = NO
SCANNER_MODIFIED = NO
SERVICE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
JSON_WORK = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```
