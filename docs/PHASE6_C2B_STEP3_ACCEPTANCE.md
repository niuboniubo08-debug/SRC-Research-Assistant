# Phase 6C-2B Step 3 Acceptance

## 1. 验收范围

本轮只验证 Phase 6C-2B 的 HTML 报告中心，覆盖以下完整链路：

```text
GUI
 ↓
ReportService
 ↓
最新 ReportSnapshot
 ↓
HTML Preview
 ↓
安全 Exporter
 ↓
HTML 文件
```

重点包括：

- `ReportService` 依赖注入；
- 无项目、项目切换、报告类型切换状态；
- Snapshot Freshness；
- `render_html()` 预览与 `write_html_report()` 正式导出；
- 固定 `reports_dir`、覆盖确认、单写者；
- 专项测试与完整回归。

本轮不验收 PDF、JSON、报告历史、Schema 或 Phase 6D。

## 2. 验收结果

| 项目 | 结果 | 证据 |
|---|---|---|
| A1 `ReportService` 由 `build_context()` 构造 | PASS | `app/bootstrap.py:128-134` |
| A2 通过 `AppContext` 注入 | PASS | `app/bootstrap.py:45`, `:148` |
| A3 `ReportPage` 不直接执行 SQL | PASS | `ui/report_page.py` 无 SQLite/Repository 调用；只使用 `context.report_service` |
| A4 `ReportPage` 不自行构造 Repository/Database | PASS | `ui/report_page.py:51-52`；仅持有 `context.report_service` |
| B1 无活动项目不能预览 | PASS | `test_no_active_project_disables_actions_and_clears_snapshot` |
| B2 无活动项目不能导出 | PASS | 同上；`export()` 还显式检查 `current_project_id` |
| B3 项目切换后旧快照失效 | PASS | `test_project_change_invalidates_snapshot`；动态 probe |
| B4 项目切换后旧预览不再作为当前项目报告 | PASS | `refresh()` 清除预览；动态 probe |
| B5 切换后重新预览获得当前项目数据 | PASS | 项目 A/B live probe：`SECOND_PROJECT_IS_B=True`、`B_HAS_MARKER=True`、`A_MARKER_NOT_IN_B=True` |
| C1 报告类型变化后旧快照失效 | PASS | `test_report_type_change_invalidates_snapshot` |
| C2 重新预览使用新报告类型 | PASS | 动态 probe：`TYPE_IS_EVIDENCE=True` |
| C3 导出不使用类型不一致旧快照 | PASS | `export()` 每次强制取快照并基于该快照构造 Request；`_request_for()` 使用当前快照类型 |
| D1 连续两次主动预览走最新快照路径 | PASS | `test_repeated_preview_fetches_a_fresh_snapshot`；服务调用 2 次、快照 ID 不同 |
| D2 主动导出获取最新快照 | PASS | `test_export_fetches_a_fresh_snapshot_after_preview` |
| D3 Finding/Evidence/Task 更新后主动预览/导出不读旧缓存 | PASS（机制已验证，Finding 实测） | 同项目下插入新 Finding 后再次预览，Finding 数量和内容变化；导出 HTML 包含新 Finding。Evidence/Task 走同一个 `get_snapshot()` 强制路径，未单独篡改实测 |
| D4 刷新清除旧快照、预览、输出路径并要求重新生成 | PASS | `test_manual_refresh_invalidates_snapshot_and_clears_preview`；`refresh()` 清除 `_snapshot`、preview、output_label |
| E1 预览只调用 `render_html()` | PASS | `ui/report_page.py:336`；`test_preview_uses_render_html_and_never_calls_writer` |
| E2 预览不产生正式 HTML 文件 | PASS | `test_preview_uses_render_html_and_never_calls_writer`；preview 无 writer 调用 |
| E3 `QTextBrowser` 不自动打开外部链接 | PASS（代码级） | `ui/report_page.py:224-225` `setOpenExternalLinks(False)`、`setOpenLinks(False)` |
| E4 明确标注“安全文本预览（非浏览器排版）” | PASS | `ui/report_page.py:219` |
| F1 固定使用 `context.config.reports_dir` | PASS | `ui/report_page.py:52`, `:380-393`；`test_export_uses_fixed_reports_dir_and_default_overwrite` |
| F2 GUI 不接受任意完整输出路径 | PASS | UI 只有报告类型/标题/备注等字段；输出路径无自由输入 |
| F3 正式导出只调用 `write_html_report()` | PASS | `ui/report_page.py:387-393`；`test_export_writes_real_html_inside_fixed_reports_dir` |
| F4 GUI 不自行 `open()` 写报告 | PASS | report page 无 `open()`/直接写文件；正式写入仅在 exporter |
| G1 默认 `overwrite=False` | PASS | `ui/report_page.py:360`；固定目录测试断言 |
| G2 `FileExistsError` 后明确确认 | PASS | `test_file_exists_confirm_then_retries_with_overwrite_true` |
| G3 覆盖重试使用同一 Snapshot/Request | PASS | `test_overwrite_retry_reuses_the_same_snapshot_and_request`；两次对象同一 |
| G4 覆盖重试使用同一 `reports_dir` | PASS | `_write()` 始终使用固定 `self._reports_dir`，两次调用相同 |
| G5 取消确认后不进行第二次写入 | PASS | `test_file_exists_decline_does_not_overwrite` |
| H1 `_exporting` 防止重复进入 | PASS | `test_exporting_guard_prevents_reentry` |
| H2 导出期间相关按钮禁用 | PASS | `_set_busy_controls()` 禁用刷新/预览/导出/类型/标题/备注 |
| H3 成功后恢复 | PASS | `finally` 恢复；成功测试 |
| H4 失败后恢复 | PASS | `test_export_exception_restores_buttons_and_does_not_show_success` |
| H5 不使用 `processEvents()` | PASS | `ui/report_page.py` 无 `processEvents` 调用 |
| H6 不使用 QThread | PASS | `ui/report_page.py` 无 QThread；同步单写者 |

