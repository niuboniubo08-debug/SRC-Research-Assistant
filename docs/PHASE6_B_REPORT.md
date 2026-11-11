# 第六阶段 B 报告：统一报告数据服务

- 执行日期：2026-11-05（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：`0.5.0`
- 数据库 Schema：`v5`（本阶段未修改）
- 阶段状态：**阶段 B 完成；阶段 C 未开始**
- 本阶段没有生成 HTML/PDF/JSON 文件，没有修改报告页面，也没有安装 ReportLab/Pillow/中文字体

## 1. 本阶段完成情况

已建立：

```text
ReportService
└── ReportRepository
    └── Database
```

完成内容：

1. 新增统一不可变报告 DTO；
2. `ReportRepository.load_snapshot(project_id)` 单连接、单只读事务读取指定项目；
3. 显式只读保护：`PRAGMA query_only = ON`，并使用 `BEGIN` 开启读事务；
4. 一次读取 Project、Authorization、ScopeAsset、ScanTask、Finding、Evidence；
5. 在事务内构造 `ReportSnapshot` DTO，结束后 rollback 并释放连接；
6. `ReportService` 生成授权摘要、任务统计、Finding 统计、证据统计、数据范围、警告和已知限制；
7. 三类报告类型：漏洞分析、证据报告、项目综合安全研究报告；
8. 严格项目隔离；
9. 证据文件只读校验：受管路径、存在性、SHA-256；
10. 18 项定向测试和 144 项全量通过测试；
11. 本报告。

本阶段**没有**：

- 修改 `database/schema.py` 或 `database/connection.py`；
- 增加迁移或 schema 字段；
- 修改 `ui/report_page.py`、`ui/main_window.py`、`app/bootstrap.py`；
- 修改第三/四/五阶段业务逻辑；
- 实现导出器或报告 GUI；
- 安装任何新依赖。

## 2. 新增文件

```text
core/models/report.py
repositories/report_repository.py
services/report_service.py
tests/test_report_service.py
docs/PHASE6_B_REPORT.md
```

没有为阶段 B 新增或修改其他生产文件。

## 3. 修改文件

**没有修改任何生产文件。**

仅由质量检查工具重新生成：

```text
docs/acceptance/code_quality.json
```

该文件是检查结果输出，不是业务代码。阶段 B 没有修改 UI、扫描器、数据库 schema/connection、bootstrap 或第三/四/五阶段业务文件。

这是刻意的阶段边界：报告服务尚未注入 `AppContext`，尚未加入报告页面，尚未连接 UI。阶段 C/D/E 需要新的明确授权才能开始。

## 4. Report DTO 结构

文件：`core/models/report.py`

### 4.1 枚举

```python
class ReportType(str, Enum):
    VULNERABILITY = "vulnerability"
    EVIDENCE = "evidence"
    PROJECT_SUMMARY = "project_summary"

class ReportFormat(str, Enum):
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
```

### 4.2 ReportRequest

```python
@dataclass(frozen=True, slots=True)
class ReportRequest:
    project_id: int
    report_type: ReportType
    report_format: ReportFormat
    title: str = ""
    include_evidence_images: bool = False
    include_notes: bool = True
    requested_at: datetime | None = None
```

### 4.3 ReportFinding

```python
@dataclass(frozen=True, slots=True)
class ReportFinding:
    finding_id: int
    project_id: int
    task_id: int | None
    title: str
    category: str
    description: str
    severity: Severity
    severity_source: str
    confidence: Confidence
    scanner_name: str
    scanner_version: str
    rule_id: str
    file_path: str
    line_number: int
    recommendation: str
    status: FindingStatus
    manual_notes: str
    detected_at: datetime
    last_seen_at: datetime
    dependency_name: str | None
    dependency_version: str | None
    vulnerability_id: str | None
    fix_versions: tuple[str, ...]
    affected_versions: str | None
    evidence_count: int
    metadata: Mapping[str, Any]
    raw_metadata_omitted: bool = False
```

- 不重新定义 `Finding` 核心模型；该 DTO 只承载报告需要的字段。
- `metadata` 采用安全白名单并冻结；未知字段通过 `raw_metadata_omitted=True` 标明，而不是在导出时重新查询原始数据。
- `dependency_*`、`vulnerability_id`、`fix_versions`、`affected_versions` 为 `None`/空 tuple 表示原始数据缺失；不补造。
- 时间字段沿用项目 `from_db_time` 的 UTC aware datetime 语义。

### 4.4 ReportEvidence

```python
@dataclass(frozen=True, slots=True)
class ReportEvidence:
    evidence_id: int
    project_id: int
    finding_id: int
    finding_title: str
    evidence_type: EvidenceType
    title: str
    description: str
    file_name: str
    source: str
    file_path: str
    managed_path: str | None
    file_hash: str
    captured_at: datetime
    created_at: datetime
    file_exists: bool | None = None
    hash_matches: bool | None = None
    file_status_note: str = ""
```

