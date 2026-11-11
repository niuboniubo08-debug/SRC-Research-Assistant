# Phase 6C-2A-R1：叶节点 Symlink 安全修复方案调查

**项目：** `D:\挖漏洞\SRC-Research-Assistant`  
**阶段：** Phase 6C-2A-R1（只读调查，不实施修复）  
**日期：** 2026-11-07  
**当前版本：** 0.5.0  
**数据库 Schema：** v5  
**调查对象：** `reports/html_exporter.py`、`tests/test_report_html.py`、`app/config.py`、`ui/report_page.py`  
**调查方式：** 阅读实际源码和现有测试；未修改生产代码、测试、数据库、Schema、模板或 GUI；未运行完整测试回归；未开始 Phase 6C-2B。

---

## 0. 结论摘要

```text
R1_INVESTIGATION = completed
RECOMMENDED_FIX = RAW_LEAF_REJECT + NO_LEAF_RESOLVE
C2B = not started
STEP_2_READINESS = READY_WITH_LIMITATIONS
```

当前问题的根因是：`write_html_report()` 在检查叶节点之前先执行：

```python
target = (root / target_name).resolve()
```

`Path.resolve()` 会跟随文件 symlink。对于内部 symlink：

```text
reports_dir/alias.html -> reports_dir/target.html
```

`target` 变成 `target.html`，后续 containment、存在性检查、`os.replace()`/`os.link()` 全部作用于目标文件。因此：

- `overwrite=True` 可覆盖内部 symlink 的目标文件；
- `overwrite=False` 对已存在目标会失败关闭，但断链 symlink 会在缺失目标路径创建文件；
- 目标如果是同目录的非 HTML 文件，只校验 `alias.html` 的后缀，仍可能被替换；
- 外部目标 symlink 目前会被 containment 拒绝，但拒绝发生在 `resolve()` 之后，不是“先识别原始叶节点”。

建议的最小修复是：

1. 在调用 `resolve()` 之前，用原始叶节点 `root / target_name` 做 symlink/junction 检查；
2. 对已存在 symlink、断链 symlink、外部 symlink 一律拒绝；
3. 不再把解析后的目标路径作为写入目标；使用已经验证过的原始叶节点路径；
4. 保留现有 containment 与普通文件 overwrite 语义；
5. 明确保留 TOCTOU 残余，不声称完全安全。

该方案可进入步骤二实施，但必须先接受“最小路径检查不等于 TOCTOU 完全关闭”的限制。

---

## 1. 调查范围与约束

### 1.1 已阅读

- `reports/html_exporter.py`：`write_html_report()`、`_resolve_reports_root()`、`_validate_filename()`、`_atomic_write()`、`_publish_exclusive()`；
- `tests/test_report_html.py`：现有普通文件、覆盖、路径逃逸、junction、root symlink、竞态、无硬链接、清理测试；
- `app/config.py`：`reports_dir` 配置来源；
- `ui/report_page.py`：报告中心仍是占位页；
- `docs/PHASE6_C2A_R_C2B_SECURITY_GATE.md`：上一轮的内部 symlink 风险结论。

### 1.2 本轮禁止

- 修改生产代码；
- 修改测试文件；
- 修改数据库或 Schema；
- 修改 HTML 模板或 GUI；
- 安装依赖；
- 执行完整测试回归；
- 开始 Phase 6C-2B；
- 实施任何实际修复。

### 1.3 本轮实际状态

- 未修改 `reports/html_exporter.py`；
- 未修改 `tests/test_report_html.py`；
- 未打开或写入数据库；
- 未运行 pytest；
- 未创建或写入任何报告输出文件；
- 仅新增本调查报告。

---

## 2. 当前真实代码执行路径

### 2.1 调用顺序

`write_html_report()` 位于 `reports/html_exporter.py:327-372`，顺序如下：

