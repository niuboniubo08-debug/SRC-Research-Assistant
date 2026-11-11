# Phase 6C-2A-R1 步骤二：叶节点 Symlink 最小修复报告

**项目：** `D:\挖漏洞\SRC-Research-Assistant`  
**阶段：** Phase 6C-2A-R1 / 步骤二  
**日期：** 2026-11-08  
**当前版本：** 0.5.0  
**数据库 Schema：** v5  
**依据：** `docs/PHASE6_C2A_R1_INVESTIGATION.md`  
**范围：** 仅修复 `write_html_report()` 对报告叶节点过早 `resolve()` 导致的 symlink/断链 symlink 跟随问题。

---

## 1. 结论摘要

```text
FIX_1_STATUS = completed
RAW_LEAF_SYMLINK_REJECTION = implemented
BROKEN_SYMLINK_REJECTION = implemented
LEAF_RESOLVE = removed
ORDINARY_OVERWRITE_SEMANTICS = preserved
SYMLINK_DYNAMIC_VALIDATION = not_available (WinError 1314)
FULL_REGRESSION = 187 passed / 7 skipped / 0 failed / 0 errors
STEP_3 = not started
C2B = not started
```

本轮实现了调查报告中的最小方案：

1. 先完成文件名校验；
2. 构造未解析的原始叶节点 `candidate = root / target_name`；
3. 在叶节点 `resolve()` 之前检查 `candidate` 是否是 symlink 或 junction；
4. 任一检查抛出 `OSError` 时失败关闭，不继续写入；
5. 不再使用“叶节点 `resolve()` 后的路径”作为写入目标；
6. 保留原有 containment、目录检查和普通文件 `overwrite` 语义；
7. 不修改 `_resolve_reports_root()` 的既有安全逻辑。

本轮没有开始步骤三，没有开始 Phase 6C-2B，没有修改数据库、Schema、GUI、模板或 `ReportService`。

---

## 2. 实际修改文件

### 2.1 生产代码

| 文件 | 修改 |
|---|---|
| `reports/html_exporter.py` | 仅修改 `write_html_report()` 的叶节点构造与检查逻辑 |

修改后大小与 SHA-256：

```text
reports/html_exporter.py
  size   24,953 bytes
  sha256 207AA3571B4D1900472CFCD8FB75856DCF354335AD81AB905AA35B69D3FAB480
```

### 2.2 测试代码

| 文件 | 修改 |
|---|---|
| `tests/test_report_html.py` | 新增 8 个测试用例（含参数化实例），未删除、跳过或弱化既有测试 |

修改后大小与 SHA-256：

```text
tests/test_report_html.py
  size   28,055 bytes
  sha256 41CFC444D59942E9E1D377D9561873B349F938776AD469F7ECE500941BCFECA0
```

### 2.3 文档

新增：

```text
docs/PHASE6_C2A_R1_FIX_1.md
```

本报告为唯一新增文档；报告自身哈希见交付回执，不在正文中自引用。

### 2.4 明确未修改

```text
database/schema.py
database/connection.py
storage/src_research.db
storage/phase5_acceptance/acceptance.db
reports/templates/*.html
services/report_service.py
repositories/report_repository.py
ui/*
app/*
```

**未修改数据库或 Schema，未执行数据库迁移，未写入数据库。**

---

## 3. 修复前后行为

### 3.1 修复前代码路径

`reports/html_exporter.py:346` 原为：

```python
target = (root / target_name).resolve()
```

问题：

- 内部文件 symlink 会被解析成目标文件；
- `overwrite=True` 会替换目标文件；
- 断链 symlink 会被解析成缺失目标，`overwrite=False` 会创建它；
- 外部 symlink 虽最终被 containment 拒绝，但拒绝发生在 `resolve()` 之后；
- 同目录 symlink 可以指向非 HTML 文件，而文件名校验只看到 `.html` 别名。

### 3.2 修复后代码路径

`reports/html_exporter.py:349-364` 现在为：

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

# Keep the raw leaf.  Resolving it here would follow an internal symlink
# and make the atomic writer replace the symlink's target instead.
target = candidate
```

之后保留：

```python
target.relative_to(root)
if target.parent != root:
    raise ValidationError("报告目标必须直接位于 reports_dir")
if target.exists() and not overwrite:
    raise FileExistsError(...)
if target.exists() and target.is_dir():
    raise ValidationError("报告目标不是文件")
