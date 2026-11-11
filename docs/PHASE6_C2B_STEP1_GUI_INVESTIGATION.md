# Phase 6C-2B Step 1：GUI 架构只读调查报告

**项目：** `D:\挖漏洞\SRC-Research-Assistant`  
**阶段：** Phase 6C-2B · Step 1（只读调查）  
**调查日期：** 2026-11-09  
**结论：** `STEP_2_READINESS = READY_WITH_LIMITATIONS`

---

## 0. 结论摘要

现有 GUI 可以直接承载报告中心，不需要重写页面框架，也不需要引入 QtWebEngine、PDF 或其他新依赖。推荐的最小方案是：

- `ReportPage` 从占位页改成接收 `AppContext` 与 `AppState` 的普通页面；
- 在 `build_context()` 中增加 `ReportRepository` 和 `ReportService`，通过 `AppContext.report_service` 注入；
- 固定使用 `AppContext.config.reports_dir`，GUI 不接受目录或绝对路径；
- HTML 预览使用已安装的 `QTextBrowser`（`PySide6.QtWidgets`），明确标注为“安全文本预览，不是浏览器排版”；
- 正式文件只通过 `reports.html_exporter.write_html_report()` 发布，GUI 不实现任何文件写入；
- 导出在 GUI 线程同步执行，用 `_exporting` 标志和按钮禁用实现单写者；
- 默认 `overwrite=False`，只在捕获 `FileExistsError` 后显示明确覆盖确认，再以 `overwrite=True` 重试；
- 不实现 PDF、JSON、报告历史表或远程资源加载。

该方案存在预览排版不精确、Windows symlink 动态验证缺失、TOCTOU 等已记录限制，因此不能宣称“完全安全”或“浏览器一致”。

---

## 1. 现有 GUI 架构与页面生命周期

### 1.1 入口与页面注册

`ui/main_window.py:35-50` 的 `MainWindow` 接收 `AppContext` 和 `AppState`。页面只在 `_add_pages()` 中创建一次，加入 `QStackedWidget`：

- `ui/main_window.py:69-71`：创建 `self.stack = QStackedWidget()`；
- `ui/main_window.py:185-208`：集中创建 10 个页面，存入 `pages_by_key`，并逐个 `stack.addWidget(page)`；
- `ui/main_window.py:197`：当前仍是 `"reports": ReportPage()`，没有传入 context/state；
- `ui/main_window.py:325-333`：`navigate(key)` 切换 `stack`、更新导航按钮并调用 `_on_page_changed(key)`。

因此报告页如果改成 `ReportPage(context, state)`，只需要修改这一处构造，不需要改导航或页面栈结构。

### 1.2 页面刷新生命周期

`_on_page_changed()` 在每次导航时刷新对应页面：

- `ui/main_window.py:231-245`：`dashboard`、`projects`、`source_audit`、`dependencies`、`vulnerabilities`、`evidence` 都有刷新分支；
- 当前没有 `"reports"` 分支；
- 推荐报告页增加 `refresh()`，并在此处调用 `self.report_page.refresh()`；
- 页面对象不会因切换而销毁，报告页不应在构造函数里做重活，应在首次导航或 `refresh()` 中加载快照。

### 1.3 页面通用构建方式

现有页面遵循相同结构：

- `ui/vulnerability_page.py:60-85`：构造时保存 `context`、`state`、`_service`，连接 `state.project_changed`；
- `ui/vulnerability_page.py:87-162`：`page_header()` + `card` 风格过滤器 + `QSplitter`；
- `ui/evidence_page.py:57-80`：同样的 context/state/service 生命周期；
- `ui/source_audit_page.py`、`ui/dependency_page.py` 使用 QThread 执行耗时扫描，但报告 HTML 导出不是扫描，不需要复用扫描 worker。

报告页可以复用 `ui/widgets.py` 的 `page_header()`、`button()`、`card()`、`confirm()`、`show_error()`，无需新增通用组件。

### 1.4 关闭路径

`ui/main_window.py:315-322` 只调用扫描/证据页面的 `shutdown()`。报告页如果采用同步导出（本报告推荐），没有线程或文件句柄，不需要额外 `shutdown()`；如果未来改为 QThread，需要在该处增加停止逻辑。

