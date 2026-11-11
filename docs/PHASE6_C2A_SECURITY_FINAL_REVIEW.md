# Phase 6C-2A 安全修复综合收尾审查

- 审查日期：2026-11-07
- 审查方式：**只读源码、测试和报告核对**
- 审查范围：Phase 6C-2A 的 SEC-01、SEC-02、SEC-04、SEC-05、SEC-07
- 审查依据：
  - `docs/PHASE6_C2A_SECURITY_REVIEW_1.md`
  - `docs/PHASE6_C2A_SECURITY_FIX_1.md`
  - `docs/PHASE6_C2A_SECURITY_FIX_1_REVIEW_EVIDENCE.md`
  - `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_REVIEW.md`
  - `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md`
- 本轮限制：不修改任何源码、测试、数据库、Schema、模板或 GUI；不写业务数据库；**未运行测试回归**；未生成正式业务报告；未进入 PDF、JSON、GUI 或 Phase 6C-2B。
- 总体结论：**PASS_WITH_LIMITATIONS**

---

## 1. 最终状态摘要

| ID | 安全问题 | 最终状态 | 说明 |
|---|---|---|---|
| SEC-01 | `overwrite=False` 原子排他发布 | **PASS** | 已改为 `os.link()` 排他发布；模拟竞态动态验证通过；未做真实双进程竞态测试 |
| SEC-02 | root junction/symlink 拒绝与叶节点 containment | **PASS_WITH_LIMITATIONS** | root junction 动态拒绝 PASS；root symlink 动态 UNKNOWN；外部叶节点 junction PASS；叶节点 symlink/内部别名、父级 reparse、TOCTOU 仍为 UNKNOWN |
| SEC-04 | 文本长度及控制字符处理 | **PASS** | 指定四个字段已限长、限条数并处理控制字符；文档中的“移除全部 C0”表述不精确，TAB/LF 被保留；统计标签仍有未限长残余 |
| SEC-05 | 异常中断后的临时文件清理 | **PASS** | `finally` 覆盖 `KeyboardInterrupt` 模拟路径；旧文件保留、临时文件清理通过；进程被强杀等极端情况不在保证范围 |
| SEC-07 | Windows 文件名校验 | **PASS** | 保留设备名、非法字符、路径分隔符、控制字符、后缀和长度校验已存在；动态参数化测试通过；未实际写设备名 |

**总体不是无保留 PASS。** SEC-02 的 symlink 动态验证、父级 reparse point 和 TOCTOU 仍不能标记为 PASS。

---

## 2. 审查方法

本轮只做了以下只读动作：

1. 读取实际源码 `reports/html_exporter.py`；
2. 读取实际测试 `tests/test_report_html.py`；
3. 对照五份历史报告及其测试记录；
4. 检查修复之间是否存在逻辑冲突、绕过或重复保护失效；
5. 对每项区分：
   - **动态验证**：已有实际运行结果；
   - **静态确认**：源码逻辑可确认，但没有对应动态对抗测试；
   - **UNKNOWN**：当前环境或本轮限制无法确认。

本轮没有：

- 修改源码或测试；
- 执行 pytest；
- 打开或写入业务数据库；
- 修改 Schema、模板、GUI；
- 修改系统 ACL 或 symlink 权限。

---

## 3. SEC-01：原子排他发布

### 3.1 实际源码

**状态：PASS**

`reports/html_exporter.py:327-360` 的 `write_html_report()` 仍有前置存在性检查：

```python
if target.exists() and not overwrite:
    raise FileExistsError(...)
```

但真正防止并发覆盖的是 `_atomic_write()` 在 `overwrite=False` 时调用的 `_publish_exclusive()`：

`reports/html_exporter.py:675-698`：