```

关键变化：

- `candidate` 未解析；
- symlink/junction 在任何 `resolve()` 之前被拒绝；
- `target = candidate`，不再使用叶节点解析结果；
- `_atomic_write()` 接收原始叶节点；
- `_resolve_reports_root()` 未修改；
- `_validate_filename()` 未修改；
- `_atomic_write()` 与 `_publish_exclusive()` 未修改。

### 3.3 行为对照

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 普通文件不存在，`overwrite=False` | 创建 | 创建（不变） |
| 普通文件不存在，`overwrite=True` | 创建 | 创建（不变） |
| 普通文件存在，`overwrite=False` | `FileExistsError` | `FileExistsError`（不变） |
| 普通文件存在，`overwrite=True` | 替换 | 替换（不变） |
| 普通目录存在，`overwrite=False` | `FileExistsError` | `FileExistsError`（不变） |
| 普通目录存在，`overwrite=True` | `ValidationError` | `ValidationError`（不变） |
| 内部文件 symlink，目标存在，`overwrite=True` | 目标文件被替换 | `ValidationError`，目标文件不变 |
| 内部文件 symlink，目标存在，`overwrite=False` | `FileExistsError` | `ValidationError`，不写入 |
| 断链 symlink，`overwrite=False` | 在缺失目标创建文件 | `ValidationError`，缺失目标仍不存在 |
| 断链 symlink，`overwrite=True` | 在缺失目标创建文件 | `ValidationError`，缺失目标仍不存在 |
| 外部文件 symlink | containment 拒绝 | 原始叶节点检查即拒绝 |
| 叶节点 symlink/junction | 可能被 `resolve()` 跟随 | 拒绝 |
| 叶节点检查抛 `OSError` | 未专门处理 | `ValidationError`，失败关闭 |

因此普通文件/普通目录语义保持不变；只有 symlink/junction 输入从“可能跟随”改为拒绝。

---

## 4. 新增测试

### 4.1 新增测试清单

| 测试 | 位置 | 覆盖 |
|---|---|---|
| `test_write_rejects_existing_directory_target`（`overwrite=False/True` 两个参数） | `tests/test_report_html.py:429` | 普通目录拒绝，两个 overwrite 分支 |
| `_make_file_symlink_or_skip()` | `:525` | symlink 创建失败时 skip；不伪造 PASS |
| `test_internal_file_symlink_leaf_is_rejected`（两个参数） | `:611` | 内部文件 symlink 拒绝，目标内容不变 |
| `test_broken_symlink_leaf_is_rejected`（两个参数） | `:636` | 断链 symlink 拒绝，不创建缺失目标 |
| `test_external_file_symlink_leaf_is_rejected` | `:659` | 外部文件 symlink 拒绝，外部文件不变 |
| `test_leaf_type_check_oserror_fails_closed` | `:683` | 叶节点检查抛 `OSError` 时失败关闭 |

### 4.2 保留且未修改的既有测试

- 普通不存在文件正常创建：`test_atomic_write_is_utf8_and_returns_artifact`（`tests/test_report_html.py:375`）；
- 普通文件 `overwrite=False/True`：`test_write_refuses_overwrite_and_preserves_old_file`（`:398`）；
- 路径逃逸/非 HTML：`test_write_rejects_path_escape_and_non_html`（`:455`）；
- 替换失败保留旧文件：`test_failed_replace_preserves_old_file_and_cleans_temp`（`:470`）；
- 正常目录导出：`test_normal_real_reports_dir_still_exports`（`:533`）；
- root junction 拒绝：`:551`；
- root symlink 拒绝：`:568`；
- 外部 junction 叶节点拒绝：`:591`；
- `overwrite=False` 竞态：`:710`；
- 无硬链接失败关闭：`:740`；
- `KeyboardInterrupt` 清理：`:768`；
- Windows 保留名/非法字符：`:863`。

没有删除、跳过或修改任何既有测试的断言。

### 4.3 symlink 测试策略

`_make_file_symlink_or_skip()`：

```python
def _make_file_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
    except OSError as exc:
        pytest.skip(f"当前环境无法创建 Windows 文件符号链接: {exc}")
    assert link.is_symlink()
