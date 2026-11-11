# SRC Research Assistant — 项目历史重建：Phase 6

- 调查日期：2026-11-06（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：`0.5.0`
- 当前数据库 Schema：`v5`
- 调查性质：只读历史/架构调查
- 本次唯一新增文件：`docs/PROJECT_HISTORY_PHASE6.md`
- 本次未修改生产代码、测试代码、数据库、Schema、依赖、Phase 5 归档、Phase 6B 归档或 Manifest
- 本次未执行完整 pytest 回归；只执行了不会写入项目内容的收集检查
- **Phase 6C-2 未开始**

## 0. 结论先行

```text
Phase 6A   = completed（仅架构/可行性调查；没有独立 A 文档，结论为 inferred）
Phase 6B   = completed / sealed_with_recorded_exception
Phase 6C-1 = completed（仅 HTML 实施前调查，无 HTML 代码）
Phase 6C-1R= completed（仅 pytest 临时目录诊断/恢复，无产品代码）
Phase 6C-2 = not started
Phase 6D/E/F = not started
Phase 6 总体 = 未完成，停在 C2 之前
```

关键结论：

1. **Phase 6 真正实现的只有 Phase 6B 的只读报告数据层**：`core/models/report.py`、`repositories/report_repository.py`、`services/report_service.py` 和 `tests/test_report_service.py`。它只生成不可变 `ReportSnapshot`，不渲染任何报告。[confirmed]
2. **没有任何 HTML/PDF/JSON exporter，也没有报告模板、报告 GUI 接入、`reports` 表写入或报告文件**。[confirmed]
3. `ui/report_page.py` 仍是占位页；`ui/main_window.py:197` 仍实例化 `ReportPage()`；`app/bootstrap.py` 没有注入 `ReportService`。[confirmed]
4. 当前 Schema 仍是 **v5**。`reports` 表在 Phase 5 之前已存在，列为 `report_id, project_id, report_format, file_path, generated_at, created_at`；主库和 Phase 5 验收库的 `reports` 均为 **0 行**。没有 v6，没有迁移。[confirmed]
5. Phase 6B 没有修改 Phase 5 的业务代码。抽查的 10 个 Phase 5 关键文件与 Phase 5 清单哈希一致；Phase 5 验收库哈希仍为 `03de4950...4ceb4c8`。[confirmed]
6. Phase 6B 归档当前实际为 **10 个文件**，清单覆盖 **14 个条目且 14/14 哈希匹配**，清单自身 SHA-256 为 `d898d4e091fc72f2885cb6db2ca99ba856552d06172ee99af2e57c6729463c6f`。[confirmed]
7. Phase 6B 的早先 `PHASE6_B_ACCEPTANCE.json` / `PHASE6_B_FINAL_SUMMARY.md` 仍写“9 个文件 / 11 条清单”等旧值；这是归档同步前的历史元数据，与当前文件系统/最终清单不一致。[contradicted，属于可解释的时序差异]
8. C1 只做 HTML 环境、字段风险、模板/安全/原子写入/测试计划调查，没有创建任何生产功能。[confirmed]
9. C1 的完整 pytest 尝试出现 **1 failed / 7 passed / 137 errors**，错误集中在 pytest-qt 临时目录 setup/清理和 `TemporaryDirectory` cleanup；不是产品断言失败。[confirmed]
10. C1R 已用专用临时目录 + full-access 测试进程恢复完整回归：**145 collected / 144 passed / 1 skipped / 0 failed / 0 errors / 40.94s / exit 0**。[confirmed，但仅在该测试执行环境下]
11. 当前普通 workspace-write 环境仍不能稳定完成完整 pytest；本次只确认 **145 tests collected in 0.71s**，没有新的普通完整绿色回归。[confirmed]
12. **当前不能按普通工作流直接进入 C2**：设计条件满足，但测试环境仅在有专用临时目录和 full-access 的条件下满足；且 C2 尚未获得明确授权。[confirmed]

## 1. Phase 6 启动背景

### 1.1 启动前的系统状态

Phase 5 已完成并封存：

- 版本 `0.5.0`；
- Schema `v5`；
- Phase 5 有 41 条 Finding、3 份 Evidence、2 条状态历史；
- 主库 `storage/src_research.db` 和 `storage/phase5_acceptance/acceptance.db` 均完整；
- Phase 5 已有统一 Finding、ScanTask、漏洞状态、证据和项目隔离；
- `ui/report_page.py` 仍为占位页。

Phase 5 的核心归档（`docs/acceptance/phase5_final/`）有 10 个文件；除清单自身外 9 个文件与清单匹配，`PHASE5_FINAL_SUMMARY.md` 的已知 SHA-256 为 `645abf1228ec8ca3081ee98e64f34bd4acf75481a1312c62cff7b7d514c74ba6`。[confirmed]

### 1.2 为什么启动报告中心

[inferred] 启动动机来自 Phase 5 之后的自然缺口：已有项目、授权、扫描任务、Finding、证据和统计，但 `报告中心` 仍然只是占位页，无法把已复核的数据整理成可交付、可归档的报告。

直接证据：

- `ui/report_page.py:6-19` 仍显示占位内容，明确列出未来能力：Jinja2 HTML/可打印 PDF、机器可读 JSON、授权/限制/风险分析、生成记录和文件完整性追踪。
- `docs/PHASE6_C1_HTML_INVESTIGATION.md:3.1` 把 `ui/report_page.py` 状态记录为 `PlaceholderPage`，并确认它未接入 `ReportService`。
- `docs/PHASE6_B_REPORT.md:406` 使用“阶段 A/第五阶段基线”这一表述，证明 Phase B 之前存在一个架构/环境评估阶段。

### 1.3 无法确认的事实

[unknown] 没有找到 Phase 6 的原始用户请求文本、启动日期或 Phase 6A 的独立文档，因此不能把“Phase 6A 的精确启动原因/范围”写成有直接快照的事实。

## 2. Phase 6 总体目标

### 2.1 原始目标（按现有文档可确认的部分）

Phase 6 的目标是建立报告中心：

- 从已有项目、授权、扫描任务、Finding、Evidence 生成报告；
- 支持 HTML、PDF、JSON 三种格式；
- 保留授权边界、检测限制、风险统计和证据完整性；
- 不访问远程目标，不伪造扫描结果；
- 报告只消费项目范围数据。

证据：

- `ui/report_page.py` 的占位文案；
- `docs/PHASE6_C1_HTML_INVESTIGATION.md` 第 3 节；
- `docs/PHASE6_B_REPORT.md` 第 18 节；
- `core/models/report.py:37-74` 的 `ReportType`/`ReportFormat`；
- C1 第 12 节的 C2 建议。

### 2.2 目标边界

Phase 6 **不是**：

- 远程扫描；
- 漏洞利用；
- 自动攻击；
- 证据上传/执行；
- 无授权项目的报告；
- 用 0 Finding 推断“没有漏洞”；
- 用无任务推断“扫描通过”；
- 把 Semgrep 夹具/模拟数据写成真实 Semgrep 扫描。