| 顺序 | 代码位置 | 行为 |
|---|---|---|
| 1 | `reports/html_exporter.py:341-342` | 校验 `request` 类型 |
| 2 | `:343` | `render_html()` 渲染 HTML 字符串 |
| 3 | `:344` | `_resolve_reports_root()` 解析并验证 `reports_dir` |
| 4 | `:345` | `_validate_filename()` 校验文件名 |
| 5 | `:346` | `target = (root / target_name).resolve()` |
| 6 | `:347-350` | `target.relative_to(root)` containment |
| 7 | `:351-352` | `target.parent != root` 检查 |
| 8 | `:353-354` | 目标存在且 `overwrite=False` → `FileExistsError` |
| 9 | `:355-356` | 目标存在且是目录 → `ValidationError` |
| 10 | `:358-359` | UTF-8 编码、计算 SHA-256 |
| 11 | `:360` | `_atomic_write(target, payload, overwrite=overwrite)` |
| 12 | `:362-372` | 构造 `ReportArtifact`，`path=str(target)` |

### 2.2 关键源码

`reports/html_exporter.py:344-360`：

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
    raise FileExistsError(f"目标报告已存在，未覆盖: {target}")
if target.exists() and target.is_dir():
    raise ValidationError("报告目标不是文件")

payload = html.encode("utf-8")
sha256 = hashlib.sha256(payload).hexdigest()
_atomic_write(target, payload, overwrite=overwrite)
```

`reports/html_exporter.py:627-640`：

```python
def _resolve_reports_root(reports_dir: str | Path) -> Path:
    root = Path(reports_dir).expanduser()
    if not root.is_absolute():
        raise ValidationError("报告输出目录必须是绝对路径")
    if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
        raise ValidationError("报告输出目录不能是符号链接或 junction")
    root = root.resolve()
    ...
    return root
```

`reports/html_exporter.py:643-662`：

```python
def _validate_filename(filename: str) -> str:
    name = str(filename).strip()
    ...
    if any(char in name for char in ("/", "\\", ":")):
        raise ValidationError("报告文件名不能包含路径分隔符")
    ...
    if not name.lower().endswith(".html"):
        raise ValidationError("HTML 报告文件名必须以 .html 结尾")
    ...
    return name
```

`reports/html_exporter.py:701-736`：

```python
def _atomic_write(target: Path, payload: bytes, *, overwrite: bool) -> None:
    ...
    if overwrite:
        os.replace(temporary, target)
        temporary = None
    else:
        _publish_exclusive(temporary, target)
        ...
```

### 2.3 为什么当前路径会跟随 symlink

`target = (root / target_name).resolve()` 是“解析后的目标”，不是“用户传入的原始叶节点”。

如果 `target_name` 是 `alias.html`，而磁盘上：

```text
reports_dir/
  alias.html -> target.html
  target.html
```

则：

```text
root / "alias.html"          = reports_dir/alias.html
(root / "alias.html").resolve() = reports_dir/target.html
```

之后所有代码都认为目标是 `target.html`。`alias.html` 本身没有被检查，也没有被保留为写入路径。

---

## 3. 内部 symlink 与断链 symlink 的风险原因

### 3.1 内部 symlink，目标存在

场景：

```text
reports_dir/
  alias.html -> target.html
  target.html  (普通 HTML 文件)
```

调用 `filename="alias.html"`：

| 步骤 | 结果 |
|---|---|
| `target = alias.html.resolve()` | `target.html` |
| `target.relative_to(root)` | 通过（target 在 root 内） |
| `target.parent != root` | 通过（直接位于 root） |
| `overwrite=False` | `target.exists()` 为真 → `FileExistsError`，不写 |
| `overwrite=True` | 检查通过 → `os.replace(temp, target.html)` |
| 实际效果 | `target.html` 被替换；`alias.html` 仍是 symlink |
| `ReportArtifact.path` | `target.html`，不是 `alias.html` |

因此 `overwrite=True` 会覆盖**另一个文件**；如果目标不是 HTML 文件（例如 `secret.txt`），只校验了 `alias.html` 的 `.html` 后缀，目标文件仍可被替换。这是非预期覆盖的核心原因。

**风险类型：** 本地数据完整性 / 非预期覆盖。  
**分类：** 静态代码确认（`Path.resolve()` 已定义语义）；动态未验证。

### 3.2 断链 symlink

场景：

```text
reports_dir/
  alias.html -> missing.html
  missing.html  (不存在)
