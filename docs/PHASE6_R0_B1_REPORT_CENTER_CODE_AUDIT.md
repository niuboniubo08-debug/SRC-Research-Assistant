# Phase 6-R0-B1 报告中心与安全性只读核查

## 审计元数据

- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 审计时间：2026-11-13T12:53:30+08:00
- 审计性质：只读代码与测试结构核查；不运行测试、不启动 GUI、不执行扫描器、不写数据库。
- 当前分支：`main`
- 当前 HEAD：`bffb5ac82bbebe7fef5992f87ff90494c9776ace`
- 审计开始时 staged：0 个文件
- 审计开始时 unstaged：`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`
- 审计开始时 untracked：`docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`、`docs/PHASE6_D1B_3_JSON_DECISION.md`、`docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md`
- 与 `origin/main`：`ahead 5 / behind 0`
- 本次只新增本报告；没有 Git add、commit、push、reset、restore、clean。

本报告把“当前代码/测试中可直接证明的事实”和“历史报告记录的事实”分开。历史结论不会自动升级为当前结论；无法由当前证据证明的事项标为 `REQUIRES_RUNTIME_TEST` 或 `UNKNOWN`。

## 1. 当前报告中心架构与调用链

### 1.1 组件与数据流

当前实现由以下层组成：

```text
ReportPage (ui/report_page.py)
  -> AppContext.report_service
    -> ReportService (services/report_service.py)
      -> ReportRepository.load_snapshot (repositories/report_repository.py)
        -> Database.connection()
        -> PRAGMA query_only = ON
        -> BEGIN
        -> 项目范围显式 SQL
      -> ReportService._finalize
        -> evidence 路径/存在性/SHA-256 注解
        -> stats/warnings/data_scope/known_limitations
    -> render_html (reports/html_exporter.py)
      -> build_report_view_model
      -> fixed Jinja2 template
  -> QTextBrowser 预览
  -> write_html_report (reports/html_exporter.py)
    -> _resolve_reports_root
    -> _validate_filename
    -> _atomic_write
```

### 1.2 数据读取边界

`ReportRepository.load_snapshot()` 位于 `repositories/report_repository.py:104`：

- 使用 `Database.connection()` 的单一连接；
- 执行 `PRAGMA query_only = ON`（`:118`）；
- 执行 `BEGIN`（`:119`）；
- 通过 `_PROJECT_SQL`、`_AUTHORIZATION_SQL`、`_SCOPE_ASSET_SQL`、`_TASK_SQL`、`_FINDING_SQL`、`_EVIDENCE_SQL` 读取；
- 所有查询都带 `project_id` 范围参数；
- 没有 `SELECT *`；
- 发生异常时 `rollback()`（`:126`），`finally` 中释放连接。

结论：**CURRENTLY_CONFIRMED**。当前代码使用单一只读事务并按项目过滤读取。没有证据表明存在跨项目 SELECT 或写入语句。

### 1.3 DTO 与数据去向

`core/models/report.py` 定义了冻结的 `ReportSnapshot`、`ReportFinding`、`ReportEvidence` 等 DTO。当前 `ReportSnapshot.project` 是完整 `Project` 对象，因此其中仍包含 `local_path`/`description` 字段；这些字段不能直接进入 HTML。

HTML 侧由 `reports/html_exporter.py:249` 的 `build_report_view_model()` 转换为单独的 View Model。该 View Model 只保留报告需要的字段，正式模板只接收 View Model，不直接接收完整 DTO。

结论：**CURRENTLY_CONFIRMED**。原始 DTO 含本地路径，但 HTML 输出路径经过了 View Model allowlist；该 allowlist 是否完整由第 3 节和测试证据继续检查。

### 1.4 历史背景

`docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:13` 记录总体 `PASS_WITH_LIMITATIONS`；`docs/PHASE6_C2B_STEP3_ACCEPTANCE.md:174` 记录 C2B `PASS_WITH_LIMITATIONS`。这些是历史结论，不是本次运行结果；本次不执行测试，因此只能作为背景。

## 2. GUI 页面接线和依赖注入核查

### 2.1 依赖注入

`app/bootstrap.py:128-134` 构造 `ReportRepository` 和 `ReportService`：

```python
report_repository = ReportRepository(database, clock=clock)
report_service = ReportService(
    database,
    report_repository,
    evidence_root=config.evidence_dir,
    clock=clock,
)
```

`app/bootstrap.py:148` 将 `report_service` 放入 `AppContext`。`ui/report_page.py:51` 只从 `context.report_service` 获取服务；`:52` 使用固定的 `context.config.reports_dir`。页面没有构造 Repository/Database，也没有 SQL。