上述真实性约束在 `services/report_service.py:62-73`、`:266-306` 和 C1 第 3.4/13 节中有明确实现或设计要求。[confirmed]

## 3. Phase 6A：报告中心架构调查

### 3.1 调查内容

Phase 6A 是 Phase 6 的架构/可行性阶段，不是实现阶段。没有找到独立的 `PHASE6_A_*.md`、Phase 6A acceptance JSON 或 Phase 6A 代码提交记录。[confirmed 的“不存在”]

可从现有材料还原的 6A 调查内容：

- `reports` 表是否已经存在；
- 是否需要 Schema v6；
- 报告输出目录；
- HTML/PDF/JSON 的可行性与依赖；
- Jinja2；
- ReportLab；
- 中文字体；
- Qt WebEngine/QtPdf；
- 报告预览；
- 证据图片；
- 最终结论和进入 B 的条件。

证据：

- `docs/PHASE6_C1_HTML_INVESTIGATION.md:1,3`;
- `docs/PHASE6_B_REPORT.md:406`;
- `docs/PHASE6_B_REPORT.md:18`（阶段 B 停止条件）；
- `database/schema.py:95-104`;
- `requirements.txt`。

### 3.2 环境与依赖（实际只读检查）

| 项目 | 实际结果 | 证据强度 |
|---|---|---|
| Python | 3.14.4 | confirmed |
| PySide6 | 6.12.0 | confirmed（历史报告；当前环境） |
| Jinja2 | 3.1.6，可导入 | confirmed |
| MarkupSafe | 3.0.4 | confirmed |
| `requirements.txt` 的 Jinja2 声明 | `Jinja2>=3.1,<4` | confirmed |
| ReportLab | 未安装 | confirmed |
| Pillow | 未安装 | confirmed |
| PyMuPDF / pypdf | 未安装 | confirmed |
| QtWebEngine / QtPdf | 未安装 | confirmed |
| 报告输出目录 | `storage/reports/`，仅 `.gitkeep`（54 bytes） | confirmed |
| `reports/` 包 | 仅 `__init__.py`（75 bytes） | confirmed |
| 报告模板/CSS/JS | 不存在 | confirmed |

没有安装、升级、卸载任何依赖；没有修改 `requirements.txt`。

### 3.3 PDF/字体限制

[confirmed] 当前没有 ReportLab、Pillow、Qt WebEngine/QtPdf，也没有项目自带的可再分发中文字体。

C1/PDF 结论：

- HTML 可以用 Jinja2 + 内联 CSS + UTF-8 实现；
- PDF 需要 ReportLab 和合法中文字体（如 Noto Sans SC / OFL），当前均不满足；
- 不能直接使用 Windows 系统字体作为随报告分发的字体；
- PDF 导出在字体授权和技术验证前不启动；
- 当前没有 PDF 预览、没有 PDF 生成、没有 PDF 测试。

[inferred] 因此 Phase 6A 的结论是“HTML 可行，PDF 被资源/授权阻断，JSON 可后续做，GUI 暂不接入”。

### 3.4 Phase 6A 结论

```text
Phase 6A = completed（调查/设计）
实现代码 = none
独立验收文件 = none found
```

[inferred] 6A 的结论通过 B 报告的“阶段 A/第五阶段基线”表述、C1 的环境检查以及占位页目标间接确认；没有独立 6A 文档可作为直接快照。

[unknown] 6A 的精确开始/结束时间、独立评审人、原始任务单。

## 4. Phase 6B：统一报告数据服务

### 4.1 新增架构

Phase 6B 只新增只读报告数据层：

```text
ReportService
└── ReportRepository
    └── Database.connection()
        └── SQLite v5
```

文件：

- `core/models/report.py`（7,594 bytes）
- `repositories/report_repository.py`（11,847 bytes）
- `services/report_service.py`（13,179 bytes）
- `tests/test_report_service.py`（22,297 bytes）
- `docs/PHASE6_B_REPORT.md`（18,053 bytes）

阶段 B 没有修改：

- `ui/report_page.py`
- `ui/main_window.py`
- `app/bootstrap.py`
- `database/schema.py`
- `database/connection.py`
- Phase 3/4/5 扫描、漏洞、证据业务代码

这些是 B 报告和实际文件哈希共同支持的。[confirmed]

### 4.2 Report DTO

`core/models/report.py` 中全部 DTO 都是冻结 dataclass（`slots=True`）。职责和数据边界如下：

| DTO | 关键字段/职责 | 数据边界 |
|---|---|---|
| `ReportType` | `vulnerability`, `evidence`, `project_summary`；报告种类 | 只决定章节/模板选择，不是三套数据库查询 |
| `ReportFormat` | `html`, `pdf`, `json`；格式选择 | B 只验证枚举，不写文件 |
| `ReportRequest` | `project_id`, `report_type`, `report_format`, `title`, `include_evidence_images`, `include_notes`, `requested_at` | 用户输入；B 只校验/传递，不直接消费 title 到文件 |
| `ReportSnapshot` | `snapshot_id`, `report_type`, `project`, `authorization`, `tasks`, `findings`, `evidence`, `stats`, `generated_at`, `schema_version`, `data_scope`, `warnings`, `known_limitations` | 唯一报告聚合根；冻结；未来 exporter 只能消费它 |
| `ReportFinding` | 报告所需的 Finding 字段、依赖字段、证据计数、过滤后的 metadata | 不重新定义核心 Finding；不携带原始 SQLite Row |
| `ReportEvidence` | 证据类型、标题、哈希、`file_path`（原始内部路径）、`managed_path`、文件存在/哈希状态 | 原始绝对路径只在 DTO 内部；未来 HTML 必须用 `managed_path`/文件名 |
| `ReportTaskSummary` | 任务类型、状态、时间、进度、扫描器、摘要、错误 | 任务目标/错误文本可能含绝对路径，默认禁止进入 HTML |
| `ReportAuthorizationSummary` | 报告生成时刻的授权计数、资产计数、`historical_scan_authorization_available=False` | 不能倒推历史扫描时授权 |
| `ReportStats` | 任务/风险/扫描器/Finding 状态/证据类型/依赖/缺失文件/哈希不一致计数 | 预置全部枚举键为 0；0 是统计值，不是缺失 |
| `ReportArtifact` | 未来结果结构：类型、格式、项目、标题、时间、快照 ID、`path`、`sha256`、warnings | B 的 `artifact_stub()` 只返回 `path=None, sha256=None`，不写文件 |

关键实现位置：

- `ReportType`：`core/models/report.py:37-52`
- `ReportFormat`：`:55-74`
- `ReportRequest`：`:77-93`
- `ReportFinding`：`:96-136`
- `ReportEvidence`：`:139-165`
- `ReportTaskSummary`：`:168-190`
- `ReportAuthorizationSummary`：`:193-209`
- `ReportStats`：`:212-239`
- `ReportSnapshot`：`:242-268`
- `ReportArtifact`：`:271-283`

### 4.3 ReportRepository

