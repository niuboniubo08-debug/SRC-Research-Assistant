# Phase 6C-2A HTML 导出安全审查（第 1 轮）

- 审查日期：2026-11-07
- 审查方式：只读静态审查；检查实际代码、模板、调用关系及已有测试证据
- 审查范围：`reports/html_exporter.py`、`reports/templates/base.html`、`reports/templates/vulnerability.html`、`reports/templates/evidence.html`、`reports/templates/project_summary.html`
- 审查边界：不修改源码、测试、数据库、配置；不执行迁移；不生成正式业务报告；不扩大 Phase 6C-2A 范围
- 结论：**PASS_WITH_LIMITATIONS**

## 1. 结论摘要

本次审查未发现 Critical / High 级问题，未发现可确认的 HTML/JavaScript 注入、远程资源加载、路径穿越写入或明确敏感字段泄漏。

已确认：

- View Model 使用显式 allowlist，未把 `Project.local_path`、`Project.description`、任务 target/error、Finding 原始绝对路径、Evidence 原始路径、权限元数据直接传给模板。
- Jinja2 使用 `autoescape=True` 和 `StrictUndefined`；模板中没有 `|safe`、`Markup`、`{% autoescape false %}`、脚本或远程资源。
- 文件名不允许 `/`、`\`、`:`、控制字符和 `..`；目标路径经过 `resolve()`、`relative_to()` 和父目录一致性检查。
- 原子写入顺序为：同目录 `mkstemp` → `write` → `flush` → `fsync` → 关闭 → `os.replace`；失败路径会尝试清理临时文件，旧文件在替换失败时保留。
- 默认 `overwrite=False`，顺序执行时会拒绝覆盖已有报告。

限制：

- `overwrite=False` 的存在性检查与 `os.replace()` 之间存在 TOCTOU 窗口；并发写入者仍可能覆盖已有报告。
- Windows junction / symlink 的实际 containment 行为未在本轮动态验证，标记为 **UNKNOWN**；静态代码看起来会拒绝指向 root 外部的叶节点链接，但 root 自身的 reparse point 未拒绝。
- Windows 保留设备名（如 `NUL.html`、`CON.html`）及部分非法文件名字符未被 `_validate_filename()` 拦截；运行时行为标记为 **UNKNOWN**。
- 模板没有 CSP；当前无脚本/远程资源，因此属于 defense-in-depth 缺口，不是已确认的注入绕过。
- Finding / Evidence 的自由文本字段会原样转义后输出，未做语义脱敏；这是产品数据边界问题，不能声称“内容不含敏感信息”。

## 2. 审查对象与调用边界

### 2.1 渲染边界

`reports/html_exporter.py:291-305` 的 `render_html()` 只接收 `ReportSnapshot` / `ReportRequest`，构建 `ReportView` 后调用固定模板：

```python
view = build_report_view_model(snapshot, request)
template = _ENV.get_template(_TEMPLATE_NAMES[snapshot.report_type])
rendered = template.render(view=view)
```

模板上下文中只传入 `view`，没有传入 `snapshot`、`Project`、`ReportEvidence` 或 repository/database 对象。`_TEMPLATE_NAMES` 是固定映射，模板名不受请求控制（`reports/html_exporter.py:50-55`）。

### 2.2 写入边界

`write_html_report()` 先调用 `render_html()`，再解析并校验输出目录和文件名，最后调用 `_atomic_write()`（`reports/html_exporter.py:308-353`）。exporter 不导入数据库、repository 或 scanner；不读取 evidence 文件。以上均与文件头声明一致（`reports/html_exporter.py:1-14`）。

## 3. 重点检查结果

### 3.1 View Model allowlist

**结论：PASS。**

`ReportView` 只暴露以下白名单字段（`reports/html_exporter.py:196-217`）：

- 标题、报告类型标签、项目视图、授权摘要、任务视图、Finding 视图、Evidence 视图、统计视图；
- 生成时间、快照 ID、Schema 版本、data scope、warnings、known limitations、备注/图片开关。

映射函数逐个构造视图对象，而不是把 domain object 直接传入模板：

- `ProjectView` 只取 `project_id`、`project_name`、类型/状态标签（`reports/html_exporter.py:382-390`）。**没有** `local_path`、`description`。
- `TaskView` 只取任务 ID、类型/状态、时间、progress、scanner 文本（`reports/html_exporter.py:414-425`）。**没有** target、error_message、result、metadata。
- `FindingView` 取标题、类别、描述、风险/置信度、scanner、rule、`source_path`、行号、建议、状态、备注、依赖字段、evidence_count（`reports/html_exporter.py:428-459`）。
  - 原始 `finding.file_path` 仅经 `_safe_relative_path()` 后进入 `source_path`（`reports/html_exporter.py:444`），不是直接透传。
  - `finding.metadata`、`task_id` 没有进入 View。
- `EvidenceView` 取证据 ID、关联 Finding、类型、标题、描述、文件名、哈希、`source_text`、时间、文件状态（`reports/html_exporter.py:462-477`）。
  - `evidence.file_path`、`managed_path` 没有进入 View；
  - `file_name` 经 `_safe_file_name()`，`source` 经 `_safe_relative_path()`。

已有测试 `tests/test_report_html.py:272-297` 对 `local_path`、`PROJECT_DESCRIPTION_SENTINEL`、task target/result/error、evidence 原始路径、metadata sentinel 做了负向断言；测试通过记录为本阶段上一轮结果，本轮未重跑。

**残留风险（非 allowlist 绕过）：**

- `FindingView.description`、`recommendation`、`manual_notes`，以及 `EvidenceView.description`、`source_text`、`file_status_note` 是业务自由文本（`reports/html_exporter.py:438-474`），可能包含用户/工具写入的路径、令牌或其他敏感内容。代码只做 HTML 转义，不做语义脱敏。详见 SEC-06。
- `ReportView.warnings`、`data_scope`、`known_limitations` 由 `ReportService` 提供，当前 service 输出未包含原始文件路径，但 exporter 对字符串内容没有 allowlist 级别的字段结构化保证。这是依赖 service 的边界，而不是当前视图映射直接泄漏 domain 字段。

### 3.2 Jinja2 autoescape 与转义旁路

**结论：PASS。**

`reports/html_exporter.py:57-65`：

```python
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR), encoding="utf-8"),
    autoescape=True,
    auto_reload=False,
    undefined=StrictUndefined,
    ...
)
```

- `autoescape=True` 对 HTML 文本和属性上下文启用默认转义。
- `StrictUndefined` 使缺失字段显式失败，避免静默输出空值。
- `render_html()` 捕获 `KeyError` / `TemplateError` 并转为 `ReportExportError`（`reports/html_exporter.py:298-304`），不会继续落盘。
- 在生产代码和模板中未发现 `|safe`、`Markup`、`{% autoescape false %}`、`html.escape` 之外的绕过。对 `reports/` 的 grep 结果只命中了 `autoescape` 说明、`description` 字段名和 sanitizer 函数名，没有 `Markup` / `|safe` 使用。
- 模板中的动态值均位于文本节点；没有把 Finding 字段拼进 `href`、`src`、`style`、事件属性或 JavaScript 字符串。
- `tests/test_report_html.py:257-269` 覆盖了 `<script>`、`<img ... onerror>`、引号属性注入；`tests/test_report_html.py:473-483` 检查模板无 `|safe`、无 `<script`、无远程 `src`/`href`、无 `@import`。这些是上一轮已通过的测试证据，本轮未重跑。

### 3.3 模板中的 JavaScript、远程资源与危险 HTML

**结论：PASS。**

逐个检查：

- `reports/templates/base.html:1-237`：只有静态 `<style>`、表格、列表和文本节点；`<title>` 与 `<h1>` 使用 `{{ view.title }}`（第 6、122 行），由 autoescape 处理；没有 `<script>`、`<iframe>`、`<object>`、`<embed>`、`<form>`、`<base>`、事件属性、远程字体或 `url(...)`。
- `vulnerability.html:1-54`：Finding 字段全部作为文本输出；`source_path` + 行号以文本拼接；没有 URL/属性。
- `evidence.html:1-56`：只展示元数据；没有 `<img>`、没有 data URI、没有原始绝对路径；文本明确说明不读取/嵌入证据图片（第 5 行）。
- `project_summary.html:1-76`：表格中的标题、类别、路径、文件名均为文本节点；没有远程资源。

grep 对模板目录的 `<script`、`<img`、`<iframe`、`javascript:`、`http://`、`https://`、`onerror=`、`onclick=`、`onload=`、`href=`、`src=`、`@import`、`url(`、`style=` 未发现命中。`base.html` 的 `@media print` 是静态 CSS，不是 `@import`。