```python
def _publish_exclusive(temporary: Path, target: Path) -> None:
    if not hasattr(os, "link"):
        raise ReportExportError(...)
    try:
        os.link(temporary, target)
    except FileExistsError as exc:
        raise FileExistsError(...) from exc
    except OSError as exc:
        if exc.errno == errno.EEXIST or getattr(exc, "winerror", None) in (80, 183):
            raise FileExistsError(...) from exc
        raise ReportExportError(...) from exc
```

`reports/html_exporter.py:701-736` 的 `_atomic_write()`：

- `overwrite=True`：`os.replace(temporary, target)`；
- `overwrite=False`：调用 `_publish_exclusive()`，成功后删除临时文件；
- 没有 `os.replace()` 回退；
- 不支持硬链接时抛 `ReportExportError`，失败关闭，而不是静默降级。

### 3.2 对应测试

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_overwrite_false_race_is_rejected_by_exclusive_publish` | `tests/test_report_html.py:579` | 通过（模拟竞态） |
| `test_no_overwrite_fails_closed_without_hardlink_support` | `tests/test_report_html.py:609` | 通过 |
| `test_write_refuses_overwrite_and_preserves_old_file` | `tests/test_report_html.py:398` | 通过（顺序执行） |

模拟竞态测试的做法是：在真实 `os.link()` 之前由 monkeypatch 写入目标文件，再调用真实 `os.link()`，断言 `FileExistsError` 且并发写入内容保留。它验证的是“目标已存在时排他发布失败”，**不是**两个独立进程同时运行的动态竞态测试。

### 3.3 判定理由与限制

**PASS 的理由：**

- `overwrite=False` 的最终发布不再依赖“检查后替换”；
- `os.link()` 在目标存在时原子失败；
- 没有不安全回退；
- 模拟竞态测试实际触发了 `FileExistsError`；
- 旧文件内容未被替换。

**限制：**

- 没有真实双进程并发测试；
- 依赖文件系统支持硬链接；不支持时失败关闭，功能可用性受影响；
- `write_html_report()` 的 `target.exists()` 前置检查仍存在，但不再是并发安全的唯一保证；
- `SEC-05` 清理逻辑在 `os.link()` 成功后若临时文件 unlink 失败，会留下临时文件（不覆盖目标），属于清洁性残余，见第 7 节。

**最终：PASS（模拟动态；真实多进程竞态为 UNKNOWN，但核心排他原语已成立）。**

---

## 4. SEC-04：文本长度及控制字符处理

### 4.1 实际源码

**状态：PASS（指定字段范围）**

常量与正则（`reports/html_exporter.py:68-86`）：

```python
_MAX_TITLE = 200
_MAX_FIELD = 2_000
_MAX_PATH = 300
_MAX_LIST_ITEMS = 100
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
```

`reports/html_exporter.py:574-599`：

```python
def _bounded_text(value: Any, limit: int = _MAX_FIELD) -> str:
    text = _CONTROL_CHARS_RE.sub("", str(value or "")).strip()
    if len(text) > limit:
        return text[: max(0, limit - 1)] + "…"
    return text


def _single_line_text(value: Any, limit: int = _MAX_TITLE) -> str:
    text = _bounded_text(value, limit)
    return re.sub(r"\s+", " ", text).strip()


def _bounded_sequence(...):
    ...
    text = _single_line_text(item, limit)
    ...
    if len(result) >= max_items:
        break
