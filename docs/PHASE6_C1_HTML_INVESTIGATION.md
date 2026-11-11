# Phase 6C-1：HTML 环境与安全架构调查报告

- 调查日期：2026-11-05（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：`0.5.0`
- 当前 schema：v5
- 调查范围：仅环境、现有架构、字段风险、导出目录/模板设计、安全策略、测试计划
- 结论：**设计条件满足进入 C2，但当前完整 pytest 受 DSH 临时目录权限问题阻塞；C2 未启动**
- 本阶段没有创建 HTML 导出器、模板、CSS、JS 或测试文件

## 1. 环境结果

| 检查项 | 实际结果 |
|---|---|
| Python | **3.14.4** |
| 虚拟环境 | `D:\挖漏洞\.venv\Scripts\python.exe` |
| Jinja2 | **已安装，3.1.6** |
| Jinja2 导入 | 成功，`jinja2.__version__ == 3.1.6` |
| MarkupSafe | 3.0.4 |
| Jinja2 `Requires-Python` | `>=3.7` |
| `requirements.txt` | 已声明 `Jinja2>=3.1,<4` |
| 当前项目版本 | 0.5.0 |
| 当前数据库 schema | v5 |

**Jinja2 适用性：** 当前 Python 3.14.4 上可正常导入，Jinja2 3.1.6 的 Python 要求为 `>=3.7`，MarkupSafe 3.0.4 可用；项目依赖声明已包含 Jinja2。没有执行任何 `pip install`。

## 2. Jinja2 状态

```text
Jinja2:
installed

version:
3.1.6

Python:
version:
3.14.4
```

补充：

- 未安装任何新依赖；
- 未修改 `requirements.txt`；
- 未生成或修改 Jinja2 模板；
- 当前 HTML 导出尚未实现。

## 3. 当前报告架构

### 3.1 文件与职责

| 文件 | 现状 |
|---|---|
| `core/models/report.py` | 已实现冻结 DTO：`ReportType`、`ReportFormat`、`ReportRequest`、`ReportSnapshot`、`ReportFinding`、`ReportEvidence`、`ReportTaskSummary`、`ReportAuthorizationSummary`、`ReportStats`、`ReportArtifact` |
| `repositories/report_repository.py` | 已实现项目范围、显式列、单连接只读 `ReportSnapshot` 读取 |
| `services/report_service.py` | 已实现快照统计、授权摘要、证据文件校验、warnings、data scope、known limitations |
| `app/config.py` | 实际配置类 `AppConfig`；**不存在 `core/config.py`** |
| `storage/reports` | 存在，仅有 `.gitkeep`（54 bytes） |
| `reports/` | 仅有 `__init__.py`（75 bytes，docstring） |
| `reports/templates` | **不存在** |
| HTML 导出器 | **不存在**；`reports/` 中无 `html_exporter.py` 或任何 `.html/.jinja/.j2/.css/.js` |
| `ui/report_page.py` | 仍是 `PlaceholderPage`；未接入 `ReportService` |
| `app/bootstrap.py` | 未注入 `ReportService` |

### 3.2 `ReportSnapshot` 结构

`ReportSnapshot` 是冻结 dataclass，字段如下：

```text
snapshot_id
report_type
project                 # 完整 Project DTO，不是报告专用精简 DTO
authorization           # ReportAuthorizationSummary
tasks                   # tuple[ReportTaskSummary]
findings                # tuple[ReportFinding]
evidence                # tuple[ReportEvidence]
stats                   # ReportStats | None
generated_at
schema_version
data_scope
warnings
known_limitations
```

`ReportSnapshot.project` 的类型是 `core.models.project.Project`，因此包含：

```text
project_id, project_name, project_type, description,
local_path, status, created_at, updated_at
```

这一点是 HTML 导出的重要风险点：不能把 `ReportSnapshot` 或 `Project` 直接交给模板或 `__dict__`。

### 3.3 三类报告如何生成

`ReportService.get_snapshot(project_id, report_type)`：

1. 校验/转换 `ReportType`；
2. 调用 `ReportRepository.load_snapshot(project_id, kind, generated_at=...)`；
3. `ReportRepository` 使用一个 `Database.connection()`；
4. 执行 `PRAGMA query_only = ON` 和 `BEGIN`；
5. 用显式列 SQL 读取当前项目的 project/authorization/scope/tasks/findings/evidence；
6. 构造 DTO；
7. `ReportService._finalize()` 计算 evidence 文件校验、stats、warnings、`data_scope` 和 `known_limitations`；
8. 最终返回 `ReportSnapshot`，不写任何文件。