`ReportRepository.load_snapshot(project_id, report_type=ReportType.PROJECT_SUMMARY, *, generated_at=None)`：

- 使用**一个** `Database.connection()`；
- 执行 `PRAGMA query_only = ON`；
- 执行显式 `BEGIN`；
- 依次读取 `projects`, `authorizations`, `scope_assets`, `scan_tasks`, `findings`, `evidence`；
- 每条 SQL 都显式列名，**没有 `SELECT *`**；
- 每条 SQL 都带 `WHERE ... project_id = ?`；
- `findings` 通过 `JOIN projects` 获取项目名，并通过相关子查询计算 `evidence_count`；
- `evidence` 通过 `JOIN projects`，LEFT JOIN `findings` 获取 Finding 标题；
- DTO 在事务内构造；
- `finally` 中 `rollback()`；
- 异常包装为 `StorageError`，项目不存在抛 `NotFoundError`。

实现位置：

- 只读事务：`repositories/report_repository.py:104-130`
- SQL 常量：`:50-94`
- 快照构造：`:132-205`
- Finding 投影/安全 metadata：`:226-272`

#### SQL 只读保护说明

SQLite 没有 `BEGIN READ ONLY` 语法，因此代码使用：

```python
connection.execute("PRAGMA query_only = ON")
connection.execute("BEGIN")
```

`query_only` 使该连接上的写入直接失败；`BEGIN` 形成显式事务边界，第一次 SELECT 建立读快照。事务结束后 rollback，连接关闭。没有修改 `database/connection.py`。[confirmed]

#### Snapshot 一致性

`tests/test_report_service.py::test_read_transaction_consistency_under_concurrent_write` 实际验证：

```text
before.findings = 1
after.findings  = 1   # 同一读事务仍看到旧快照
outside.findings = 2  # 结束后新事务看到新数据
```

结论：不是只凭“单连接”推断，而是在临时 SQLite 上用并发写入验证了 WAL 读事务的一致性快照。[confirmed]

#### 项目隔离

`test_project_isolation` 验证：

- 项目 A 快照的 Finding 全部属于 A；
- 项目 B 快照的 Finding 全部属于 B；
- A/B Finding ID 集合不相交；
- B 的证据不出现在 A 快照；
- 不存在的项目抛 `NotFoundError`；
- 项目 ID 0 抛 `NotFoundError`。

结果：通过。[confirmed]

### 4.4 ReportService

`ReportService` 位于 `services/report_service.py:76-336`。它做：

- 校验/转换报告类型与格式；
- 调用 `ReportRepository.load_snapshot()`；
- 对证据文件做受管路径、存在性、SHA-256 校验；
- 生成 `ReportStats`；
- 生成 `warnings`；
- 附加 `data_scope`；
- 附加固定的 `known_limitations`；
- 返回不可变 `ReportSnapshot`；
- `artifact_stub()` 只返回元数据占位，不写文件。

关键行为：

- `get_snapshot(project_id, report_type)`：`:94-102`
- `get_snapshot_for_request(request)`：`:104-108`
- `_finalize()`：`:110-121`
- `_annotate_evidence()`：`:123-215`
- `_build_stats()`：`:217-264`
- `_build_warnings()`：`:266-306`
- `_coerce_type/_coerce_format`：`:308-320`
- `artifact_stub()`：`:322-336`

#### 是否写数据库 / 是否含 UI SQL

- **不写数据库**：没有 INSERT/UPDATE/DELETE，没有 `reports` 行，没有 migration；证据校验只读文件。[confirmed]
- **不含 UI SQL**：Service 不导入 Qt，不导入 `sqlite3`，不执行 SQL；SQL 集中在 Repository。[confirmed]
- Service 没有将 `ReportService` 接入 `AppContext`，因此当前没有 GUI 调用路径。[confirmed]

#### warnings 与 known_limitations

`_build_warnings()` 明确产生：

- 没有扫描任务：`项目没有扫描任务；不能据此推断扫描通过。`
- 没有 Finding：`项目没有 Finding；不能据此推断不存在漏洞。`
- 没有 Evidence；
- 没有授权记录 / 当前没有有效授权；
- 存在失败或取消任务；
- 未配置证据根目录；
- 证据文件缺失/不可读；
- SHA-256 不一致；
- metadata 仅保留白名单字段。

`_KNOWN_LIMITATIONS`（`services/report_service.py:62-73`）固定包含：

1. Semgrep 当前 Windows CA 限制；
2. pip-audit 无 CVSS/severity 与精确 affected range；
3. 当前授权摘要不是历史扫描时授权快照；
4. 没有跨扫描 Finding 去重；
5. 数据库没有统一“真实/夹具/模拟”来源标记；
6. 只读本地 SQLite/受管证据，不访问远程目标。

#### 敏感数据边界

- `ReportFinding.metadata` 经 `_SAFE_METADATA_KEYS` 白名单过滤；未知字段被丢弃，并标记 `raw_metadata_omitted=True`（`repositories/report_repository.py:32-48,226-272`）。
- `ReportEvidence.file_path` 是数据库原始绝对路径，DTO 保留供内部校验；未来 exporter 不得直接输出。
- `ReportSnapshot.project` 是完整 `Project`，包含 `local_path`/`description`；未来 exporter 必须投影，不能 `__dict__` 全量序列化。
- C1 已明确禁止 `local_path`、`Project.description`、原始 `Evidence.file_path`、任务目标/错误、原始 Authorization/ScopeAsset、SQLite Row、未过滤 metadata 进入 HTML。

### 4.5 数据一致性

- 所有表按项目过滤；
- 所有 DTO 冻结；
- Stats、Authorization、Finding、Evidence 在同一次读事务中构造；
- 证据文件校验在事务结束后进行，只读文件，不改变数据库；
- 没有数据写入，因此不存在“报告生成改变原数据”的路径。

### 4.6 测试

新增文件：`tests/test_report_service.py`，**18 tests**。

覆盖：

- 三类报告快照；
- 默认 `PROJECT_SUMMARY`；
- 正常数据、空项目、部分字段缺失；
- 项目隔离；
- 不存在项目；
- 授权摘要/授权缺失；
- Finding/Evidence/Task 统计；
- 证据 SHA-256；
- 原始数据未修改；
- DTO 不可变；
- 单事务一致性；
- 并发写入快照；
- 异常连接释放；
- 0 与缺失区分；
- `ReportRequest` 与 `ReportArtifact` 空结果。

结果：

```text
定向：18 passed in 3.86s
全量历史：145 collected / 144 passed / 1 skipped / 0 failed / 38.44s
归档任务重跑：145 collected / 144 passed / 1 skipped / 0 failed / 41.51s
```

唯一 skip：

```text
tests/test_evidence_service.py:184
当前 Windows 会话无法创建文件符号链接：
[WinError 1314] 客户端没有所需的特权
```

该 skip 在 Phase 5 已存在，不是 Phase 6B 新增。[confirmed]

### 4.7 验收与封存

当前实际状态：