---

## 2. `ReportService` 接口与依赖注入方式

### 2.1 真实构造参数

`services/report_service.py:76-92`：

```python
class ReportService:
    def __init__(
        self,
        database,
        repository,
        *,
        evidence_root: str | Path | None = None,
        clock=utc_now,
    ) -> None:
```

真实依赖为：

- `database`：现有 `Database`；
- `repository`：`ReportRepository`；
- `evidence_root`：项目受管证据根目录，生产应传 `config.evidence_dir`；
- `clock`：可注入时钟，测试可固定时间。

`ReportRepository` 的构造在 `repositories/report_repository.py:30-32` 附近为 `ReportRepository(database, clock=...)`，实际测试 fixture 见 `tests/test_report_service.py:29-43`。

### 2.2 公开接口

当前真正可供 GUI 使用的接口：

- `get_snapshot(project_id: int, report_type: ReportType | str) -> ReportSnapshot`：`services/report_service.py:94-102`；
- `get_snapshot_for_request(request: ReportRequest) -> ReportSnapshot`：`:104-108`；
- `ReportSnapshot` 是 frozen dataclass，含 `project`、`authorization`、`tasks`、`findings`、`evidence`、`stats`、`generated_at`、`schema_version`、`data_scope`、`warnings`、`known_limitations`，见 `core/models/report.py:242-268`；
- `ReportArtifact` 在 `core/models/report.py:271-283`，字段为 `report_type`、`report_format`、`project_id`、`title`、`generated_at`、`snapshot_id`、`path`、`sha256`、`warnings`。

`ReportService` 不负责 HTML 渲染，也不写文件；这是它与导出器的明确边界（`services/report_service.py:1-6` 的模块说明）。

### 2.3 当前未注入生产 Context

`app/bootstrap.py:30-43` 的 `AppContext` 当前字段没有 `report_service`；`app/bootstrap.py:105-124` 只构造漏洞/证据服务。`ui/main_window.py:197` 也仍使用无参占位页。

推荐在 `build_context()` 中增加：

```python
from repositories.report_repository import ReportRepository
from services.report_service import ReportService

report_repository = ReportRepository(database, clock=clock)
report_service = ReportService(
    database,
    report_repository,
    evidence_root=config.evidence_dir,
    clock=clock,
)
```

并在 `AppContext` 增加 `report_service` 字段。这样报告页只依赖 `context.report_service`，不需要自己构造 repository/database，也不需要在 UI 中写 SQL。

不推荐的替代方案：

- 在 `ReportPage` 内直接构造 `ReportRepository`：会造成 UI 与数据库连接生命周期耦合；
- 把 `ReportRepository` 暴露给 UI：扩大页面可访问边界；
- 让 GUI 直接查询 `findings`/`evidence`：违反现有 UI 不直接 SQL 的架构。

### 2.4 快照与导出调用顺序

推荐顺序：

1. `snapshot = context.report_service.get_snapshot(project_id, report_type)`；
2. `html = reports.html_exporter.render_html(snapshot, request)` 仅用于预览；
3. 用户点击导出时，仍以同一 `snapshot` 调 `write_html_report(...)`；
4. 不在 GUI 中拼接 SQL 结果，不从 exporter 读数据库。

`render_html()` 与 `write_html_report()` 都只接收 `ReportSnapshot`/`ReportRequest`，不导入数据库、repository 或 scanner（`reports/html_exporter.py:11-13`）。

---

## 3. `AppConfig.reports_dir` 的传递路径

### 3.1 配置解析

`app/config.py:43-65` 定义 `reports_dir: Path` 字段；`app/config.py:90-95` 解析：

```python
reports_dir = _resolve(base, storage.get("reports"), "storage/reports")
```

`_resolve()` 在 `app/config.py:36-40` 将相对路径按配置文件目录展开，并返回 `.resolve()` 后的绝对路径。

`app/config.py:131-142` 的 `ensure_directories()` 会在启动时创建 `reports_dir`。

### 3.2 运行时路径

实际配置 `config.yaml` 的 `storage.reports` 解析结果为：