结论：**CURRENTLY_CONFIRMED**。GUI 通过 `AppContext` 注入报告服务，不自行构造数据层。

### 2.2 MainWindow 接线

- `ui/main_window.py:197`：`"reports": ReportPage(self._context, self._state)`；
- `:208`：`self.report_page = pages["reports"]`；
- `:247-248`：导航到 `reports` 时调用 `self.report_page.refresh()`。

结论：**CURRENTLY_CONFIRMED**。报告页已实际注册到 `QStackedWidget`，不再是独立占位页。

### 2.3 项目选择与页面生命周期

`ReportPage.__init__()` 在 `ui/report_page.py:47-59`：

- 保存 `context`、`state`、`report_service`；
- 保存固定 `reports_dir`；
- 初始化 `_snapshot`、`_snapshot_project_id`、`_snapshot_type`、`_exporting`；
- 连接 `state.project_changed` 到 `_on_project_changed()`；
- 初始化时调用 `refresh()`。

页面没有第二个项目选择器；顶部 `MainWindow` 的当前项目是唯一选择源。`ui/main_window.py:229-230` 还处理项目列表变化，`ReportPage` 自身处理当前项目变化。

结论：**CURRENTLY_CONFIRMED**（代码接线）。实际项目切换后的视觉行为属于 `REQUIRES_RUNTIME_TEST`；历史 C2B 测试有 `test_project_change_invalidates_snapshot`，但本次未运行。

### 2.4 测试证据

`tests/test_ui_report.py:377` 的 `test_main_window_uses_report_page_and_context_service` 验证：

- `window.report_page is window.pages_by_key["reports"]`；
- 页面类型为 `ReportPage`；
- 页面持有 `context.report_service`。

结论：**CURRENTLY_CONFIRMED**（测试代码存在且断言明确）；实际执行结果属于 `HISTORICAL_ONLY`，因为本次未运行 pytest。

## 3. HTML 生成与转义安全核查

### 3.1 Jinja2 环境

`reports/html_exporter.py:58-64` 的 `_ENV`：

- `autoescape=True`（`:60`）；
- `undefined=StrictUndefined`（`:62`）；
- 模板目录固定为应用内 `reports/templates`，不接收用户模板路径；
- 没有 `select_autoescape` 的关闭分支。

结论：**CURRENTLY_CONFIRMED**。当前 Jinja2 环境对 HTML 文本执行自动转义。

### 3.2 View Model allowlist

`build_report_view_model()` 位于 `reports/html_exporter.py:249`，构造 `ReportView`，其中：

- `ProjectView` 不包含 `local_path`/`description`；
- `TaskView` 不包含 `target`/`error`/`result`；
- `FindingView` 的 `source_path` 经过 `_safe_relative_path()`；
- `EvidenceView` 不包含原始 `file_path`/`managed_path`；只保留受控的 `source_text`、`file_name` 等；
- `_bounded_text`、`_single_line_text`、`_bounded_sequence` 对文本进行长度和字符卫生处理（`:574-599`）。

`_safe_relative_path()`（`:620-632`）拒绝：

- 空值；
- 以 `/` 或 `//` 开头的路径；
- 第一段含 `:` 的盘符/ADS 形式；
- 含 `..` 路径段的值。

结论：**CURRENTLY_CONFIRMED**（静态代码与测试断言一致）。这不等于“所有自由文本都已语义脱敏”；语义脱敏仍是设计边界。

### 3.3 模板安全

四个模板：

- `reports/templates/base.html`
- `reports/templates/vulnerability.html`
- `reports/templates/evidence.html`
- `reports/templates/project_summary.html`

当前模板：

- 没有 `|safe`；
- 没有 `Markup`；
- 没有 `<script>`；
- 没有远程 `src=`/`href=`；
- 没有 `@import`；
- 没有证据图片嵌入（`include_evidence_images` 只生成提示，不读取/嵌入图片）。

`tests/test_report_html.py:499` 的 `test_templates_have_no_safe_markup_or_remote_or_script` 对这些静态条件做了断言。`tests/test_report_html.py:318` 的 `test_evidence_images_are_not_embedded_or_read` 断言没有 `<img>`/`data:image`。

结论：**CURRENTLY_CONFIRMED**（静态模板 + 测试代码）。浏览器实际渲染结果属于 `REQUIRES_RUNTIME_TEST`。

### 3.4 XSS 转义测试

`tests/test_report_html.py:260` 的 `test_malicious_text_is_escaped_in_text_and_attributes`：

