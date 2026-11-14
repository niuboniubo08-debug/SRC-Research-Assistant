# Phase 6 Stage 1B-2C：RC-01 统计契约最终确认

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 性质：READ_ONLY / DESIGN_ONLY
- 已批准：不完整审计 → FAILED；禁止假“无漏洞”；不需要 Schema 迁移；`DATA_CARRIER = ScanOutput.metadata`
- 本报告全部建议：`PROPOSED`
- `PRODUCT_APPROVED = NO`
- `IMPLEMENTATION_APPROVED = NO`

## 1. 已确认前提

1. `ScanOutput` 已存在 `metadata: Mapping[str, Any]`（`scanners/base.py:66-70`），且当前已承载 `audited_dependencies`。
2. `PipAuditScanner.scan()` 已把 `audited_dependencies` 写入 metadata（`scanners/pip_audit_scanner.py:194-208`）。
3. 当前 `parse_output()` 返回 `(findings, warnings, len(dependencies))`（`:210-311`），将 skipped 记录计入了审计数。
4. `DependencyAuditService.run_audit()` 只读取 `audited_dependencies`，仅当它为 0 时失败（`services/dependency_audit_service.py:325-338`）。
5. `DependencyAuditOutcome` 没有 skipped/total/complete 字段；`scan_tasks` 没有独立统计列。
6. 因此，RC-01 不需要新数据库字段、新任务状态或新 Schema。

## 2. 每个候选字段的结论

### 2.1 `audited_dependencies`

**结论：保留。**

- 它是现有 metadata 键，不能删除；否则会破坏现有扫描器接口与测试。
- 但必须修正语义：从“`len(dependencies)`”改为“真正完成漏洞查询的依赖数”。
- **不计入**带非空 `skip_reason` 的记录；也不计入非 dict、缺 name/version、`vulns` 非 list 的记录。
- 一条记录即使发现多个漏洞，也只计 1 个 audited dependency；Findings 可多个。

### 2.2 `skipped_dependencies`

**结论：建议保留，属于 RC-01 最小可解释字段。**

- 没有它，service 仍可用 `audited < total` 判定失败，但无法区分“被 pip-audit 跳过”与“输入记录非法”，也无法生成准确的“审计不完整：N 中跳过 M”说明。
- 对 RC-01 的“不得假称无漏洞”而言，状态门禁只需要 `audited + total`；但为了保证不把 skipped 静默吞掉并让 UI/测试可解释，保留 `skipped` 是本文推荐的最小结构。
- 精确定义：`dependencies` 数组中，dict 且 `skip_reason` 为非空字符串的记录数；即使该记录同时带有 `vulns`，也按 skipped 处理，不生成审计 Finding。

### 2.3 `total_dependencies`

**结论：必需。**

- 没有 total，无法知道部分 skipped 或非法记录是否存在；只有 audited 无法区分“完整审计 0 漏洞”和“只审计了一部分”。
- 精确定义：`payload["dependencies"]` 数组的元素总数，包括正常、skipped、非 dict 和其他非法记录。
- `total` 必须来自原始数组长度，不能只统计 dict 或只统计有 `vulns` 的项。

### 2.4 `invalid_dependencies`

**结论：不属于 RC-01 最小修复必需字段，建议不引入。**

- 非 dict、缺必要字段、`vulns` 非 list 的记录可以统一表现为：

```text
audited + skipped < total
```

- service 只需把这种“差额”视为不完整并 FAILED，不需要额外字段。
- 新增 `invalid_dependencies` 会扩大 metadata 契约、测试矩阵和 UI 文案范围，但对“是否完整”的判定没有新增必要信息。
- 如未来需要诊断具体非法原因，应作为独立改进另行批准，不能搭车进入 RC-01。

### 2.5 `audit_complete`

**结论：不放入 metadata，由 Service 派生。**

比较：

| 方式 | 优点 | 问题 |
|---|---|---|
| metadata 直接携带 bool | 读取简单 | scanner 可输出与计数矛盾的 true；多一个可伪造/不一致字段；测试需维护两份真相 |
| Service 根据计数派生 | 单一真相；计数矛盾自然 fail closed | 需要 service 集中实现不变量 |

推荐 **Service 派生**：

```text
audit_complete =
    total > 0
    and audited == total
    and skipped == 0
```

并在读取时校验 `audited + skipped <= total`。不把 `audit_complete` 写入 `ScanOutput.metadata`，也不新增 DTO。

## 3. 最小字段集合

```text
ScanOutput.metadata:
    audited_dependencies: int   # 现有键，修正语义
    skipped_dependencies: int   # 新增，用于解释不完整
    total_dependencies: int     # 新增，用于判断是否完整
```

明确不加入：

- `invalid_dependencies`
- `audit_complete`
- `vulnerabilities_found`
- 新 DTO、`ScanOutput` 字段、`DependencyAuditOutcome` 字段
- 数据库字段或新状态

## 4. 每个字段的精确定义

### 4.1 audited_dependencies

计数条件（全部满足）：

1. 记录是 JSON object（dict）；
2. `name` 去空白后非空；
3. `version` 去空白后非空；
4. `vulns` 是 list；
5. `skip_reason` 去空白后为空。

计数单位是“依赖记录”，不是漏洞数。多个漏洞去重后仍只增加 1 次 audited。