```text
phase_b_status          = sealed_with_recorded_exception
sealed                  = true
seal_exception_present  = true
phase_c_started         = false
phase_c_allowed         = false
schema_changed          = false
production_code_modified = false
phase5_core_archive_status = valid_and_hash_matching
historical_workspace_manifest_exact_match = false
```

归档目录：`docs/acceptance/phase6_b_final/`

当前文件数：**10**

当前清单：`PHASE6_B_FILE_MANIFEST.txt`

清单覆盖：

- 5 个 Stage B 交付物；
- 9 个归档记录（不含清单自身）；
- 共 **14/14 条目哈希匹配**；
- 清单自身 SHA-256：`d898d4e091fc72f2885cb6db2ca99ba856552d06172ee99af2e57c6729463c6f`。

已记录两个例外：

- `P6B-EX-001`：`docs/acceptance/code_quality.json` 被 Phase 6B 质量检查重新生成；旧哈希 `5993473a...`，当前 `f0d0fca2...`；`product_file_count 57 → 59`；旧副本在 `backups/src-research-assistant_phase5_final.zip`。
- `P6B-EX-002`：`storage/_rebuild_manifest.py` 在 Phase 5 清单中存在，当前缺失；清单记录 size `4150`、SHA `aed42f24...`；没有副本，原因未知；用户接受为未解决历史差异；未恢复、未伪造、未改清单。

#### 归档元数据的历史冲突

[contradicted] 当前归档文件系统是 10 个文件，最终清单 14 条；但：

- `PHASE6_B_ACCEPTANCE.json` 仍记录 `file_count: 9`、`manifest_entries: 11`、`manifest_covers_seal_documents: false`；
- `PHASE6_B_FINAL_SUMMARY.md` 第 7 节仍写“archive now contains 9 files”；
- `PHASE6_B_DATABASE_INFO.md` 第 143 行仍写“formal sealing is refused”，而后续 `PHASE6_B_SEAL_DECISION.md` 记录 `sealed_with_recorded_exception`。

解释：这些是封存/归档同步前生成的文档，后续清单同步到 14 条并新增了调查记录，但没有重写旧文档。当前有效事实应以后期 `PHASE6_B_FILE_MANIFEST.txt` 与实际 10 个文件为准；旧值保留为历史记录，不视为当前状态。[inferred，结合时间顺序与清单内容]

## 5. Phase 6C-1：HTML 实施前调查

### 5.1 HTML 架构

C1 只设计，不实现。推荐结构：

```text
reports/
├── __init__.py
├── html_exporter.py          # 不存在
└── templates/                # 不存在
    ├── base.html
    ├── vulnerability_report.html
    ├── evidence_report.html
    └── project_summary_report.html
```

推荐：

- `jinja2.FileSystemLoader` 加载本地包内模板；
- `Environment(autoescape=True, auto_reload=False, undefined=StrictUndefined)`；
- 模板名来自固定 allowlist，不用用户输入作为模板名；
- 单文件 HTML，内联 CSS，无 JS；
- 不生成 `<link rel="stylesheet" href="http...">`、远程 `<script src>`、远程图片、`@import`；
- 证据图片第一版默认不嵌入；
- 输出目录 `AppConfig.reports_dir`（当前 `storage/reports`）。

C1 没有创建 exporter、template、CSS、JS 或 `tests/test_report_html.py`。[confirmed]

### 5.2 安全策略

| 项目 | C1 结论 | 实现状态 |
|---|---|---|
| autoescape | 必须 `True`；所有自由文本只作为文本节点/带引号属性 | 未实现 |
| `|safe` / `Markup` | 禁止 | 未实现（无模板） |
| JavaScript | 第一版禁止；无 `<script>`、无事件属性、无 `javascript:` | 未实现 |
| 远程资源 | 禁止；无远程 CSS/JS/图片/字体/`@import` | 未实现 |
| CSS | 内联 `<style>`，静态常量，含 `@media print` | 未实现 |
| CSP | **C1 没有定义 Content-Security-Policy（meta 或 header）** | 未设计/未实现 |
| 超链接 | 默认不把 URL 变成可点击链接；URL 只作为转义文本 | 未实现 |
| Markdown | 不渲染 | 未实现 |
| 字段 allowlist | 报告专用 view model；禁止 `__dict__`/全量 dataclass | 未实现 |

CSP 是一个明确的调查缺口：C1 的安全策略主要依赖“无 JS、无远程资源、autoescape、禁 `|safe`”，但没有给出 CSP 字符串、`default-src`、`img-src`、`style-src` 等具体策略。若 C2 要做 CSP，需要单独设计并测试；当前不能声称已具备 CSP。

### 5.3 字段 allowlist

C1 建议允许进入 HTML 的字段：

- 项目：`project_id`、`project_name`、`project_type` 标签、`status` 标签；
- 报告：类型、生成时间、schema 版本、snapshot_id、data_scope、warnings、limitations；
- 授权摘要：全部计数、`as_of`、note；
- 任务：ID、类型/状态标签、时间、进度、scanners；
- Finding：ID、标题、类别、风险/置信度标签、扫描器/版本、规则、相对文件路径、行号、时间、依赖字段、状态；
- Finding 文本：`description`/`recommendation` 仅在 autoescape 下作为纯文本；
- 备注：仅 `include_notes=True` 时，autoescape 后作为纯文本；
- Evidence：ID、Finding ID、标题、类型标签、文件名（去路径）、哈希、创建时间、存在/哈希状态；
- Stats：全部计数。

必须禁止：

- `Project.local_path`；
- `Project.description`（默认禁止）；
- `ReportEvidence.file_path`（原始绝对路径）；
- `ReportTaskSummary.target` / `error_message`；
- 原始 `Authorization`/`ScopeAsset`/`Evidence` 对象；
- `__dict__`/`vars()`/dataclass 全量序列化；
- 原始 SQLite Row；
- 未经过 `_SAFE_METADATA_KEYS` 的 metadata；
- 认证令牌、密码、API key、授权凭证、内部绝对路径、用户主目录。

### 5.4 证据图片

C1 第一版结论：**默认不嵌入任何证据图片**。

理由：

- 截图可能含凭据、个人信息、客户数据；
- 会放大单文件；
- 增加图片解析/解码攻击面；
- 需要额外格式/哈希/containment 校验。

未来若允许嵌入，必须同时满足：

- 仅 PNG/JPEG；拒绝 SVG/GIF/WebP/PDF；
- 单文件 ≤ 5 MiB；
- SHA-256 与数据库记录一致；
- `resolve()` 后位于 `evidence_root/project_<id>/`；
- 拒绝符号链接/目录联接/`..`/UNC/设备路径；
- 仅读取已校验的受管文件；
- 使用 `data:image/png;base64,...` 或 `data:image/jpeg;base64,...`；
- 不生成远程 URL；
- 用户显式 opt-in 和敏感信息提示；
- 任一失败则不嵌入并写 warning。

当前 `ReportRequest.include_evidence_images` 存在，但 C2 第一版应保持关闭/忽略；没有实现。

