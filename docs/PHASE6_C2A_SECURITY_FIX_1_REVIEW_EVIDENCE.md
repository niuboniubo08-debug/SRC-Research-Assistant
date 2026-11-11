# Phase 6C-2A Security Fix 1 Review Evidence

## 0. 结论摘要

本次为只读证据补充，未修改源码、测试、数据库、Schema、模板或归档文件；唯一新增文件为本报告。

- **SEC-01**：新增了两个相关测试。其中 `test_overwrite_false_race_is_rejected_by_exclusive_publish` 是**确定性的抢占时序模拟**，由一个 monkeypatch 的“竞争者”在 exporter 调用 `os.link()` 前创建目标，再让真实 `os.link()` 失败；它**不是**两个真实并发线程/进程同时调用 `write_html_report()` 的并发测试。该测试能证明：在目标已被另一个写入者创建后，exporter 不会覆盖目标并抛出 `FileExistsError`；但不能证明真实并发调度、压力或多进程下的行为。`test_no_overwrite_fails_closed_without_hardlink_support` 只验证硬链接不可用时 fail-closed，不是并发测试。
- **SEC-04**：实现确实对 `title`、`warnings`、`data_scope`、`known_limitations` 做了长度、控制字符和空白规范化。但报告第 58 行“移除 C0 控制字符”的表述不精确：TAB（`\x09`）和 LF（`\x0A`）被排除在正则之外，`_bounded_text()` 会保留它们（仅在首尾被 `strip()` 去掉），随后 `_single_line_text()` 才把它们折叠为空格。报告第 70 行对测试覆盖的描述基本正确，但该测试没有覆盖 CR 和 DEL；且用于说明“TAB/换行被清理”时应区分“正则移除”和“单行折叠”。
- 本次未运行 pytest，未打开或写入数据库；仅做静态代码检查和只读 helper 行为探测。

## 1. 检查范围与依据

- 依据报告：`docs/PHASE6_C2A_SECURITY_FIX_1.md`
- 检查对象：
  - `reports/html_exporter.py`
  - `tests/test_report_html.py`
- 检查方式：只读源码、测试代码、报告文本；用 `python -B` 调用不写文件的内部 helper 进行行为探测；不运行完整测试，不执行数据库操作。
- 不修改任何已有文件；唯一新增文件为本报告。

## 2. SEC-01：并发排他发布

### 2.1 本次新增的 SEC-01 测试名称

本次修复新增的 SEC-01 相关测试为：

| 测试名称 | 位置 | 性质 |
|---|---|---|
| `test_overwrite_false_race_is_rejected_by_exclusive_publish` | `tests/test_report_html.py:487-514` | 确定性抢占时序模拟，非真实并发 |
| `test_no_overwrite_fails_closed_without_hardlink_support` | `tests/test_report_html.py:517-542` | 硬链接不支持时 fail-closed |

补充说明：`tests/test_report_html.py:396-423` 的 `test_write_refuses_overwrite_and_preserves_old_file` 是既有顺序覆盖保护测试，不是本次新增，也不是并发测试；本次不把它计入 SEC-01 并发证据。

### 2.2 对应测试代码

`tests/test_report_html.py:487-514`：

```python
def test_overwrite_false_race_is_rejected_by_exclusive_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"
    real_link = html_exporter.os.link

    def racing_link(src, dst, *args, **kwargs):
        Path(dst).write_text("concurrent winner", encoding="utf-8")
        return real_link(src, dst, *args, **kwargs)

    def forbidden_replace(*args, **kwargs):
        raise AssertionError("overwrite=False must not use os.replace")

    monkeypatch.setattr(html_exporter.os, "link", racing_link)
    monkeypatch.setattr(html_exporter.os, "replace", forbidden_replace)

    with pytest.raises(FileExistsError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert target.read_text(encoding="utf-8") == "concurrent winner"
    assert not list(output_dir.glob(".*.tmp"))
```

`tests/test_report_html.py:517-542`：