```

调用 `filename="alias.html"`：

| 步骤 | 结果 |
|---|---|
| `target = alias.html.resolve()` | `missing.html`（`strict=False` 下返回缺失目标路径） |
| `target.relative_to(root)` | 通过 |
| `target.parent != root` | 通过 |
| `target.exists()` | `False` |
| `overwrite=False` | `_publish_exclusive()` 使用 `os.link(temp, missing.html)` |
| 实际效果 | `missing.html` 被创建；`alias.html` 从断链变为有效链接 |
| 覆盖已有文件 | 否 |
| 非预期行为 | 是：调用方传入 `alias.html`，实际创建的是 `missing.html` |

断链 symlink 不造成“覆盖已有文件”，但会把写入重定向到另一个名字，且在没有 `missing.html` 的情况下创建它。对报告目录而言，这不是预期的“拒绝断链”行为。

**风险类型：** 非预期目标创建 / 路径重定向。  
**分类：** 静态代码确认；动态未验证。

### 3.3 外部文件 symlink

场景：

```text
reports_dir/escape.html -> outside/secret.html
```

当前代码：

```text
target = escape.html.resolve()  -> outside/secret.html
target.relative_to(root)        -> ValueError
-> ValidationError，不写入
```

因此外部目标当前**不会**被写入；这是现有 containment 的作用。但拒绝发生在 `resolve()` 之后，意味着代码已经跟随了 symlink，只是最终因 containment 失败而停止。对安全边界而言，应该先识别并拒绝原始叶节点，而不是依赖后续 containment。

### 3.4 普通目录

场景：

```text
reports_dir/name.html  (真实目录)
```

当前语义：

- `target.exists()` 为真；
- `overwrite=False` → 先抛 `FileExistsError`；
- `overwrite=True` → `target.is_dir()` 为真 → `ValidationError`；
- 两条路径都不写入文件。

新增叶节点检查不能改变这两个结果；普通目录不是 symlink/junction，应继续由现有顺序处理。

### 3.5 风险分类汇总

| 原始叶节点 | `resolve()` 结果 | containment | 当前 `overwrite=False` | 当前 `overwrite=True` | 需要的处理 |
|---|---|---|---|---|---|
| 普通文件，存在 | 同一文件 | 通过 | `FileExistsError` | 替换文件 | 保持原语义 |
| 普通文件，不存在 | 同一路径 | 通过 | 创建 | 创建 | 保持原语义 |
| 普通目录 | 同一目录 | 通过 | `FileExistsError` | `ValidationError` | 保持原语义 |
| 内部文件 symlink，目标存在 | 目标文件 | 通过 | `FileExistsError` | 替换目标文件 | **拒绝** |
| 内部文件 symlink，目标缺失 | 缺失目标 | 通过 | 创建目标 | 创建目标 | **拒绝** |
| 外部文件 symlink | root 外目标 | 拒绝 | 拒绝 | 拒绝 | **先拒绝原始叶节点** |
| 内部目录 symlink/junction | 目标目录 | 视目标而定 | 可能 `FileExistsError` | 可能 `ValidationError` | **拒绝** |
| symlink 链/循环 | 最终目标或异常 | 视结果而定 | 未统一捕获 | 未统一捕获 | 拒绝或失败关闭 |

---

## 4. Python 3.14.4 / Windows 下的可靠性评估

### 4.1 `Path.is_symlink()`

- 基于 `lstat` 语义，不跟随最终 symlink；
- 对**断链 symlink**返回 `True`，这是关键：必须在 `exists()` 之前检查；
- 对普通文件、普通目录返回 `False`；
- Windows 文件 symlink 可识别；
- 对 junction 通常返回 `False`，因此不能只依赖它。

### 4.2 `Path.is_junction()`

- Python 3.12+ 提供；当前 Python 3.14.4 可用；
- 对 Windows directory junction 返回 `True`；
- 对 symlink 通常返回 `False`；
- 应与 `is_symlink()` 同时检查；
- 若未来兼容更旧 Python，使用：

```python
getattr(path, "is_junction", lambda: False)()
```

当前 `_resolve_reports_root()` 已经使用这个兼容写法（`reports/html_exporter.py:631`），可以复用同一风格。

### 4.3 `Path.exists()`

- 跟随 symlink；
- 对断链 symlink 返回 `False`；
- 因此不能把 `exists()` 当作“叶节点是否存在”的 symlink 检查；
- 在新增检查中必须位于 symlink/junction 检查之后。

### 4.4 `Path.resolve()`

- 跟随 symlink/junction；
- 对内部 symlink 返回目标路径；
- 对断链 symlink（`strict=False`）返回缺失目标路径；
- 对循环可能抛出 `OSError`/`RuntimeError`，当前代码没有统一捕获；
- 因此**不能作为第一道叶节点安全检查**。

### 4.5 本会话限制

本会话 Python 无 `SeCreateSymbolicLinkPrivilege`；上一轮受控探测得到：

```text
OSError [WinError 1314] 客户端没有所需的特权
```

因此本报告无法动态创建文件 symlink 并执行 exporter。所有 symlink 行为结论是**静态代码结论**，不是动态测试结论。动态行为继续保持 **UNKNOWN**。

---

## 5. 建议的最小修复方案

### 5.1 目标

在不改变普通文件行为、不增加依赖的前提下：

1. 在 `resolve()` 之前识别原始叶节点；
2. 拒绝已有 symlink（包括断链）；
3. 拒绝 junction/目录 reparse；
4. 不允许写入 `resolve()` 跟随后的目标；
5. 保留 containment 检查；
6. 保留普通文件的 `overwrite=True/False` 语义。

### 5.2 推荐代码形态（未实施）

在 `write_html_report()` 中，将当前 `reports/html_exporter.py:345-346`：

```python
target_name = _validate_filename(filename or _default_filename(snapshot))
target = (root / target_name).resolve()
```

改为：

```python
target_name = _validate_filename(filename or _default_filename(snapshot))
candidate = root / target_name
if candidate.parent != root:
    raise ValidationError("报告目标必须直接位于 reports_dir")