**限制：** `base.html:3-6` 的 `<head>` 没有 CSP meta；见 SEC-03。这不是当前可执行的注入路径，因为模板没有脚本或远程内容。

### 3.4 路径 containment

**结论：路径穿越（filename 输入）PASS；Windows junction/symlink 与 root reparse point 为 UNKNOWN。**

`write_html_report()` 的路径链（`reports/html_exporter.py:325-337`）：

```python
root = _resolve_reports_root(reports_dir)
target_name = _validate_filename(filename or _default_filename(snapshot))
target = (root / target_name).resolve()
target.relative_to(root)          # ValueError -> 越界
if target.parent != root:         # 必须直接位于 root
    raise ValidationError(...)
```

`_validate_filename()`（`reports/html_exporter.py:598-612`）拒绝：

- `/`、`\`、`:`；
- 空名、`.`、`..`；
- 非 `.html` 后缀；
- 超过 180 字符；
- `\x00-\x1f` 控制字符。

因此以下输入均不能穿过目标目录：

- `../escape.html`；
- `C:\outside.html`；
- `subdir/inside.html`；
- UNC 形式（反斜杠被拒绝）；
- Windows 设备路径（反斜杠/冒号被拒绝）；
- 正斜杠绝对路径（`/` 被拒绝）。

`_safe_relative_path()`（`reports/html_exporter.py:559-571`）对 Finding/Evidence 的展示路径还会拒绝：

- 以 `/` 或 `//` 开头；
- 第一段含 `:`（盘符、URI scheme 等）；
- 任一段为 `..`。