### 5.5 原子写入

C1 未来方案（未实现）：

```text
目标同目录临时文件 target.html.tmp.<uuid>
        ↓
UTF-8 写入
        ↓
flush()
        ↓
fsync()（平台支持时）
        ↓
close()
        ↓
os.replace(tmp, target.html)
```

要求：

- 临时文件与目标同目录/同卷；
- `uuid4` 临时名；
- 固定 UTF-8；
- flush/fsync/close 成功后再 replace；
- 目标存在时必须显式覆盖确认；
- 未确认覆盖时失败，不截断原文件；
- 渲染/写入/flush/fsync 失败时删除临时文件，保留原目标；
- `os.replace` 失败时保留原目标，临时文件用于诊断/清理；
- 输出路径必须在 `AppConfig.reports_dir` 内，安全文件名，不允许用户任意绝对路径/`..`；
- 不放在系统临时目录后跨卷 replace；
- 导出失败绝不能把不完整内容替换为正式报告。

Windows 限制：

- `os.replace` 同卷原子，但目标被浏览器/杀毒软件占用可能 `PermissionError`；
- 路径长度限制；
- `fsync` 可用但需捕获 `OSError`；
- `os.replace` 不是覆盖前备份；覆盖确认是产品要求；
- 临时文件必须 `finally` 清理；
- 不把临时文件放在 `storage/reports` 之外。

### 5.6 测试计划

C1 只设计，未来文件应为 `tests/test_report_html.py`。计划覆盖：

- 三类报告正确模板/章节；
- UTF-8 中文/emoji；
- 空项目/空 Finding/空 Evidence；
- 正常数据；
- 生成前后数据不变；
- warnings/limitations 不丢失；
- `<script>`、`<img onerror>`、恶意属性、`javascript:` 转义；
- 无远程 CSS/JS/图片/字体；
- 敏感字段（local_path/file_path/token/password）不进入 HTML；
- 路径越界/符号链接证据不进入；
- 无 `|safe`/`Markup`；
- 无 JavaScript；
- 原子写入/覆盖保护/失败清理/目录 containment/Windows 锁定；
- HTML 可解析、内联 CSS、打印样式、空状态文案；
- 不写“无漏洞=安全”/“无任务=通过”。

C1 没有创建该测试文件。[confirmed]

### 5.7 已知风险

1. Jinja2 autoescape 不是 HTML sanitizer；不能替代字段 allowlist。
2. `ReportSnapshot.project` 是完整 `Project`，含 `local_path`/`description`。
3. `ReportEvidence.file_path` 是原始绝对路径。
4. 自由文本可能含凭据/PII。
5. 证据图片有 SVG/远程 URL/哈希不一致/符号链接风险。
6. Windows 文件替换有占用、跨卷、路径长度、临时文件残留风险。
7. DSH 临时目录 ACL 使完整 pytest 不稳定。
8. 报告真实性文案不能把 0 Finding 写成“无漏洞”，不能把无任务写成“通过”，不能把 Semgrep 夹具写成真实扫描。
9. Jinja2 3.1.6/Python 3.14.4 当前可导入，但仍需 C2 实际渲染测试。
10. `ReportService` 未接入 UI；C2 接入时必须保持只读和线程边界。
11. C1 没有定义 CSP。

### 5.8 Phase 6C-1 结论

```text
Phase 6C-1 = completed
生产功能 = 0
HTML exporter = 不存在
HTML template = 不存在
HTML test = 不存在
C2 = not started
```

C1 的结论是“设计条件满足，但完整 pytest 受 ACL 阻塞”；不是 HTML 已实现。

## 6. Phase 6C-2 当前状态

当前实际检查：

| 检查项 | 结果 |
|---|---|
| `reports/html_exporter.py` | **不存在** |
| `reports/templates/` | **不存在** |
| `tests/test_report_html.py` | **不存在** |
| `ui/report_page.py` 是否接入 | **否**，仍是 `PlaceholderPage` |
| `ui/main_window.py:197` | `"reports": ReportPage()`，无参数、无 Service |
| `app/bootstrap.py` 是否注入 `ReportService` | **否** |
| 是否生成 HTML 报告 | **否** |
| 是否写入 `reports` 表 | **否**，0 行 |
| 是否修改 Schema | **否**，仍 v5 |
| 是否存在 HTML 文件 | **否**；`reports/` 仅 `__init__.py`，`storage/reports/` 仅 `.gitkeep` |

结论：

```text
Phase 6C-2 = not started
```

不得把 C1 的设计文档描述成 HTML 已实现。

## 7. 当前测试环境与 pytest ACL 问题

### 7.1 历史绿色基线

Phase 6B 封存前/封存时：

```text
145 collected
144 passed
0 failed
1 skipped
```

历史全量耗时 `38.44s`；阶段 B 归档任务重跑为 `41.51s`，exit code 0。

Skip：

```text
tests/test_evidence_service.py:184
test_symlink_to_outside_is_rejected
Windows current session cannot create file symlink:
[WinError 1314] 客户端没有所需的特权
```

这是 Phase 5 既有环境限制，不是产品断言失败。[confirmed]

### 7.2 C1 期间的完整执行失败

C1 尝试普通完整 pytest：

```text
PermissionError: [WinError 5] 拒绝访问。:
'C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs\pytest-of-lenovo'
```

改用工作区临时目录后：

```text
PermissionError: [WinError 5] 拒绝访问。:
'D:\挖漏洞\SRC-Research-Assistant\storage\_c1_pytest_tmp\pytest-of-lenovo'
```

实际结果：

```text
1 failed, 7 passed, 137 errors in 1.71s
```

错误集中在：

- pytest-qt 的 `tmp_path` fixture setup；
- pytest session 临时目录清理；
- `test_pip_audit_actual_available` 的 `TemporaryDirectory` cleanup。

不是产品断言失败；没有修改测试、断言或 skip。[confirmed]

### 7.3 根因

C1R 的实际结论：

1. 测试进程是 Windows **Low Mandatory Level S-1-16-4096**；
2. DSH 临时目录有 `Everyone:(CI)(DENY)(DC)` 和 Low Mandatory Label `(OI)(CI)(NW)`；
3. 项目/storage 继承类似 ACL；
4. `pytest-of-lenovo` 目录访问被拒绝；
5. `_pytest/tmpdir.py:375 cleanup_dead_symlinks(basetemp)` 调用 `os.scandir` 触发 `PermissionError: [WinError 5]`；
6. `_pytest/pathlib.py:398` 是实际 `os.scandir` 位置；
7. `TemporaryDirectory` 清理在 `tempfile.py:916-955` 的 `_rmtree` → `_resetperms` → `chmod(..., follow_symlinks=False)` 处失败；
8. `pytestqt/plugin.py:168-182` 的 `result = yield` 只是 fixture wrapper，不是根因。

单独修 ACL 到一个新候选目录后，普通低完整性进程仍不能写；只有 full-access 测试进程能写。这是 DSH 低完整性测试环境限制，不是产品代码缺陷。[confirmed]