```python
def test_no_overwrite_fails_closed_without_hardlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"

    def unsupported_link(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, "hard links unsupported")

    def forbidden_replace(*args, **kwargs):
        raise AssertionError("overwrite=False must not fall back to os.replace")

    monkeypatch.setattr(html_exporter.os, "link", unsupported_link)
    monkeypatch.setattr(html_exporter.os, "replace", forbidden_replace)

    with pytest.raises(html_exporter.ReportExportError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert not target.exists()
    assert not list(output_dir.glob(".*.tmp"))
```

### 2.3 关键断言

- `test_overwrite_false_race...`：
  - `with pytest.raises(FileExistsError)`：exporter 必须拒绝覆盖并给出目标已存在错误。
  - `assert target.read_text(...) == "concurrent winner"`：目标内容必须仍是“竞争者”写入的内容，exporter 不能替换它。
  - `assert not list(output_dir.glob(".*.tmp"))`：失败后不能遗留临时文件。
  - `forbidden_replace`：若 `overwrite=False` 路径调用 `os.replace()`，测试立即失败；该断言强化了“没有不安全回退”。
- `test_no_overwrite_fails_closed...`：
  - `with pytest.raises(html_exporter.ReportExportError)`：硬链接不支持时必须明确失败。
  - `assert not target.exists()`：失败时不能生成目标文件。
  - `assert not list(output_dir.glob(".*.tmp"))`：失败时不能遗留临时文件。
  - `forbidden_replace`：不能退回 `os.replace()`。

### 2.4 是否真正模拟两个写入者竞争

**没有真正模拟两个并发写入者竞争同一个目标文件。**

具体原因：

1. 测试只启动了一个 exporter 调用；另一个“写入者”是 `racing_link()` 内的 `Path(dst).write_text("concurrent winner")`，不是第二个 `write_html_report()` 调用，也不是独立线程、进程或 OS 级写入者。
2. `racing_link()` 在 exporter 已经完成临时文件写入、调用 `os.link()` 的时刻，直接创建目标并写入内容；这模拟的是“目标在预检查之后、原子发布之前被另一个写入者抢先创建”的确定性窗口，而不是两个写入者实际并发调度。
3. 测试没有使用线程、进程池、`Barrier`、重复压力循环或实际文件锁竞争；因此不能证明真实多写入者并发下的时序、失败率或平台差异。

因此，该测试名称中的 `race` 应理解为**确定性抢占时序模拟**，不是并发压力测试。它证明了“在目标先被创建的情况下，exporter 不会覆盖”，但没有证明“两个真实 exporter 同时运行时最终只有一个成功”这一更强的并发性质。

### 2.5 实现层面的排他性

`reports/html_exporter.py:673-696` 的 `_publish_exclusive()`：

- `overwrite=False` 最终使用 `os.link(temporary, target)` 发布。
- 目标已存在时，`os.link` 在 POSIX 和 Windows NTFS 上原子失败；代码把 `FileExistsError` 及 `EEXIST`/WinError 80/183 统一转换为 `FileExistsError`。
- 硬链接不可用或不支持时抛出 `ReportExportError`，没有 `os.replace()` 或其他不安全回退。
- `write_html_report()` 在 `reports/html_exporter.py:353-354` 保留 `target.exists()` 快速拒绝；该检查只用于尽早反馈，最终安全性仍依赖 `os.link()`。

这与“一个模拟竞争者先写目标、exporter 后发布失败”的测试路径一致。

## 3. SEC-04：控制字符处理

### 3.1 实际实现

`reports/html_exporter.py:72`：

```python
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
```

该正则的匹配范围是：

- `\x00-\x08`：NUL、SOH、STX、ETX、EOT、ENQ、ACK、BEL、BS
- `\x0b-\x1f`：VT、FF、CR、SO、SI、DLE、DC1-DC4、NAK、SYN、ETB、CAN、EM、SUB、ESC、FS、GS、RS、US
- `\x7f`：DEL

**不匹配**：TAB（`\x09`）和 LF（`\x0A`）。

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