**已验证的部分：**

- `tests/test_report_html.py:425-441` 覆盖 `../escape.html`、`C:\outside.html`、`subdir/inside.html`、`report.txt`，均抛 `ValidationError`，且确认 `escape.html` 未生成。
- `tests/test_report_html.py:272-297` 确认 `C:\secret\absolute-source.py` 不出现在 HTML。
- 静态代码的 `resolve() → relative_to() → parent` 三段检查，对指向 root 外部的**已存在叶节点 symlink/junction**会把 `target` 解析到 root 外，随后被 `relative_to()` 拒绝。

**UNKNOWN 的部分：**

- 没有在本轮创建 Windows symlink/junction 进行动态验证；因此“实际 `Path.resolve()` 对 junction 的解析 + `relative_to()` 拒绝”仍标记 **UNKNOWN**，见 SEC-02。
- `_resolve_reports_root()` 会先 `root.resolve()`（`reports/html_exporter.py:584-595`），但没有拒绝 `reports_dir` 本身是 symlink/junction。若攻击者能替换整个 `reports_dir`，输出会落到该 reparse point 的真实目标；这不是 filename 穿越，但属于 root 信任边界问题，见 SEC-02。
- 并发替换 root/父目录的 TOCTOU 未验证；本地攻击者若已能修改 reports_dir，通常已具备删除/替换报告的能力。

### 3.5 原子写入顺序与失败清理

**结论：顺序 PASS；失败清理 PASS（普通 `Exception`）；`BaseException` 与目录持久性为限制。**

`_atomic_write()`（`reports/html_exporter.py:625-655`）的实际顺序：