```text
D:\挖漏洞\SRC-Research-Assistant\storage\reports
```

当前该目录只有 `.gitkeep`，没有报告文件。`app/bootstrap.py:63` 调用 `config.ensure_directories()`，因此页面构造时该目录应已存在。

### 3.3 到组件的传递链

```text
build_context()
  -> AppConfig.load()
  -> config.ensure_directories()
  -> AppContext(config=...)
  -> MainWindow(context, state)
  -> ReportPage(context, state)
  -> context.config.reports_dir
```

推荐报告页保存：

```python
self._reports_dir = context.config.reports_dir
```

不推荐：

- 从环境变量或当前工作目录重新推导；
- 让用户在 `QLineEdit` 输入完整目录；
- 在 GUI 中调用 `Path.mkdir()` 或自己写文件；
- 把 `reports_dir` 和文件名用字符串拼接后再交给任意文件 API。

导出的固定根目录应由 `write_html_report()` 的 `_resolve_reports_root()` 再次验证，见 `reports/html_exporter.py:645-658`。

---

## 4. 项目选择组件复用方案

### 4.1 全局项目状态

`ui/app_state.py:11-42` 的 `AppState` 持有当前活动项目，并提供：

- `current_project`；
- `current_project_id`；
- `project_changed` / `projects_changed` 信号；
- `set_active_project()`。

`ui/main_window.py:171-175` 的全局 `project_combo` 是唯一的项目切换入口；`ui/main_window.py:267-281` 切换时调用 `state.set_active_project()`。

### 4.2 现有页面的复用方式

- `ui/vulnerability_page.py:258-273`：页面内 `project_filter` 使用“全部项目”+ 项目列表，选择后通过 `refresh()` 过滤；
- `ui/evidence_page.py:107-125`：同样使用页面内 `project_filter`；
- 这两个页面都通过 `state.project_changed` 同步全局项目。

### 4.3 报告页建议

报告必须严格属于一个项目，不应出现“全部项目”报告。因此建议：

- 不在报告页新增第二个项目下拉框；
- 直接使用 `AppState.current_project_id` 和 `AppState.current_project`；
- 顶部显示当前项目名称，和现有页面的项目卡片一致；
- 连接 `state.project_changed`，项目切换后重建快照并刷新预览；
- 未选择项目时，项目卡片显示“请先在顶部选择当前项目”，预览和导出按钮禁用。

如果步骤二明确要求页面内独立选择器，可以复用 `ui/vulnerability_page.py:258-273` 的 `QComboBox` 模式，但必须：

- 不允许“全部项目”；
- 选择项目时调用 `state.set_active_project()`，而不是只改页面局部变量；
- 避免页面选择器与全局选择器状态分叉。

**结论：** 现有全局 `project_combo + AppState` 足够复用，报告页不需要新增项目选择组件。

---

## 5. HTML 预览技术方案及实际依赖证据

### 5.1 依赖探测结果

在项目虚拟环境中实际执行（`PySide6 6.12.0`）：

| 模块 | 可用 |
|---|---|
| `PySide6.QtWidgets` | 是 |
| `PySide6.QtWebEngineWidgets` | 否 |
| `PySide6.QtWebEngineCore` | 否 |
| `PySide6.QtPdf` | 否 |
| `PySide6.QtPdfWidgets` | 否 |
| `PySide6.QtGui` | 是 |

`QTextBrowser`、`QTextEdit` 和 `QLabel` 均可从 `PySide6.QtWidgets` 导入；`QTextBrowser` 提供 `setHtml` 和 `setSource`。

### 5.2 为什么选择 `QTextBrowser`

- 不需要安装 QtWebEngine、PySide6-Addons 或其他依赖；
- `QTextBrowser` 只做 Qt rich text 渲染，不提供浏览器 JavaScript 引擎；
- 本次探针设置包含 `<script>alert(1)</script>` 的 HTML 后，文档纯文本中未出现 `alert`，同时中文“报告预览”正常显示；
- 可以作为“安全文本预览”，不会把报告当成本地 Web 应用执行。

探针结果摘要：