```

实际使用位置：

- 标题：`_request_title()` 使用 `_single_line_text(..., _MAX_TITLE)`（`reports/html_exporter.py:396-403`）；
- warnings / data_scope / known_limitations：均走 `_bounded_sequence()`（`:299-301`）；
- Finding / Evidence / 项目 / 授权 / 任务文本：逐项 `_bounded_text()`；
- 展示路径：`_safe_relative_path()` / `_safe_file_name()`（`:602-624`）。

### 4.2 关键事实

1. 控制字符正则**不删除 TAB `\x09` 和 LF `\x0a`**，只删除 `\x00-\x08`、`\x0b-\x1f`、`\x7f`。
2. `_single_line_text()` 会把 TAB/LF 折叠为空格，因此标题和列表项最终不含 TAB/LF。
3. `description`、`recommendation` 等长文本使用 `_bounded_text()` 而不是 `_single_line_text()`，会保留换行和制表符。
4. 这些值仍经过 Jinja2 autoescape，不能形成 HTML 注入；保留换行是显示语义，不是转义绕过。
5. 历史报告 `docs/PHASE6_C2A_SECURITY_FIX_1.md` 将正则描述为“移除 C0 控制字符”，表述不够精确；实际是“移除 C0 中除 TAB/LF 之外的字符及 DEL”。**这是文档准确性问题，不是当前代码回归。**

### 4.3 对应测试

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_untrusted_text_fields_are_bounded_and_control_chars_removed` | `tests/test_report_html.py:666` | 通过 |
| `test_warning_list_is_bounded` | `tests/test_report_html.py:702` | 通过 |

测试覆盖：

- 标题上限 200；
- warnings/data_scope/known_limitations 单项上限 2,000；
- warnings 最多 100 条；
- NUL、SOH、STX、US、TAB、换行在指定字段中被清除或折叠；
- 未覆盖 CR/DEL 的独立断言，也未覆盖 `description`/`recommendation` 中保留 TAB/LF 的行为。

### 4.4 额外残余（不推翻本轮 SEC-04 结论）

实际源码中统计标签仍存在未限长路径：

- `_count_views()` 的未知键：`CountView(str(key), count)`（`reports/html_exporter.py:534-537`）；
- `_named_count_views()`：`CountView(str(key), ...)`（`:541-546`）。

这些 key 来自统计映射，可能包含长字符串或控制字符。Jinja2 会自动转义，但长度/控制字符卫生不统一。它不属于原 SEC-04 明确点名的 `title`、`warnings`、`data_scope`、`known_limitations` 四项，**分类为附加 LOW 残余，建议后续统一走 `_bounded_text()`；本轮不把它写成已修复。**

**最终：PASS（本轮指定字段已动态验证；文档措辞和统计标签残余需记录，不是未修复的指定字段）。**

---

## 5. SEC-05：异常中断后的临时文件清理

### 5.1 实际源码

**状态：PASS**

`reports/html_exporter.py:701-736`：

```python
def _atomic_write(target: Path, payload: bytes, *, overwrite: bool) -> None:
    fd: int | None = None
    temporary: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(...)
        temporary = Path(temporary_name)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, target)
            temporary = None
        else:
            _publish_exclusive(temporary, target)
            try:
                temporary.unlink()
            except OSError:
                pass
            temporary = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
```

关键点：

- 清理从旧的 `except Exception` 改为 `finally`；
- `KeyboardInterrupt`、`SystemExit` 等 `BaseException` 也会触发 `finally`；
- 替换失败时旧文件保留，临时文件被尝试删除；
- `os.replace()` 成功前不会截断旧文件。