三类报告不是三个数据库查询接口，而是同一个项目快照的三种 `ReportType` 和 `data_scope`：

| 类型 | `data_scope` |
|---|---|
| `vulnerability` | project, current_authorization, scan_tasks, findings, finding_stats |
| `evidence` | project, current_authorization, scan_tasks, evidence, evidence_stats, linked_findings |
| `project_summary` | project, current_authorization, scan_tasks, findings, evidence, finding_stats, evidence_stats |

当前三类类型在数据层都读取同一组项目范围行；未来 HTML exporter 根据 `report_type` 选择模板和展示章节，不能改变快照数据或伪造缺失章节。

### 3.4 只读与真实性约束

- Repository 使用 `PRAGMA query_only = ON`，只读事务，`finally` 中 rollback；
- 所有查询按 `project_id` 过滤；
- 使用显式列，无 `SELECT *`；
- Service 不写数据库、不生成文件；
- `ReportService._KNOWN_LIMITATIONS` 明确保留：
  - Semgrep 当前 Windows CA 限制；
  - pip-audit 无 CVSS/severity 和精确 affected range；
  - 当前授权摘要不是历史扫描时授权快照；
  - 无跨扫描 Finding 去重；
  - 数据库没有统一“真实/夹具/模拟”标记；
  - 不访问远程目标。
- warnings 明确：没有任务不能推断“扫描通过”，没有 Finding 不能推断“没有漏洞”。

## 4. DTO 导出字段风险

### 4.1 可能进入 HTML 的字段

按报告类型，候选字段包括：

| DTO | 候选字段 | 风险 |
|---|---|---|
| `ReportSnapshot` | `snapshot_id`, `report_type`, `generated_at`, `schema_version`, `data_scope`, `warnings`, `known_limitations` | 低；仍应 autoescape |
| `Project` | `project_id`, `project_name`, `project_type`, `status` | `project_name` 可含 HTML；`local_path`、`description` 不应直接进入 |
| `ReportFinding` | `finding_id`, `title`, `category`, `description`, `severity`, `severity_source`, `confidence`, `scanner_name`, `scanner_version`, `rule_id`, `file_path`, `line_number`, `recommendation`, `status`, `manual_notes`, `detected_at`, `last_seen_at`, 依赖字段 | 大量自由文本；描述/备注可能含代码、凭据、HTML；`file_path` 可能含绝对路径 |
| `ReportEvidence` | `evidence_id`, `finding_id`, `finding_title`, `evidence_type`, `title`, `description`, `file_name`, `source`, `file_hash`, `captured_at`, `created_at`, `file_exists`, `hash_matches` | 描述/来源可能含敏感信息；`file_path` 是原始绝对路径；`managed_path` 是受管相对路径 |
| `ReportTaskSummary` | `task_id`, `task_type`, `status`, `started_at`, `finished_at`, `progress`, `scanners` | 低；`target`/`error_message` 可能含绝对路径或内部细节 |
| `ReportAuthorizationSummary` | 全部计数字段、`as_of`、`note` | 低；不含原始授权文件/凭证 |
| `ReportStats` | 全部计数 | 低 |
| `ReportRequest` | `title` | 用户输入，必须转义 |
| `ReportArtifact` | `title`, `path`, `sha256`, `warnings` | 未来路径必须受控；`path` 不应直接暴露内部绝对路径 |

### 4.2 当前实际数据中的标记

只读扫描 `storage/phase5_acceptance/acceptance.db` 的所有文本列（按大小写不敏感）：

| 标记 | 当前结果 |
|---|---|
| `<script` | 0 |
| `<img` | 0 |
| `<a ` | 0 |
| `href=` | 0 |
| `onerror=` | 0 |
| `onclick=` | 0 |
| `http` | **31 行**，全部位于 `findings.description` |

结论：

- 当前验收数据没有已出现的 HTML 标签/事件处理器样本；
- 但 `findings.description` 中含 31 条 `http` 文本（pip-audit advisory 的说明/Markdown 链接样式）；
- 字段是自由文本，未来可能出现 `<script>`、`<img onerror>`、`onclick`、`<a>` 或恶意属性；
- **不能以“当前数据没有”作为不转义的理由。**