- 注入 `<script>`、`<img>`、属性和 `<b>`；
- 断言输出中只有转义形式，没有原始标签。

`tests/test_report_html.py:275` 的 `test_sensitive_fields_are_not_in_html`：

- 注入绝对源码路径、项目描述、任务 target/result/error、证据原始路径、managed path、metadata secret；
- 断言 sentinel 不出现在 HTML 中。

结论：**CURRENTLY_CONFIRMED**（测试代码明确覆盖这些输入）。本次没有运行测试，因此这是“覆盖存在”，不是“本轮通过”。

### 3.5 CSP 与纵深防御

当前模板没有 `Content-Security-Policy` meta 或响应头；`reports/html_exporter.py` 也没有 CSP 注入逻辑。模板当前没有脚本或远程资源，因此这不是直接的 XSS 注入点，但属于缺失的纵深防御。

历史记录：

- `docs/PHASE6_C2A_SECURITY_DEBT.md:550` 的 `DEBT-07` 明确记录 CSP 未修复；
- `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:565` 同样记录 SEC-03 CSP 属于 LOW、未修复。

结论：**CURRENTLY_CONFIRMED**：当前没有 CSP；影响等级 LOW/纵深防御。`CSP` 的浏览器实际行为属于 `REQUIRES_RUNTIME_TEST`，但“没有 CSP”本身是静态可确认的。

### 3.6 展示字段的长度/控制字符残余

`reports/html_exporter.py:545-556` 的 `CountView` 对统计映射的未知 key 使用 `str(key)`，没有统一走 `_bounded_text()`。Jinja2 仍会转义 HTML，所以这不是 HTML 注入；但超长 key 或控制字符可能造成布局/资源消耗问题。

历史记录：

- `docs/PHASE6_C2A_SECURITY_DEBT.md:324` 的 `DEBT-04` 记录该 LOW 残余；
- `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:192-199` 记录同类观察。

结论：**CURRENTLY_CONFIRMED**（静态代码）；实际 UI 资源消耗属于 `REQUIRES_RUNTIME_TEST`。

## 4. 输出路径和文件写入安全核查

### 4.1 固定输出目录

GUI 的 `ui/report_page.py:52` 保存 `context.config.reports_dir`。`_write()`（`:380-393`）只把这个固定值传给 `write_html_report()`；页面没有文件名输入框，也没有任意目录输入框。

`app/config.py:90-95` 从 `storage.reports` 解析目录，`app/config.py:131-142` 创建目录。当前 GUI 路径固定。

结论：**CURRENTLY_CONFIRMED**（GUI 调用链）。实际 `reports_dir` 的部署路径依赖 `config.yaml`，配置本身不在本次审计范围。

### 4.2 文件名和叶节点

`write_html_report()` 位于 `reports/html_exporter.py:327`。重要顺序：

1. 校验 `ReportRequest`；
2. `render_html()`；
3. `_resolve_reports_root()`；
4. `_validate_filename()`；
5. 构造原始 `candidate = root / target_name`（`:350`）；
6. 在 **任何叶节点 resolve 之前** 检查 `candidate.is_symlink()`/`is_junction()`（`:353-360`）；
7. 使用原始 `candidate` 作为 `target`（`:364`），而不是解析后的目标；
8. 检查 `target.relative_to(root)` 和 `target.parent == root`（`:365-370`）；
9. `overwrite=False` 且目标存在时抛出 `FileExistsError`（`:371-372`）；
10. 目录目标拒绝（`:373-374`）；
11. `_atomic_write()`（`:378`）。

`_validate_filename()`（`:661-680`）拒绝：

- 空文件名；
- `/`、`\`、`:`；
- Windows 非法字符集合（含 `?*<>|"`）；
- `.`/`..`；
- 非 `.html`；
- 超过 180 字符；
- C0/DEL 控制字符；
- Windows 保留设备名（CON/PRN/AUX/NUL/COM1-9/LPT1-9 等）。

结论：**CURRENTLY_CONFIRMED**。当前叶节点使用原始 candidate，不跟随内部 symlink；文件名不接受路径分隔符。

### 4.3 根目录 reparse 检查

`_resolve_reports_root()`（`:645-658`）：

```python
if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
    raise ValidationError("报告输出目录不能是符号链接或 junction")
root = root.resolve()
```

结论：**CURRENTLY_CONFIRMED**：`reports_dir` 自身在 resolve 前被拒绝为 symlink/junction。**但父级路径没有逐级 reparse 检查**；`Path.resolve()` 会跟随父级 symlink/junction。该限制与历史 `DEBT-01` 一致。

### 4.4 原子写入与发布

`_atomic_write()`（`:719-754`）：