1. `tempfile.mkstemp(dir=target.parent)` 创建同目录临时文件（629-633）；
2. `os.fdopen(fd, "wb")`，`write(payload)`（635-637）；
3. `handle.flush()`（638）；
4. `os.fsync(handle.fileno())`（639）；
5. 退出 `with`，文件关闭（635-639）；
6. 可选的存在性复查（640-641）；
7. `os.replace(temporary, target)`（642）；
8. `temporary = None`（643）。

同目录临时文件保证 `os.replace()` 在同一卷上完成原子替换；`fsync` 在关闭前执行；旧文件在 `os.replace()` 失败时不会被截断。`tests/test_report_html.py:444-470` 通过 monkeypatch `os.replace` 失败，验证旧文件字节不变且 `.tmp` 被清理；`tests/test_report_html.py:372-392` 验证 UTF-8 输出、artifact SHA-256 和无残留 `.tmp`。

**失败清理：**

- `except Exception` 分支关闭未交付的 fd，并 `unlink(missing_ok=True)` 临时文件（644-654）。
- 普通写入失败、`fsync` 失败、存在性复查失败、`os.replace` 失败均会走该分支。
- 如果旧文件存在，替换失败时旧文件保留；临时文件被清理。
- `BaseException`（如 `KeyboardInterrupt`、`SystemExit`）不会走 `except Exception`，可能留下临时文件；见 SEC-05。旧文件不会被替换，因此不是数据损坏，但属于清理缺口。
- 没有对父目录执行 `fsync`；崩溃后的目录项持久性不是本实现的强保证，但这属于 durability，不是注入/越权问题。

### 3.6 默认禁止覆盖

**结论：顺序执行 PASS；并发执行存在 LOW 级 TOCTOU。**

- `write_html_report()` 默认 `overwrite: bool = False`（`reports/html_exporter.py:313`）。
- 第一次检查：`if target.exists() and not overwrite: raise FileExistsError`（334-335）。
- 第二次检查：`_atomic_write()` 在写入临时文件后再次 `if not overwrite and target.exists(): raise FileExistsError`（640-641）。
- `tests/test_report_html.py:395-422` 验证顺序调用时第二次写入被拒绝，旧文件字节不变；随后显式 `overwrite=True` 才替换。

但两次 `exists()` 与 `os.replace()` 之间不是原子“仅当不存在才创建”。如果另一个进程/线程在第二次检查之后、`os.replace()` 之前创建目标文件，`os.replace()` 会直接替换它。详见 SEC-01。

另外，`Path.exists()` 会跟随符号链接：断链 symlink 返回 `False`，随后 `os.replace()` 会替换该链接本身。这不会写到链接目标（因此不构成越界），但会绕过“存在即拒绝”的语义。该行为本轮未动态验证，按 **UNKNOWN** 处理，归入 SEC-01/SEC-02 的边界说明。

## 4. 问题清单

| ID | 风险 | 位置 | 状态 | 摘要 |
|---|---|---|---|---|
| SEC-01 | LOW | `reports/html_exporter.py:334-341`, `:640-642` | 静态确认；并发竞态未动态复现 | `overwrite=False` 的存在性检查与 `os.replace()` 非原子，存在 TOCTOU 覆盖窗口 |
| SEC-02 | UNKNOWN | `reports/html_exporter.py:325-337`, `:584-595` | 叶节点静态逻辑 PASS；实际 junction/symlink 与 root reparse **UNKNOWN** | 未动态验证 Windows junction/symlink；`reports_dir` 自身 reparse point 未被拒绝 |
| SEC-03 | LOW | `reports/templates/base.html:3-6` | 已确认缺失 | 无 CSP；当前无脚本/远程资源，属 defense-in-depth 缺口 |
| SEC-04 | LOW | `reports/html_exporter.py:248-257`, `:280-282`, `:377-381` | 静态确认 | `title`/warnings/data scope/known limitations 未统一限长或清除控制字符；autoescape 仍有效 |
| SEC-05 | LOW | `reports/html_exporter.py:644` | 静态确认 | `except Exception` 不覆盖 `KeyboardInterrupt`/`SystemExit`，异常中断可能残留临时文件 |
| SEC-06 | LOW / 设计边界 | `reports/html_exporter.py:438-474` | 自由文本内容 **UNKNOWN** | 描述、建议、人工备注、证据说明可含敏感文本；已转义但未语义脱敏 |
| SEC-07 | LOW / 运行时 UNKNOWN | `reports/html_exporter.py:598-612` | 静态确认未拦截；Windows 设备名实际行为未验证 | Windows 保留设备名及 `?*<>|"` 等非法字符未拒绝；不构成目录穿越，但可能导致写入失败或设备名解析 |