```text
HTML_LEN 809
TEXT '报告预览\n本地 HTML 渲染'
HAS_SCRIPT_IN_TEXT False
HAS_CJK True
DEFAULT_STYLE True
```

### 5.3 预览实现建议

推荐：

```python
self.preview = QTextBrowser()
self.preview.setOpenExternalLinks(False)
self.preview.setOpenLinks(False)
self.preview.setHtml(render_html(snapshot, request))
```

说明：

- `setOpenLinks(False)` 防止点击锚点时让 `QTextBrowser` 自行导航；当前模板没有链接，但这是防御性设置；
- `setOpenExternalLinks(False)` 防止未来模板出现外部链接时自动调用系统浏览器；
- 不使用 `setSource(QUrl.fromLocalFile(...))` 作为首选，因为预览不需要读取磁盘文件；`setHtml` 直接消费 `render_html()` 的返回值，不产生临时文件；
- 不加载远程 CSS、字体、图片或脚本；模板 `reports/templates/base.html` 没有 `<script>`、`<link>`、`<img>` 或外部 `href`。

### 5.4 预览的能力边界

`QTextBrowser` 不是 Chromium/WebEngine，不能保证与浏览器排版一致：

- `reports/templates/base.html:8-28,48-69` 使用 CSS 变量、`display: grid`、`flex`、`max-width` 等；Qt rich text 只支持 HTML/CSS 子集，复杂布局可能被忽略或降级；
- 预览应明确标注“安全文本预览（非浏览器排版）”，不能让用户把它当成最终版式；
- 最终交付文件仍以 `write_html_report()` 写出的 UTF-8 HTML 为准，可在系统浏览器中人工检查；
- 不把预览截图作为验收证据，也不宣称预览与导出文件视觉一致。

### 5.5 不采用的方案

| 方案 | 结论 | 原因 |
|---|---|---|
| `QWebEngineView` | 不采用 | 当前 `PySide6.QtWebEngineWidgets` 不可用；新增依赖超出最小范围 |
| `QtPdf` / `QtPdfWidgets` | 不采用 | 当前不可用，且 PDF 不属于 Step 2 |
| `QDesktopServices.openUrl()` 作为主预览 | 仅可作为“在系统浏览器打开”辅助 | 会把文件交给外部程序，不是应用内预览；不应默认自动打开 |
| `QTextEdit` | 不采用 | 不是浏览器视图，导航/文档语义弱于 `QTextBrowser` |
| 自行解析 HTML 并绘制 | 不采用 | 与安全导出器重复，增加攻击面 |

**结论：** Step 2 可以做内嵌预览，但必须用 `QTextBrowser` 并明确其非浏览器性质；如果产品要求像素级浏览器预览，则应另立阶段评估 QtWebEngine 的依赖、许可证和安全边界，而不是在 C2B 偷加依赖。

---

## 6. 导出按钮的单写者方案

### 6.1 推荐：GUI 线程同步导出

报告 HTML 的步骤是：

1. 读取本地 SQLite 快照；
2. Jinja2 渲染字符串；
3. 原子写入固定目录。

当前数据规模下这是本地、短时操作，推荐在 GUI 线程同步执行，理由：

- 不需要 QThread 生命周期、取消和关闭协调；
- 天然只有一个导出调用在运行；
- 不会出现“后台 worker 未结束，页面已切换”的竞态；
- `write_html_report()` 自身用临时文件、`fsync`、`os.replace`/`os.link` 和 `finally` 清理，见 `reports/html_exporter.py:719-754`。

### 6.2 单写者状态机

推荐页面字段：

```python
self._exporting = False
```

导出入口：

```python
def _export(self) -> None:
    if self._exporting or self._snapshot is None:
        return
    self._exporting = True
    self.export_button.setEnabled(False)
    self.preview_button.setEnabled(False)
    try:
        self._do_export()
    finally:
        self._exporting = False
        self.export_button.setEnabled(True)
        self.preview_button.setEnabled(True)
```

要点：