### 5.2 对应测试

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_keyboard_interrupt_cleans_temp_and_preserves_old_file` | `tests/test_report_html.py:637` | 通过 |
| `test_failed_replace_preserves_old_file_and_cleans_temp` | `tests/test_report_html.py:447` | 通过（历史） |
| `test_atomic_write_is_utf8_and_returns_artifact` | `tests/test_report_html.py:375` | 通过（历史） |

`KeyboardInterrupt` 测试通过 monkeypatch 让 `os.replace` 抛出 `KeyboardInterrupt`，断言：

- 旧报告字节不变；
- 没有残留 `.tmp` 文件。

这是对清理路径的动态模拟，不是进程被强杀（`TerminateProcess`/断电）的测试。

### 5.3 限制

- 普通 `finally` 不保证进程被强制终止、系统崩溃或断电时的清理；
- 清理中的 `unlink` 失败被静默忽略，可能残留临时文件；
- 成功发布后 `temporary.unlink()` 失败也会留下临时文件（不覆盖目标）；
- 未对父目录执行 `fsync`；这是 durability 限制，不是注入/越权问题。

**最终：PASS（`KeyboardInterrupt` 模拟清理动态通过；强制终止和清理失败为已知限制）。**

---

## 6. SEC-07：Windows 文件名校验

### 6.1 实际源码

**状态：PASS（校验逻辑；设备名实际写入 UNKNOWN）**

`reports/html_exporter.py:643-662`：

```python
def _validate_filename(filename: str) -> str:
    name = str(filename).strip()
    if not name:
        raise ValidationError("报告文件名不能为空")
    if any(char in name for char in ("/", "\\", ":")):
        raise ValidationError("报告文件名不能包含路径分隔符")
    if any(char in _INVALID_FILENAME_CHARS for char in name):
        raise ValidationError("报告文件名包含 Windows 非法字符")
    if name in {".", ".."}:
        raise ValidationError("报告文件名无效")
    if not name.lower().endswith(".html"):
        raise ValidationError("HTML 报告文件名必须以 .html 结尾")
    if len(name) > 180:
        raise ValidationError("报告文件名过长")
    if re.search(r"[\x00-\x1f\x7f]", name):
        raise ValidationError("报告文件名包含非法字符")
    device_stem = name.split(".", 1)[0].rstrip(" .").upper()
    if device_stem in _WINDOWS_RESERVED_NAMES:
        raise ValidationError("报告文件名不能使用 Windows 保留设备名")
    return name
```

保留名集合（`reports/html_exporter.py:74-86`）包括：

```text
CON, PRN, AUX, NUL, CLOCK$, CONIN$, CONOUT$,
COM1..COM9, LPT1..LPT9
```

非法字符集合（`:73`）为：

```text
? * < > | "
```

另外拒绝 `/`、`\`、`:`、空名、`.`、`..`、非 `.html` 后缀、长度 >180 和控制字符。

### 6.2 对应测试

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_write_rejects_windows_reserved_names_and_invalid_chars` | `tests/test_report_html.py:713-746` | 通过（14 个参数化名称） |

覆盖的名称包括：

```text
NUL.html, nul.html, CON.html, PRN.html, AUX.html,
COM1.html, LPT9.html, CONIN$.html,
report?.html, report*.html, report<.html,
report>.html, report|.html, report".html
```

### 6.3 判定理由与限制

**PASS 的理由：**

- 设备名校验大小写不敏感；
- 取第一个 `.` 前的主干并去除尾部空格/点，覆盖 `NUL .html` 一类变体；
- 覆盖 `?*<>|"`；
- 覆盖路径分隔符和控制字符；
- 动态参数化测试通过，并断言输出目录没有生成文件。

**限制：**

- 没有真正尝试写 `NUL.html`/`CON.html` 到 Windows 设备；运行时行为为 **UNKNOWN**；校验层已经拒绝，因此不应依赖未验证的设备写入结果；
- 未覆盖 Unicode 设备名变体、末尾点/空格的其他组合、`COM0` 等非标准名称；
- 文件名边界由调用方传入；`_default_filename()` 生成安全名称，但未来 GUI 若允许用户自定义，仍需沿用同一校验入口。

**最终：PASS（校验动态；实际设备写入 UNKNOWN，且不需要以设备写入作为通过条件）。**

---

## 7. SEC-02：root reparse point 与叶节点路径包含

### 7.1 实际源码

**状态：PASS_WITH_LIMITATIONS**

root 解析（`reports/html_exporter.py:627-640`）：

```python
def _resolve_reports_root(reports_dir: str | Path) -> Path:
    root = Path(reports_dir).expanduser()
    if not root.is_absolute():
        raise ValidationError("报告输出目录必须是绝对路径")
    if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
        raise ValidationError("报告输出目录不能是符号链接或 junction")
    root = root.resolve()
    if root.exists() and not root.is_dir():
        raise ValidationError("报告输出目录不是目录")
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportExportError(f"无法创建报告输出目录: {exc}") from exc
    return root
```