### 4.3 不能直接进入 HTML 的字段

默认禁止或必须特殊处理：

| 字段 | 原因 |
|---|---|
| `Project.local_path` | 内部绝对路径，可能暴露操作系统用户名/目录结构 |
| `Project.description` | 用户自由文本，可能含凭据/内部信息；默认不进入报告 |
| `ReportEvidence.file_path` | 原始证据绝对路径；不得展示/写入 HTML |
| `ReportTaskSummary.target` | 扫描目标，可能含绝对路径 |
| `ReportTaskSummary.error_message` | 异常文本，可能含路径/内部细节；默认不进入 |
| `ReportFinding.manual_notes` | 人工备注可能含敏感信息；仅 `include_notes=True` 且用户知情时，转义后进入 |
| `ReportFinding.description` / `recommendation` | 扫描器/漏洞文本，可能含恶意 HTML；只能作为转义文本，不能作为 HTML |
| `ReportFinding.metadata` | 只允许 Repository 已过滤的安全键；不 dump 原始 metadata |
| `ReportEvidence.source` / `file_name` | 可能含原始路径/敏感文件名；展示前应移除绝对路径，只保留文件名或受控相对路径 |
| `ReportEvidence.description` | 用户自由文本；默认转义；敏感内容需用户确认 |
| 原始 `Authorization` / `ScopeAsset` / `Evidence` 对象 | 不进入快照以外的 HTML；不得读取数据库原始行 |
| `__dict__` / dataclasses 全量序列化 | 会越过 allowlist，可能带出路径/内部字段 |

### 4.4 允许进入 HTML 的字段原则

HTML exporter 必须使用**报告专用 allowlist / view model**，例如：

```text
ReportView
  project: {project_id, project_name, type_label, status_label}
  authorization: ReportAuthorizationSummary
  stats: ReportStats
  findings: [只投影 ReportFinding 的展示字段]
  evidence: [只投影 title/type/hash/受管相对路径/状态]
  tasks: [只投影 task_id/type/status/时间/进度/扫描器]
  warnings / limitations / data_scope
```

不允许：

- exporter 直接读取数据库；
- exporter 接收 ORM/SQLite Row；
- exporter `dump(__dict__)`；
- exporter 通过 `SELECT *` 自行补充字段；
- exporter 把 `ReportSnapshot` 原样传入模板而不做字段选择。

## 5. 模板目录设计

推荐目录（**只设计，未创建**）：

```text
reports/
├── __init__.py
├── html_exporter.py
└── templates/
    ├── base.html
    ├── vulnerability_report.html
    ├── evidence_report.html
    └── project_summary_report.html
```

评估：

- 该结构适合现有项目：`reports` 已是包，`storage/reports` 是输出目录，模板属于代码资源，不应放进可写的报告输出目录；
- 模板目录应位于 `reports/templates/`，不要放在 `storage/reports/`；
- 使用 `jinja2.FileSystemLoader` 是合适的：模板是本地包资源，可显式指定绝对路径，避免 `PackageLoader` 在打包/工作目录变化时的歧义；
- 建议：

```python
Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=True,
    auto_reload=False,
    undefined=StrictUndefined,
)
```

- `auto_reload=False` 用于生产确定性；开发期可开启，但不能改变安全配置；
- 不把用户输入作为模板名；模板名来自固定 allowlist（三种报告类型）；
- 不需要独立 CSS 文件：第一版使用 `<style>` 内联，保持 single-file；
- 若未来需要可维护性，可保留 `templates/_styles.css` 作为**模板片段**，渲染时内联到 `<style>`，但不能生成 `<link rel="stylesheet">` 外部引用；
- 不需要 JavaScript 文件；第一版没有 JS。

## 6. HTML 安全策略

### 6.1 HTML 注入

**Jinja2 `autoescape = required`。**

- 使用 `Environment(autoescape=True)`，或至少 `select_autoescape(["html", "xml"], default=True)`；
- 所有 DTO 文本只放在 HTML 文本节点或**带引号的属性**中；
- 不使用：

```text
|safe
Markup(...)
"<div>" + user_value + "</div>"
render_template_string(user_template)
```

