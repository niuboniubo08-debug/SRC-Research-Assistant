# Phase 6C-2A-R：C2B 前安全边界确认

**项目：** `D:\挖漏洞\SRC-Research-Assistant`  
**阶段：** Phase 6C-2A-R（只读确认）  
**日期：** 2026-11-07  
**当前版本：** 0.5.0  
**数据库 Schema：** v5  
**审查对象：** `reports/html_exporter.py`、`docs/PHASE6_C2A_SECURITY_DEBT.md`、`app/config.py`、`ui/report_page.py`、现有报告架构  
**审查方式：** 实际源码阅读 + 受控临时目录路径探测；未运行完整测试回归，未修改生产代码、测试、数据库、Schema、HTML 模板或 GUI。

---

## 0. 结论摘要

```text
C2B_SECURITY_GATE = CONDITIONAL_GO
INTERNAL_SYMLINK_OVERWRITE_RISK = CONFIRMED_STATIC
INTERNAL_SYMLINK_DYNAMIC = UNKNOWN
C2B_OUTPUT_DIR = FIXED_APP_CONFIG_REPORTS_DIR
C2B_CONCURRENCY = SERIAL_REQUIRED
DEBT_09_CORRECTION = DONE
C2B_STARTED = FALSE
```

结论不是无条件通过：

1. `write_html_report()` 先执行 `target = (root / target_name).resolve()`，因此 **reports_dir 内部的文件 symlink 会被解析为其目标文件**；`overwrite=True` 时实际 `os.replace()` 的是目标文件，而不是 symlink 本身。
2. 因此存在一个**静态确认的非预期覆盖路径**：`alias.html` 指向同目录的 `other.html`（甚至同目录的非 HTML 文件）时，`overwrite=True` 会覆盖 `other.html` / 目标文件，而 `alias.html` 仍是 symlink；调用方传入的是 `alias.html`，最终 artifact 路径却是目标文件。
3. 当前无法在本会话创建文件 symlink：受控探测返回 `WinError 1314`，与既有 symlink 测试 skip 原因一致。因此上述结论是**静态代码确认**，不是动态通过；动态 symlink 行为仍为 **UNKNOWN**。
4. C2B 可以保持固定 `AppConfig.reports_dir`，不需要用户自定义完整输出路径；但只有在**固定目录、应用生成文件名、默认 `overwrite=False`、单写者/串行导出**的约束下，才建议启动 C2B。
5. 如果 C2B 暴露用户自定义文件名、完整路径或 `overwrite=True`，或允许并发写同一目标，则应在启动前先修复叶节点 symlink 处理；不能把当前状态写成“symlink 已安全”。

---

## 1. 审查范围与约束

### 1.1 本轮允许

- 阅读实际源码、测试、配置、报告文档；
- 在项目外的专用临时目录做受限路径探测；
- 修改 `docs/PHASE6_C2A_SECURITY_DEBT.md` 的 DEBT-09 文档表述；
- 新增本报告。

### 1.2 本轮禁止

- 修改生产代码、测试文件、数据库、Schema、HTML 模板、GUI；
- 运行完整测试回归；
- 开始 C2B；
- 实施安全修复；
- 把 UNKNOWN 写成 PASS。

### 1.3 环境限制

```text
OS: Windows
Python: 3.14.4
文件 symlink 创建: OSError [WinError 1314]（客户端没有所需的特权）
受控探测目录: D:\挖漏洞\pytest_c1r_tmp\c2a_r_probe_*
探测结果: SYMLINK_ERROR，目录已清理
```

本会话没有 `SeCreateSymbolicLinkPrivilege`，因此不能创建文件 symlink，也不能用真实 symlink 端到端执行 `write_html_report()`。本文所有 symlink 结论都明确标注为静态/动态分类。

---

## 2. 实际源码路径

### 2.1 输出目录解析

`reports/html_exporter.py:344`：

```python
root = _resolve_reports_root(reports_dir)
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
    if root.exists() and not root.is_dir():
        raise ValidationError("报告输出目录不是目录")
    ...
    return root
```

- `reports_dir` 必须是绝对路径；
- root 自身若是 symlink/junction，在 `resolve()` 前被拒绝；
- root 解析后必须是目录；
- 这里只检查 root，**不检查报告文件名对应的叶节点**。

### 2.2 目标文件名与路径解析