叶节点 containment（`reports/html_exporter.py:344-356`）：

```python
root = _resolve_reports_root(reports_dir)
target_name = _validate_filename(filename or _default_filename(snapshot))
target = (root / target_name).resolve()
try:
    target.relative_to(root)
except ValueError as exc:
    raise ValidationError("报告目标路径越界") from exc
if target.parent != root:
    raise ValidationError("报告目标必须直接位于 reports_dir")
if target.exists() and not overwrite:
    raise FileExistsError(...)
if target.exists() and target.is_dir():
    raise ValidationError("报告目标不是文件")
```

关键点：

- root 的 symlink/junction 检查发生在 `root.resolve()` **之前**；
- 叶节点先 `resolve()`，再 `relative_to(root)`，再要求父目录必须是 root；
- 外部 junction/symlink 叶节点会解析到 root 外，被 `relative_to()` 拒绝；
- 内部叶节点目录 junction 会通过 `relative_to()`，随后因 `target.exists() and target.is_dir()` 被拒绝；
- 没有叶节点 reparse point 的显式类型判断；内部别名/断链处理依赖解析结果和后续存在性检查。

### 7.2 动态验证证据

来自 `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md` 和 `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_REVIEW.md`：

| 场景 | 实际结果 | 状态 |
|---|---|---|
| 正常真实 `reports_dir` | 正常导出 | PASS |
| `reports_dir` 自身为 junction | `ValidationError`；junction 目标目录无新增文件 | **PASS（动态）** |
| `reports_dir` 自身为 symlink | `os.symlink` 返回 `WinError 1314`；测试 skip | **UNKNOWN** |
| 外部叶节点 junction | `ValidationError`（路径越界）；外部目录无新增 | **PASS（动态）** |
| 外部叶节点 symlink | 当前会话无法创建 symlink | **UNKNOWN** |
| 内部叶节点目录 junction | 因目标目录存在而拒绝（`FileExistsError`/目录检查），无外部写入 | PASS（无外部写入；非显式 reparse 拒绝） |
| 内部叶节点文件 symlink | 当前会话无 symlink | **UNKNOWN** |
| 断链 junction | 被拒绝，无写入 | PASS（动态；依赖 `resolve()` 行为） |
| 断链 symlink | 当前会话无 symlink | **UNKNOWN** |
| 父级路径为 reparse point | 未执行专项动态验证；代码不检查父级 | **UNKNOWN** |
| 并发替换 root/父目录 | 未执行对抗测试 | **UNKNOWN（TOCTOU）** |

### 7.3 对应测试

| 测试 | 位置 | 状态 |
|---|---|---|
| `test_normal_real_reports_dir_still_exports` | `tests/test_report_html.py:502` | PASS |
| `test_reports_dir_itself_junction_is_rejected` | `tests/test_report_html.py:520` | PASS（动态） |
| `test_reports_dir_itself_symlink_is_rejected_when_available` | `tests/test_report_html.py:537` | SKIP / UNKNOWN |
| `test_external_junction_leaf_is_rejected` | `tests/test_report_html.py:560` | PASS（动态） |
| `test_write_rejects_path_escape_and_non_html` | `tests/test_report_html.py:432` | PASS（历史） |

### 7.4 父级 reparse point

代码只检查 `reports_dir` 自身：

- 如果 `reports_dir` 是 `D:\trusted\reports`；
- 但 `D:\trusted` 本身是 junction；
- `root.is_junction()` 对 `D:\trusted\reports` 可能返回 False；
- `root.resolve()` 会跟随父级，最终写入真实目标。

因此：