### 7.4 C1R 的恢复结果

最终专用目录：

```text
D:\挖漏洞\pytest_c1r_tmp
basetemp: D:\挖漏洞\pytest_c1r_tmp\bt_full
```

最终命令环境：

```text
TEMP=D:\挖漏洞\pytest_c1r_tmp
TMP=D:\挖漏洞\pytest_c1r_tmp
TMPDIR=D:\挖漏洞\pytest_c1r_tmp
PYTEST_DEBUG_TEMPROOT=D:\挖漏洞\pytest_c1r_tmp
QT_QPA_PLATFORM=offscreen
```

执行层：

- 使用 DSH full-access 测试进程；
- 普通 workspace-write 仍不能稳定完成完整 pytest；
- 最终目录没有做 ACL 修改，保留继承 ACL。

结果：

```text
145 tests collected in 0.17s
144 passed, 1 skipped in 40.94s
exit code 0
```

已验证：

- `tempfile.gettempdir()` 返回 `D:\挖漏洞\pytest_c1r_tmp`；
- `mkdtemp()`、写入、读取、`shutil.rmtree`、`TemporaryDirectory` cleanup 全部成功；
- pytest-qt setup/teardown 成功；
- 1 个 skip 仍是 Windows 文件符号链接权限。

### 7.5 本次调查的当前状态

本次只执行：

```text
145 tests collected in 0.71s
```

没有在当前普通环境重跑完整测试，也没有修改 pytest 配置、删除测试、删除 skip、降低断言或修复 ACL。

因此：

- 历史绿色基线 **144 passed / 1 skipped / 145 collected** 仍然有效；
- 它不是当前普通 workspace-write 环境下“刚重新跑出来的”结果；
- C1R 的 40.94s 全绿结果仅在其专用临时目录 + full-access 执行条件下有效；
- 当前没有新的普通完整绿色回归。[confirmed]

### 7.6 ACL 影响范围

- **主要影响**：pytest-qt 的 `tmp_path` setup/清理、session 临时目录清理、`TemporaryDirectory` cleanup；
- **不影响**：产品断言本身、报告服务逻辑、数据库只读逻辑（在没有触发临时目录清理的路径上）；
- **不是**：产品测试失败、报告实现失败、用户数据损坏；
- **特殊历史噪声**：C1R 第一次全量运行在路径含 `env` 的 `.pytest-c1r-env` 下出现 2 个 Bandit 0 findings 失败；原因是 `BanditScanner` 排除 `env` 段，不是 ACL，也不是产品回归。改名为 `pytest_c1r_tmp` 后消失。

## 8. 数据库与 Schema 影响

### 8.1 当前 Schema

```text
PRAGMA user_version = 5
```

没有 v6，没有新表，没有新列，没有 migration。[confirmed]

### 8.2 当前数据库只读检查

| 数据库 | 大小 | SHA-256 | Schema | Integrity | FK violations | Tables | `reports` 行 |
|---|---:|---|---:|---|---:|---:|---:|
| `storage/src_research.db` | 147,456 | `f03cfb81bf0cf4cee3367e1413e26919e30fa763c2d1b792aa03b5300e3128bb` | 5 | ok | 0 | 11 | 0 |
| `storage/phase5_acceptance/acceptance.db` | 352,256 | `03de49509b43428eb303f7dc38e1ff749cc58d1b3f186070c63706bba4ceb4c8` | 5 | ok | 0 | 11 | 0 |

检查方式：SQLite URI `mode=ro`，不初始化数据库、不迁移、不写事务、不复制数据库、不使用 WAL/SHM 代替备份。

### 8.3 `reports` 表

当前列：

```text
report_id INTEGER PRIMARY KEY AUTOINCREMENT
project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE
report_format TEXT NOT NULL CHECK(report_format IN ('html','pdf','json'))
file_path TEXT NOT NULL
generated_at TEXT NOT NULL
created_at TEXT NOT NULL
```

`database/schema.py:95-104` 定义。`reports` 没有 `report_type` 列；报告类型目前只在 DTO / 未来 sidecar 中表达，未改 Schema。

### 8.4 Phase 6B 与 Phase 5 数据库对比

Phase 5 封存时/Phase 6B 验收记录：

- 主库：`f03cfb81...`，schema 5，`reports=0`，业务表空；
- Phase 5 acceptance：`03de4950...`，schema 5，`reports=0`，41 findings / 3 evidence / 4 tasks / 3 scope assets / 2 history。

本次只读检查结果与 Phase 6B `PHASE6_B_ACCEPTANCE.json` 记录一致；两个数据库哈希均未变化。[confirmed]

## 9. 与 Phase 5 的边界

### 9.1 抽查的 Phase 5 文件

当前文件哈希与 `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` 的记录逐项一致：

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `services/vulnerability_service.py` | 7,081 | `151831ff724f0ddde852ab7da6c0c9052abf7234a6759c627605b64d9e233fca` |
| `services/evidence_service.py` | 11,853 | `7bc5434dab77aa45505ebb28cf0372371cfc6568cddf7380126c9d3e22ee46c6` |
| `repositories/vulnerability_repository.py` | 8,244 | `5a03e692389f41704dd667b4e6bafcff00febea2dcbd39d3d57fe1f0249e0467` |
| `repositories/evidence_repository.py` | 5,196 | `70218e88b7725ec254110684fafd94741b07cc96916c3a9affeb23f7eb588082` |
| `ui/vulnerability_page.py` | 23,436 | `c8517760a50e798c168a8c1a565added5edf6006d28011b3f49c16b3074d9ab9` |
| `ui/evidence_page.py` | 17,146 | `3ea86d20ac9a6727507c054ceeff27d1ad16c18f46f3e9bddcf2420934a1a54b` |
| `ui/main_window.py` | 13,124 | `ee1f51cd1258cef966823c42b8ea3443dde38263f61257e15bd3aa1f8b45819b` |
| `database/schema.py` | 12,874 | `62b3c37c028e244908998cc0b25a325176f01b3c62d68c1801dd11a87890ce92` |
| `database/connection.py` | 10,599 | `1d549ccc222f79ab77101eec0055d8a70ff05d6617a90592f8107e44d7beb28b` |
| `app/bootstrap.py` | 4,763 | `7365d9067085fb5176d40a8d65bcfbd33b43c8d0f6845a728d1c6da11680e9c1` |

结论：Phase 6 没有修改 Phase 5 的漏洞服务、证据服务、Repository、GUI 页面或数据库 Schema。[confirmed]

### 9.2 Phase 5 归档

- `docs/acceptance/phase5_final/` 当前 10 个文件；
- 除清单自身外 9 个文件与 Phase 5 清单匹配；
- `PHASE5_FINAL_SUMMARY.md` 的已知 SHA-256 为 `645abf1228ec8ca3081ee98e64f34bd4acf75481a1312c62cff7b7d514c74ba6`；
- Phase 5 核心归档状态：`valid_and_hash_matching`；
- Phase 5 workspace-wide manifest 仍有两个历史例外（`code_quality.json` 与缺失的 `_rebuild_manifest.py`），不影响 Phase 5 核心验收材料，但使“整个工作区清单完全可复现”为 false。