```

- 创建失败时 `pytest.skip`；
- skip 不视为 PASS；
- 不修改系统权限；
- 不使用 `takeown`；
- 不伪造符号链接结果；
- 目标测试目录均在 `tmp_path` 下。

---

## 5. 测试结果

### 5.1 定向测试

```text
pytest tests/test_report_html.py -q
43 passed, 6 skipped in 0.78s
```

49 个测试实例中：

- 43 passed；
- 6 skipped；
- 0 failed；
- 0 errors。

skip 明细：

```text
tests/test_report_html.py:577
  root symlink 创建失败：WinError 1314
tests/test_report_html.py:529
  内部文件 symlink 参数 0：WinError 1314
tests/test_report_html.py:529
  内部文件 symlink 参数 1：WinError 1314
tests/test_report_html.py:529
  断链 symlink 参数 0：WinError 1314
tests/test_report_html.py:529
  断链 symlink 参数 1：WinError 1314
tests/test_report_html.py:529
  外部文件 symlink：WinError 1314
```

### 5.2 完整回归

```text
D:\挖漏洞\.venv\Scripts\python.exe -m pytest -q
187 passed, 7 skipped in 41.19s
```

共 194 个测试实例：

- 187 passed；
- 7 skipped；
- 0 failed；
- 0 errors；
- 退出码 0。

7 个 skip：

1. 既有 evidence service 文件 symlink：`tests/test_evidence_service.py:184`，`WinError 1314`；
2. root symlink：`tests/test_report_html.py:577`，`WinError 1314`；
3–4. 内部文件 symlink 两个参数：`:529`，`WinError 1314`；
5–6. 断链 symlink 两个参数：`:529`，`WinError 1314`；
7. 外部文件 symlink：`:529`，`WinError 1314`。

测试执行环境：

```text
TEMP/TMP/TMPDIR = D:\挖漏洞\pytest_c1r_tmp
--basetemp      = D:\挖漏洞\pytest_c1r_tmp\bt_r1_fix
                  D:\挖漏洞\pytest_c1r_tmp\bt_r1_full