`reports/html_exporter.py:345-356`：

```python
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
```

关键点：

1. `_validate_filename()` 只验证**传入名称**：是否带路径分隔符、是否 `.html`、是否 Windows 保留名、长度/控制字符等；它不检查该名称在磁盘上是不是 symlink。
2. `(root / target_name).resolve()` 会跟随叶节点 symlink，返回**目标文件的真实路径**。
3. `target.relative_to(root)` 和 `target.parent != root` 只做 containment/直接子文件检查；内部 symlink 的目标若也在 root 且直接位于 root，会通过。
4. 后续 `target` 是解析后的目标路径，不是原始 symlink 路径。

### 2.3 两条发布路径

`reports/html_exporter.py:360`：

```python
_atomic_write(target, payload, overwrite=overwrite)
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

- `overwrite=True`：`os.replace()` 直接替换 `target`；
- `overwrite=False`：`_publish_exclusive()` 使用 `os.link()`，目标已存在时原子失败（`reports/html_exporter.py:675-698`）。

由于 `target` 已经 `resolve()`，两条路径都作用于**symlink 的目标文件**，不是 `alias.html` 本身。

---

## 3. 内部文件 symlink 的真实代码行为

### 3.1 场景定义

设：

```text
reports_dir/
  alias.html       -> target.html       (同一目录内的文件 symlink)
  target.html      (普通 HTML 文件，已存在)
```

调用：

```python
write_html_report(..., reports_dir=reports_dir, filename="alias.html")
```

### 3.2 逐项回答

#### 问题 1：`resolve()` 返回什么路径？

`target = (root / "alias.html").resolve()` 返回：

```text
<reports_dir>/target.html
```

即 symlink 的目标文件路径；不是 `alias.html` 路径。

**分类：STATIC_CONFIRMED**（Python `Path.resolve()` 的已定义行为；本会话无法动态创建 symlink）。

#### 问题 2：containment 检查是否通过？

- `target.relative_to(root)`：`target.html` 在 root 内，通过；
- `target.parent != root`：目标直接位于 root，通过；
- `target.exists()`：为 `True`；
- `target.is_dir()`：为 `False`。

因此 internal file symlink 会通过路径检查。

**分类：STATIC_CONFIRMED**。

#### 问题 3：实际写入的是 symlink 本身还是其目标文件？

实际写入 `target.html`，不是 `alias.html`：

- `overwrite=True`：`os.replace(temporary, target.html)`；`target.html` 内容被替换；
- `alias.html` 仍然是 symlink，继续指向 `target.html`；
- `ReportArtifact.path` 返回的是 `str(target)`，即 `target.html`，不是调用方传入的 `alias.html`（`reports/html_exporter.py:369`）。

**分类：STATIC_CONFIRMED**。

#### 问题 4：`overwrite=True` 是否可能替换目标文件？

**是。**

代码路径：

```text
target = alias.html.resolve()              -> target.html
target.exists() == True
overwrite == True                          -> 不抛 FileExistsError
target.is_dir() == False
_atomic_write(target.html, overwrite=True)
  -> os.replace(temp, target.html)         -> 目标文件被替换
```

因此：

- 若 `target.html` 是另一个报告，会被覆盖；
- 若 symlink 指向同目录的非 HTML 文件（如 `secret.txt`），`_validate_filename()` 只检查 `alias.html` 的 `.html` 后缀，仍可覆盖 `secret.txt`；
- symlink 本身不会被替换，目标文件被替换后 symlink 仍有效。

**分类：STATIC_CONFIRMED；这是非预期覆盖风险。**

#### 问题 5：`overwrite=False` 是否可能产生非预期行为？

分两种情况：

**A. 目标文件存在**

```text
target.exists() == True
overwrite == False
-> raise FileExistsError
```

不写入、不替换，失败关闭。这是安全行为。

**B. 断链 symlink（目标不存在）**

```text
alias.html -> missing.html
target = missing.html.resolve()
target.exists() == False
overwrite == False
-> _publish_exclusive(temp, missing.html)
   -> os.link(temp, missing.html)
