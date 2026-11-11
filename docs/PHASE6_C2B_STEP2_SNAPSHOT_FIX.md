# Phase 6C-2B Step 2 Snapshot Freshness Fix

## 1. 问题根因

补充审查报告 `docs/PHASE6_C2B_STEP2_REVIEW.md` 确认了一个 **Medium** 问题：

- `ReportPage._ensure_snapshot()` 只根据“项目 ID + 报告类型”判断缓存是否可复用。
- 同一项目、同一报告类型下，如果数据库中的 Finding、Evidence 或 ScanTask 已变化，页面仍会继续返回旧的 `ReportSnapshot`。
- 原 `refresh()` 只在项目或报告类型与缓存不一致时才清除快照；同一项目下点击刷新不会清除快照。
- 因此，用户可能长期看到旧预览，并在导出时使用旧快照。

目标不是给每个业务页面增加全局数据版本信号，而是保证用户每次主动预览或导出时，都从 `ReportService` 获取当前快照。

## 2. 实际修改文件

| 文件 | 修改 |
|---|---|
| `ui/report_page.py` | 增加强制刷新快照路径；主动预览/导出强制重新读取；刷新时清除快照和旧预览 |
| `tests/test_ui_report.py` | 增加 4 个直接相关测试，覆盖新快照、刷新清除、导出新快照、覆盖重试一致性 |
| `docs/PHASE6_C2B_STEP2_SNAPSHOT_FIX.md` | 本报告（新文件） |

未修改：

- `reports/html_exporter.py`
- `reports/templates/`
- `services/report_service.py`
- `repositories/report_repository.py`
- `app/bootstrap.py`
- 数据库、Schema、`config.yaml`
- 其他业务页面

## 3. 快照获取的新调用逻辑

`ui/report_page.py` 中的 `_ensure_snapshot()` 现在接受内部参数：

```python
def _ensure_snapshot(self, *, force: bool = False) -> ReportSnapshot:
```

- `force=False`：保留页面内部缓存语义，供页面状态和测试使用。
- `force=True`：无论项目/类型是否相同，都调用 `ReportService.get_snapshot(project_id, selected_type)`，替换 `_snapshot`，重新生成摘要。

用户主动操作路径：

```text
generate_preview()
  -> _ensure_snapshot(force=True)
  -> 当前 project_id + 当前 ReportType
  -> ReportService.get_snapshot()
  -> 新 ReportSnapshot
  -> _request_for(snapshot) 读取当前标题/备注
  -> render_html(snapshot, request)
```

```text
export()
  -> _ensure_snapshot(force=True)   # 每次主动导出只获取一次
  -> _request_for(snapshot)          # 每次主动导出只构造一次
  -> write_html_report(..., overwrite=False)
  -> FileExistsError 且用户确认时：
       write_html_report(同一 snapshot, 同一 request, ..., overwrite=True)
```

因此：

- 预览不会仅因项目/类型未变而使用旧快照。
- 导出不会使用预览时留下的旧快照。
- 标题/备注修改后，下一次预览/导出使用当前 Request。
- 一次导出中的两次写入共享同一 Snapshot 和 Request，不会在覆盖重试时改变报告内容或目标文件名。

## 4. 刷新后的行为

`refresh()` 现在在存在活动项目时一律执行：

1. 清除 `_snapshot`、`_snapshot_project_id`、`_snapshot_type`；
2. 清除旧预览，显示“请先生成预览。”；
3. 清除旧输出路径；
4. 状态栏提示“请先生成预览，确认内容后再导出。”；
5. 保持预览/导出按钮按当前项目状态启用。

项目切换仍通过 `AppState.project_changed` 调用 `refresh()`；报告类型切换仍调用 `_on_report_type_changed()` 清除快照。两者不会再保留旧预览。

## 5. 单次覆盖重试一致性

`export()` 的 `FileExistsError` 分支现在只使用同一次导出开始时取得的两个对象：

- 同一个 `snapshot`
- 同一个 `request`

覆盖确认后不会重新调用 `ReportService.get_snapshot()`，也不会重新构造 `ReportRequest`。固定参数继续为：

- `reports_dir = context.config.reports_dir`
- `filename = None`
- 首次 `overwrite=False`
- 确认覆盖后 `overwrite=True`

因此默认文件名、快照 ID 和目标路径在同一次覆盖重试中保持一致。

## 6. 实际测试结果

测试环境：项目 venv、PySide6 offscreen/Qt 测试环境，使用 `D:\挖漏洞\pytest_c1r_tmp` 专用临时根目录和 DSH full-access 测试进程；未修改 ACL。

新增/修改文件直接测试：

```text
tests/test_ui_report.py
16 passed in 6.64s
```

直接相关 UI/Service 测试：

```text
tests/test_ui_report.py
tests/test_ui.py
tests/test_report_service.py
36 passed in 13.46s
```

本次没有运行完整全量回归；按步骤二停止条件，最终验收留给人工审核。`reports/html_exporter.py` 的安全测试未修改、未删除、未弱化。

## 7. 未解决限制

- 未增加 `AppState` 的 Finding/Evidence/Task 数据版本信号；页面只能在用户主动预览、导出或刷新时取得最新数据，后台数据库变化不会自动刷新界面。
- `_snapshot` 仍保存在页面内，用于页面状态和单次导出一致性；它不会阻止主动预览/导出获取新快照。
- C2A/R1 已记录的导出限制仍然存在：检查与发布之间的 TOCTOU、父级 reparse point、symlink 链/循环、其他 reparse 类型，以及 Windows symlink 动态验证的 `WinError 1314` UNKNOWN。
- 未运行完整回归；本轮不涉及 PDF、JSON、报告历史、Schema 或 Phase 6D。
- 预览仍是 `QTextBrowser` 安全文本预览，不是浏览器级排版。

## 8. 是否修改 exporter

**没有。**

`reports/html_exporter.py`、模板、`ReportService`、`ReportRepository`、`app/bootstrap.py` 均未修改。GUI 仍然只调用既有的 `render_html()`（预览）和 `write_html_report()`（正式写入），没有自行实现文件写入。

## 9. 是否建议重新审核并关闭 C2B Step 2

**建议重新审核并在记录上述限制的前提下关闭 C2B Step 2。**

依据：

- 审查指出的“同项目/同类型无限期复用旧 Snapshot”已修复；
- 主动预览、主动导出均强制获取新快照；
- 刷新会清除快照和旧预览；
- 覆盖重试共用同一快照/请求；
- 新增测试 `16 passed`，直接相关测试 `36 passed`。

关闭时应保留：

- 未运行完整回归；
- TOCTOU、父级 reparse point、symlink 动态 UNKNOWN；
- 无后台数据变化自动刷新信号；
- 预览不是浏览器级排版。

本轮完成即停止，不进入 C2B Step 3、JSON、PDF 或 Phase 6D。