风险统计：Critical 0；High 0；Medium 0；Low 6；UNKNOWN 验证项 2（SEC-02、SEC-06 的内容边界；SEC-07 的运行时行为）。

## 5. 问题详情与最小修复建议

### SEC-01 — 默认不覆盖不是并发原子的（LOW）

**文件/行号：** `reports/html_exporter.py:334-341`，`reports/html_exporter.py:640-642`

**实际代码证据：**

```python
# write_html_report
if target.exists() and not overwrite:
    raise FileExistsError(f"目标报告已存在，未覆盖: {target}")

# _atomic_write
if not overwrite and target.exists():
    raise FileExistsError(f"目标报告已存在，未覆盖: {target}")
os.replace(temporary, target)
```

**风险：** 两个 `exists()` 检查都不是“创建独占目标”的原子操作。并发写者可以在第二次检查后创建目标，`os.replace()` 会覆盖它。影响是 reports_dir 内已有报告被替换，可能造成报告完整性/证据留存问题；不会把内容写到 root 之外。

**能否复现/验证：** 逻辑可静态确认；本轮没有启动两个并发写入者做动态复现。单线程已有测试通过。

**最小修复建议（未实施）：**

- 对 `overwrite=False` 使用独占创建原语：例如先 `os.link(temp, target)`（目标已存在则 `FileExistsError`），成功后 `unlink(temp)`；或使用平台支持的 `O_CREAT|O_EXCL` 目标创建。
- 仅 `overwrite=True` 使用 `os.replace()`。
- 增加两个并发写入者测试：一个写成功，另一个必须收到 `FileExistsError`，旧文件保持不变。
- 对断链 symlink 明确使用 `lexists`/`is_symlink` 策略，避免“存在即拒绝”被断链绕过。

### SEC-02 — Windows junction/symlink 与 root reparse point 的 containment 未动态确认（UNKNOWN）

**文件/行号：** `reports/html_exporter.py:325-337`，`reports/html_exporter.py:584-595`

**实际代码证据：**

```python
target = (root / target_name).resolve()
try:
    target.relative_to(root)
except ValueError as exc:
    raise ValidationError("报告目标路径越界") from exc
if target.parent != root:
    raise ValidationError("报告目标必须直接位于 reports_dir")
```

```python
root = Path(reports_dir).expanduser()
if not root.is_absolute():
    raise ValidationError("报告输出目录必须是绝对路径")
root = root.resolve()
```

**风险：** 叶节点若是已存在的 symlink/junction，`resolve()` 应把目标解析到真实位置，随后 `relative_to()` 拒绝 root 外部路径；静态逻辑成立。但本轮没有实际创建 junction/symlink 验证，尤其没有验证 Windows `Path.resolve()` 对 junction 的行为，因此不能把该攻击面写成 PASS。另一个缺口是 `reports_dir` 自身若是 symlink/junction，代码会解析并写入其真实目标，而不是拒绝 reparse point；是否可利用取决于攻击者能否替换该目录。

**能否复现/验证：** 叶节点逻辑可静态推理；**实际 junction/symlink 行为 UNKNOWN**。未执行创建链接的测试，未修改 ACL。

**最小修复建议（未实施）：**