- **父级 reparse point 未覆盖**；
- 如果 `reports_dir` 的父目录可被低权限用户替换，仍可能发生输出重定向；
- 信任边界必须明确：`reports_dir` 及其父目录由受信任配置/管理员控制；若攻击者已能改写该目录树，通常也能直接改写已有报告。

该边界不能写成 PASS。

### 7.5 TOCTOU

检查与使用之间存在窗口：

1. `root.is_symlink()` / `root.is_junction()` 检查；
2. `root.resolve()`；
3. `root.mkdir()`；
4. 叶节点 `target.resolve()`、`relative_to()`、`parent` 检查；
5. `target.exists()` 检查；
6. `_atomic_write()` 的 `os.link()`/`os.replace()`。

攻击者若在 1-5 之间替换 root、父目录或叶节点，检查结果可能已经过期。当前实现没有目录句柄约束或 `openat`-style 的路径固定，**不能宣称完全消除 TOCTOU**。

### 7.6 最终判定

- root junction 拒绝：**PASS（动态）**；
- root symlink 拒绝：**UNKNOWN（静态逻辑存在，动态权限不足）**；
- 外部叶节点 junction containment：**PASS（动态）**；
- 叶节点 symlink、内部别名、断链 symlink：**UNKNOWN**；
- 父级 reparse point、并发替换：**UNKNOWN**。

**SEC-02 总体：PASS_WITH_LIMITATIONS，不是无条件 PASS。**

---

## 8. 修复之间的逻辑冲突检查

本轮未发现会使已有修复失效的直接冲突：

1. **SEC-01 与 SEC-05**
   - `_publish_exclusive()` 成功后，`_atomic_write()` 删除临时文件；
   - `finally` 再兜底清理；
   - 成功路径中 `temporary` 被置为 `None`，不会重复删除目标或误删旧文件；
   - 残余：成功后的 `temporary.unlink()` 失败会留下临时文件，但不覆盖目标。

2. **SEC-02 与 SEC-01**
   - root 检查在 `resolve()` 前；
   - 叶节点 containment 使用解析后的 root；
   - `_publish_exclusive()` 不再重新解析 target，只对已校验路径发布；
   - 没有发现 root/leaf 检查被 `os.replace()` 绕过；但 TOCTOU 仍存在。

3. **SEC-04 与 SEC-07**
   - SEC-04 处理 HTML 文本内容；
   - SEC-07 处理文件名；
   - 两者使用不同的清理函数，没有出现“文件名被文本清理后改变语义”或“文本清理绕过文件名检查”的路径。

4. **SEC-04 与模板 autoescape**
   - autoescape 仍是最终 HTML 输出保护；
   - 长度/控制字符清理是展示层加固，不是转义的替代；
   - 没有发现 `|safe`、`Markup` 或 `autoescape false` 回退。