try:
    is_link_like = candidate.is_symlink() or getattr(
        candidate, "is_junction", lambda: False
    )()
except OSError as exc:
    raise ValidationError("无法确认报告目标类型") from exc

if is_link_like:
    raise ValidationError("报告目标不能是符号链接或 junction")

# 不再对叶节点调用 resolve()；root 已在 _resolve_reports_root() 中解析。
target = candidate
```

后续保持：

```python
target.relative_to(root)
if target.parent != root:
    raise ValidationError("报告目标必须直接位于 reports_dir")
if target.exists() and not overwrite:
    raise FileExistsError(...)
if target.exists() and target.is_dir():
    raise ValidationError("报告目标不是文件")
_atomic_write(target, payload, overwrite=overwrite)
```

### 5.3 为什么使用原始 `candidate` 作为写入目标

如果先检查 `candidate`，再调用 `candidate.resolve()`，仍会在“检查完成、解析开始”之间留下一次跟随窗口；而且一旦解析，写入的是目标路径，不是原始叶节点。

使用 `target = candidate` 的好处：

- 正常文件：`candidate` 已经是 `root` 下的绝对路径，行为不变；
- 内部 symlink：在写入前已被拒绝，不会进入 `_atomic_write()`；
- 断链 symlink：`is_symlink()` 为真，拒绝，不会创建缺失目标；
- 外部 symlink：在原始叶节点检查阶段就拒绝，同时保留 containment 作为第二道检查；
- 普通目录：仍由后续 `exists`/`is_dir` 分支处理；
- 不需要新增第三方依赖，不改变 `_atomic_write()` 接口。

### 5.4 错误语义

建议统一使用 `ValidationError`：

```text
报告目标不能是符号链接或 junction
```

理由：

- 这是路径/目标类型校验失败，不是“文件已存在”；
- 与 `_resolve_reports_root()` 的 root symlink/junction 错误风格一致；
- 不应向调用方暴露目标真实路径；
- 不把内部 symlink 和外部 symlink 分成两个写路径，统一拒绝。

### 5.5 不改变普通文件覆盖语义

新增检查对普通文件全部返回 `False`：

- 普通文件存在，`overwrite=False`：仍在 `:353-354` 抛 `FileExistsError`；
- 普通文件存在，`overwrite=True`：仍由 `:360` 的 `_atomic_write()` 替换；
- 普通文件不存在，`overwrite=False`：仍由 `_publish_exclusive()` 创建；
- 普通目录存在：仍在 `overwrite=False` 时 `FileExistsError`，`overwrite=True` 时 `ValidationError`。

唯一变化的输入是 symlink/junction：从“可能跟随/覆盖”变为“拒绝”，这是修复目标。

### 5.6 不能声称完全安全

这个最小方案解决的是**静态内部/断链 symlink 路径**，不解决以下问题：

- 检查与发布之间的 TOCTOU；
- 父级 reparse point；
- 检查后叶节点被替换成 symlink；
- 强制终止/清理失败；
- Windows 设备名实际运行时行为；
- 其他 reparse point 类型（非 symlink/junction）。

因此修复后仍应保留 `PASS_WITH_LIMITATIONS`，不能宣称“任意 symlink 已完全安全”。

---

## 6. 需要修改的具体函数与代码位置

### 6.1 生产代码（步骤二才实施）

| 文件/函数 | 当前行 | 计划 |
|---|---|---|
| `reports/html_exporter.py` / `write_html_report()` | `:344-346` | 新增原始 `candidate` 计算、`is_symlink()`/`is_junction()` 检查、拒绝 `ValidationError` |
| `reports/html_exporter.py` / `write_html_report()` | `:346` | 不再将叶节点 `resolve()` 结果作为写入目标 |
| `reports/html_exporter.py` / `write_html_report()` | `:347-356` | 保留 containment/parent/exists/dir 检查 |
| `reports/html_exporter.py` / `_resolve_reports_root()` | `:627-640` | 不修改；root 已在进入叶节点前解析并校验 |
| `reports/html_exporter.py` / `_validate_filename()` | `:643-662` | 不修改；仍负责名称/保留名/非法字符 |
| `reports/html_exporter.py` / `_atomic_write()` | `:701-736` | 不修改；继续接收已验证的 `target` |
| `reports/html_exporter.py` / `_publish_exclusive()` | `:675-698` | 不修改；继续负责 `overwrite=False` 的硬链接排他发布 |

### 6.2 测试文件（步骤二才实施）

| 文件/位置 | 计划 |
|---|---|
| `tests/test_report_html.py` 约 `:489` 附近 | 新增文件 symlink 辅助函数，创建失败时 `pytest.skip` |
| `tests/test_report_html.py` 约 `:579` 之前 | 新增内部 symlink、断链、外部 symlink 测试 |
| 现有 `:398-425` | 保留普通文件覆盖语义测试，不改断言 |
| 现有 `:428-444` | 保留路径逃逸/非 HTML 测试 |
| 现有 `:447-473` | 保留失败替换/临时文件清理测试 |
| 现有 `:502-516` | 保留正常目录导出测试 |
| 现有 `:520-576` | 保留 root junction/root symlink/外部 junction 测试 |
| 现有 `:579-634` | 保留竞态、无硬链接失败关闭测试 |

---

## 7. 测试增补清单

### 7.1 辅助函数

建议新增：

```python
def _make_file_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"当前环境无法创建 Windows 文件符号链接: {exc}")
    assert link.is_symlink()