- `file_exists=None` 表示没有文件（文本证据）或未校验；`False` 表示明确缺失/不可读。
- `hash_matches=None` 表示无记录哈希或无法读取；`False` 表示明确不一致。
- `file_path` 为数据库原始路径，导出器必须优先使用 `managed_path`，不得把原始绝对路径当作可访问路径。

### 4.5 ReportTaskSummary

```python
@dataclass(frozen=True, slots=True)
class ReportTaskSummary:
    task_id: int
    project_id: int
    task_type: ScanTaskType
    target: str
    status: ScanTaskStatus
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    result_summary: str
    error_message: str
    progress: int
    scanners: tuple[str, ...]
    current_scanner: str
```

### 4.6 ReportAuthorizationSummary

```python
@dataclass(frozen=True, slots=True)
class ReportAuthorizationSummary:
    as_of: datetime
    total_count: int
    effective_count: int
    confirmed_count: int
    expired_count: int
    pending_count: int
    revoked_count: int
    scope_asset_count: int
    active_scope_asset_count: int
    historical_scan_authorization_available: bool = False
    note: str = ""
```

- 只表示报告生成时刻的授权摘要。
- `historical_scan_authorization_available` 固定为 `False`：数据库没有扫描时授权快照，不能把当前状态倒推为历史状态。

### 4.7 ReportStats

```python
@dataclass(frozen=True, slots=True)
class ReportStats:
    task_count: int = 0
    task_status_counts: Mapping[str, int] = ...
    task_scanner_counts: Mapping[str, int] = ...
    finding_count: int = 0
    severity_counts: Mapping[str, int] = ...
    scanner_counts: Mapping[str, int] = ...
    finding_status_counts: Mapping[str, int] = ...
    dependency_finding_count: int = 0
    evidence_count: int = 0
    evidence_type_counts: Mapping[str, int] = ...
    file_evidence_count: int = 0
    missing_evidence_file_count: int = 0
    hash_mismatch_count: int = 0
```

- 任务状态、Finding 风险、Finding 状态、证据类型均预置**全部枚举键为 0**，因此 0 是已统计的零值，不是缺失。
- `task_scanner_counts` 和 `scanner_counts` 只包含实际出现的键；没有扫描器时为空映射，不伪造扫描器。
- 映射使用 `MappingProxyType` 冻结。

### 4.8 ReportSnapshot

```python
@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    snapshot_id: str
    report_type: ReportType
    project: Project
    authorization: ReportAuthorizationSummary
    tasks: tuple[ReportTaskSummary, ...]
    findings: tuple[ReportFinding, ...]
    evidence: tuple[ReportEvidence, ...]
    stats: ReportStats | None
    generated_at: datetime
    schema_version: int
    data_scope: tuple[str, ...]
    warnings: tuple[str, ...]
    known_limitations: tuple[str, ...]
```

- `stats` 在 Repository 原始快照中为 `None`；`ReportService` 补全统计后才交给导出器。
- `data_scope` 明确该报告类型应消费的部分；`findings`/`evidence` 仍只属于当前项目，不跨项目。
- `warnings` 记录空数据、缺失授权、失败任务、证据文件缺失/哈希不一致等，不以“通过”措辞替代。

### 4.9 ReportArtifact

```python
@dataclass(frozen=True, slots=True)
class ReportArtifact:
    report_type: ReportType
    report_format: ReportFormat
    project_id: int
    title: str
    generated_at: datetime
    snapshot_id: str
    path: str | None = None
    sha256: str | None = None
    warnings: tuple[str, ...] = ()
```

仅定义未来导出结果的结构；阶段 B 的 `ReportService.artifact_stub()` 返回 `path=None`、`sha256=None`，不创建任何文件。

## 5. Repository 查询范围

文件：`repositories/report_repository.py`

`ReportRepository.load_snapshot(project_id, report_type=PROJECT_SUMMARY, *, generated_at=None)`：

- 只使用项目现有 `Database.connection()`；
- 单个连接；
- 所有查询都带 `WHERE project_id = ?`：
  - `projects`
  - `authorizations`
  - `scope_assets`
  - `scan_tasks`
  - `findings`
  - `evidence`
- 全部使用显式列名，**没有 `SELECT *`**；
- 不读取其他项目、不读取项目外文件、不调用扫描器；
- 在事务内构造 `Project`、`Authorization`、`ScopeAsset`、`ScanTask`、`Finding`、`Evidence` 以及报告 DTO；
- 查询结束后 rollback 并释放连接。

关联字段：