```

因为本会话的 workspace-write 低完整性进程仍受 ACL 限制，完整测试在 DSH **full-access** 测试进程中运行；没有修改 ACL，没有使用 `takeown`，没有修改系统权限策略。

### 5.3 与修复前对比

| 项目 | 修复前 | 修复后 |
|---|---|---|
| `test_report_html.py` 测试实例 | 41 | 49 |
| 完整测试实例 | 186 | 194 |
| 完整 passed | 184 | 187 |
| 完整 skipped | 2 | 7 |
| 完整 failed/errors | 0 / 0 | 0 / 0 |
| 普通文件行为 | 正常 | 正常，既有测试通过 |
| 内部 symlink | 可跟随（静态风险） | 拒绝（静态实现） |
| 断链 symlink | 可创建缺失目标（静态风险） | 拒绝（静态实现） |

新增的 5 个 symlink 参数实例全部因为当前 Windows 会话无符号链接权限而 skip，因此“动态 symlink 行为”仍未验证；这不是把失败隐藏成通过。

---

## 6. Symlink 动态验证状态

### 6.1 当前状态

```text
SYMLINK_DYNAMIC_VALIDATION = UNKNOWN
```

原因：

- 当前 Python 进程创建文件 symbol link 时返回：
  ```text
  OSError [WinError 1314]
  客户端没有所需的特权
  ```
- 当前环境没有 `SeCreateSymbolicLinkPrivilege`；
- 即使测试进程使用 DSH full-access，也未获得该 Windows 安全特权；
- 所有文件 symlink 测试按设计 `pytest.skip`；
- root symlink 测试同样 skip；
- full-access 不是“伪造 symlink 权限”。

### 6.2 已验证与未验证的边界

**静态已确认（代码路径）：**

- `is_symlink()` 在 `exists()`/`resolve()` 前调用；
- 内部 symlink 的原始叶节点会返回 `True`；
- 断链 symlink 的 `is_symlink()` 返回 `True`；
- junction 通过 `is_junction()` 检查；
- `OSError` 分支抛出 `ValidationError`；
- 普通文件不会命中该分支。

**动态未验证（UNKNOWN）：**

- Windows 上实际创建文件 symlink 后的拒绝结果；
- Windows 上断链文件 symlink 的实际创建/拒绝结果；
- 外部文件 symlink 的实际拒绝结果；
- symlink 链、循环和竞态行为；
- 其他 reparse point 类型的实际行为。

因此本报告不能声称“symlink 已动态验证通过”；只能声称“代码已加入静态检查，相关动态测试因环境权限 skip”。

---

## 7. 未解决的限制

### 7.1 TOCTOU

在“原始叶节点检查”与 `_atomic_write()` 的最终 `os.replace()`/`os.link()` 之间仍存在窗口：

```text
T1: candidate.is_symlink()/is_junction() == False
T2: candidate.exists()/is_dir() 检查
T3: mkstemp + write
T4: os.replace() 或 os.link()
```

攻击者可在 T1 与 T4 之间把普通文件替换成 symlink，或替换父目录。`overwrite=True` 的 `os.replace()` 尤其仍可能跟随后来出现的叶节点 symlink。

本修复关闭的是“调用开始时已经存在的内部/断链 symlink”，不是“任意时刻并发替换”的 TOCTOU。

### 7.2 父级 reparse point

`_resolve_reports_root()` 检查 root 本身，但不检查 root 的父级路径中是否含有 reparse point。若 `reports_dir` 的父目录被替换成 junction/symlink，仍可能影响输出位置。

### 7.3 symlink 链与循环

`is_symlink()` 只能识别叶节点本身；symlink 链、循环或通过父级 symlink 的间接路径未做完整解析校验。循环可能导致 `OSError`，当前叶节点检查会失败关闭，但不保证错误类型统一。

### 7.4 其他 reparse point

当前只显式识别 Windows symlink 和 junction；其他 reparse point 类型（例如某些云盘/挂载点）未做专门处理。

### 7.5 Windows 设备名实际行为

文件名校验拒绝 `CON`、`NUL`、`COM1` 等保留名，但没有实际创建这些设备名的测试；实际运行时行为仍为 UNKNOWN。

### 7.6 清理失败

`_atomic_write()` 的 `finally` 清理仍可能因文件被占用/权限变化而失败；失败会被吞掉，不保证临时文件一定删除。

### 7.7 并发

`overwrite=False` 的硬链接发布仍是对“写入目标名”的排他操作；`overwrite=True` 仍使用 `os.replace()`。没有实现跨进程锁或目录句柄级发布。

---

## 8. 为什么没有修改 `_resolve_reports_root()`

`_resolve_reports_root()` 已负责：

- 绝对路径校验；
- root 本身 symlink/junction 拒绝；
- root 解析；
- 目录存在性/类型检查；
- 创建输出目录。

本轮只处理“root 下的叶节点”。如果在该函数中继续增加叶节点逻辑，会混淆“输出根目录安全”和“单次目标安全”的职责边界，也会扩大修改面。因此保持该函数不变是符合最小修复原则的。

---

## 9. 实际验证命令

### 9.1 定向测试

```powershell
$env:TEMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMPDIR='D:\挖漏洞\pytest_c1r_tmp'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest tests\test_report_html.py -q `
  --basetemp='D:\挖漏洞\pytest_c1r_tmp\bt_r1_fix' --disable-warnings
```

结果：`43 passed, 6 skipped in 0.78s`。

### 9.2 完整回归

```powershell
$env:TEMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMPDIR='D:\挖漏洞\pytest_c1r_tmp'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q `
  --basetemp='D:\挖漏洞\pytest_c1r_tmp\bt_r1_full' --disable-warnings
```

结果：`187 passed, 7 skipped in 41.19s`，退出码 0。

### 9.3 未执行

- 未执行任何数据库写入或迁移；
- 未执行 GUI 测试或 GUI 启动；
- 未执行 PDF/JSON 导出；
- 未执行 Phase 6C-2B；
- 未执行步骤三。

---

## 10. 修改文件清单

```text
M  reports/html_exporter.py
M  tests/test_report_html.py
A  docs/PHASE6_C2A_R1_FIX_1.md
```

没有其他文件变更。

---

## 11. 停止与后续边界

本轮完成：

- 叶节点原始 symlink/junction 检查；
- 断链 symlink 拒绝；
- `OSError` 失败关闭；
- 移除叶节点 `resolve()` 写入目标；
- 保留普通文件覆盖语义；
- 新增定向测试并完成完整回归。

本轮**未**完成、也不声称完成：

- TOCTOU 完全关闭；
- 父级 reparse point 防护；
- symlink 链/循环完整防护；
- 所有 reparse point 类型；
- 动态文件 symlink 验证（环境无权限，skip）；
- 并发导出锁；
- C2B、PDF、JSON、GUI 或步骤三。

**本报告生成后停止。未进入步骤三，未进入 Phase 6C-2B。**