- `tempfile.mkstemp(..., dir=target.parent)`：临时文件与目标同目录；
- `write`、`flush`、`os.fsync`、`close`；
- `overwrite=True`：`os.replace(temporary, target)`；
- `overwrite=False`：`_publish_exclusive(temporary, target)`，使用 `os.link`，不提供 `os.replace` 回退；
- `finally` 清理 `fd` 和 `temporary`。

`_publish_exclusive()`（`:693-716`）：

- 没有 `os.link` 时直接 fail-closed；
- `EEXIST` 或 Windows `winerror` 80/183 转为 `FileExistsError`；
- 其他 OSError 转为 `ReportExportError`。

结论：**CURRENTLY_CONFIRMED**（原语和顺序）。真实文件系统上的 `os.link`、`os.replace`、`fsync` 行为属于 `REQUIRES_RUNTIME_TEST`。

### 4.5 已确认的清理残余

`_atomic_write()` 在 `overwrite=False` 成功 `os.link` 后：

```python
try:
    temporary.unlink()
except OSError:
    pass
temporary = None
```

如果删除临时文件失败，代码静默忽略并继续返回成功。目标文件是正确的，但可能留下一个隐藏临时文件。该问题与历史 `DEBT-05` 一致。

结论：**CURRENTLY_CONFIRMED**（静态代码）；实际残留属于 `REQUIRES_RUNTIME_TEST`。影响等级 LOW/运维卫生，不是越权写入。

### 4.6 输出路径安全测试

`tests/test_report_html.py` 中的相关测试：

- `:455` `test_write_rejects_path_escape_and_non_html`：`../`、绝对路径、子目录、非 HTML；
- `:429` `test_write_rejects_existing_directory_target`：目录目标；
- `:398` `test_write_refuses_overwrite_and_preserves_old_file`：默认不覆盖、覆盖后旧文件变化；
- `:470` `test_failed_replace_preserves_old_file_and_cleans_temp`：`os.replace` 失败时旧文件保留、临时文件清理；
- `:551` `test_reports_dir_itself_junction_is_rejected`；
- `:568` `test_reports_dir_itself_symlink_is_rejected_when_available`；
- `:591` `test_external_junction_leaf_is_rejected`；
- `:611` `test_internal_file_symlink_leaf_is_rejected`；
- `:636` `test_broken_symlink_leaf_is_rejected`；
- `:659` `test_external_file_symlink_leaf_is_rejected`；
- `:683` `test_leaf_type_check_oserror_fails_closed`；
- `:710` `test_overwrite_false_race_is_rejected_by_exclusive_publish`（通过 monkeypatch 模拟竞争，不是真实双进程）；
- `:740` `test_no_overwrite_fails_closed_without_hardlink_support`；
- `:768` `test_keyboard_interrupt_cleans_temp_and_preserves_old_file`。

结论：**CURRENTLY_CONFIRMED**（测试代码覆盖）；实际运行结果属于 `HISTORICAL_ONLY` 或 `REQUIRES_RUNTIME_TEST`，本次没有执行。

### 4.7 父级 reparse 与 TOCTOU

当前代码不检查 `reports_dir` 的父级路径是否为 reparse point。`_resolve_reports_root()` 只检查 root 自身；root 的父级仍可能被 `Path.resolve()` 跟随。

检查与 `os.link`/`os.replace` 之间没有目录句柄约束；并发替换 root、父目录或 leaf 仍存在 TOCTOU 窗口。历史 `DEBT-01`/`DEBT-03` 已记录。

结论：

- 父级 reparse 缺失：**CURRENTLY_CONFIRMED**（静态代码）；
- 实际利用：**REQUIRES_RUNTIME_TEST**；
- TOCTOU 结构性存在：**CURRENTLY_CONFIRMED**（静态调用顺序）；
- 实际竞争成功：**UNKNOWN**（未运行对抗测试）。

## 5. 预览、导出和错误处理核查

### 5.1 预览不写文件

`ReportPage.generate_preview()` 位于 `ui/report_page.py:330`：

- 若 `_exporting` 为真直接返回；
- `_ensure_snapshot(force=True)`；
- `_request_for(snapshot)`；
- `render_html(snapshot, request)`；
- `self.preview.setHtml(html)`；
- 状态为“预览已生成，尚未写入文件”；
- `output_label.clear()`。

预览只调用 `render_html`，不调用 `write_html_report`。`tests/test_ui_report.py:128` 的 `test_preview_uses_render_html_and_never_calls_writer` 明确断言 writer 被禁止调用。

结论：**CURRENTLY_CONFIRMED**（代码和测试代码）。