def _bounded_sequence(
    values: Any,
    *,
    limit: int = _MAX_FIELD,
    max_items: int = _MAX_LIST_ITEMS,
) -> tuple[str, ...]:
    result: list[str] = []
    for item in values or ():
        text = _single_line_text(item, limit)
        if text:
            result.append(text)
        if len(result) >= max_items:
            break
    return tuple(result)
```

相关调用：

- `reports/html_exporter.py:396-403`：`_request_title()` 对 title 调用 `_single_line_text(..., _MAX_TITLE)`，`_MAX_TITLE = 200`。
- `reports/html_exporter.py:299-301`：`data_scope`、`warnings`、`known_limitations` 均通过 `_bounded_sequence(...)` 进入 `ReportView`。
- `reports/html_exporter.py:265`、`:300`：`warnings` 先规范化，追加 `image_notice`/备注提示后再次规范化；最终每项仍为单行、最多 2,000 字符、最多 100 项。

### 3.2 对应测试代码

`tests/test_report_html.py:574-618`：

```python
def test_untrusted_text_fields_are_bounded_and_control_chars_removed() -> None:
    long_text = "x" * 2_500
    snapshot = replace(
        _snapshot(ReportType.PROJECT_SUMMARY),
        warnings=(f"warning\x00\x01\t{long_text}",),
        data_scope=(f"scope\x02\t{long_text}",),
        known_limitations=(f"limitation\x1f\t{long_text}",),
    )
    request = _request(
        ReportType.PROJECT_SUMMARY,
        title=f"\x00\x01Title{long_text}\nsecond line",
    )

    view = html_exporter.build_report_view_model(snapshot, request)

    assert len(view.title) <= 200
    assert view.title.startswith("Title")
    assert "\n" not in view.title
    assert len(view.warnings) == 1
    assert len(view.warnings[0]) <= 2_000
    assert len(view.data_scope[0]) <= 2_000
    assert len(view.known_limitations[0]) <= 2_000
    for text in (
        view.title,
        *view.warnings,
        *view.data_scope,
        *view.known_limitations,
    ):
        assert "\x00" not in text
        assert "\x01" not in text
        assert "\x02" not in text
        assert "\x1f" not in text
        assert "\t" not in text
        assert "\n" not in text