```

注意：

- 不在 `_make_file_symlink_or_skip()` 里写生产目录；
- 只用 `tmp_path`；
- 创建失败时 skip，不把 skip 计为 PASS；
- 与现有 `_make_windows_junction()` 的 skip 风格一致。

### 7.2 必增测试

| 测试名（建议） | 场景 | 断言 |
|---|---|---|
| `test_internal_file_symlink_leaf_is_rejected` | `alias.html -> target.html`，目标存在 | `ValidationError`；`target.html` 原内容不变；`alias.html` 仍是 symlink；无临时文件 |
| `test_broken_symlink_leaf_is_rejected` | `alias.html -> missing.html` | `ValidationError`；`missing.html` 不存在；`alias.html` 仍为断链；不会创建目标 |
| `test_external_file_symlink_leaf_is_rejected` | `escape.html -> outside/secret.html` | `ValidationError`；外部文件内容不变；无外部写入 |
| `test_directory_symlink_leaf_is_rejected`（可选） | `alias.html -> 目录` | `ValidationError`；目录没有新增文件 |

内部/断链测试建议参数化：

```python
@pytest.mark.parametrize("overwrite", [False, True])
```

这样同时覆盖：

- `overwrite=False`：旧行为是 `FileExistsError` 或创建缺失目标；新行为统一 `ValidationError`；
- `overwrite=True`：旧行为会覆盖/创建目标；新行为拒绝且目标不变。

### 7.3 不应重复添加的测试

以下现有测试已经覆盖，不应改写断言：

- 普通文件 `overwrite=False` 拒绝、`overwrite=True` 覆盖：`tests/test_report_html.py:398-425`；
- 路径逃逸/非 HTML：`:428-444`；
- 替换失败保留旧文件：`:447-473`；
- 正常目录导出：`:502-516`；
- root junction 拒绝：`:520-534`；
- root symlink 拒绝（环境允许时）：`:537-556`；
- 外部 junction 叶节点拒绝：`:560-576`；
- `overwrite=False` 竞态：`:579-606`；
- 无硬链接失败关闭：`:609-634`；
- `KeyboardInterrupt` 清理：`:637-663`。

### 7.4 测试数量与运行策略

步骤二建议：

1. 先运行 `tests/test_report_html.py` 定向测试；
2. 再运行报告模块相关测试；
3. 最后按项目既定隔离临时目录方式运行完整回归；
4. 报告实际 passed/failed/skipped，不把 skip 计为 PASS；
5. 本步骤不运行任何测试，不减少现有测试数量。

---

## 8. 普通文件覆盖语义兼容性分析

| 场景 | 当前行为 | 修复后行为 | 是否兼容 |
|---|---|---|---|
| 普通文件存在，`overwrite=False` | `FileExistsError` | `FileExistsError` | 是 |
| 普通文件存在，`overwrite=True` | 替换文件 | 替换文件 | 是 |
| 普通文件不存在，`overwrite=False` | 硬链接排他创建 | 硬链接排他创建 | 是 |
| 普通文件不存在，`overwrite=True` | `os.replace` 创建 | `os.replace` 创建 | 是 |
| 普通目录存在，`overwrite=False` | `FileExistsError` | `FileExistsError` | 是 |
| 普通目录存在，`overwrite=True` | `ValidationError` | `ValidationError` | 是 |
| 内部文件 symlink，目标存在 | `overwrite=True` 覆盖目标 | `ValidationError` | **有意不兼容（修复）** |
| 断链 symlink | `overwrite=False` 创建目标 | `ValidationError` | **有意不兼容（修复）** |
| 外部 symlink | containment 拒绝 | 原始叶节点检查即拒绝 | 安全结果相同；错误阶段更早 |
| 普通目录 symlink/junction | 取决于目标目录 | `ValidationError` | **有意拒绝** |

结论：普通文件/普通目录的既有语义保持不变；只有 symlink/junction 输入从“可能跟随”变为“拒绝”。

---

## 9. TOCTOU 与未解决限制

### 9.1 最小方案的 TOCTOU 窗口

即使加入原始叶节点检查，仍有窗口：

```text
T1: candidate.is_symlink() / is_junction() == False
T2: candidate.exists()
T3: _atomic_write() 打开临时文件
T4: os.replace(temp, target) 或 os.link(temp, target)
```

在 T1 与 T4 之间，攻击者可以：

- 把普通文件替换成 symlink；
- 把普通目录替换成 junction；
- 替换父目录（root 的父级 reparse point）；
- 在 `overwrite=True` 下替换目标路径。

### 9.2 为什么不在本方案中完全关闭

- Python 标准库的 `os.replace`/`os.link` 没有跨平台统一的“按目录句柄、不跟随叶节点”的 rename API；
- Windows 上要可靠关闭，需要 `CreateFileW`/`SetFileInformationByHandle` 等句柄级操作，复杂度和兼容性成本超出最小修复；
- 使用 `pathlib` 的“检查再写入”本质上仍是 check-then-use；
- 在不增加第三方依赖、不改变写入接口的约束下，无法宣称完全关闭。

### 9.3 本方案仍保留的限制

1. 检查后叶节点被替换的 TOCTOU；
2. 父级 reparse point 未检查；
3. symlink 链/循环的异常类型未统一；
4. `Path.is_junction()` 之外的其他 reparse point 类型；
5. Windows 设备名实际运行时行为仍 UNKNOWN；
6. 强制终止/清理失败；
7. 真实双进程并发测试仍缺失。

### 9.4 可后续加固的方向（不在本步骤实施）

- 使用目录句柄/`O_NOFOLLOW` 等平台能力做无跟随发布；
- 发布前对目标做 `lstat` 二次校验（仍非完全 TOCTOU 关闭）；
- 以独占随机临时文件名 + 原子发布替代可预测文件名；
- 对父级 reparse point 做完整检查；
- 在具备 symlink 权限的隔离环境中做动态测试。

---

## 10. 实际修改文件清单

### 10.1 本轮新增

```text
docs/PHASE6_C2A_R1_INVESTIGATION.md
```

本报告没有自引用哈希；最终文件大小和 SHA-256 见交付回执。

### 10.2 本轮修改

**无。**

### 10.3 未修改

```text
reports/html_exporter.py
  24,132 bytes
  SHA-256 593E4F67928BAEF698BC52111BB19C868D28F3AB574617A50916C77159BE7C18