5. **SEC-07 与 SEC-02**
   - 文件名先校验，再拼接到 root；
   - `/`、`\`、`:`、控制字符、保留设备名在路径解析前被拒绝；
   - 没有发现可通过文件名绕过 root 检查的路径。

**结论：没有发现修复之间的直接逻辑冲突；存在的是共同边界（TOCTOU、父级 reparse、symlink 动态缺失），不是相互抵消。**

---

## 9. 动态、静态与 UNKNOWN 分类

### 9.1 已动态验证

- SEC-01 的模拟竞态：目标存在时 `os.link()` 失败；
- SEC-01 的不支持硬链接失败关闭：`ReportExportError`，无目标、无临时文件；
- SEC-04 的指定字段限长、限条数、控制字符清理；
- SEC-05 的 `KeyboardInterrupt` 模拟清理；
- SEC-07 的 14 个保留名/非法字符参数化拒绝；
- SEC-02 的 root junction 拒绝、正常目录导出、外部叶节点 junction 拒绝；
- 外部叶节点 junction 拒绝后目标目录保持为空。

### 9.2 仅静态确认

- SEC-01 的真实并发语义依赖操作系统 `link()` 原子性；没有真实双进程测试；
- SEC-05 的 `SystemExit`/强制终止边界没有动态测试；
- SEC-07 的 Windows 设备名实际写入行为没有动态测试；
- SEC-02 的 root symlink 分支有代码但当前权限无法动态创建；
- 叶节点内部文件 symlink 的别名行为没有动态测试。

### 9.3 UNKNOWN

- `reports_dir` 自身 symlink 的动态行为；
- 外部/内部叶节点 symlink、断链 symlink 的动态行为；
- 父级目录为 reparse point 时的输出路径；
- 检查与发布之间的 TOCTOU 并发替换；
- 真实 Windows 设备名（`NUL.html` 等）的实际写入/系统行为；
- 统计标签未限长的实际影响范围。

**UNKNOWN 不等于 PASS。**

---

## 10. 剩余风险与信任边界

### 10.1 已记录风险

| 风险 | 分类 | 说明 |
|---|---|---|
| 父级 reparse point | UNKNOWN / 设计边界 | 只检查 `reports_dir` 自身，不递归检查父级 |
| TOCTOU | UNKNOWN / 竞争条件 | 检查与 `resolve()`、`mkdir()`、`os.link()` 之间不是同一目录句柄操作 |
| root symlink 动态 | UNKNOWN | 当前 Windows 会话 `WinError 1314` |
| 叶节点 symlink / 内部别名 | UNKNOWN | 仅外部 junction 和正常目录动态验证 |
| SEC-01 真实双进程竞态 | UNKNOWN（核心原语 PASS） | 模拟测试不是进程级并发 |
| SEC-04 统计标签 | 附加 LOW | `CountView` 未知 key 未统一限长 |
| SEC-05 清理失败 | 已知残余 | `unlink` 失败被忽略；强制终止不保证清理 |
| SEC-07 实际设备写入 | UNKNOWN | 校验已拒绝，但没有实际写设备名 |
| SEC-03 CSP | 未修复 LOW | 模板无脚本/远程资源；不在本轮五项修复内 |
| SEC-06 语义脱敏 | 未修复 / 设计边界 | 自由文本只做 HTML 转义，不做敏感信息语义脱敏 |

### 10.2 信任边界

本实现的安全信任边界应明确为：

1. `reports_dir` 及其父目录由受信任的应用配置或管理员控制；
2. 本地攻击者若已经能替换 `reports_dir` 或父目录，通常也已经能修改/删除报告；root reparse 检查降低误写风险，但不是对所有本地写权限的隔离；
3. 数据库中的 Finding/Evidence 自由文本是业务数据，HTML 转义保证不执行脚本，但**不保证内容不含敏感信息**；
4. 报告文件是本地文件，不是远程服务；没有脚本、远程资源和图片嵌入；
5. `overwrite=False` 的硬链接要求在目标文件系统上可用；不支持时失败关闭，不静默降级；
6. 完整测试环境仍受 Windows 低完整性/临时目录 ACL 限制，需独立临时目录和 full-access 测试进程；这不属于产品安全边界，但属于验证边界。

---

## 11. 历史测试与数据库证据

### 11.1 测试结果

**SEC-01/04/05/07 第一轮修复完成后（历史记录）：**

- HTML 专项：`37 passed`；
- 完整回归：`181 passed, 1 skipped, 0 failed, 0 errors`；
- 跳过项：Windows symlink `WinError 1314`。

**SEC-02 修复完成后（最新历史记录，见 `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md`）：**

- HTML 专项：`40 passed, 1 skipped in 0.36s`；
- 完整回归：`184 passed, 2 skipped, 0 failed, 0 errors in 39.72s`；
- 退出码：`0`；
- 测试项总数：186（184 passed + 2 skipped）；
- skip 1：既有 Windows symlink `WinError 1314`；
- skip 2：SEC-02 root symlink 测试，当前会话 `WinError 1314`；
- 测试环境：`D:\挖漏洞\pytest_c1r_tmp\bt_sec02_fix_full`，DSH full-access 测试进程；
- 本轮**未重跑**测试，以上均为历史执行结果。

### 11.2 数据库

**本轮未打开或写入业务数据库。** 历史只读检查（SEC-02 修复报告）为：

```text
storage/src_research.db
size=147456
sha256=F03CFB81BF0CF4CEE3367E1413E26919E30FA763C2D1B792AA03B5300E3128BB
user_version=5
integrity=ok
fk_rows=0
tables=11
reports=0