- `findings` JOIN `projects` 获取 `project_name`，并用相关子查询计算每条 Finding 的证据数量；
- `evidence` JOIN `projects`，LEFT JOIN `findings` 获取 Finding 标题；
- 所有 ID、时间、状态由现有模型 `from_row` 解析，不复制字段定义。

## 6. 只读事务实现方式

`load_snapshot`：

```python
with self._db.connection() as connection:
    connection.execute("PRAGMA query_only = ON")
    connection.execute("BEGIN")
    try:
        return self._build_snapshot(...)
    finally:
        connection.rollback()
```

说明：

1. SQLite 没有 `BEGIN READ ONLY` 语法；使用 `PRAGMA query_only = ON` 使该连接上的写入直接失败，作为可执行的只读保护。
2. `BEGIN` 是显式事务边界；第一次 SELECT 建立该连接的读快照。
3. `PRAGMA query_only` 和 `BEGIN` 都在同一连接上，所有查询和 DTO 构造在事务结束前完成。
4. `finally` 中 rollback，随后 `with` 退出关闭连接。
5. 发生 SQLite 错误时包装为 `StorageError`；不会把错误吞掉当作成功。
6. 项目不存在时抛 `NotFoundError`，不返回空项目快照。

**没有修改** `database/connection.py` 或数据库连接架构。

## 7. SQLite 快照一致性验证结果

测试：`test_read_transaction_consistency_under_concurrent_write`

步骤：

1. 在临时数据库插入 1 条 Finding；
2. 手动打开连接并 `BEGIN`；
3. 用 `_build_snapshot` 读取第一次快照；
4. 另一个连接写入第 2 条 Finding；
5. 在同一读事务中再次读取；
6. rollback，再用新的 `load_snapshot` 读取。

结果：

```text
before.findings = 1
after.findings  = 1   # 同一读事务仍看到旧快照
outside.findings = 2  # 结束后新事务看到新数据
```

结论：当前 SQLite WAL 模式下的读事务确实提供一致性快照；不是仅凭“单连接”推断。该测试通过。

## 8. 项目隔离测试结果

测试 `test_project_isolation`：

- 项目 A 快照的所有 Finding `project_id` 均为 A；
- 项目 B 快照的所有 Finding `project_id` 均为 B；
- A 的 Finding ID 集合与 B 不相交；
- B 的证据 ID 不出现在 A 快照；
- 不存在的项目抛 `NotFoundError`；
- 0 项目 ID 抛 `NotFoundError`。

结果：全部通过；未发现跨项目读取。

## 9. 空数据测试结果

测试 `test_empty_project_snapshot` 和 `test_stats_zero_is_not_missing_data`：

- 空项目返回空 `tasks/findings/evidence`；
- `ReportStats` 中风险、状态、证据类型键存在且为 0；
- 没有任何“扫描通过”“不存在漏洞”的错误结论；
- 警告明确写出：
  - 项目没有扫描任务，不能推断扫描通过；
  - 项目没有 Finding，不能推断不存在漏洞；
  - 项目没有授权记录，报告不能作为授权完成证明。

结果：通过。

## 10. 原始数据未修改验证

测试 `test_original_data_is_not_modified`：

对比快照前后：

```text
findings count / open count
evidence count
scan_tasks count
```

结果完全一致。

补充：

- 没有 INSERT/UPDATE/DELETE；
- 没有修改 Finding 状态、人工备注或授权；
- 没有创建报告记录或文件；
- 只读事务 rollback；
- 证据哈希校验只读取受管文件，不写文件。

## 11. 新增测试数量

新增文件：`tests/test_report_service.py`

```text
18 tests
```

相对阶段 A/第五阶段基线：

```text
原基线：127 collected，126 passed，0 failed，1 skipped
新增：18 passed
最终：145 collected，144 passed，0 failed，1 skipped
```

跳过项仍是第五阶段遗留的 Windows 文件符号链接创建权限限制，不是本阶段新增失败。

## 12. 定向测试结果

命令：

```powershell
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests\test_report_service.py
```

结果：

```text
18 passed in 3.86s
```

覆盖：

- 三类报告快照；
- 正常项目数据；
- 空数据；
- 部分字段缺失（text evidence、无 metadata、无截图）；
- 项目隔离；
- 不存在项目；
- 授权摘要和授权缺失；
- Finding 统计；
- Evidence 统计与 SHA-256；
- ScanTask 统计；
- 原始数据不变；
- DTO 不可变；
- 单事务一致性；
- 并发写入快照；
- 异常连接释放；
- 0 与缺失区分；
- 默认 `load_snapshot(project_id)` 类型；
- 报告请求和 artifact 空结果。

## 13. 完整测试结果

命令：

```powershell
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
```

结果：

```text
144 passed, 1 skipped in 38.44s
```

与阶段 B 前基线对比：