tests/test_report_html.py
  23,880 bytes
  SHA-256 72755296ED04E1E070AF9A30A418D6E8BCDE7FBF665215E0375F5EC39ACD5C42
```

同时未修改：

- 数据库：`storage/src_research.db`
- 验收数据库：`storage/phase5_acceptance/acceptance.db`
- Schema：`database/schema.py`
- HTML 模板：`reports/templates/*.html`
- GUI：`ui/*`
- 配置：`app/config.py`

### 10.4 声明

**本轮没有修改生产代码、测试文件、数据库或 Schema；没有安装依赖；没有运行完整测试回归；没有开始 Phase 6C-2B；没有实施任何实际修复。**

---

## 11. 最终结论与步骤二条件

### 11.1 结论

```text
STEP_2_READINESS = READY_WITH_LIMITATIONS
```

具备进入步骤二的条件，但结论不是“修复已完成”，而是：

- 已定位当前代码路径；
- 已确认内部 symlink/断链 symlink 的静态风险；
- 已给出最小、可测试、无依赖的修复方案；
- 已明确普通文件覆盖语义保持不变；
- 已明确 TOCTOU 无法在本轮完全解决。

### 11.2 进入步骤二的前提

1. 接受“先检查原始叶节点、再拒绝 symlink/junction、使用原始 candidate 作为 target”的最小方案；
2. 保留 `containment` 检查；
3. 不改变普通文件的 `overwrite=True/False` 语义；
4. 测试中 symlink 创建失败必须 skip，不能伪造 PASS；
5. 报告中继续保留 TOCTOU/父级 reparse/设备名等 UNKNOWN；
6. 步骤二只实施该最小修复，不扩展到 C2B 或并发导出。

### 11.3 明确不能承诺的事项

- 不能承诺“所有 symlink 已完全安全”；
- 不能承诺“TOCTOU 已关闭”；
- 不能承诺“内部 symlink 已动态验证”；
- 不能把本调查报告当作生产代码已修复；
- 不能在没有人工审核的情况下开始步骤二。

**本报告完成后立即停止，等待人工审核；未开始步骤二，未开始 Phase 6C-2B。**