```

结果是：

- 不覆盖已有文件；
- 但会在 `missing.html` 路径创建新文件；
- `alias.html` 从断链变成有效链接；
- 最终 artifact 路径是 `missing.html`，不是 `alias.html`。

这不是“覆盖”，但属于**非预期的目标文件创建/路径重定向**，应在 C2B 中避免把用户提供的 symlink 名当作普通文件名。

**分类：STATIC_CONFIRMED；无覆盖，但有非预期创建。**

### 3.3 其他叶节点形态

| 叶节点形态 | `resolve()` 结果 | containment | `overwrite=False` | `overwrite=True` |
|---|---|---|---|---|
| 内部文件 symlink，目标存在 | 目标文件（root 内） | PASS | `FileExistsError`，不写 | 覆盖目标文件 |
| 内部文件 symlink，目标缺失（断链） | 缺失目标路径（root 内） | PASS | 创建缺失目标，alias 变有效 | 创建缺失目标，alias 变有效 |
| 内部 symlink 指向 root 子目录文件 | 子目录文件 | `target.parent != root` → 拒绝 | 拒绝 | 拒绝 |
| 外部文件 symlink | root 外路径 | `relative_to` 失败 → 拒绝 | 拒绝 | 拒绝 |
| 内部目录 symlink | 目录 | PASS | `FileExistsError` | `target.is_dir()` → `ValidationError` |
| 外部目录 junction/symlink | root 外路径 | 拒绝 | 拒绝 | 拒绝 |
| symlink 链/循环 | 最终目标或 `OSError` | 依结果而定 | 未统一捕获 | 未统一捕获 |

表中“内部文件 symlink，目标存在”和“断链”两行是本次重点。

### 3.4 动态验证限制

实际受控探测：

```text
ROOT D:\挖漏洞\pytest_c1r_tmp\c2a_r_probe_...
SYMLINK_ERROR OSError 1314 [WinError 1314]
CLEANED
```

因此：

- **没有**动态执行 internal symlink 的 `write_html_report()`；
- **没有**动态证明 `overwrite=True` 的真实覆盖结果；
- 上述结论来自实际源码路径，不是动态测试；
- 不得把 `INTERNAL_SYMLINK_DYNAMIC` 写成 PASS；
- 既有 `tests/test_report_html.py:537` 的 root symlink 测试同样因 `WinError 1314` skip，不能作为通过证据。

---

## 4. 非预期覆盖风险评估

### 4.1 是否存在风险

**是，限 `overwrite=True`，且叶节点是内部文件 symlink。**

风险链：

1. `reports_dir` 中存在 `alias.html -> target.html`；
2. 调用方传入 `filename="alias.html"`，并允许覆盖；
3. `resolve()` 把目标变成 `target.html`；
4. `os.replace()` 替换 `target.html`；
5. 调用方以为写的是 `alias.html`，实际替换了另一个文件。

### 4.2 影响

- 可能覆盖同一 `reports_dir` 内的另一个报告；
- 可能覆盖同目录的非 HTML 文件（因为只校验 alias 名称后缀，不校验解析后目标的后缀）；
- 不会写到 root 外部：外部目标会在 containment 被拒绝；
- 不会替换 symlink 本身；symlink 仍指向被替换后的目标；
- 单用户本地场景下是数据完整性问题，不是远程代码执行或任意目录写入。

### 4.3 风险等级

**Medium（本地数据完整性）**，前提是 `overwrite=True` 且攻击者/用户能在 `reports_dir` 放置内部 symlink。

`overwrite=False` 对“已存在目标”是失败关闭；断链场景没有覆盖，但会创建目标文件，属于低风险的非预期创建。

### 4.4 是否阻塞 C2B

- 若 C2B 保持 `overwrite=False`、文件名由应用生成、目录固定：**不阻塞**，但必须保留本风险记录；
- 若 C2B 允许用户输入文件名并允许覆盖：**阻塞**，必须先拒绝叶节点 symlink 或改为不跟随叶节点 symlink 的安全发布；
- 不得用“containment 已通过”证明内部 symlink 安全；containment 只证明目标在 root 内，不证明目标身份符合调用方预期。

---

## 5. C2B 输出路径边界

### 5.1 现有配置

`app/config.py:55`：

```python
reports_dir: Path
```

`app/config.py:94`：

```python
reports_dir = _resolve(base, storage.get("reports"), "storage/reports")
```

`app/config.py:118` 将 `reports_dir` 放入 `AppConfig`。

当前实际值：

```text
D:\挖漏洞\SRC-Research-Assistant\storage\reports
```

当前目录只有 `.gitkeep`，没有用户自定义路径字段。

### 5.2 是否存在用户自定义完整路径的必要

**没有。**

- 现有配置已提供固定 `reports_dir`；
- `ui/report_page.py` 仍是 `PlaceholderPage`，没有路径选择器；
- `ui/main_window.py:197` 仍为 `ReportPage()`；
- `ReportService` 尚未接入 `bootstrap`；
- 当前没有报告导出 GUI 或用户路径 API。

因此 C2B 可以、也应该继续使用固定 `AppConfig.reports_dir`。

### 5.3 GUI 文件名边界

建议 C2B：

- 只允许应用生成文件名（例如 `project_<id>_<type>_<snapshot>.html`）；
- 若允许用户输入，只接受 basename，不接受 `/`、`\`、`:`、绝对路径、`..`；
- 继续使用 `_validate_filename()` 的检查；
- 不把 `reports_dir` 暴露为 GUI 输入；
- 不提供“选择任意输出目录”；
- 不对 symlink 文件名作“普通文件名”处理；需要单独拒绝叶节点 symlink。

`_validate_filename()`（`reports/html_exporter.py:643-662`）已经覆盖：

- 路径分隔符；
- `?*<>|"`；
- 控制字符；
- 非 `.html`；
- 超长；
- Windows 保留设备名。

