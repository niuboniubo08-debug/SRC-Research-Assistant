# Phase 6C-2B Step 2 — 最小 HTML 报告中心 GUI 实施报告

日期：2026-11-09  
范围：报告中心 GUI 接入与依赖注入；不包含 JSON、PDF、报告历史或 Schema 修改。  
状态：**STEP_2_IMPLEMENTED_WITH_LIMITATIONS**；等待人工审核，未开始下一步。

## 1. 实施结论

本轮完成了最小可用的 HTML 报告中心：

- `AppContext` 增加只读 `report_service`，由 composition root 构造；
- `ReportPage` 从占位页替换为真实页面，支持当前项目显示、报告类型、标题、人工备注选项、安全文本预览、HTML 导出、状态/错误和输出信息；
- 项目或报告类型改变时立即失效旧快照；导出始终基于当前项目、当前类型和当前标题/备注构造正式 `ReportRequest`；
- 预览只调用 `render_html()`，不写文件；
- 正式导出只调用 `write_html_report()`，固定使用 `context.config.reports_dir`，默认 `overwrite=False`；只有捕获 `FileExistsError` 并得到用户明确确认后才以 `overwrite=True` 重试；
- 导出期间使用 `_exporting` 防止重复进入，禁用相关控件，并在 `finally` 恢复；
- 未修改 C2A/R1 导出核心、模板、`ReportService`、`ReportRepository`、数据库或 Schema。

## 2. 实际修改文件

仅修改以下允许文件：

| 文件 | 变更 |
|---|---|
| `app/bootstrap.py` | 引入 `ReportRepository`/`ReportService`；新增 `AppContext.report_service`；在 `build_context()` 中构造并注入 |
| `ui/report_page.py` | 用完整 `ReportPage(context, state)` 替换占位页 |
| `ui/main_window.py` | 以 `(context, state)` 创建 `ReportPage`；页面切换时刷新；侧栏阶段标识更新为 `PHASE 6` |
| `tests/test_ui_report.py` | 新增 12 个最小 UI 测试 |

新增：

| 文件 | 说明 |
|---|---|
| `docs/PHASE6_C2B_STEP2_IMPLEMENTATION.md` | 本报告 |

最终文件摘要：

```text
app/bootstrap.py       5,161 bytes  SHA-256 9D3E789FE7FF1C2C2368C78268C677CB129702E8AA49085870968B8E93D68CC1
ui/report_page.py     18,278 bytes  SHA-256 F558F8D21895FC29C2A95E8DF3F43643B1CC1EBF6AE03765059BC6DD3AC363F6
ui/main_window.py     13,264 bytes  SHA-256 0F673ECC499C8C85ADF880E0F4EB9F3E7FE4C0EC9190DE20B6C8E7B0DE036F69
tests/test_ui_report.py 10,321 bytes SHA-256 3A8205BAFC0484832C019A5B7056BC2C5CFC557E6021C69CA4F203D30A895E9C
```

未修改的核心文件哈希：

```text
reports/html_exporter.py  24,953 bytes  SHA-256 207AA3571B4D1900472CFCD8FB75856DCF354335AD81AB905AA35B69D3FAB480
tests/test_report_html.py 28,055 bytes  SHA-256 41CFC444D59942E9E1D377D9561873B349F938776AD469F7ECE500941BCFECA0
```

## 3. 依赖注入

`app/bootstrap.py`：

- `AppContext` 新增字段 `report_service: ReportService`（第 45 行）。
- `build_context()` 在 `ReportService` 所需 repository 已创建后执行：

```python
report_repository = ReportRepository(database, clock=clock)
report_service = ReportService(
    database,
    report_repository,
    evidence_root=config.evidence_dir,
    clock=clock,
)
```

- 最终将 `report_service=report_service` 传入 `AppContext`（第 148 行）。
- `ReportPage` 只读取 `context.report_service`、`context.config.reports_dir` 和 `AppState`；不构造 `Database`、`ReportRepository`，不执行 SQL。