```

该测试输入覆盖 NUL、SOH、STX、US、TAB、LF；**没有覆盖 CR（`\x0D`）和 DEL（`\x7F`）**。`test_warning_list_is_bounded`（`:610-618`）只验证 100 项上限，不是控制字符测试。

### 3.3 五种字符的实际处理结果

使用只读 helper 探测，输入均为 `a<控制字符>b`（未触及首尾空白剥离）：

| 字符 | 正则阶段 | `_bounded_text()` 结果 | `_single_line_text()` / `_bounded_sequence()` 结果 | 最终 title/warnings/data_scope/known_limitations |
|---|---|---|---|---|
| TAB `\x09` | 不匹配，保留 | `a\tb`（内部保留；首尾会被 `.strip()` 去掉） | `a b`（`\s+` 折叠为空格） | 空格，不含 TAB |
| CR `\x0D` | `\x0b-\x1f`，移除 | `ab` | `ab` | 移除，无空格 |
| LF `\x0A` | 不匹配，保留 | `a\nb`（内部保留；首尾会被 `.strip()` 去掉） | `a b`（折叠为空格） | 空格，不含 LF |
| NUL `\x00` | `\x00-\x08`，移除 | `ab` | `ab` | 移除 |
| DEL `\x7F` | `\x7f`，移除 | `ab` | `ab` | 移除 |

只读探测的实际输出：

```text
CONTROL_PATTERN [\x00-\x08\x0b-\x1f\x7f]
TAB raw= 'a\tb' bounded= 'a\tb' single= 'a b' seq= ('a b',)
CR raw= 'a\rb' bounded= 'ab' single= 'ab' seq= ('ab',)
LF raw= 'a\nb' bounded= 'a\nb' single= 'a b' seq= ('a b',)
NUL raw= 'a\x00b' bounded= 'ab' single= 'ab' seq= ('ab',)
DEL raw= 'a\x7fb' bounded= 'ab' single= 'ab' seq= ('ab',)
```

### 3.4 各字段的实际边界

- **`title`**：`_request_title()` 调用 `_single_line_text(..., 200)`；TAB/LF 折叠为空格，CR/NUL/DEL 被移除；最大 200 字符；空标题回退到“报告类型 · 项目名称”。
- **`warnings`**：`_bounded_sequence(snapshot.warnings)`；每项经 `_single_line_text(..., 2000)`，TAB/LF 折叠为空格，CR/NUL/DEL 移除；最多 100 项；最终 `_bounded_sequence(warnings)` 再规范化一次。
- **`data_scope`**：`_bounded_sequence(snapshot.data_scope)`；同上，单行、最多 2,000 字符、最多 100 项。
- **`known_limitations`**：`_bounded_sequence(snapshot.known_limitations)`；同上，单行、最多 2,000 字符、最多 100 项。

### 3.5 与报告第 58、70 行的核对

报告第 58 行原文：

> 新增统一控制字符正则：移除 C0 控制字符和 DEL（`\x00-\x08`、`\x0b-\x1f`、`\x7f`）。

**结论：不精确。** C0 控制字符的范围包含 TAB（`\x09`）和 LF（`\x0A`），但正则明确排除了它们，`_bounded_text()` 实际会保留内部 TAB/LF（仅 `strip()` 去掉首尾）。准确表述应为：

> 移除 C0 中除 TAB/LF 外的字符（`\x00-\x08`、`\x0b-\x1f`）以及 DEL（`\x7f`）；TAB/LF 随后由 `_single_line_text()` 折叠为空格。

报告第 70 行原文：

> `test_untrusted_text_fields_are_bounded_and_control_chars_removed`：验证标题、警告、数据范围、已知限制的长度上限，以及 NUL、SOH、STX、US、TAB、换行等控制字符被清理。

**结论：基本准确，但不完整。** 测试确实覆盖 NUL、SOH、STX、US、TAB、LF，并断言最终 View 字段不含 TAB/LF；但：

- 测试没有覆盖 CR 和 DEL；
- 对 TAB/LF，所谓“清理”实际发生在 `_single_line_text()` 的空白折叠阶段，而不是正则移除阶段；
- 报告没有说明该测试是“最终 View 层规范化”而非原始字符串删除。

本次仅记录上述差异，**不修改报告、源码或测试**。

## 4. 只读检查结果

- 未修改 `reports/html_exporter.py`、`tests/test_report_html.py`、`docs/PHASE6_C2A_SECURITY_FIX_1.md`。
- 未打开、查询或写入 SQLite 数据库；未执行 Schema 操作。
- 未运行 pytest；未创建测试临时文件或输出报告。
- 仅执行了不写文件的 Python `-B` helper 探测，以及源码/测试/报告只读检查。
- 唯一新增文件：`docs/PHASE6_C2A_SECURITY_FIX_1_REVIEW_EVIDENCE.md`。

## 5. 复核结论

- **SEC-01**：实现采用 `os.link()` 原子排他发布，代码层面符合 fail-closed 目标；测试能证明“目标由模拟竞争者先创建后，exporter 不覆盖”，但**没有真实双写入者并发测试**。该结论不应被表述为“已通过并发压力验证”。
- **SEC-04**：实现对 TAB、CR、LF、NUL、DEL 的行为与上表一致；`title`、`warnings`、`data_scope`、`known_limitations` 的最终 View 字段不含 TAB/LF，CR/NUL/DEL 被移除，长度和列表项数受限。报告第 58 行需要更精确的措辞；第 70 行需要补充“测试未覆盖 CR/DEL，TAB/LF 是折叠而非正则删除”的限定。
- 未发现需要立即修改源码的新的高风险问题；本报告不构成修复。