### 5.2 QTextBrowser 预览边界

`ReportPage` 的预览控件是 `QTextBrowser`；代码设置：

- `setOpenExternalLinks(False)`；
- `setOpenLinks(False)`。

当前 HTML 不包含脚本、远程 `href` 或图片，因此预览不会主动加载远程资源。`QTextBrowser` 不是完整浏览器；CSS grid/flex 等布局可能降级，页面文案也标明“安全文本预览（非浏览器排版）”。

结论：**CURRENTLY_CONFIRMED**（静态代码与模板）；实际控件行为和复杂 HTML 表现属于 `REQUIRES_RUNTIME_TEST`。

### 5.3 导出默认不覆盖

`ReportPage.export()` 位于 `ui/report_page.py:345`：

- 一开始检查 `_exporting`；
- 设置 `_exporting=True` 并禁用按钮；
- `_ensure_snapshot(force=True)`；
- 使用当前 Request；
- 首次 `_write(..., overwrite=False)`；
- 只有捕获 `FileExistsError` 后才 `confirm(..., dangerous=True)`；
- 确认后 `_write(..., overwrite=True)`；
- 拒绝确认则显示取消，不写入；
- `finally` 中 `_exporting=False`，恢复按钮。

`tests/test_ui_report.py` 的 `:199`（确认后重试）、`:221`（拒绝覆盖）、`:241`（异常恢复）、`:267`（防重入）覆盖这些路径。`:349` 还验证覆盖重试复用同一 Snapshot/Request。

结论：**CURRENTLY_CONFIRMED**（代码和测试代码）。实际点击/确认框行为属于 `REQUIRES_RUNTIME_TEST`。

### 5.4 快照一致性

`_ensure_snapshot(force=True)` 在预览和导出时都强制重新读取；`_snapshot` 的项目/类型校验在 `:296-301`。`refresh()`（`:246-264`）清除快照、预览和输出路径。`tests/test_ui_report.py:286`、`:311`、`:327` 覆盖连续预览、手动刷新、预览后导出取新快照。

结论：**CURRENTLY_CONFIRMED**（代码和测试代码）；数据真实更新后的动态行为在历史 C2B Step3 有 Finding 实测，但本次不重跑。

### 5.5 失败后的文件状态

- `write_html_report` 在 `os.replace` 失败时保留旧文件，由 `:470` 测试覆盖；
- `KeyboardInterrupt` 由 `:768` 测试覆盖；
- `overwrite=False` 的 `os.link` 失败不落回 `os.replace`，由 `:740` 覆盖；
- 导出异常时页面恢复按钮、不显示成功，由 `:241` 覆盖。

结论：**CURRENTLY_CONFIRMED**（代码/测试代码）；强制进程终止、磁盘满、权限变化等仍无法由现有测试完全证明，属于 `REQUIRES_RUNTIME_TEST`/`UNKNOWN`。

## 6. 测试覆盖矩阵

本节只检查测试代码，不执行测试。测试函数数量按 `def test_` 计：

- `tests/test_report_service.py`：18 个；
- `tests/test_report_html.py`：28 个；
- `tests/test_ui_report.py`：16 个；
- 合计 62 个报告中心相关测试函数。

历史完整回归记录（来自 `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md:113-124`）：210 collected / 203 passed / 7 skipped / 0 failed / 0 errors / 49.92s。该结果属于 `HISTORICAL_ONLY`，本次没有重跑。