- 不使用用户提供模板字符串；模板名只来自固定 allowlist；
- 不对 `description` 做 Markdown 渲染；否则需要额外的 HTML sanitizer，本阶段不引入；
- 不把不可信值放入 `style`、`class`、`href`、`src` 或事件属性；
- `ReportRequest.title` 同样必须转义；
- `Project.project_name`、Finding 的 `title/category/rule_id`、Evidence 的 `title/description` 都可能含 HTML。

当前实际数据未发现 `<script>`/`<img>`/`<a>`/`onerror`/`onclick`，但 31 条 `http` 文本证明自由文本会出现 URL 样式内容；不能因此关闭 autoescape。

### 6.2 JavaScript

**第一版 HTML 报告禁止 JavaScript，且可以完全不用 JS。**

- 不生成 `<script>`；
- 不生成内联事件属性：`onclick`、`onerror`、`onload` 等；
- 不使用 `javascript:` URL；
- 不引入交互式图表/筛选；报告是静态、可打印文档；
- 测试必须断言输出中不存在 `<script` 和事件属性。

### 6.3 外部资源

禁止：

| 资源 | 策略 |
|---|---|
| remote CSS | 禁止；不生成 `<link rel="stylesheet" href="http...">` |
| remote JS | 禁止；不生成 `<script src=...>` |
| remote image URL | 禁止；不生成 `src="http..."` |
| remote font | 禁止；不引用 Google Fonts/CDN |
| CSS `@import` | 禁止 |
| CSS `url(http...)` | 禁止 |
| 自动网络访问 | 禁止；导出过程不发起网络请求 |
| 超链接 | 默认不把 URL 变成可点击链接；URL 只作为转义文本 |

- 第一版是 single-file HTML；
- 不依赖任何 `https://`/`http://` 外部资源；
- 不自动加载漏洞公告链接；
- 如未来需要链接，必须单独评审并明确 `rel="noopener noreferrer"`、协议 allowlist 和用户确认；本阶段不做。

### 6.4 CSS

推荐 **A. CSS 内联到 HTML `<style>`**。

理由：

1. single-file 报告，方便移动、归档、脱机查看；
2. 不依赖外部文件或 CDN；
3. 不受相对路径/打包目录影响；
4. 便于一次性计算 HTML 哈希；
5. 可以用 `@media print` 规划打印样式。

不推荐第一版使用独立 CSS 文件，因为会破坏 single-file 和离线可移植性。CSS 必须是静态常量，不能把 DTO 文本插入 `style` 内容。打印样式只使用静态 CSS，例如 `@media print { ... }`。

## 7. 证据图片安全策略

### 7.1 当前 DTO

`ReportEvidence` 同时有：

```text
file_path       # 数据库中的原始证据路径，可能是绝对路径
managed_path    # 相对 evidence_root 的受管路径，例如 project_1/xxx.png
file_hash       # SHA-256
file_exists     # Service 校验结果
hash_matches    # Service 校验结果
file_status_note
```

`ReportService._annotate_evidence()` 当前行为：

1. 只接受绝对路径；
2. 拒绝 `path.is_symlink()`；
3. `path.resolve(strict=False)` 后必须 `relative_to(evidence_root/project_<project_id>)`；
4. 必须是 `is_file()`；
5. 有 `file_hash` 时计算 SHA-256 并比较；
6. 记录 `managed_path`/`file_exists`/`hash_matches` 和 warnings；
7. 不读取项目外文件。

### 7.2 项目隔离

证据根目录按项目隔离：

```text
storage/evidence/project_<project_id>/
```

`ReportService` 以 `evidence_root/project_<snapshot.project.project_id>` 作为 containment root，因此不同项目的证据不能互相引用。`ReportEvidence.managed_path` 是相对路径，不直接包含本机绝对根目录。

### 7.3 路径越界与符号链接

现有校验覆盖：

- 数据库路径不是绝对路径 → 不读取；
- 路径本身是符号链接 → 不读取；
- `resolve` 后不在项目证据目录 → 不读取；
- 不存在/不是文件 → 标记缺失；
- 哈希不一致 → warning，不声称完整。

HTML 导出阶段仍必须重新执行 containment 检查和 SHA-256 校验，不能只信任 DTO 中的 `file_exists=True`。

### 7.4 第一版策略：默认不包含证据图片

**推荐第一版 HTML 不嵌入任何证据图片。**

原因：