## 4. ReportPage GUI 功能

顶部：页面标题、阶段标识、刷新按钮和安全提示。

项目区：

- 显示当前活动项目编号和名称；
- 显示项目类型/状态；
- 显示固定输出目录 `context.config.reports_dir`，不可由用户输入完整路径。

参数区：

- `报告类型`：`漏洞分析报告`、`证据报告`、`项目综合安全研究报告`；
- `报告标题`：最多 200 字符，可留空；
- `包含人工处理备注`：对应 `ReportRequest.include_notes`；
- 文件名不由用户输入，显示“由安全导出器自动生成”。

操作区：

- `生成预览`；
- `导出 HTML`；
- 状态标签；
- 摘要区显示报告类型、项目、生成时间、快照短 ID、任务/Finding/Evidence 数量、授权摘要、警告数量；
- 导出成功后显示实际路径与 SHA-256。

预览区：

- 使用 `QTextBrowser`；
- `setOpenLinks(False)`、`setOpenExternalLinks(False)`；
- 明确显示“安全文本预览（非浏览器排版）”；
- 预览只调用 `render_html()`，不创建文件；
- 未使用 `QWebEngine`、`QtPdf` 或远程资源。

无活动项目时：

- 清空 `_snapshot`；
- 预览/导出禁用；
- 恢复预览提示；
- 状态显示“未选择活动项目”。

## 5. 快照一致性

关键状态：

```text
_snapshot
_snapshot_project_id
_snapshot_type
```

行为：

1. `_ensure_snapshot()` 只有当项目 ID 和报告类型都匹配时才复用 `_snapshot`；否则重新调用 `ReportService.get_snapshot()`。
2. 项目变化：`AppState.project_changed` → `_on_project_changed()` → `refresh()`；旧快照立即失效，预览清空。
3. 报告类型变化：`report_type_combo.currentIndexChanged` → `_on_report_type_changed()`；旧快照立即失效，预览清空。
4. 活动项目被移除：`refresh()` 清空快照并禁用操作。
5. 标题/备注变化：不伪造数据快照，只更新当前 Request；`_request_for(snapshot)` 每次从当前控件重新读取标题和 `include_notes`。
6. 导出不读取“上一次预览所用”的旧 Request；`export()` 重新调用 `_ensure_snapshot()` 和 `_request_for()`。
7. 导出期间禁用报告类型、标题、备注和按钮，避免导出中途改变参数（本轮为同步单写者，无事件循环处理）。

## 6. 导出安全边界

### 固定输出目录

`ReportPage._write()` 只传：

```python
write_html_report(
    snapshot,
    request,
    self._reports_dir,
    overwrite=overwrite,
    filename=None,
)
```

`self._reports_dir` 来自 `context.config.reports_dir`，未提供路径输入框，不接受完整输出路径。

### 默认不覆盖

- 首次调用固定 `overwrite=False`；
- 捕获取消 `FileExistsError` 后，使用 `ui.widgets.confirm()` 要求用户确认；
- 只有确认后才以 `overwrite=True` 重试；
- 用户拒绝时状态为“已取消：未覆盖现有报告”，不写入。

### 单写者

- `self._exporting` 在进入导出时立即设为 `True`；
- 重复进入直接返回；
- 导出期间禁用预览/导出/刷新/类型/标题/备注；
- `finally` 中恢复 `_exporting = False` 并调用 `_update_controls()`；
- 未调用 `processEvents()`，未使用 `QThread`。

### 文件写入

GUI 不打开文件、不拼接路径、不调用 `Path.write_text`/`open`；正式发布仅通过 `write_html_report()`。

## 7. 测试

### 新增测试

`tests/test_ui_report.py`：**12 passed in 4.90s**。

覆盖：