| 范围 | 已有覆盖 | 关键测试 | 覆盖判断 | 未覆盖/限制 |
|---|---|---|---|---|
| 数据读取与项目隔离 | 项目、授权、资产、任务、Finding、Evidence；空项目；事务一致性；连接释放 | `test_three_report_snapshots`、`test_project_isolation`、`test_read_transaction_consistency_under_concurrent_write`、`test_connection_is_released_after_error` | `CURRENTLY_CONFIRMED`（测试代码） | 未覆盖 evidence project root 为 junction/symlink 的情况 |
| 授权真实性 | 无授权不伪造；有效/待审/过期统计 | `test_authorization_summary`、`test_missing_authorization_is_reported_not_invented` | `CURRENTLY_CONFIRMED`（测试代码） | 未覆盖历史授权推断的所有组合 |
| Evidence 路径/哈希 | 文件证据哈希、内部/外部/缺失文件、非绝对路径 | `test_file_evidence_is_hashed_and_scoped`、`test_missing_and_outside_evidence_files_are_not_read` | `CURRENTLY_CONFIRMED`（测试代码） | 未覆盖 project_root 自身 reparse；未覆盖 junction leaf |
| HTML 转义/敏感字段 | script/img/属性、绝对路径、description、task、evidence 原始路径、metadata | `test_malicious_text_is_escaped_in_text_and_attributes`、`test_sensitive_fields_are_not_in_html` | `CURRENTLY_CONFIRMED`（测试代码） | 未证明所有未来字段/统计 key 都进入 allowlist |
| 模板静态安全 | 无 `|safe`、Markup、script、远程资源、@import | `test_templates_have_no_safe_markup_or_remote_or_script` | `CURRENTLY_CONFIRMED`（测试代码） | 没有 CSP；没有真实浏览器渲染 |
| 输出文件名/路径 | `..`、绝对路径、子目录、非 HTML、目录、Windows 非法字符、保留设备名 | `test_write_rejects_path_escape_and_non_html`、`:429`、`:863` | `CURRENTLY_CONFIRMED`（测试代码） | 未执行 Windows 设备名真实写入 |
| 根/叶 symlink/junction | root junction、root symlink（条件 skip）、外部 junction、内部/断链/外部 symlink | `:551`、`:568`、`:591`、`:611`、`:636`、`:659` | `CURRENTLY_CONFIRMED`（测试代码） | symlink 测试在 `WinError 1314` 时 skip，不能算动态通过；无真实 symlink 链/父级 reparse |
| 原子写入/覆盖 | UTF-8、默认拒绝覆盖、覆盖保存旧文件、replace 失败清理、KeyboardInterrupt 清理、无硬链接 fail-closed | `:375`、`:398`、`:470`、`:740`、`:768` | `CURRENTLY_CONFIRMED`（测试代码） | 没有真实双进程并发、真实 fsync 失败、磁盘满 |
| 竞争条件 | `os.link` 排他发布；monkeypatch 模拟竞争 | `:710` | `CURRENTLY_CONFIRMED`（模拟） | **不是**真实两个进程；`DEBT-06` 记录测试缺口 |
| GUI 无项目/失效/预览/导出 | 无项目禁用、切换失效、预览不写、固定目录、覆盖确认/拒绝、异常恢复、防重入 | `tests/test_ui_report.py:63,95,115,128,156,199,221,241,267` | `CURRENTLY_CONFIRMED`（测试代码） | 未运行；未覆盖真实外部链接点击/完整窗口长时间交互 |
| GUI 快照新鲜度 | 连续预览、刷新清除、预览后导出新快照、覆盖重试同对象 | `tests/test_ui_report.py:286,311,327,349` | `CURRENTLY_CONFIRMED`（测试代码） | 未重跑；Evidence/Task 更新没有独立动态测试 |
| MainWindow 接线 | 页面注册、context service 注入 | `tests/test_ui_report.py:377` | `CURRENTLY_CONFIRMED`（测试代码） | 未运行 GUI |

测试结构结论：**CURRENTLY_CONFIRMED**：关键安全边界有明确测试代码；**HISTORICAL_ONLY**：上一轮完整回归结果；**REQUIRES_RUNTIME_TEST**：所有动态文件系统、真实浏览器、真实 GUI 和真实并发行为；**UNKNOWN**：本次未运行造成的当前通过/失败状态。

## 7. 当前已确认问题

### 7.1 证据项目根目录 reparse 未拒绝（Medium）

`services/report_service.py:129`：

```python
project_root = (self._root / f"project_{snapshot.project.project_id}").resolve()
```

`_annotate_evidence()` 只对证据文件叶节点调用 `path.is_symlink()`（`:148`），没有检查：

- `project_root` 自身是否为 symlink/junction；
- `project_root` 的父级是否为 reparse point；
- 叶节点 `is_junction`。

如果 `storage/evidence/project_<id>` 被替换为指向外部目录的 junction，`project_root.resolve()` 会跟随到外部；随后外部文件可能通过 `relative_to()` 并进入 `sha256_file()`。当前报告 HTML 不嵌入文件内容，但会暴露文件存在性和哈希结果。该风险与本地文件系统写权限相关。

分类：

- 静态逻辑缺口：**CURRENTLY_CONFIRMED**；
- 实际利用/实际读取：**REQUIRES_RUNTIME_TEST**；
- 现有测试覆盖：无专门测试，**UNKNOWN**。

### 7.2 父级 reparse point 未检查（Medium）

`reports/html_exporter.py:645-658` 只检查 `reports_dir` 自身。父级 symlink/junction 会在 `root.resolve()` 时被跟随；当前没有逐级检查。

分类：**CURRENTLY_CONFIRMED**（代码路径）；实际输出越界：**REQUIRES_RUNTIME_TEST**。历史 `DEBT-01` 记录一致。