### 9.3 Phase 5 验收库

- `storage/phase5_acceptance/acceptance.db` 哈希 `03de4950...`；
- 41 findings / 3 evidence / 4 tasks / 3 scope assets / 2 history；
- `reports=0`；
- 未修改、未迁移、未复制。[confirmed]

## 10. 当前 Phase 6 架构

### 10.1 实际架构（B 已实现部分）

```text
当前 UI
  ui/report_page.py = PlaceholderPage
  ui/main_window.py:197 = ReportPage()
  app/bootstrap.py = ReportService 未注入
        │
        │ 当前没有调用路径
        ▼
ReportService (services/report_service.py)
  - 类型校验
  - 证据文件校验
  - stats / warnings / data_scope / limitations
        │
        ▼
ReportRepository (repositories/report_repository.py)
  - 一个 Database.connection()
  - PRAGMA query_only = ON
  - BEGIN
  - 项目范围显式列 SQL
        │
        ▼
SQLite v5
  projects / authorizations / scope_assets
  scan_tasks / findings / evidence
```

### 10.2 ReportSnapshot 的位置

- `ReportRepository` 读取数据库并构造 **原始** `ReportSnapshot`（`stats=None`）；
- `ReportService._finalize()` 返回带 stats/warnings/data_scope/limitations 的 **最终** `ReportSnapshot`；
- 未来 HTML/PDF/JSON exporter 只能消费最终 `ReportSnapshot`；
- exporter 不允许直接读数据库；
- UI 未来只能调用 Service，不能直接 Repository 或 SQL。

### 10.3 谁负责什么

| 层 | 当前状态 | 职责 |
|---|---|---|
| UI | `ReportPage` 占位 | 未来选择项目/类型/格式、预览、导出、覆盖确认 |
| ReportService | 已实现，未接入 | 组装快照、统计、授权摘要、warnings、证据校验 |
| ReportRepository | 已实现 | 单连接只读、项目隔离、显式列 SQL、构造 DTO |
| ReportSnapshot | 已实现 | 不可变数据契约；未来 exporter 唯一输入 |
| HTML/PDF/JSON exporter | **不存在** | 未来 C2/D/E 实现 |
| SQLite | v5 | 只读来源 |

## 11. Phase 6 时间线

| 时间 | 事件 | 证据强度 |
|---|---|---|
| 2026-11-05 14:22 左右 | Phase 5 final closeout；Phase 5 清单生成 | confirmed（清单时间） |
| Phase 6A（具体时间 unknown） | 报告中心架构/可行性调查；没有独立文档 | inferred |
| 2026-11-05 | Phase 6B 实现：DTO/Repository/Service；18 tests | confirmed |
| 2026-11-05 | Phase 6B 归档任务重跑：144/1/41.51s；两个历史例外记录 | confirmed |
| 2026-11-05 | Phase 6B 封存：`sealed_with_recorded_exception`；C 未开始 | confirmed |
| 2026-11-05 20:15:34 +08:00 | 最终归档清单生成；14 条；当前归档 10 文件 | confirmed（清单 Generated 行） |
| 2026-11-05 | Phase 6C-1 HTML 调查完成；仅新增 C1 文档 | confirmed |
| 2026-11-05 | Phase 6C-1 完整 pytest 受阻：1 failed/7 passed/137 errors | confirmed |
| 2026-11-05 | Phase 6C-R 完成；专用临时目录 + full-access 全量 144/1/40.94s | confirmed |
| 2026-11-06 13:04 +08:00 | 本历史调查开始 | confirmed（用户时间） |
| 当前 | 停在 C1-R 之后；C2 not started | confirmed |

[unknown] Phase 6A 的精确起止时间；Phase 6 的原始任务单；C1/C1R 的精确完成时刻；Phase 6D/E/F 的详细计划（只有 C1 的停止声明）。

## 12. 核心文件清单

### 12.1 Phase 6B 生产/测试

```text
core/models/report.py
repositories/report_repository.py
services/report_service.py
tests/test_report_service.py
docs/PHASE6_B_REPORT.md
```

### 12.2 Phase 6C 调查文档

```text
docs/PHASE6_C1_HTML_INVESTIGATION.md
docs/PHASE6_C1_R_TEST_ENV_REPORT.md
```

### 12.3 Phase 6B 归档

```text
docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json
docs/acceptance/phase6_b_final/PHASE6_B_ARCHITECTURE.md
docs/acceptance/phase6_b_final/PHASE6_B_ARCHIVE_DIFFERENCE_INVESTIGATION.md
docs/acceptance/phase6_b_final/PHASE6_B_DATABASE_INFO.md
docs/acceptance/phase6_b_final/PHASE6_B_EXCEPTION_REGISTER.md
docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt
docs/acceptance/phase6_b_final/PHASE6_B_FINAL_SUMMARY.md
docs/acceptance/phase6_b_final/PHASE6_B_SEAL_DECISION.md
docs/acceptance/phase6_b_final/PHASE6_B_TEST_OUTPUT.txt
docs/acceptance/phase6_b_final/PHASE6_B_TEST_REPORT.md
```

### 12.4 未存在/未实现

```text
reports/html_exporter.py          # not found
reports/templates/                # not found
tests/test_report_html.py         # not found
reports/*.html / *.j2 / *.css / *.js  # not found in reports/
storage/reports/*.html            # not found; only .gitkeep
reports table rows                # 0 in both DBs
```

## 13. 测试与验收结果

### 13.1 Phase 6B

```text
新增 tests：18
定向：18 passed / 3.86s
全量历史：145 collected / 144 passed / 1 skipped / 0 failed / 38.44s
归档重跑：145 collected / 144 passed / 1 skipped / 0 failed / 41.51s / exit 0
```

### 13.2 C1

```text
collect-only：145 collected / 0.35s
完整尝试：1 failed / 7 passed / 137 errors / 1.71s
```

不是产品断言失败；是 DSH 临时目录 ACL。

### 13.3 C1R

```text
collect-only：145 collected / 0.17s
最终完整：144 passed / 1 skipped / 0 failed / 0 errors / 40.94s / exit 0
```

### 13.4 本次调查

```text
collect-only：145 tests collected / 0.71s
完整 pytest：未执行（避免再次触发 ACL 噪声；且本任务只调查）
```

### 13.5 与基线对比

| 指标 | Phase 5 基线 | Phase 6B | C1R | 当前 |
|---|---:|---:|---:|---:|
| collected | 127 | 145 | 145 | 145 |
| passed | 126 | 144 | 144 | 历史有效 |
| failed | 0 | 0 | 0 | 0（历史） |
| skipped | 1 | 1 | 1 | 1（历史） |
| 普通完整运行 | 通过 | 通过 | 仅在 full-access 下通过 | 当前未重跑 |

## 14. unknown / contradicted / 环境限制

### 14.1 unknown