- 增加使用 `cmd /c mklink /J`（junction）和 `os.symlink`（可用时）的测试，覆盖：root 外叶节点 junction、root 外叶节点 symlink、root 内 symlink、断链 symlink、`reports_dir` 自身 junction。
- 若要求“配置目录本身必须是真实目录”，在 `_resolve_reports_root()` 中拒绝 `Path(reports_dir).is_symlink()` 或 reparse point；若允许，需在文档中明确 root 解析后的信任边界。
- 对高保证场景可使用目录句柄/`os.open` + `dir_fd`（Windows 支持有限）减少 TOCTOU；本轮不建议扩大实现。

### SEC-03 — 缺少 CSP（LOW，defense-in-depth）

**文件/行号：** `reports/templates/base.html:3-6`（`<head>` 只有 charset/viewport/title）

**实际代码证据：** 模板 `<head>` 中无 `Content-Security-Policy` meta；模板也没有脚本、远程资源或表单。动态内容全部经过 autoescape。

**风险：** 当前没有可执行的注入路径，因此不是已确认绕过。若未来模板增加脚本、远程资源或内联事件，缺少 CSP 会降低纵深防御。

**能否复现/验证：** 已通过读取 `base.html:3-6` 和模板 grep 确认缺失；没有动态注入复现。

**最小修复建议（未实施）：**

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'">
```

若未来通过 HTTP 提供报告，优先使用响应头 CSP；`frame-ancestors` 不能通过 meta 完整表达。

### SEC-04 — 标题/警告/范围文本未统一限长或清除控制字符（LOW）

**文件/行号：** `reports/html_exporter.py:248-257`，`:280-282`，`:377-381`

**实际代码证据：**

```python
warnings = list(str(item) for item in snapshot.warnings)
...
data_scope=tuple(str(item) for item in snapshot.data_scope),
warnings=tuple(warnings),
known_limitations=tuple(str(item) for item in snapshot.known_limitations),
```

```python
def _request_title(snapshot, request):
    candidate = request.title.strip() if request is not None else ""
    if candidate:
        return candidate[:_MAX_TITLE]
    return f"{snapshot.report_type.label} · {snapshot.project.project_name}"
```

- `_request_title()` 只做 `strip()` 和截断，不像 `_bounded_text()` 那样移除 `\x00`；fallback 直接使用 `project_name`，没有长度上限。
- `warnings` / `data_scope` / `known_limitations` 只做 `str()`，没有统一长度上限或控制字符清理。
- 这些值最终进入文本节点，autoescape 会转义 `<`、`>`、`&`、引号，因此**未发现 XSS**；风险是异常/超长/控制字符导致 HTML 质量或资源消耗问题。

**能否复现/验证：** 静态确认；未构造 NUL/超长标题做动态测试。

**最小修复建议（未实施）：**

- `_request_title()` 对用户标题和 fallback 都调用 `_bounded_text(..., _MAX_TITLE)`。
- `warnings`、`data_scope`、`known_limitations` 逐项 `_bounded_text`，并限制条数。
- 在 `_bounded_text()` 中统一移除除 `\n`、`\t` 之外的 C0 控制字符。

### SEC-05 — `BaseException` 中断可能残留临时文件（LOW）

**文件/行号：** `reports/html_exporter.py:644`

**实际代码证据：**

```python
except Exception:
    if fd is not None:
        ...
    if temporary is not None:
        temporary.unlink(missing_ok=True)
    raise