### 7.3 TOCTOU 窗口（Medium，结构性）

检查与发布不是同一目录句柄操作：

- `candidate.is_symlink()` / `is_junction()`；
- `target.exists()`；
- `_atomic_write()` 的 `mkstemp`；
- `os.link`/`os.replace`。

在本地攻击者可以并发替换 root、父目录或 leaf 的情况下，检查结果可能过期。`overwrite=False` 的 `os.link` 解决了“目标已存在”的原子排他，但没有解决 root/父路径替换；`overwrite=True` 的 `os.replace` 仍允许覆盖竞争目标，这是用户明确确认覆盖后的预期语义。

分类：**CURRENTLY_CONFIRMED**（调用顺序）；实际竞争成功：**UNKNOWN**。历史 `DEBT-03` 记录一致。

### 7.4 CSP 缺失（Low，纵深防御）

模板没有 CSP；当前也没有脚本/远程资源，因此不是已确认的 XSS 注入路径。分类：**CURRENTLY_CONFIRMED**（静态）；历史 `DEBT-07` 记录一致。

### 7.5 CountView 未统一限长（Low）

`reports/html_exporter.py:545-556` 对统计映射未知 key 直接 `str(key)`；HTML 转义存在，但长度/控制字符卫生不统一。分类：**CURRENTLY_CONFIRMED**（静态）；实际资源影响：**REQUIRES_RUNTIME_TEST**。历史 `DEBT-04` 记录一致。

### 7.6 临时文件清理失败被静默忽略（Low）

`reports/html_exporter.py:739-742` 在 `temporary.unlink()` 失败时 `pass`；目标文件正确，但可能留下隐藏临时文件。分类：**CURRENTLY_CONFIRMED**；历史 `DEBT-05` 记录一致。

### 7.7 公共写入 API 接受任意目录（Low，调用方责任）

`write_html_report(snapshot, request, reports_dir, ...)` 本身接受任意绝对目录。GUI 固定使用 `context.config.reports_dir`，但其他调用方若把用户输入传入该参数，会绕过 GUI 的固定目录约束。当前产品代码中没有发现这种调用。

分类：**CURRENTLY_CONFIRMED**（API 签名）；GUI 越界：无证据，`UNKNOWN`。建议将“固定目录”约束封装在 UI/service 边界，而不是仅依赖调用约定。

### 7.8 `get_snapshot_for_request` 接受 PDF/JSON 格式（Low，API 语义）

`services/report_service.py:104-108` 只校验 `ReportRequest` 和格式枚举，然后按项目/类型取快照；它不拒绝 PDF/JSON，也没有渲染。当前 GUI 固定 `ReportFormat.HTML`；PDF 已取消、JSON 未批准。分类：**CURRENTLY_CONFIRMED**（代码）；实际误用风险取决于未来调用方，**UNKNOWN**。

## 8. 需要运行验证的问题

以下事项不能仅凭代码存在判定为通过：

1. **真实 root symlink**：`test_reports_dir_itself_symlink_is_rejected_when_available` 在 `WinError 1314` 时 skip；需要用具备 symlink 权限的隔离环境确认拒绝。
2. **真实 leaf symlink/断链 symlink**：`test_internal_file_symlink_leaf_is_rejected`、`test_broken_symlink_leaf_is_rejected`、`test_external_file_symlink_leaf_is_rejected` 依赖 `os.symlink`；当前历史环境 skip。
3. **父级 reparse point**：当前没有测试；需要验证父目录 junction/symlink 时实际输出位置。
4. **TOCTOU**：需要两个并发进程/线程在实际文件系统上竞争 root/leaf；现有 `test_overwrite_false_race...` 是 monkeypatch 模拟，不是真实并发。
5. **真实 QTextBrowser 渲染**：需要启动 GUI，验证外部链接、样式降级、超长统计 key 的布局表现。
6. **真实浏览器打开导出 HTML**：验证 CSP 不存在时的实际行为、样式、无脚本/远程资源，以及 HTML 结构。
7. **真实 SQLite 数据与项目切换**：本次未运行 GUI/数据库；需要用实际项目验证快照新鲜度和跨项目隔离。
8. **Evidence 项目根目录 junction**：验证 `project_<id>` 为 junction 时 `_annotate_evidence()` 是否读取外部文件；这是当前静态缺口的动态确认。
9. **磁盘满、权限拒绝、fsync 失败**：验证失败后的临时文件和旧文件状态。
10. **Windows 设备名实际写入**：代码会拒绝；不要实际写设备，需在隔离环境确认行为。
11. **当前完整 pytest**：本次未运行；历史 203 passed/7 skipped 不能替代本轮。
12. **Reports 目录可写性与实际产物**：本次未执行导出；历史 C2B 产物存在，但不能证明当前环境仍可写。