| 指标 | 阶段 B 前 | 阶段 B 后 |
|---|---:|---:|
| collected | 127 | 145 |
| passed | 126 | 144 |
| failed | 0 | 0 |
| skipped | 1 | 1 |
| 新增失败 | — | 0 |

唯一 skip：

```text
tests/test_evidence_service.py:184
当前 Windows 会话无法创建符号链接：
[WinError 1314] 客户端没有所需的特权
```

该 skip 是第五阶段既有环境限制；本阶段没有降低断言或删除测试。

## 14. 真实执行、模拟测试和测试夹具

### 真实执行

- 使用 `storage/phase5_acceptance/acceptance.db` 的真实第五阶段验收数据执行只读 ReportSnapshot；
- 项目 1：22 条 Finding（3 条真实 Bandit + 19 条第四阶段真实 pip-audit）、3 份 Evidence、2 个 ScanTask；
- 风险统计：high=1、medium=20、low=1、critical=0、info=0；
- 扫描器统计：bandit=3、pip-audit=19；
- schema 5；
- 授权摘要为 0 条授权记录，报告如实警告，没有补造授权；
- 执行前后数据库 schema 仍为 v5；没有写入。

### 测试夹具/模拟

- `tests/test_report_service.py` 使用临时 SQLite 和确定性 `insert_finding`/`insert_task` 夹具；
- 3 个扫描器示例（Bandit/Semgrep/pip-audit）是单元测试夹具，**不是**真实扫描；
- 并发写入测试使用临时数据库和第二个连接，不涉及真实目标；
- 证据文件测试使用临时受管目录和测试字节。

### 未声称真实执行

- Semgrep 实际运行：仍受 Windows CA 存储限制，未运行；
- 阶段 C/D/E 的 HTML/PDF/JSON 文件生成：未实现，未执行；
- 远程扫描/配置检查：本阶段没有执行。

## 15. 已知问题和技术限制

1. `ReportSnapshot` 仍携带当前项目的完整 Finding/Evidence 集合；`data_scope` 只标记各类报告应消费的章节。阶段 C/D 的导出器必须遵守 scope，不能把不需要的章节写入报告。
2. `ReportService` 未注入 `app/bootstrap.py`；阶段 B 只提供数据服务，尚未连接 GUI，这是授权的阶段边界。
3. `ReportService` 的证据哈希/存在性校验只有在调用方传入 `evidence_root` 时启用；当前阶段没有 UI 传参路径。
4. 数据库没有历史扫描时的授权快照，`historical_scan_authorization_available=False`；报告只能显示当前授权摘要。
5. 数据库没有统一“真实/测试夹具”来源字段；报告不会自动把夹具标记为真实，而是给出通用限制说明，要求人工核对。
6. `ReportEvidence.file_path` 保留数据库原始绝对路径供内部校验；阶段 C 导出器必须只输出 `managed_path` 或受控文件名，不能直接序列化该字段。
7. Semgrep 真实运行仍待 Linux/WSL；pip-audit 的 severity/affected range 仍保持原有限制，报告不补造。
8. 没有 ReportLab、Pillow、QtWebEngine/QtPdf 或合法中文字体；PDF 导出被阻止，等待独立字体授权和技术验证。
9. 没有跨扫描 Finding 去重。
10. 没有 `reports` 表写入；阶段 B 不创建报告记录，不改变 Schema v5。

## 16. 数据库 Schema 是否保持 v5

**是。**

- 本阶段未修改 `database/schema.py`；
- 未修改 `database/connection.py`；
- 未增加迁移；
- 未执行 `ALTER TABLE`/`CREATE TABLE`；
- 真实验收快照读取后 `PRAGMA user_version = 5`；
- 主库仍为 v5。

## 17. 前五阶段功能是否受到影响

**未受影响。**

- 完整测试：144 passed / 1 skipped；
- 第五阶段基线：126 passed / 1 skipped；
- 新增 18 项全部通过；
- 跳过项仍是原有 Windows 符号链接权限；
- 未修改 UI、扫描器、漏洞管理、证据中心、数据库 schema 或 bootstrap；
- 未改变任何原始 Finding、Evidence、ScanTask 或授权。

## 18. 下一阶段建议

1. 只有收到新的明确授权后，才进入阶段 C：HTML 导出。
2. 阶段 C 只消费 `ReportSnapshot`，不得自行查询数据库。
3. HTML 导出必须：
   - 自动转义；
   - 不加载远程资源；
   - 不输出 `ReportEvidence.file_path` 原始绝对路径；
   - 不把 `warnings` 中的空数据误写成“扫描通过”。
4. PDF 必须等待合法的中文字体资源（Noto Sans SC/OFL）和 ReportLab 技术验证；当前不得安装或临时下载。
5. JSON 导出需要白名单序列化，排除内部原始路径和未经允许的 metadata。
6. 阶段 B 到此停止，不自动进入阶段 C。