- `_exporting` 必须在最前面检查，不能只依赖按钮禁用；
- 按钮禁用只是视觉反馈，不是并发控制；
- 不要调用 `QApplication.processEvents()` 来“让界面响应”，否则会打开重入窗口；
- 不要在 `except` 中提前恢复按钮，统一放在 `finally`；
- 导出完成、用户取消覆盖、导出失败都必须走同一恢复路径；
- 如果未来改为 QThread，必须只允许一个 worker，且 `finished` 后才能再次启动；本阶段不推荐引入线程。

### 6.3 与主窗口的忙碌状态

现有 `MainWindow._set_scanning_busy()`（`ui/main_window.py:294-303`）是为扫描任务设计的，会禁用项目切换。报告同步导出期间 GUI 不会处理项目切换事件，因此本阶段不必复用该机制；如果使用异步 worker，则应：

- 页面发出 `exporting_changed(bool)`；
- 主窗口在导出期间禁用 `project_combo`；
- 不允许导出期间切换项目，避免快照与项目状态不一致。

---

## 7. 覆盖确认交互方案

### 7.1 默认行为

`write_html_report()` 的签名默认 `overwrite: bool = False`，见 `reports/html_exporter.py:327-333`。GUI 第一次调用必须显式或隐式使用默认值：

```python
try:
    artifact = write_html_report(
        snapshot,
        request,
        context.config.reports_dir,
        overwrite=False,
        filename=filename_or_none,
    )
except FileExistsError:
    if not confirm(self, "覆盖报告", f"目标已存在：\n{target_display}\n\n是否覆盖？", dangerous=True):
        self._set_status("已取消：未覆盖现有报告")
        return
    artifact = write_html_report(
        snapshot,
        request,
        context.config.reports_dir,
        overwrite=True,
        filename=filename_or_none,
    )
```

### 7.2 关键约束

- **不得**先 `Path.exists()` 再直接把 `overwrite=True` 传给导出器；应以导出器的 `FileExistsError` 为唯一覆盖触发条件；
- 覆盖确认必须显示目标文件名/路径，并明确“旧文件将被替换”；
- 默认按钮应为“否”（`ui/widgets.py:141-154` 的 `confirm()` 已把默认设为 No）；
- 用户拒绝后不得删除、移动或改写旧文件；
- 覆盖重试仍必须走 `write_html_report()`，不得用 `open()`/`Path.write_text()` 自行写；
- 覆盖模式下 exporter 使用 `os.replace()`；目标目录和叶子节点仍先经过 `_resolve_reports_root()`、symlink/junction、containment 和目录检查；
- 覆盖失败（权限、磁盘、symlink 变化）应显示错误并保持旧文件；不得把失败显示为成功；
- 覆盖确认对话框是模态的，但 `_exporting` 仍要保持 True，防止对话框关闭后重复点击。

### 7.3 已记录限制

覆盖路径仍存在 C2A 已报告的 TOCTOU 和父级 reparse point 风险：

- `overwrite=True` 的 `os.replace()` 与前面的检查之间存在窗口；
- 父目录 reparse point 不在本阶段动态验证范围；
- Windows 文件 symlink 动态测试受 `WinError 1314` 限制；
- 这些限制必须在报告页的安全提示和测试报告中保留，不得因为“有确认框”就宣称已消除。

---

## 8. 推荐的最小 GUI 文件修改清单

### 8.1 必需修改

| 文件 | 修改 |
|---|---|
| `app/bootstrap.py` | 导入并构造 `ReportRepository`、`ReportService`；`AppContext` 增加 `report_service`；传入 `config.evidence_dir` 和 `clock` |
| `ui/report_page.py` | 用真正的 `ReportPage(context, state)` 替换 `PlaceholderPage`；实现项目卡片、报告类型/标题/备注选项、`QTextBrowser` 预览、同步单写者导出、覆盖确认、状态/错误展示 |
| `ui/main_window.py` | `"reports": ReportPage(self._context, self._state)`；`_on_page_changed()` 增加 `report_page.refresh()`；保存 `self.report_page`；关闭路径无需新增线程清理 |
| `tests/test_ui_report.py` | 新增 UI 测试（见第 9 节） |

### 8.2 建议但非功能必需