## 9. 尚无法确认的问题

- **当前会话下测试是否全部通过**：`UNKNOWN`。本次按任务约束未运行 pytest；历史结果只是 `HISTORICAL_ONLY`。
- **真实 Windows ACL 环境下的 symlink/junction 行为**：`UNKNOWN`。历史跳过是 `WinError 1314`。
- **父级 reparse point 的实际攻击可行性**：`UNKNOWN`。代码未检查，但没有动态证明可越界；取决于本地文件系统权限。
- **TOCTOU 的实际竞争窗口**：`UNKNOWN`。结构窗口存在，但未做真实并发实验。
- **CSP 对当前报告的实际影响**：CSP 缺失是静态确认；当前无脚本/远程资源，实际浏览器影响未测试。
- **QTextBrowser 对复杂 HTML/CSS 的显示保真度**：`UNKNOWN`。它被设计为安全文本预览，不是浏览器。
- **Evidence 根目录 reparse 的实际读取范围**：静态代码显示可能跟随，但未动态验证。
- **完整产品在真实用户工作流中的可用性**：`UNKNOWN`。本次不启动 GUI、不执行扫描器、不验证实际项目数据库。

## 10. 总体交付判断及证据依据

### 10.1 结论

```text
OVERALL_DELIVERY_JUDGMENT = READY_WITH_LIMITATIONS
HTML_REPORT_FUNCTIONAL_COMPLETENESS = IMPLEMENTED
CURRENT_XSS_INJECTION = NOT_CONFIRMED
OUTPUT_PATH_BOUNDARY = PARTIAL_WITH_DOCUMENTED_UNKNOWNS
EVIDENCE_PROJECT_ROOT_REPARSE = CURRENTLY_CONFIRMED_GAP
CSP = ABSENT
CURRENT_TESTS_RUN = NO
CURRENT_FULL_SUITE_RESULT = UNKNOWN
```

### 10.2 判定依据

支持 `READY_WITH_LIMITATIONS` 而非 `NOT_READY` 的证据：

- 数据层使用单一只读连接、`PRAGMA query_only=ON`、`BEGIN`、项目范围显式 SQL，无 SELECT *；
- 报表输出使用 View Model allowlist；Jinja2 `autoescape=True` + `StrictUndefined`；模板无 `|safe`/脚本/远程资源；
- 输出目录由 GUI 固定；文件名不接受路径分隔符；默认 `overwrite=False`；覆盖需要明确确认；
- 叶节点在 resolve 前做 symlink/junction 检查；`overwrite=False` 使用 `os.link` 原子排他，失败 fail-closed；
- 预览只调用 `render_html`；正式写入只调用 `write_html_report`；
- `_exporting` 单写者保护、`finally` 恢复；
- 62 个报告相关测试函数覆盖了主要正常路径和安全边界；历史完整回归为 203 passed / 7 skipped。

不能判定为无条件 `READY` 的证据：

- 本次没有运行测试/GUI/真实文件系统实验，当前通过状态 `UNKNOWN`；
- root symlink/leaf symlink 动态测试在历史环境被 skip；
- 父级 reparse point 代码未检查；
- TOCTOU 结构性存在，未有真实并发验证；
- Evidence 项目根目录 reparse 是当前静态缺口；
- 没有 CSP；`CountView` 未限长；临时文件清理失败被静默忽略；
- `write_html_report` 的公共 API 接受任意目录，固定目录只是 GUI 层约束；
- `get_snapshot_for_request` 接受 PDF/JSON 格式但不渲染。

因此，当前实现适合**本地单用户、固定配置、默认不覆盖、不把报告目录暴露给不可信路径来源**的使用方式；在多人环境、用户自定义输出目录、不可信本地文件系统或把“安全”作为无保留承诺前，需要先处理第 7、8 节列出的项。

### 10.3 本次实际文件变化

- 新增：`docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md`（本报告）
- 修改生产代码：无
- 修改测试代码：无
- 修改数据库/Schema：无
- 修改模板/GUI：无
- 修改 README/已有文档：无
- Git 操作：无（没有 add/commit/push/reset/restore/clean）

### 10.4 结束状态

```text
PHASE6_R0_B1_STATUS = COMPLETED
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
EXISTING_DOCS_MODIFIED = NO
GIT_MUTATION = NO
TESTS_RUN = NO
GUI_STARTED = NO
SCANNER_EXECUTED = NO
```
