# Phase 6 Stage 1B-2B：RC-01 最小数据接口承载位置

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 性质：READ_ONLY
- 已批准规则：不完整审计 → FAILED；禁止假“无漏洞”；不新增任务状态；不需要 Schema 迁移
- 结论标签：`PROPOSED`
- `PRODUCT_APPROVED = NO`
- `IMPLEMENTATION_APPROVED = NO`

## 1. 实际数据路径

当前 RC-01 相关数据只沿以下路径流动：

```text
pip-audit JSON
  -> PipAuditScanner.parse_output()
       (findings, warnings, audited)          # 当前三元组
  -> PipAuditScanner.scan()
       ScanOutput(findings, warnings, metadata)
       metadata["audited_dependencies"]       # 当前唯一结构化计数
  -> DependencyAuditService.run_audit()
       audited = metadata["audited_dependencies"]
       if audited == 0 -> FAILED
       else -> 映射/保存 Finding -> 固定摘要 -> COMPLETED
```

关键位置（当前代码）：

| 位置 | 事实 |
|---|---|
| `scanners/base.py:66-70` | `ScanOutput` 已有 `findings`、`warnings`、`metadata: Mapping[str, Any]` |
| `scanners/pip_audit_scanner.py:194-208` | `scan()` 调用 `parse_output()`，并把 `audited_dependencies` 写入 `ScanOutput.metadata` |
| `scanners/pip_audit_scanner.py:210-311` | `parse_output()` 返回 `(findings, warnings, len(dependencies))` |
| `services/dependency_audit_service.py:69-77` | `DependencyAuditOutcome` 只有 `audited_dependencies`，没有 skipped/total/complete |
| `services/dependency_audit_service.py:325-338` | 只以 `audited == 0` 作为失败门禁 |
| `services/dependency_audit_service.py:356-373` | 完整/0 漏洞都写成 COMPLETED 摘要 |
| `services/dependency_audit_service.py:516-599` | `_finish(..., skipped: tuple[str, ...])` 参数存在但未被使用；审计 details 只记录 `audited_dependencies` |
| `database/schema.py:47-58` | `scan_tasks` 只有 status、summary、error 等字段，无审计统计列 |

因此，当前真正可复用的结构化承载点只有一个：**`ScanOutput.metadata`**。`warnings` 只是字符串，不能作为可靠计数来源；`ScanTask` 没有独立统计字段；`DependencyAuditOutcome` 没有 skipped/total。

## 2. 候选承载位置

### 候选 A：扩展现有 `ScanOutput.metadata`（扁平键）

在 `PipAuditScanner.scan()` 的现有 metadata 中增加：

```text
audited_dependencies       # 已完成审计的依赖数（排除 skipped/invalid）
skipped_dependencies       # 有 skip_reason 的依赖数
invalid_dependencies       # 非 dict/缺必要字段的依赖数
total_dependencies         # dependencies 数组总记录数
```

`audit_complete` 建议由 service 根据不变量计算，而不是相信 scanner 布尔值：

```text
audit_complete =
    total > 0
    and skipped == 0
    and invalid == 0
    and audited == total
```

- 需要改：`PipAuditScanner.scan/parse_output`、`DependencyAuditService.run_audit`、相关测试。
- 不需要改：`ScanOutput` 类型、`BaseScanner`、数据库 Schema、`ScanTaskStatus`。
- 类型安全：弱（`Mapping[str, Any]`），但当前 `audited_dependencies` 已是同类用法。

### 候选 B：给 `ScanOutput` 增加显式字段

例如：

```python
@dataclass(frozen=True, slots=True)
class ScanOutput:
    findings: tuple[Finding, ...]
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    audited_dependencies: int | None = None
    skipped_dependencies: int | None = None
    total_dependencies: int | None = None
```

- 需要改：`scanners/base.py`、所有构造 `ScanOutput` 的 scanner/fake/tests。
- 不需要 Schema 迁移。
- 类型安全更好，但为了一个 pip-audit 专属语义修改通用接口，影响面大于候选 A。

### 候选 C：新增 `DependencyAuditStats` DTO / `PipAuditParseResult`

新增独立 dataclass，并由 `ScanOutput.metadata` 或 `ScanOutput` 新字段携带。

- 需要改：新类型、scanner 返回、service、测试；可能还要处理类型循环。
- 不需要 Schema。
- 可读性/类型安全最好，但产生新的公开接口面，超出“最小承载”。

### 候选 D：增加数据库字段或新任务状态

例如 `scan_tasks.audited_dependencies`、`skipped_dependencies` 或 `partial` 状态。

- 需要 Schema 迁移、CHECK 变更、迁移备份、查询/UI 审查。
- 与 `SCHEMA_MIGRATION = NOT_REQUIRED`、`NEW_TASK_STATUS = NOT_APPROVED` 冲突。
- 不是最小方案，当前不应采用。

### 候选 E：只写 `warnings` 字符串

- 不增加字段，但 service/UI 只能解析自然语言，测试脆弱，无法可靠断言 skipped/total。
- 不符合“结构化数据传递”的目标，拒绝。