- 图片会把单文件体积放大；
- 截图可能包含凭据、个人信息、客户数据；
- 需要额外的图片解析/解码攻击面；
- 当前 `ReportRequest.include_evidence_images` 虽存在，但不应在 C2 第一版启用；
- 报告可以列出证据标题、类型、哈希和“文件存在/缺失”状态，不展示原图。

### 7.5 未来如允许嵌入

必须同时满足：

- 格式：仅 PNG/JPEG；拒绝 SVG（可含脚本/外部实体）、GIF、WebP、PDF；
- 大小：单文件上限建议 5 MiB；
- SHA-256：必须与数据库记录一致，不一致拒绝；
- containment：`resolve()` 后必须位于 `evidence_root/project_<id>/`；
- 拒绝符号链接、目录联接、`..`/UNC/设备路径；
- 只读取已通过校验的受管文件；
- 使用 `data:image/png;base64,...` 或 `data:image/jpeg;base64,...`；
- 不生成远程 URL；
- 嵌入前必须有用户显式 opt-in 和敏感信息提示；
- 任何一项失败：不嵌入、报告 warning，不伪造图片。

本阶段不实现以上图片逻辑。

## 8. 敏感字段与 allowlist

### 8.1 可以进入 HTML 的字段（建议）

- 项目：`project_id`、`project_name`、`project_type` 标签、`status` 标签；
- 报告：`report_type`、`generated_at`、`schema_version`、`snapshot_id`、`data_scope`、`warnings`、`known_limitations`；
- 授权摘要：全部计数、`as_of`、`note`；
- 任务：`task_id`、`task_type` 标签、`status` 标签、开始/结束时间、`progress`、`scanners`；
- Finding：`finding_id`、标题、类别、风险等级/置信度标签、扫描器/版本、规则 ID、相对文件路径、行号、检测时间、依赖字段、状态；
- Finding 文本：`description`、`recommendation` 仅在严格 autoescape 下作为**纯文本**；不得作为 HTML/Markdown 渲染；
- 备注：仅 `include_notes=True` 且用户知情时，autoescape 后作为纯文本；
- Evidence：`evidence_id`、`finding_id`、标题、类型标签、`file_name`（去除路径）、`file_hash`、`created_at`、`file_exists`/`hash_matches` 状态；
- Stats：全部计数。

### 8.2 必须禁止进入 HTML 的字段

- `Project.local_path`；
- `Project.description`（默认禁止；如未来展示需专门脱敏评审）；
- `ReportEvidence.file_path`；
- `ReportTaskSummary.target`；
- `ReportTaskSummary.error_message`；
- 原始 `Authorization`、`ScopeAsset`、`Evidence` 对象的任意字段；
- `__dict__`、`vars()`、dataclass 全量序列化；
- 原始 SQLite Row；
- 未经过 `_SAFE_METADATA_KEYS` 的 metadata；
- 任何数据库连接/查询结果；
- 认证令牌、密码、API key、授权凭证、内部绝对路径、项目根路径、用户主目录。

### 8.3 数据流约束

```text
ReportRepository (read-only snapshot)
        ↓
ReportService (stats / warnings / evidence verification)
        ↓
HTML exporter view-model allowlist
        ↓
Jinja2 autoescape template
        ↓
single-file HTML
```

禁止：

```text
HTML exporter → Database
HTML exporter → ORM/SQLite Row
HTML exporter → ReportSnapshot.__dict__
HTML exporter → SELECT *
HTML exporter → 用户提供的模板字符串
```

## 9. 文件写入安全方案

未来应采用：

```text
target.html.tmp.<random>
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
        ↓
target.html
```

要求：

1. 临时文件与目标文件在**同一目录/同一卷**，保证 `os.replace` 原子性；
2. 使用 `uuid4` 生成临时名，避免并发冲突；
3. 写入编码固定 UTF-8，显式换行策略；
4. `flush` + `fsync` + `close` 成功后才 replace；
5. `os.replace` 前目标已存在时，必须由调用方/UI 显式确认覆盖；
6. 未确认覆盖时，目标存在即失败，不截断原文件；
7. 渲染失败、写入失败、flush/fsync 失败：删除临时文件，保留原目标；
8. `os.replace` 失败：保留临时文件用于诊断或清理，原目标不变；
9. 输出路径必须在 `AppConfig.reports_dir` 内，使用安全文件名；
10. 不允许用户提供任意绝对路径/`..` 输出路径；
11. 不允许把临时文件放在系统临时目录后跨卷 replace；
12. 导出失败绝不能把不完整内容替换成正式报告。