### FAIL / UNKNOWN / SKIPPED

- **FAIL：无。**
- **SKIPPED：** Windows symlink 动态创建因 `WinError 1314` 被测试跳过，不能写成通过。
- **UNKNOWN：**
  - root/leaf symlink 的动态行为；
  - 父级 reparse point；
  - 检查与 `os.link()` 发布之间的 TOCTOU；
  - symlink 链/循环和其他 reparse 类型；
  - `QTextBrowser` 不是完整浏览器渲染，不能作为浏览器排版验收。

## 3. 测试结果

### 第一层：C2B 直接相关专项测试

命令：

```text
pytest tests/test_ui_report.py tests/test_report_service.py tests/test_report_html.py -q
```

结果：

```text
77 passed, 6 skipped in 9.26s
exit code = 0
```

6 个 skip 均为 Windows symlink 创建失败 `WinError 1314`，不是通过；其中 6 个来自 `tests/test_report_html.py` 的 symlink 分支。

### 第二层：完整回归

命令：

```text
pytest -q
```

结果：

```text
210 tests collected
203 passed, 7 skipped in 49.92s
exit code = 0
```

7 个 skip：

- `tests/test_evidence_service.py:184`：现有 evidence symlink 测试，`WinError 1314`；
- `tests/test_report_html.py:577`：reports dir symlink 测试；
- `tests/test_report_html.py:529`：内部文件 symlink、断链 symlink、外部文件 symlink 等 5 个参数化/分支测试。

以上 skip 均为当前 Windows 会话无法创建 symlink，不能算作通过。没有 failed、error 或 collection error。

测试使用专用临时目录 `D:\挖漏洞\pytest_c1r_tmp` 和 DSH full-access 测试进程；未修改 ACL，未修改测试代码。

## 4. Snapshot Freshness