| 文件 | 修改 | 原因 |
|---|---|---|
| `ui/main_window.py:139` | 将 `PHASE 5` 更新为 `PHASE 6` 或 `PHASE 6 · C2B` | 当前页脚与已实现的 C2A/C2B 状态不一致 |
| `ui/settings_page.py:84-86` | 将“未开发：报告导出”改为“已实现 HTML 报告；PDF/JSON 尚未实现” | 避免系统设置页继续显示过时的产品状态 |
| `docs/` | Step 2 完成报告和验收记录 | 保持阶段证据链 |

### 8.3 明确不应修改

- `reports/html_exporter.py`：C2A 与 R1 已封存的安全边界，C2B 只能调用；
- `reports/templates/*.html`：模板已通过 C2A 安全检查；
- `repositories/report_repository.py`、`services/report_service.py`：只读接口已稳定；
- `database/schema.py`、`database/connection.py`：不新增报告表，不改 Schema；
- `config.yaml`：继续使用 `storage.reports`，不新增用户可写目录配置；
- `ui/theme.py`、`ui/widgets.py`：无需新组件；复用现有 `card`、`button`、`confirm`、`show_error`。

### 8.4 页面结构建议

```text
page_header("报告中心", "...", "Phase 6C-2B · HTML 报告")
[安全提示] 固定输出目录；默认不覆盖；仅本地生成
[项目卡片] 当前项目 / 报告目录（只读） / 项目状态
[选项卡片] 报告类型 QComboBox / 标题 QLineEdit / 备注 QCheckBox / 文件名（只读自动生成或单段安全输入）
[操作行] 预览按钮 / 导出 HTML 按钮 / 状态标签
[QSplitter]
  左: 报告摘要（类型、生成时间、发现数、证据数、警告）
  右: QTextBrowser 预览（安全文本预览，非浏览器排版）
[底部] 输出路径 / SHA-256（成功后显示）
```

文件名建议：