它**没有**覆盖：

- 已存在的内部 file symlink；
- 解析后目标的后缀；
- 目标是否为另一个报告。

### 5.4 路径边界结论

```text
C2B_OUTPUT_DIR = FIXED_APP_CONFIG_REPORTS_DIR
USER_DEFINED_FULL_PATH_REQUIRED = NO
GUI_PATH_SELECTOR_REQUIRED = NO
```

固定目录可以保留；这能避免“任意目录写入”，但不能单独消除内部 symlink 覆盖问题。

---

## 6. 并发导出边界

### 6.1 现有实现

- `write_html_report()` 是同步函数；
- `ui/report_page.py` 没有导出按钮、没有 `QThread`、没有后台报告任务；
- `ReportService` 未接入 `bootstrap`；
- 当前没有“多个导出任务同时写同一目标”的产品路径。

### 6.2 C2B 风险

C2B 若引入 GUI 或后台任务，可能出现：

- 用户重复点击导致两个导出同时进行；
- 两个请求写同一个 `reports_dir` + 文件名；
- `overwrite=True` 下后写者覆盖先写者；
- 内部 symlink 目标被两个请求同时替换；
- 断链 symlink 被两个请求同时创建目标。

### 6.3 结论

```text
C2B_CONCURRENCY = SERIAL_REQUIRED
```

建议：

- 同一 `reports_dir`/目标文件只允许一个 in-flight 导出；
- GUI 在导出期间禁用按钮；
- 使用默认 `overwrite=False`；
- 如必须覆盖，先完成显式确认和叶节点 symlink 拒绝；
- 不把 `overwrite=True` 作为默认或后台自动行为。

`overwrite=False` 的 `os.link()` 发布对“目标已存在”是原子失败；但它不能解决“内部 symlink 目标存在”的语义问题。并发约束不能替代路径安全修复。

---

## 7. DEBT-09 文档修正结果

### 7.1 修改内容

仅修改 `docs/PHASE6_C2A_SECURITY_DEBT.md` 的 DEBT-09：

1. 将 `11.5 尚缺少的验证` 改为 `11.5 验证边界`；
2. 删除“在隔离 Windows 测试环境中验证 `NUL.html` 实际打开行为”的建议；
3. 删除“验证 `Path.exists()`/`os.link()` 对设备名行为”的实际写入建议；
4. 保留校验层测试、名称变体检查和 `UNKNOWN` 说明；
5. `11.6` 删除“可在隔离虚拟机/容器中用受控 API 验证”的设备写入建议；
6. 明确“不要求、也不建议实际写入 `NUL.html`、`CON.html` 等 Windows 保留设备名”；
7. 明确实际设备行为保持 **UNKNOWN**，本轮不安排任何实际设备写入验证。

### 7.2 保留内容

- `tests/test_report_html.py:713-746` 的 14 个参数化非法名称测试仍为校验层 **PASS**；
- `_validate_filename()` 的静态校验仍为 **PASS**；
- 实际 Windows 设备行为仍为 **UNKNOWN**；
- 不声称“设备名运行时已验证”。