### 4.2 skipped_dependencies

计数条件：

1. 记录是 JSON object；
2. `skip_reason` 去空白后非空。

优先级：`skip_reason` 高于 `vulns`。带 skip_reason 的记录不计 audited，不生成 Finding，只计 skipped。

### 4.3 total_dependencies

等于 `len(payload["dependencies"])`，包含：

- 正常记录；
- skipped 记录；
- 非 dict 元素；
- 缺 name/version 或 `vulns` 非 list 的记录。

如果 `dependencies` 不是 list，属于解析错误，不进入统计契约，而是 `ScannerParseError` → FAILED。

### 4.4 不引入的字段

`invalid_dependencies` 不是必需：非法项的差额由 `total - audited - skipped` 表达。该差额大于 0 时审计不完整。

## 5. 一致性规则

对 metadata 的三个整数使用以下最小不变量：

```text
audited >= 0
skipped >= 0
total >= 0

audited + skipped <= total
```

完整性判定：

```text
audit_complete =
    total > 0
    and skipped == 0
    and audited == total
```

由此：

- `total == 0`：空审计，**不得** COMPLETED，必须 FAILED；
- `audited == 0`：没有任何依赖完成审计，FAILED；
- `skipped > 0`：审计不完整，FAILED；
- `audited + skipped < total`：存在非法/未分类记录，FAILED；
- `audited + skipped > total`：计数矛盾，FAILED；
- 只有 `total > 0`、`skipped == 0`、`audited == total` 才允许 COMPLETED。

0 个 Finding 不等于无漏洞：必须同时满足 `audit_complete == True` 才能显示“未发现已知漏洞”。

## 6. 缺失/非法数据的 fail-closed 规则

以下任一情况都视为不完整/非法，任务必须 FAILED，且不得显示“未发现漏洞”：

1. metadata 缺失 `audited_dependencies`、`skipped_dependencies` 或 `total_dependencies`；
2. 值为 `None`、字符串、浮点数、bool（bool 虽为 int 子类，也必须拒绝）或负数；
3. `audited + skipped > total`；
4. `total == 0`；
5. `skipped > 0`；
6. `audited + skipped < total`（存在非法/未分类记录）；
7. `audited == 0`；
8. `findings` 中存在来自 skipped/invalid 记录的 Finding（解析阶段应阻止）。

建议错误消息明确区分：

- “审计输入不完整，不能判定无漏洞”；
- “没有依赖完成审计”；
- 不得使用“未发现已知漏洞”。

具体错误文案未批准。

## 7. `audit_complete` 的承载或派生建议

推荐 **不承载，完全由 Service 派生**：

- `ScanOutput.metadata` 只携带三个原始计数；
- `DependencyAuditService` 读取、校验、计算 `audit_complete`；
- 任务状态仍使用现有 `COMPLETED`/`FAILED`，不新增状态；
- 不把 `audit_complete` 写入数据库；
- UI 根据 FAILED/error_message/result_summary 展示“不完整”，不直接信任 scanner 布尔值。

这是最小且最不易出现“计数与标志矛盾”的方案。

## 8. 明确未批准的实现细节

- 三个 metadata 键的最终名称（本报告使用 `audited_dependencies`、`skipped_dependencies`、`total_dependencies`，是 `PROPOSED`）。
- 是否保留 `invalid_dependencies`（本报告建议不引入，未批准）。
- `parse_output()` 的最终返回形状（继续返回三元组、四元组或具名结果，均未批准）。
- 是否将 `audited_dependencies` 重命名（不建议）。
- 是否给 `DependencyAuditOutcome` 增加 skipped/total/complete 字段（未批准）。
- 具体错误消息、UI 文案和日志字段（未批准）。
- metadata 缺失时是否兼容旧 fake scanner（本报告要求 fail closed，未批准为最终实现策略）。
- 是否将统计写入 `scan_tasks.result_summary` 之外的审计日志字段（未批准）。

## 9. 未确认事项

- `pip-audit` 对非 dict、缺 name/version、`skip_reason` 与 `vulns` 同时存在的真实 JSON 形态，尚无当前运行样本。
- `total_dependencies` 是否应包含非 dict 元素：本报告建议包含（保证差额可见）；尚需真实样本确认。
- skipped 记录是否总是没有 version/vulns：当前样例没有，但不能假定所有版本一致。
- `skipped_dependencies` 是否最终被产品视为“最小必需”还是“最小可解释”；本报告建议保留，需人工确认。
- 三个计数的序列化类型/范围检查由 scanner 还是 service 承担，尚未批准。
- 是否需要把 skipped 原因逐条持久化，尚未批准。

## 10. 文件变化状态

- 唯一新增文件：`docs/PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md`
- 生产代码：未修改
- 测试：未修改
- 数据库/Schema：未修改
- UI：未修改
- pytest/pip-audit/GUI：未运行
- Git：未执行 add/commit/push/reset/restore/clean

```text
STATISTICS_CONTRACT_DESIGN = COMPLETE
PRODUCTION_CODE_MODIFIED = NO
TESTS_MODIFIED = NO
PYTEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

Git 参考（只读）：branch `main`，HEAD `bffb5ac82bbebe7fef5992f87ff90494c9776ace`，staged 0；本报告为新增未跟踪文件，原有 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 及其他未跟踪报告未改动。