- Phase 6A 的精确起止时间和独立评审记录；
- Phase 6 的原始用户任务单/启动日期；
- Phase 6C-1 和 C1R 的精确完成时刻；
- Phase 6D/E/F 的详细计划（现有材料只声明未开始）；
- C2 的最终 GUI 交互/覆盖确认方案；
- C1 未定义的 CSP 具体策略；
- Phase 5 workspace manifest 中 `storage/_rebuild_manifest.py` 的用途和缺失原因（Phase 6B 已接受为历史差异）。

### 14.2 contradicted / 历史时序差异

1. `PHASE6_B_ACCEPTANCE.json` 写 `file_count=9`、`manifest_entries=11`、`manifest_covers_seal_documents=false`；
2. `PHASE6_B_FINAL_SUMMARY.md` 写“archive now contains 9 files”；
3. `PHASE6_B_DATABASE_INFO.md` 写“formal sealing is refused”；
4. 当前实际归档 10 文件、清单 14 条、`sealed_with_recorded_exception`。

解释：前者是封存/归档同步前的记录，后者是后续清单同步后的状态。当前应以实际文件系统和最终清单为准；旧文档保留为历史快照。

### 14.3 环境限制

- 普通 workspace-write 的 Low Mandatory Level 测试进程不能稳定写/清理 DSH 临时目录；
- 完整 pytest 需要 `D:\挖漏洞\pytest_c1r_tmp` + full-access 测试进程；
- 文件符号链接创建仍受 Windows 权限限制（`WinError 1314`）；
- Semgrep 仍不可用；
- 没有 ReportLab/Pillow/合法中文字体，PDF 不能开始；
- 没有 QtWebEngine/QtPdf，无内嵌预览；
- C1 没有 CSP；
- 当前没有普通环境的全量绿色结果，只有 C1R 的定向环境绿色结果。

## 15. 当前准确停止点

```text
Phase 6A   = completed（调查/设计；无独立 A 文档）
Phase 6B   = completed / sealed_with_recorded_exception
Phase 6C-1 = completed（调查；无 HTML 代码）
Phase 6C-1R= completed（测试环境恢复；无产品代码）
Phase 6C-2 = not started
Phase 6D/E/F = not started
```

当前项目状态：

- 版本 0.5.0；
- Schema v5；
- 主库空业务数据；Phase 5 验收库 41 findings；
- `reports` 表 0 行；
- `ui/report_page.py` 占位；
- `ReportService` 已实现但未接入；
- 无 HTML/PDF/JSON exporter；
- 无报告文件；
- 无 C2 代码/模板/测试；
- C1/C1R 文档已存在；
- Phase 5 核心归档有效；Phase 6B 归档 `sealed_with_recorded_exception`，两个历史例外已记录。

## 16. 是否满足进入 C2 的条件

### 16.1 设计条件

**满足**：

- Jinja2 3.1.6 已安装；
- `ReportSnapshot`/Repository/Service 已存在且只读；
- 字段 allowlist、autoescape、模板目录、图片默认禁用、原子写入、测试计划已在 C1 明确；
- 没有已有 HTML exporter/模板需要兼容；
- 数据库和 Phase 5 数据未被 Phase 6 修改。

### 16.2 测试环境条件

**条件满足，但不是普通工作流**：

- 普通 workspace-write 完整 pytest 仍受 ACL 限制；
- 只有使用 `D:\挖漏洞\pytest_c1r_tmp` + full-access 测试进程，才能复现 144/1/40.94s；
- C1R 的结论是“条件性满足 C2 测试前置条件”。

### 16.3 授权条件

**未满足**：

- Phase 6B 封存明确 `phase_c_allowed=false`；
- C1 只被授权做调查，不被授权实现 HTML；
- C2 未开始；
- 需要新的明确授权。

### 16.4 结论

```text
设计：可以进入 C2
普通测试环境：不可以稳定进入 C2 回归
专用 full-access 测试环境：可以
产品授权：尚未授权 C2
当前决定：C2 not started，停止在本调查
```

## 17. 历史证据索引

| 证据 | 路径/值 |
|---|---|
| Phase 6B 实现报告 | `docs/PHASE6_B_REPORT.md` |
| Phase 6B 验收 JSON | `docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json` |
| Phase 6B 最终摘要 | `docs/acceptance/phase6_b_final/PHASE6_B_FINAL_SUMMARY.md` |
| Phase 6B 封存决定 | `docs/acceptance/phase6_b_final/PHASE6_B_SEAL_DECISION.md` |
| Phase 6B 例外登记 | `docs/acceptance/phase6_b_final/PHASE6_B_EXCEPTION_REGISTER.md` |
| Phase 6B 数据库说明 | `docs/acceptance/phase6_b_final/PHASE6_B_DATABASE_INFO.md` |
| Phase 6B 清单 | `docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt` |
| Phase 6B 清单自身 SHA-256 | `d898d4e091fc72f2885cb6db2ca99ba856552d06172ee99af2e57c6729463c6f` |
| C1 HTML 调查 | `docs/PHASE6_C1_HTML_INVESTIGATION.md` |
| C1R 测试环境报告 | `docs/PHASE6_C1_R_TEST_ENV_REPORT.md` |
| Phase 5 核心归档摘要 | `docs/acceptance/phase5_final/PHASE5_FINAL_SUMMARY.md`；SHA `645abf1228ec8ca3081ee98e64f34bd4acf75481a1312c62cff7b7d514c74ba6` |
| Phase 5 清单 | `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` |
| 主库 | `storage/src_research.db`；SHA `f03cfb81...e3128bb`；v5；reports=0 |
| Phase 5 验收库 | `storage/phase5_acceptance/acceptance.db`；SHA `03de4950...ceb4c8`；v5；reports=0 |
| 报告页面占位 | `ui/report_page.py` |
| 主窗口占位接入 | `ui/main_window.py:197` |
| 报告 Schema | `database/schema.py:95-104` |
| 报告 DTO | `core/models/report.py` |
| 报告 Repository | `repositories/report_repository.py` |
| 报告 Service | `services/report_service.py` |
| 报告测试 | `tests/test_report_service.py` |

### 本次实际检查数量

```text
实际检查现有文件：33
实际检查 SQLite 数据库：2
实际检查目录：4
```

33 个文件包括：

- 13 个代码/配置/包文件；
- 14 个 Phase 6/Phase 5 文档或 JSON；
- 6 个 Phase 5 边界源码文件。

10 个 Phase 6B 归档文件逐个 SHA-256 校验，14 条清单条目全部匹配。

### 本次修改声明

```text
生产代码修改：否
测试代码修改：否
数据库修改：否
Schema 修改：否
依赖安装/升级/卸载：否
Phase 5 归档修改：否
Phase 6B 归档修改：否
Manifest 修改：否
本次新增：docs/PROJECT_HISTORY_PHASE6.md（仅此一个文件）
```

调查完成，停止在 C2 之前；未开始 HTML exporter、模板、PDF/JSON、GUI 接入或 C2 开发。