Windows 注意：

- `os.replace` 在同一个卷上是原子替换；目标被浏览器/杀毒软件占用时可能 `PermissionError`，此时保留原目标并报告错误；
- 路径长度受 Windows 限制影响，输出文件名应限制长度；
- `fsync` 在 Windows 上对普通文件可用，但仍需捕获 `OSError`；
- `os.replace` 不是“覆盖前备份”；覆盖确认是产品层要求，不能只依赖文件系统；
- 临时文件必须用 `finally` 清理，避免残留敏感内容；
- 不将临时文件放在 `storage/reports` 之外。

本阶段不实现写入器。

## 10. 测试计划（未来 `tests/test_report_html.py`）

只设计，不创建测试。

### 功能

- 三类报告都能生成；
- UTF-8 中文/emoji/特殊字符正确；
- 空项目/空 Finding/空 Evidence；
- 正常有数据项目；
- 生成前后原始数据库/快照数据不变；
- 三类型使用正确模板和章节；
- `warnings`/`known_limitations` 不被丢弃。

### 安全

- `<script>alert(1)</script>` 被转义，输出无真实 `<script>`；
- `<img src=x onerror=alert(1)>` 被转义/事件属性不成为属性；
- 恶意 HTML 属性（`" onmouseover=...`）不逃逸属性上下文；
- `javascript:` URL 不作为链接；
- `http://`/`https://` 文本不自带远程资源请求；
- 输出不含 `<link rel="stylesheet" href="http...">`、`<script src=...>`、远程 `<img src=...>`；
- 敏感字段（local_path、file_path、authorization document、password/token/secret 样本）不进入 HTML；
- 路径越界/符号链接证据不进入 HTML；
- `|safe`/`Markup` 不使用（代码审查 + 输出断言）；
- 无 JavaScript；
- 无远程 URL 资源。

### 文件

- 临时文件创建、写入、flush/fsync、close、replace；
- 原子替换后目标内容完整；
- 写入失败不覆盖已有目标；
- 目标已存在且未确认覆盖时失败；
- 临时文件在失败后清理；
- 输出路径 containment；
- Windows 锁定目标时错误可报告、原目标保留。

### 输出

- HTML 可被标准解析器解析（基础结构）；
- 不含 `<script`；
- 不含远程 `src`/`href`/`@import`；
- 存在内联 CSS；
- 存在打印样式 `@media print`；
- 标题/统计/章节/空状态文案存在；
- 不声称“无漏洞=安全”或“无任务=通过”。

### 测试环境备注

当前完整 pytest 受 DSH 临时目录 ACL 影响（见第 11 节），未来 HTML 测试应优先使用项目工作区内可控 `tmp_path`，或先修复临时目录权限；不能通过删除/弱化既有测试来“通过”。

## 11. 当前测试基线

### 11.1 收集结果

```text
145 tests collected in 0.35s
```

### 11.2 完整执行尝试

本次调查尝试执行完整 `pytest -q -p no:cacheprovider`，但当前 DSH 临时目录权限导致大量 pytest-qt setup 错误，未得到有效完整测试结论：

```text
PermissionError: [WinError 5] 拒绝访问。:
'C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs\pytest-of-lenovo'
```

改用工作区临时目录后：

```text
PermissionError: [WinError 5] 拒绝访问。:
'D:\挖漏洞\SRC-Research-Assistant\storage\_c1_pytest_tmp\pytest-of-lenovo'
```

结果：

```text
1 failed, 7 passed, 137 errors in 1.71s
```

错误集中在 pytest-qt 的 setup/临时目录清理；`test_pip_audit_actual_available` 的 `TemporaryDirectory` cleanup 也因 `chmod(... follow_symlinks=False)` 被拒绝。不是产品断言失败，也不是测试代码被修改。

阶段 B 封存前记录的完整基线为：

```text
144 passed, 1 skipped, 145 collected
```

本次 C1 只确认 collect-only 为 145；未将环境受阻的完整执行伪造成绿色结果。

### 11.3 修改声明

- 生产代码修改：否
- 测试代码修改：否
- 数据库修改：否
- Schema 修改：否
- 依赖安装：否
- 第五阶段/阶段 B 归档修改：否

## 12. 推荐 C2 实施方案

建议 C2 只做 HTML 第一版，不做 PDF/JSON/GUI 全面接入：