storage/phase5_acceptance/acceptance.db
size=352256
sha256=03DE49509B43428EB303F7DC38E1FF749CC58D1B3F186070C63706BBA4CEB4C8
user_version=5
integrity=ok
fk_rows=0
tables=11
reports=0
```

这些值来自历史记录；本轮没有重新执行数据库检查，因此不能把“当前再次验证”写成事实。

---

## 12. 是否建议关闭 Phase 6C-2A 安全加固

**建议：以“记录限制”的方式关闭，不建议无保留关闭。**

理由：

- 五项修复均实际存在于源码；
- SEC-01、SEC-04、SEC-05、SEC-07 的指定问题有实际测试或代码证据；
- SEC-02 的 root junction 和外部叶节点 junction 已动态验证；
- 没有发现 Critical / High 问题，也没有发现修复之间的直接逻辑冲突；
- 但 SEC-02 的 root symlink、叶节点 symlink、父级 reparse point 和 TOCTOU 仍为 UNKNOWN；
- SEC-04 统计标签、SEC-05 清理失败、SEC-07 设备写入仍有限制；
- SEC-03 CSP、SEC-06 语义脱敏不在本轮五项修复内，仍应按既有记录跟踪。

因此建议的关闭状态是：

```text
Phase 6C-2A Security Hardening: CLOSED_WITH_RECORDED_LIMITATIONS
```

而不是：

```text
Unconditional PASS / 安全加固完全结束
```

---

## 13. 是否具备进入 Phase 6C-2B 的条件

**结论：条件性具备。**

可以进入 6C-2B 的前提：

1. 接受本报告记录的 SEC-02 UNKNOWN 与 TOCTOU/父级 reparse 残余；
2. 不把 C2A 的 HTML 导出描述为“完全路径安全”或“无敏感信息”；
3. 6C-2B 不绕过 `write_html_report()` 的路径、文件名、排他发布和清理入口；
4. 6C-2B 的测试继续使用独立临时目录，记录 Windows symlink 权限限制；
5. 若 6C-2B 引入用户自定义输出路径/文件名，必须先补 SEC-02 父级/符号链接策略和 SEC-07 的扩展测试；
6. 不自动进入下一阶段，仍需明确授权。

**不建议将“具备条件”写成“无条件通过”。**

---

## 14. 最终结论

- **SEC-01：PASS**（模拟竞态动态通过；真实多进程未测）。
- **SEC-02：PASS_WITH_LIMITATIONS**（root junction 动态 PASS；root symlink UNKNOWN；外部叶节点 junction PASS；叶节点 symlink/父级/TOCTOU UNKNOWN）。
- **SEC-04：PASS**（指定字段动态通过；文档措辞和统计标签残余需记录）。
- **SEC-05：PASS**（`KeyboardInterrupt` 模拟清理通过；强制终止为限制）。
- **SEC-07：PASS**（校验动态通过；设备实际写入 UNKNOWN）。

总体：**PASS_WITH_LIMITATIONS**。

建议：

- 以 `CLOSED_WITH_RECORDED_LIMITATIONS` 关闭 Phase 6C-2A 安全加固；
- Phase 6C-2B 条件性具备，需接受残余风险并明确授权；
- 本轮停止，不修改源码、测试、数据库、Schema、模板或 GUI，不进入下一阶段。