```

**风险：** `KeyboardInterrupt`、`SystemExit` 等 `BaseException` 不会触发清理，可能留下 `.report.html.*.tmp`。旧报告不会被替换，因此不是数据损坏；是清理/卫生问题。

**能否复现/验证：** 静态确认；本轮未注入 `KeyboardInterrupt`。

**最小修复建议（未实施）：**

- 将清理逻辑放入 `finally`，或在 `except BaseException` 中清理后 `raise`；注意不要吞掉取消/退出信号。
- 增加 `KeyboardInterrupt` 模拟测试，断言旧文件存在且无临时文件。

### SEC-06 — 自由文本字段可能包含敏感内容（LOW / 设计边界）

**文件/行号：** `reports/html_exporter.py:438-474`；模板 `vulnerability.html:36-47`、`evidence.html:21-27`。

**实际代码证据：**

```python
description=_bounded_text(finding.description),
recommendation=_bounded_text(finding.recommendation),
manual_notes=(_bounded_text(finding.manual_notes) if include_notes else ""),
...
description=_bounded_text(evidence.description),
source_text=_safe_relative_path(evidence.source),
file_status_note=_bounded_text(evidence.file_status_note),
```

**风险：** 这些字段是业务自由文本，可能由扫描器输出、公告内容、项目文件路径或人工备注带入敏感信息。Jinja2 会转义 HTML，但不会识别/脱敏令牌、凭据、客户路径。不能据此宣称“报告不含敏感数据”。

**能否复现/验证：** 字段确实被输出可静态确认；某条记录是否含敏感信息 **UNKNOWN**，本轮未扫描真实数据库内容。

**最小修复建议（未实施）：**

- 在产品层明确“报告包含原始描述/备注”的数据边界，并在 UI/文档提示；不要扩大到本轮实现。
- 若未来要求脱敏，增加独立的、可审计的脱敏/密钥扫描步骤，而不是在模板中做不可靠的正则替换。
- 至少保持 `include_notes` 默认策略和用户显式选择；当前实现已支持关闭备注。

### SEC-07 — Windows 保留设备名/非法文件名字符未拒绝（LOW；运行时 UNKNOWN）

**文件/行号：** `reports/html_exporter.py:598-612`

**实际代码证据：**

```python
if any(char in name for char in ("/", "\\", ":")):
    raise ValidationError("报告文件名不能包含路径分隔符")
...
if not name.lower().endswith(".html"):
    raise ValidationError("HTML 报告文件名必须以 .html 结尾")
if re.search(r"[\x00-\x1f]", name):
    raise ValidationError("报告文件名包含非法字符")
```

未检查：

- Windows 保留设备名：`CON`、`PRN`、`AUX`、`NUL`、`COM1`…`COM9`、`LPT1`…`LPT9`（含扩展名，如 `NUL.html`）；
- Windows 不允许的字符：`? * < > | "`；
- 结尾点/空格（开头的 `strip()` 会去掉首尾空格，但中间/其他形式仍需考虑）。

**风险：** 这些名称可能导致 `os.replace()` 失败、写入设备名或被系统拒绝；会破坏报告生成，但不构成目录穿越。调用方目前可使用默认安全文件名；风险主要在未来 GUI 允许用户自定义文件名时。

**能否复现/验证：** 静态确认未拦截；实际 Windows 对 `NUL.html`/`CON.html` 的行为本轮 **UNKNOWN**，未做写文件实验。

**最小修复建议（未实施）：**

- 对文件名 basename 做大小写不敏感的 Windows 保留名检查；
- 拒绝 `?*<>|"` 及结尾 `.`/空格；
- 增加 Windows 文件名校验测试，但不实际写设备名；
- 或只允许 `[A-Za-z0-9._-]` 的保守字符集。

## 6. UNKNOWN 清单

以下项目不能写成 PASS：

1. **Windows junction/symlink 的实际 containment**：静态逻辑使用 `resolve()` + `relative_to()` + `parent` 检查，但本轮未创建 junction/symlink 动态验证；见 SEC-02。
2. **`reports_dir` 自身为 symlink/junction**：代码解析并写入真实目录，未拒绝 root reparse point；可利用性取决于目录替换权限，未验证。
3. **并发 `overwrite=False`**：静态确认存在 TOCTOU，未用两个并发进程复现；见 SEC-01。
4. **Windows 保留设备名/非法文件名字符的运行时行为**：静态确认未拦截，未实际写 `NUL.html`/`CON.html`；见 SEC-07。
5. **自由文本是否含敏感信息**：只确认字段被输出；未对真实数据库内容做敏感信息扫描；见 SEC-06。
6. **CSP 缺失的实际影响**：当前无脚本/远程资源，未发现注入路径；不构成已确认漏洞，但纵深防御未验证。