1. 新增 `reports/html_exporter.py`：
   - 输入 `ReportSnapshot`/`ReportRequest`；
   - 生成报告专用 view model allowlist；
   - 选择固定模板；
   - 渲染为 UTF-8 HTML 字符串；
   - 不读数据库。
2. 新增 `reports/templates/base.html`、三类报告模板：
   - 内联 CSS；
   - 无 JS；
   - 无外部资源；
   - 严格 autoescape；
   - 打印样式。
3. 新增原子写入函数：
   - 输出到 `AppConfig.reports_dir`；
   - temp + fsync + close + `os.replace`；
   - 覆盖保护；
   - 失败清理。
4. 不实现证据图片嵌入；`include_evidence_images` 第一版保持关闭/忽略并提示。
5. 不写 `reports` 表，不改 schema；如需生成记录，后续单独评审。
6. 先写 `tests/test_report_html.py`，覆盖第 10 节；再接入 `ui/report_page.py`（如 C2 范围包含 GUI）。
7. 所有 C2 变更需先解决当前完整 pytest 临时目录权限问题，或使用工作区内 tmp 验证；不能降低既有断言。

推荐 C2 顺序：

```text
C2a: view model + templates + autoescape + atomic writer
C2b: HTML security/output/file tests
C2c: optional UI wiring and overwrite confirmation
```

## 13. 已知风险

1. **Jinja2 autoescape 不是 HTML sanitizer**：它不阻止 Markdown 链接、CSS/URL 上下文或未来错误的 `|safe`；必须配合字段 allowlist、URL 不作为链接、静态 CSS。
2. **`ReportSnapshot.project` 是完整 Project**：包含 `local_path`/`description`；exporter 必须投影，不能直接传对象。
3. **`ReportEvidence.file_path` 是原始绝对路径**：HTML 只能使用受管相对路径或文件名校验结果，不能直接展示 raw path。
4. **自由文本可能含凭据/PII**：description、manual_notes、evidence description、project description 需要用户提示与转义；不能自动脱敏承诺。
5. **证据图片**：第一版不嵌入；未来若嵌入，SVG/远程 URL/哈希不一致/符号链接均是高风险入口。
6. **Windows 文件替换**：目标被占用、跨卷、路径过长、临时文件未清理；必须原子替换和覆盖确认。
7. **当前测试环境**：DSH 临时目录 ACL 导致完整 pytest 无法稳定执行；C2 必须先解决测试环境，否则无法证明安全回归。
8. **报告真实性**：不得把 0 Finding 写成“无漏洞”，不得把无任务写成“通过”，不得把 Semgrep 夹具写成真实扫描；模板文案必须保留 warnings/limitations。
9. **Jinja2 3.1.6/Python 3.14.4**：当前导入正常，但应继续锁定版本并在 C2 测试中验证实际渲染；不在本阶段升级/安装。
10. **未接入 `ReportService`**：C1 没有修改 bootstrap/UI；C2 接入时必须保持只读边界和现有页面线程模型。

## 14. 是否满足进入 C2 的条件

**设计条件：满足。**

- Jinja2 3.1.6 已安装且可导入；
- 现有 `ReportSnapshot`/Repository/Service 提供只读、项目隔离、真实性 warnings；
- HTML 安全策略、模板目录、字段 allowlist、图片默认禁用、原子写入和测试计划已明确；
- 不存在已有 HTML exporter/template/CSS/JS 需要兼容。

**进入 C2 前必须处理的环境前置：**

- 当前 DSH 临时目录 ACL 导致完整 pytest 无法稳定执行；C2 的测试必须使用工作区内可控临时目录，或修复 pytest-qt 临时目录权限；
- 未修改任何测试；不得删除 skip 或降低断言。

**未满足/未启动：**

- C2 未开始；
- 未创建 HTML exporter/模板/CSS/测试；
- 未修改 ReportService/Repository/DTO/GUI/DB/schema；
- 未安装依赖；
- 未修改第五阶段或阶段 B 归档。

## 15. 本次实际修改

仅新增调查报告：

```text
docs/PHASE6_C1_HTML_INVESTIGATION.md
```

未修改其他生产文件、测试、数据库、schema、报告输出目录或归档。

## 16. 停止状态

```text
Phase 6C-1 = completed
Phase 6C-2 = not started
Phase 6D/E/F = not started
```