| 场景 | 结果 | 说明 |
|---|---|---|
| 主动预览 | PASS | 每次 `generate_preview()` 使用 `force=True` 重新取 Snapshot |
| 主动导出 | PASS | 每次 `export()` 在写入前重新取 Snapshot；覆盖重试不重取 |
| 项目切换 | PASS | `refresh()` 清除旧快照/预览；项目 A→B probe 获得 B 数据 |
| 类型切换 | PASS | `_on_report_type_changed()` 清除快照；类型 probe 返回 `ReportType.EVIDENCE` |
| 刷新 | PASS | `_snapshot`、preview、output_label 清除，状态要求重新生成 |
| Finding 更新 | PASS | 插入新 Finding 后再次预览及导出，新 Finding 出现在 Snapshot、预览和 HTML |
| Evidence/Task 更新 | 机制 PASS，未单独篡改实测 | 与 Finding 共用同一个 `ReportService.get_snapshot()` 强制路径，无独立缓存键 |

## 5. 安全边界

- **GUI 不直接 SQL：** `ReportPage` 不导入 `sqlite3`、不访问 `Database`，只调用 `context.report_service`。
- **GUI 不直接写文件：** `ReportPage` 没有 `open()`、`write_text()` 或直接文件写入；正式发布只走 `write_html_report()`。
- **固定 `reports_dir`：** 页面初始化时保存 `context.config.reports_dir`，`_write()` 始终传入该目录，`filename=None`。
- **Exporter 未被绕过：** 预览只调用 `render_html()`，正式导出只调用 `write_html_report()`；没有替代写入路径。
- **覆盖确认：** 首次 `overwrite=False`；仅捕获 `FileExistsError`，用户明确确认后才 `overwrite=True`；取消则不进行第二次写入。
- **单写者：** `_exporting` 阻止重入；导出期间禁用刷新、预览、导出、类型、标题、备注；`finally` 恢复；同步执行，无 QThread/processEvents。

## 6. 已知限制

- Windows symlink 动态验证仍受 `WinError 1314` 限制，相关 root/leaf symlink 行为为 UNKNOWN。
- C2A/R1 已记录的 reparse point、TOCTOU、symlink 链/循环、其他 reparse 类型限制仍然存在。
- `QTextBrowser` 是安全文本预览，不是完整浏览器渲染，CSS/排版不能按浏览器级验收。
- 后台 Finding/Evidence/Task 数据变化不会自动刷新页面；用户必须主动预览、导出或刷新。
- 预览不嵌入证据图片；本轮不涉及 PDF、JSON、报告历史或 Schema。

## 7. 实际修改

本轮验收**没有修改生产代码、测试代码、数据库或 Schema**。

新增文件：

- `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md`（本报告）

本轮使用的临时 live probe 脚本位于 `D:\挖漏洞\pytest_c1r_tmp`，执行后已删除；没有写入项目生产代码或测试目录。

### 环境说明

- 主数据库 `storage/src_research.db` 当前 SHA-256 为 `ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8`，本轮未执行数据库写操作。
- `storage/reports` 中现有两个 HTML 文件（`project_1_project_summary_c296b0982419.html`、`project_2_project_summary_a312f270d9a9.html`，时间 22:19/22:22）在本轮开始前已存在；本轮未修改或删除。专项测试的真实导出使用临时项目目录，不写入该生产报告目录。

## 8. 最终结论

**PASS_WITH_LIMITATIONS**

专项测试 `77 passed, 6 skipped`，完整回归 `203 passed, 7 skipped`，收集 `210`，`0 failed`，`0 errors`，exit code 0。C2B GUI、Snapshot Freshness、HTML 预览、固定目录导出、覆盖确认和单写者链路均有代码与测试证据；未发现真实 FAIL。

**建议正式关闭 Phase 6C-2B**，关闭记录必须保留：

- Windows symlink `WinError 1314` 动态验证限制；
- C2A/R1 的 reparse point / TOCTOU 等未解决边界；
- `QTextBrowser` 非完整浏览器渲染；
- 后台数据变化不会自动刷新，需要用户主动预览、导出或刷新；
- 本轮没有单独对 Evidence/Task 做更新后 UI 实测，仅有共用快照获取路径的机制验证。

本轮完成即停止，不进入 JSON、PDF、补天提交辅助或 Phase 6D。