## 7. 已通过项汇总

| 检查项 | 结论 | 依据 |
|---|---|---|
| View Model 字段 allowlist | PASS | `reports/html_exporter.py:232-288`, `:382-477`; `tests/test_report_html.py:272-297` |
| `Project.local_path` / `description` 排除 | PASS | `ProjectView` 仅 4 字段，`reports/html_exporter.py:82-87`, `:384-390` |
| 任务 target/error/result 排除 | PASS | `TaskView` 仅 8 字段，`reports/html_exporter.py:106-115`, `:414-425` |
| Finding 原始绝对路径排除 | PASS | `source_path=_safe_relative_path(...)`，`reports/html_exporter.py:444`, `:559-571` |
| Evidence 原始/受管路径排除 | PASS | `EvidenceView` 无 `file_path`/`managed_path`，`reports/html_exporter.py:154-168`, `:462-477` |
| Jinja2 autoescape | PASS | `autoescape=True`，`reports/html_exporter.py:57-65` |
| 模板无 `|safe`/Markup/autoescape off | PASS | 全模板 grep；`tests/test_report_html.py:473-483` |
| 模板无脚本/远程资源/事件属性 | PASS | `base.html`, `vulnerability.html`, `evidence.html`, `project_summary.html` 实际内容；模板 grep 无命中 |
| filename 路径穿越 | PASS | `reports/html_exporter.py:598-612`；`tests/test_report_html.py:425-441` |
| 目标必须直接位于 root | PASS | `target.parent != root`，`reports/html_exporter.py:332-333` |
| 原子写入顺序 | PASS | `reports/html_exporter.py:625-643` |
| 失败时旧文件保留/临时清理 | PASS（普通异常） | `reports/html_exporter.py:644-655`；`tests/test_report_html.py:444-470` |
| 默认不覆盖（顺序） | PASS | `reports/html_exporter.py:313`, `:334-337`, `:640-642`；`tests/test_report_html.py:395-422` |
| 报告类型/请求校验 | PASS | `reports/html_exporter.py:368-374`；`tests/test_report_html.py:349-369` |
| 无证据图片读取/嵌入 | PASS | `_evidence_view` 不读取文件；`reports/html_exporter.py:249-255`, `:462-477`；测试 `:315-330` |

## 8. 测试与数据库状态

本轮为只读审查，未运行测试、未写数据库、未迁移、未修改源码/测试/配置。

- 上一轮 Phase 6C-2A 完整测试记录：`163 collected / 162 passed / 1 skipped / 0 failed / 0 errors / 42.58s / exit 0`；skip 为 Windows symlink `WinError 1314`。
- 其中 `tests/test_report_html.py` 18 项通过；本报告引用了该文件作为安全行为的辅助证据。
- 数据库未变：主库 `f03cfb81...e3128bb`，schema 5，`integrity_check=ok`，FK 0，reports 0；验收库 `03de4950...ceb4c8`，schema 5，`integrity_check=ok`，FK 0，reports 0。
- 本轮唯一新增文件：`docs/PHASE6_C2A_SECURITY_REVIEW_1.md`。

## 9. 最终结论

**PASS_WITH_LIMITATIONS。**

- 无 Critical / High；无已确认的 XSS、脚本/远程资源注入、allowlist 敏感字段直传或 filename 路径穿越。
- 路径 containment 的叶节点静态逻辑 PASS；Windows junction/symlink 与 root reparse point 仍需实际测试，标记 UNKNOWN，不能写成 PASS。
- 默认不覆盖在顺序执行下 PASS；并发下存在 LOW 级 TOCTOU，建议按 SEC-01 修复。
- CSP、文件名保留设备名、控制字符/长度、`BaseException` 清理、自由文本脱敏属于 LOW/纵深防御/设计边界问题，不阻塞本轮“只读审查”结论。
- 本轮未自动修复任何问题，未开始 PDF/JSON/GUI，未扩大 Phase 6C-2A 范围。