## 3. 最小修改比较

| 候选 | 最小修改范围 | 架构一致性 | 测试可验证性 | Schema |
|---|---|---|---|---|
| A. `ScanOutput.metadata` 扁平计数 | 小：pip-audit scanner + dependency service + 测试 | 高：已有 `audited_dependencies` 先例 | 高：service/fake 直接读键，无需 UI 交互 | 不需要 |
| B. `ScanOutput` 新字段 | 中：base + 所有构造者/fakes + tests | 中：通用模型为一个工具扩展 | 高 | 不需要 |
| C. 新 DTO/parse result | 中到大：新类型 + scanner + service + tests | 中：新增公共抽象 | 高 | 不需要 |
| D. DB 字段/新状态 | 大：schema v6 + 迁移 + 查询 + UI | 低：违反已批准约束 | 中 | 需要，禁止 |
| E. warnings 字符串 | 很小 | 低 | 低：只能字符串匹配 | 不需要 |

结论：**A 的修改面最小，且与现有 `metadata["audited_dependencies"]` 一致。**

## 4. 推荐方案

> `PROPOSED`  
> `PRODUCT_APPROVED = NO`  
> `IMPLEMENTATION_APPROVED = NO`

推荐采用 **候选 A**：

```text
ScanOutput.metadata = {
    "audited_dependencies": int,
    "skipped_dependencies": int,
    "invalid_dependencies": int,
    "total_dependencies": int,
}
```

由 `DependencyAuditService` 读取并校验：

```text
total > 0
audited + skipped + invalid == total
audited > 0 仅表示至少一项完成，不表示 complete
audit_complete = skipped == 0 and invalid == 0 and audited == total and total > 0
```

理由：

- 现有 `ScanOutput.metadata` 已经是 scanner → service 的真实数据通道；
- 不改变 `BaseScanner` 公共形状，不新增 DTO；
- 不需要 Schema/任务状态变更；
- fake scanner 可在 metadata 中构造 skipped，测试成本低；
- 服务端可以 fail closed：metadata 缺失/计数不一致/`total<=0` 均视为不完整，而不是默认成功；
- 不把 `audit_complete` 的真相交给 scanner 单方面布尔值，减少“计数和标志矛盾”的风险。

`DependencyAuditOutcome` 是否需要新增 skipped 字段，是**下游 API 的另一项决定**，不属于本最小承载位置结论，当前未批准。

## 5. 明确未批准事项

以下均未获批准，不得在后续实施中自行选择：

- 修改 `parse_output()` 为三元组、四元组或其他新返回形状；
- 新增 `PipAuditParseResult`/`DependencyAuditStats` 等 DTO；
- 给 `ScanOutput` 增加字段；
- 给 `DependencyAuditOutcome` 增加 skipped/total/complete 字段；
- 新数据库列、`scan_tasks` 统计列或 Schema 迁移；
- 新增 `partial` 等任务状态或修改 `ScanTaskStatus`；
- 修改 UI 文案/结构（本轮只允许调查）；
- 固定 metadata 键名（本报告使用 `skipped_dependencies` 等是 `PROPOSED`，不是已批准契约）；
- 是否把 `audit_complete` 作为 scanner 输出或 service 派生值；
- 是否在 `audit.jsonl`/task details 中持久化每个 skipped 依赖的名称。

本报告只推荐承载位置，不实施任何接口形状。

## 6. 未确认事项

- `pip-audit` 对“非 dict”“缺 name/version/vulns”“skip_reason 同时有 vulns”的具体 JSON 形态尚无当前运行样本；计数规则需实现时以真实样本验证。
- 计数的严格口径（invalid 是否包含无 name/version 的 skipped）尚未最终批准。
- metadata 键名、类型、是否允许负数/缺失、是否要求常量集中定义，尚未批准。
- `audit_complete` 是 scanner 输出还是 service 计算，尚未批准；本报告推荐后者。
- `DependencyAuditOutcome`/UI 是否需要结构化 skipped 展示，尚未批准。
- 历史 fake scanner 缺少新键时，service 应 fail closed 还是兼容默认值，尚未批准；按“不完整不得成功”原则不应默认完整。
- 是否需要保留旧的 `audited_dependencies` 键名（当前已有）尚未批准，但为最小兼容建议保留。

## 7. 文件变化状态

- 唯一新增文件：`docs/PHASE6_STAGE1B2B_RC01_DATA_INTERFACE_DESIGN.md`
- 生产代码：未修改
- 测试：未修改
- 数据库/Schema：未修改
- UI：未修改
- pytest/pip-audit/GUI：未运行
- Git：未执行 add/commit/push/reset/restore/clean

```text
DATA_INTERFACE_INVESTIGATION = COMPLETE
FILES_MODIFIED_EXCEPT_REPORT = NO
TESTS_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
PYTEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

Git 参考（只读）：branch `main`，HEAD `bffb5ac82bbebe7fef5992f87ff90494c9776ace`，staged 0；本报告为新增未跟踪文件，原有 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 及其他未跟踪报告未改动。