- 默认由 exporter 生成安全文件名，页面不拼接目录；
- 如果步骤二要求可编辑，只允许单段 basename，不允许 `/`、`\`、`:`，最终仍由 `_validate_filename()` 校验；
- 页面不提供 `QFileDialog.getSaveFileName()` 选择目录，因为那会产生任意绝对路径。

---

## 9. 测试方案

Step 2 实现后至少需要以下测试。所有测试使用临时数据库/临时 `reports_dir`，不访问远程目标。

### 9.1 页面与生命周期

- `test_report_page_requires_active_project`：无活动项目时预览/导出禁用，项目卡片显示提示；
- `test_report_page_has_only_html_option`：报告格式不暴露 PDF/JSON；默认类型/标题/备注可操作；
- `test_report_page_refreshes_when_project_changes`：`state.project_changed` 后快照/预览更新，旧项目快照不残留；
- `test_main_window_navigates_to_report_page`：`pages_by_key["reports"]` 是真实页面，导航触发 `refresh()`。

### 9.2 预览

- `test_preview_uses_render_html_without_writing`：monkeypatch `ui.report_page.render_html`，断言预览内容进入 `QTextBrowser`，`write_html_report` 未被调用；
- `test_preview_marks_non_browser_rendering`：页面存在“非浏览器排版”提示；
- `test_preview_does_not_open_external_links`：`preview.openExternalLinks()` 为 False、`openLinks()` 为 False。

### 9.3 导出调用与单写者

- `test_export_passes_fixed_reports_dir_and_html_format`：monkeypatch `ui.report_page.write_html_report`，断言：
  - `reports_dir == context.config.reports_dir`；
  - `request.report_format is ReportFormat.HTML`；
  - `include_evidence_images is False`；
  - 首次 `overwrite is False`；
  - 文件名不含路径分隔符；
- `test_export_is_single_writer`：在导出入口内再次调用 `_export()`，断言只有一次 `write_html_report` 调用；可用 monkeypatch 在第一次调用中递归触发；
- `test_export_rejects_without_snapshot`：未加载快照时不调用 exporter，状态提示明确；
- `test_export_failure_restores_buttons`：exporter 抛异常，断言 `show_error` 被调用、按钮恢复、无成功状态/路径。

### 9.4 覆盖确认

- `test_existing_file_declined_does_not_overwrite`：第一次抛 `FileExistsError`，`confirm` 返回 False；断言没有第二次调用，旧文件哈希不变；
- `test_existing_file_confirmed_retries_with_overwrite_true`：`confirm` 返回 True；断言第二次调用 `overwrite is True`，成功后才显示路径/hash；
- `test_export_uses_exporter_file_exists_signal`：源码级断言页面不先用 `Path.exists()` 决定覆盖（或只允许导出器异常作为触发）。

### 9.5 安全边界

- `test_report_page_does_not_import_database_or_sql`：静态检查 `ui/report_page.py` 不导入 `database`/`sqlite3`，不出现 `SELECT`/`INSERT`；
- `test_report_page_only_calls_approved_writer`：静态断言使用 `write_html_report`，没有 `open(..., "w")`/`Path.write_text()`；
- `test_filename_validation_still_authoritative`：以 `../x.html` 或 `CON.html` 调 exporter，断言异常且不创建文件；
- `test_export_error_does_not_show_success`：异常后状态为失败，不展示虚假路径/hash。

### 9.6 真实导出（集成）

- 在 `tmp_path` 作为 `config.reports_dir` 的测试 context 上，调用真实 `write_html_report()`，断言：
  - 文件存在且 UTF-8 可读；
  - `ReportArtifact.sha256` 与文件哈希一致；
  - 默认不覆盖已有文件；
  - 确认后才覆盖；
  - 不存在临时 `.tmp` 残留。

### 9.7 测试运行限制

当前 Windows 测试环境需要：

- 独立临时目录 `D:\挖漏洞\pytest_c1r_tmp`；
- DSH full-access 测试进程；
- 不能使用工作区默认的低完整性临时目录。

C1R 已记录完整测试需要专用环境；Step 2 测试计划应沿用该限制，不把因 ACL 导致的失败误判为产品失败。Step 1 本身不运行完整回归。

---

## 10. 安全边界与 UNKNOWN

### 10.1 已确认的安全边界

- 输出根目录固定为 `AppConfig.reports_dir`，页面不提供任意目录输入；
- 文件名只作为单段 basename 传递，最终由 `_validate_filename()` 检查；
- 默认 `overwrite=False`，覆盖必须用户确认；
- 正式发布只调用 `write_html_report()`，GUI 不自行写文件；
- 不访问远程目标、不上传报告、不加载远程资源；
- 不实现 PDF/JSON，不修改数据库报告表；
- 不并发导出；GUI 线程同步 + `_exporting` 标志；
- 预览不执行 JavaScript，`QTextBrowser` 设置禁止外部链接自动打开；
- 保留 C2A/R1 的 symlink、TOCTOU、父级 reparse point 限制，不宣称完全安全。

### 10.2 UNKNOWN / 已记录限制

| 项目 | 状态 | 说明 |
|---|---|---|
| `QTextBrowser` 对当前模板的精确排版 | UNKNOWN/有限 | Qt rich text 不是浏览器；CSS grid/flex/变量可能被忽略；必须标“非浏览器预览” |
| Windows 文件 symlink 动态测试 | UNKNOWN | `WinError 1314` 阻止创建；静态拒绝逻辑已存在，但没有动态 PASS |
| 父级 reparse point | UNKNOWN | R1 未覆盖父目录多级 reparse；固定 `reports_dir` 降低但不消除风险 |
| 覆盖模式 TOCTOU | UNKNOWN | 检查与 `os.replace()` 之间仍有窗口；串行导出和确认只能降低机会，不能证明消除 |
| 报告输出目录自身为 reparse point | 静态拒绝 | `_resolve_reports_root()` 在 resolve 前检查 `is_symlink()`/`is_junction()`；动态 symlink 未验证 |
| 真实多进程并发导出 | 未测试 | 单写者只保证 GUI 内部不重复；外部进程写入不在保证范围 |
| 设备名实际写入 | 未测试 | `_validate_filename()` 拒绝保留名；实际设备写入未尝试 |
| `QTextBrowser` 资源加载 | 当前无资源 | 模板无 `<img>/<link>/<script>`；未来加图片需重新评估 |
| 完整测试回归 | 未执行 | 本轮仅只读调查；Step 2 需专用 temp + full-access |
| 报告历史/DB 记录 | 不在范围 | `reports` 表保持未使用；不写数据库 |

### 10.3 不得声称的事项

- 不得声称预览与浏览器完全一致；
- 不得声称 symlink/TOCTOU 已彻底解决；
- 不得声称导出支持 PDF/JSON；
- 不得声称报告历史已持久化；
- 不得声称没有动态测试的风险已被证明安全；
- 不得在用户拒绝覆盖后仍发布文件或显示成功。

---

## 11. 本轮实际修改文件清单

**新增：**

- `docs/PHASE6_C2B_STEP1_GUI_INVESTIGATION.md`（本报告）

**未修改：**

- 生产代码：`app/`、`ui/`、`reports/`、`services/`、`repositories/`、`database/`；
- 测试代码与断言：`tests/`；
- 数据库与 Schema：`storage/src_research.db`、`database/schema.py`；
- HTML 模板：`reports/templates/`；
- `config.yaml`、依赖文件、Phase 5/6B/C2A 已封存文件。

**只读检查的边界文件哈希（调查时点）：**

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `reports/html_exporter.py` | 24,953 | `207AA3571B4D1900472CFCD8FB75856DCF354335AD81AB905AA35B69D3FAB480` |
| `tests/test_report_html.py` | 28,055 | `41CFC444D59942E9E1D377D9561873B349F938776AD469F7ECE500941BCFECA0` |
| `ui/report_page.py` | 691 | `995B342F370741CFB5CBF59F5F6CF2F697853CB64ABEAEAE201FFFB597A64576` |
| `ui/main_window.py` | 13,124 | `EE1F51CD1258CEF966823C42B8EA3443DDE38263F61257E15BD3AA1F8B45819B` |
| `app/bootstrap.py` | 4,763 | `7365D9067085FB5176D40A8D65BCFBD33B43C8D0F6845A728D1C6DA11680E9C1` |
| `services/report_service.py` | 13,179 | `7E0E56A5B4E69BE1EE6F36B0B16AE2C02B40F50416DC1DD43C1697034D9CFFCD` |

**实际执行：**

- 只读读取上述源码/测试/模板；
- 一次 Qt 模块与 `QTextBrowser` 探针；
- 未运行 pytest、未启动真实导出、未打开数据库写事务、未修改任何生产文件或测试文件。

---

## 12. 是否具备进入步骤二的条件

**结论：`STEP_2_READINESS = READY_WITH_LIMITATIONS`。**

可以进入 Step 2 的条件已经具备：

1. `ReportService`/`ReportRepository` 的构造和公开接口已确认；
2. `AppConfig.reports_dir` 的传递路径固定且可验证；
3. 现有 `MainWindow`/`AppState`/页面生命周期可直接扩展；
4. 项目选择可复用全局 `AppState`，不需要新增选择器；
5. `QTextBrowser` 在当前 PySide6 6.12.0 可用，且不需要新依赖；
6. 安全导出入口 `write_html_report()` 有明确的 `overwrite`/filename/atomic 行为；
7. 单写者、覆盖确认、测试方案都有可实现的最小路径。

进入 Step 2 时必须遵守的附加条件：

- 报告页只能使用 `context.config.reports_dir`；
- 不允许用户输入完整路径，只能传单段文件名或不传（由 exporter 生成）；
- 默认 `overwrite=False`，覆盖必须明确确认；
- 正式发布只走 `write_html_report()`；
- 导出期间禁用按钮并设置 `_exporting`，禁止并发/重入；
- 预览必须标注“非浏览器排版”；
- 不引入 QtWebEngine/PDF/JSON；
- 不修改 exporter/模板/Repository/Schema；
- 保留 symlink、TOCTOU、父级 reparse point 的 UNKNOWN 记录；
- Step 2 测试需在独立临时目录 + full-access 环境运行，或如实报告环境阻塞。

在上述限制下，Step 2 可以开始；如果产品要求“浏览器级像素一致预览”，则当前依赖条件不满足，应先单独评估 QtWebEngine，而不是在 C2B 中扩大范围。