### 7.3 修正后的边界

```text
DEBT_09_VALIDATION_LAYER = PASS (existing tests)
DEBT_09_DEVICE_RUNTIME = UNKNOWN
DEBT_09_ACTUAL_DEVICE_WRITE_TEST = NOT_RECOMMENDED / NOT_REQUIRED
```

---

## 8. C2B 是否可以启动

### 8.1 判定

```text
C2B_SECURITY_GATE = CONDITIONAL_GO
```

不是无条件 GO，也不是全面 NO-GO。

### 8.2 允许启动的条件

C2B 必须同时满足：

1. 输出目录固定为 `AppConfig.reports_dir`；
2. 不提供用户自定义完整输出路径；
3. 文件名由应用生成，或只接受经过 `_validate_filename()` 的 basename；
4. 默认 `overwrite=False`；
5. 同一目标串行导出，禁止并发写；
6. 文档保留“内部 file symlink 的 overwrite=True 风险”；
7. 不声称 symlink 已动态验证或已完全安全。

在上述条件下，C2B 可以使用现有固定目录和 HTML exporter 的核心路径，风险被限制在“本地 reports_dir 预置 symlink + 显式 overwrite=True”的组合。

### 8.3 必须先修复/收紧的条件

出现以下任一情况，C2B 不应启动：

- GUI 允许用户输入任意文件名并允许 `overwrite=True`；
- C2B 暴露 `reports_dir` 或完整路径参数；
- C2B 引入并发导出写同一目标；
- C2B 把“containment 通过”写成“symlink 安全”；
- C2B 需要在 reports_dir 内跟随已有 symlink。

此时应先增加叶节点 symlink 拒绝（或改为不跟随叶节点的安全发布），并补充具备 `SeCreateSymbolicLinkPrivilege` 的隔离环境动态测试。

---

## 9. 尚未解决的 UNKNOWN

以下项目不能写成 PASS：

1. **内部 file symlink 动态行为**：静态代码确认会跟随目标，但本会话 `WinError 1314`，没有端到端执行；
2. **断链 symlink 动态行为**：静态推演为创建目标，未动态执行；
3. **外部 file symlink 动态拒绝**：静态 containment 拒绝；动态未执行；
4. **root symlink 动态**：既有测试 skip，不能作为通过；
5. **父级 reparse point**：未做动态验证；
6. **TOCTOU**：叶节点在 `resolve()` 与 `os.replace()` 之间被替换的窗口未关闭；
7. **设备名实际运行时行为**：DEBT-09 保持 UNKNOWN，且不建议实际写入；
8. **清理失败/强制终止后的残留**：未做真实故障注入；
9. **C2B 并发路径**：当前无实现，无法验证。

---

## 10. 实际修改与停止状态

### 10.1 修改文件

**修改：**

```text
docs/PHASE6_C2A_SECURITY_DEBT.md
  - 仅 DEBT-09 的 11.5/11.6
  - 大小: 33,689 bytes
  - SHA-256: E66EE52DB36D951001365A77E818A8167AD33EF28EEE86618121442A51858626
```

**新增：**

```text
docs/PHASE6_C2A_R_C2B_SECURITY_GATE.md
  - 本报告
```

**未修改：**

- `reports/html_exporter.py`：24,132 bytes，SHA-256 `593E4F67928BAEF698BC52111BB19C868D28F3AB574617A50916C77159BE7C18`；
- `tests/test_report_html.py`：23,880 bytes，SHA-256 `72755296ED04E1E070AF9A30A418D6E8BCDE7FBF665215E0375F5EC39ACD5C42`；
- 数据库、Schema、HTML 模板、GUI、`app/config.py`；
- Phase 5 / Phase 6B / Phase 6C 既有归档。

### 10.2 测试与数据库

- 未运行完整 pytest 回归；
- 未运行生产路径测试；
- 未打开或写入业务数据库；
- 未创建/修改报告文件、模板或 GUI；
- 唯一动态操作是专用临时目录中的 symlink 创建尝试；因 `WinError 1314` 失败，临时目录已清理。

### 10.3 停止状态

```text
Phase 6C-2A-R: completed
C2B: not started
Next action: 等待人工审核本报告和 C2B 启动条件
```

**本报告不实施任何代码修复；内部 symlink 覆盖风险的修复、动态验证和 C2B 均需后续明确授权。**