1. 无活动项目禁用预览/导出，并清空快照；
2. 移除活动项目后清空旧快照并禁用按钮；
3. 项目变化使旧快照失效；
4. 报告类型变化使旧快照失效；
5. 预览只调用 `render_html()`，不调用 writer；
6. 导出固定使用 `context.config.reports_dir`，使用当前标题和 `include_notes`，首次 `overwrite=False`、`filename=None`；
7. `FileExistsError` + 确认后以 `overwrite=True` 重试；
8. 拒绝覆盖时不重试；
9. 导出异常后按钮恢复，不显示成功；
10. `_exporting` 阻止重入；
11. 真实 HTML 导出测试：文件位于固定输出目录，内容包含当前项目名；
12. `MainWindow` 使用 `ReportPage(context, state)` 并从 `AppContext` 取得 `report_service`。

### 直接相关测试集合

执行：

```text
tests/test_ui_report.py
tests/test_ui.py
tests/test_report_service.py
tests/test_report_html.py
```

结果：

```text
75 passed, 6 skipped in 12.99s
```

跳过全部为 Windows 文件/目录 symlink 创建受限：

- `tests/test_report_html.py:529`：内部/断链/外部文件 symlink，共 5 个；
- `tests/test_report_html.py:577`：报告根目录 symlink，1 个；
- 原因：`[WinError 1314] 客户端没有所需的特权`。

没有 failure，没有 error。本轮未修改既有测试，未弱化断言，未跳过任何测试。

### 测试环境

- 专用临时目录：`D:\挖漏洞\pytest_c1r_tmp`；
- `--basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_c2b_*`；
- 测试进程使用 DSH full-access；未修改项目或用户目录 ACL；
- 未运行完整最终验收（遵守停止条件）。

## 8. 未解决限制

1. **未运行完整回归/最终验收**：本轮按要求只运行新增和直接相关测试；完整 6C-2B 验收需后续单独授权。
2. **既有 C2A/R1 限制未改变**：TOCTOU、父级 reparse point、symlink 链/环、其他 reparse 类型、设备名实际写入等仍在既有报告中记录；本轮未修改导出核心。
3. **动态 symlink 验证仍受限**：Windows `WinError 1314` 导致相关测试跳过；不能把静态判断宣称为动态完全验证。
4. **预览不是浏览器**：`QTextBrowser` 只做安全文本预览，模板中的 CSS 布局可能与真实浏览器不同；页面已明确标注。
5. **同步导出**：按用户要求未使用 QThread；导出是同步调用，极大报告或慢磁盘时可能短暂阻塞 UI。
6. **无 PDF/JSON/报告历史**：本轮只做 HTML；未写 `reports` 表，未生成历史记录，未修改 Schema。
7. **无证据图片嵌入**：`include_evidence_images=False` 固定关闭；GUI 不提供图片选项。
8. **覆盖确认的粒度**：默认自动文件名；仅在同名文件已存在时询问覆盖，不提供文件名/目录选择。
9. **设置页文案仍可能滞后**：本轮不允许修改 `ui/settings_page.py`；如果该页仍描述“报告导出未开发”，属于已知 UI 文案残留，不是本轮功能缺失。
10. **单写者仅进程内**：`_exporting` 防止同一页面重入；不能防止另一个进程同时写同一目录。导出器自身的 `overwrite=False` 排他发布仍提供文件层面的最后防线。

## 9. C2A/R1 导出核心变更声明

**没有修改**：

- `reports/html_exporter.py`
- `reports/templates/`
- `services/report_service.py`
- `repositories/report_repository.py`
- 数据库/Schema/`config.yaml`

`ui/report_page.py` 只导入并调用既有 `render_html()` 和 `write_html_report()`；没有复制或重写导出逻辑。

## 10. 停止条件

本轮在完成 GUI、测试和本报告后停止：

- 未开始 JSON/PDF；
- 未开始 Phase 6D；
- 未开始完整最终验收；
- 未修改数据库或 Schema；
- 等待人工审核。
