# Phase 6C-2A SEC-02 Windows 路径修复 1

## 1. 结论

**PASS_WITH_LIMITATIONS**

本轮只修复 SEC-02 中“`reports_dir` 自身为 Windows junction / reparse point 时，报告被重定向写入真实目标目录”的问题。

修复后：

- 真实普通目录仍可正常导出。
- `reports_dir` 自身是 junction 时，在 `resolve()` 之前拒绝。
- 拒绝后 junction 目标目录没有新增文件。
- 原有“输出目录内部叶节点为外部 junction”的防护继续有效。
- 未删除、跳过或弱化任何原有测试。
- 未修改数据库、Schema、Repository、ReportService、GUI、模板或其他业务模块。

仍存在边界：检查与后续 `mkdir()`、`resolve()`、叶节点检查、`os.replace()`/`os.link()` 之间不能完全消除 TOCTOU；`reports_dir` 的父级组件若为 reparse point，本轮不单独拒绝；当前 Windows 会话无法创建 symlink，symlink 动态验证为 **UNKNOWN**。

---

## 2. 修改范围

只修改了以下两个文件：

| 文件 | 修改内容 |
|---|---|
| `reports/html_exporter.py` | `_resolve_reports_root()` 在 `resolve()` 前增加原始路径的 symlink/junction 拒绝 |
| `tests/test_report_html.py` | 新增 SEC-02 正常目录、根 junction、根 symlink（可用时）、外部叶节点 junction 测试 |

新增：

| 文件 | 内容 |
|---|---|
| `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md` | 本报告 |

明确没有修改：

- `database/`、`core/models/report.py`、`repositories/report_repository.py`、`services/report_service.py`
- `ui/report_page.py`、`app/bootstrap.py`
- `reports/templates/*`
- 数据库文件或 Schema 版本

---

## 3. 修复前行为

修复前 `_resolve_reports_root()` 的顺序是：

1. `Path(reports_dir).expanduser()`
2. 检查绝对路径
3. `root.resolve()`
4. 检查是否为目录
5. `mkdir(parents=True, exist_ok=True)`

因此，如果 `reports_dir` 本身是一个 junction：

- `Path` 仍指向 junction 路径；
- `root.resolve()` 会把它解析成真实目标；
- 后续目录检查、临时文件创建和最终发布都发生在真实目标目录；
- 应用没有在“解析前”识别原始路径是 junction。

这会造成“用户以为写入授权输出目录，实际写入 junction 目标”的重定向风险。

---

## 4. 修复后代码

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
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportExportError(f"无法创建报告输出目录: {exc}") from exc
    return root
```

关键点：

- 检查发生在 `root.resolve()` **之前**，保留原始路径的链接信息。
- `Path.is_symlink()` 覆盖普通符号链接。
- `Path.is_junction()`（Python 3.12+，本项目 Python 3.14.4）覆盖 Windows junction。
- 使用 `getattr(..., lambda: False)` 保持对无 `is_junction` 实现的兼容；不会因此放行 Windows junction。
- 命中后抛出 `ValidationError`，没有不安全回退。
- 真实普通目录、非目录路径、相对路径、不可创建目录的既有行为保持不变。

---

## 5. 修复前后对比

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 普通真实目录 | 允许导出 | 允许导出 |
| `reports_dir` 是 junction | `resolve()` 后写入真实目标 | 解析前 `ValidationError` |
| `reports_dir` 是 symlink | 可能跟随链接 | 解析前 `ValidationError` |
| 输出目录内的叶节点是外部 junction | 由叶节点检查处理 | 继续由叶节点检查处理 |
| 相对路径 | `ValidationError` | `ValidationError` |
| 普通文件占位 | `ValidationError` | `ValidationError` |

---

## 6. 新增测试

`tests/test_report_html.py` 新增 4 个测试：

| 测试 | 行号 | 目的 |
|---|---|---|
| `test_normal_real_reports_dir_still_exports` | `tests/test_report_html.py:502` | 正常真实目录仍可导出 |
| `test_reports_dir_itself_junction_is_rejected` | `tests/test_report_html.py:520` | `reports_dir` 自身为 junction 时拒绝 |
| `test_reports_dir_itself_symlink_is_rejected_when_available` | `tests/test_report_html.py:537` | 符号链接可用时拒绝；不可用则 skip/UNKNOWN |
| `test_external_junction_leaf_is_rejected` | `tests/test_report_html.py:560` | 原有外部叶节点 junction 防护继续有效 |

测试辅助函数：

`tests/test_report_html.py:489-499`：

```python
def _make_windows_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        pytest.skip(f"当前环境无法创建 Windows junction: {detail}")
    assert link.is_junction()
```

测试只使用 pytest 独立临时目录和无害文件；没有删除用户文件，没有使用 `takeown`，没有修改系统权限。

### 6.1 根 junction 拒绝并验证目标目录未新增文件

`test_reports_dir_itself_junction_is_rejected`：

1. 创建 `outside` 目录；
2. 在临时目录创建指向 `outside` 的 `reports_link` junction；
3. 调用 `html_exporter.write_html_report(..., reports_dir=reports_link)`；
4. 断言抛出 `ValidationError`；
5. 断言 `list(outside.iterdir()) == []`。

实际结果：**通过**。

### 6.2 根 symlink

`test_reports_dir_itself_symlink_is_rejected_when_available`：

- 尝试 `os.symlink(..., target_is_directory=True)`；
- 当前 Windows 会话返回 `[WinError 1314] 客户端没有所需的特权`；
- 测试 `pytest.skip`，未修改系统权限；
- 因此 **symlink 动态验证 = UNKNOWN**；静态代码路径已覆盖 `is_symlink()` 分支，但不能把 UNKNOWN 写成已验证。

### 6.3 外部叶节点 junction

`test_external_junction_leaf_is_rejected`：

1. 创建正常 `reports` 目录；
2. 在 `reports/escape.html` 创建指向外部 `outside` 的 junction；
3. 调用导出 `filename="escape.html"`；
4. 断言 `ValidationError`；
5. 断言 `outside` 为空。

实际结果：**通过**，说明原有叶节点外部重定向防护未被破坏。

---

## 7. 实际测试结果

执行环境：

- Python `3.14.4`
- pytest `9.2.0`
- pytest-qt `4.5.0`
- 独立临时根目录：`D:\挖漏洞\pytest_c1r_tmp`
- 测试进程按既有 C1-R 方案使用 DSH full-access，未调整 ACL
- 未修改测试断言或跳过标记

### 7.1 HTML 专项

命令（等效）：

```text
python -m pytest -q tests/test_report_html.py \
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_sec02_fix_targeted \
  -p no:cacheprovider
```

结果：

```text
40 passed, 1 skipped in 0.36s
```

跳过项为：

```text
tests/test_report_html.py:546:
当前环境无法创建 Windows 符号链接: [WinError 1314] 客户端没有所需的特权。
```

### 7.2 完整回归

命令（等效）：

```text
python -m pytest -q \
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_sec02_fix_full \
  -p no:cacheprovider
```

结果：

```text
184 passed, 2 skipped in 39.72s
FULL_EXIT_CODE=0
```

完整测试共 `186` 项（`184 passed + 2 skipped`），0 failed，0 errors。

两个 skip：

1. `tests/test_evidence_service.py:184`：既有 Windows 文件 symlink `WinError 1314`；
2. `tests/test_report_html.py:546`：本轮根 symlink 测试，当前会话无法创建 symlink。

与修复前对比：

| 指标 | 修复前 | 修复后 |
|---|---|---|
| 完整测试项 | 182 | 186 |
| passed | 181 | 184 |
| skipped | 1 | 2 |
| failed/errors | 0/0 | 0/0 |
| 耗时 | 39-43 秒区间 | 39.72 秒 |

新增的 4 项中 3 项通过、1 项因环境权限 skip；没有删除或弱化原有测试。

---

## 8. 数据库完整性

只读检查，未执行迁移、写入或 Schema 修改：

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

结论：

- 两个数据库 `integrity_check=ok`；
- `foreign_key_check` 为 0 行；
- Schema 仍为 v5；
- `reports` 表仍为 0 行；
- 数据库文件 SHA-256 与修复前一致。

---

## 9. 修改文件摘要

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `reports/html_exporter.py` | 24,132 | `593E4F67928BAEF698BC52111BB19C868D28F3AB574617A50916C77159BE7C18` |
| `tests/test_report_html.py` | 23,880 | `72755296ED04E1E070AF9A30A418D6E8BCDE7FBF665215E0375F5EC39ACD5C42` |

本报告是唯一新增文档。

---

## 10. Windows junction 动态证据

本轮不是只做静态代码审查：

- 使用独立临时目录创建实际 junction；
- `Path.is_junction()` 在测试辅助函数中做断言；
- `write_html_report()` 实际走完整导出入口；
- 期望异常为 `ValidationError`；
- junction 目标目录在失败后仍为空。

对应测试：

- `test_reports_dir_itself_junction_is_rejected`
- `test_external_junction_leaf_is_rejected`

两项在完整回归中均通过。

---

## 11. Symlink 未验证项

当前 Windows 会话：

```text
[WinError 1314] 客户端没有所需的特权。
```

因此：

- 没有创建任何 symlink；
- 没有调整本地安全策略、开发者模式或 ACL；
- 根 symlink 测试被标记为 skip；
- 状态为 **UNKNOWN**，不是 PASS；
- 不能据此宣称 symlink 路径已完成动态验证。

静态上，`_resolve_reports_root()` 的 `root.is_symlink()` 分支会在 `resolve()` 前拒绝 symlink 根目录；该分支仍需在具备 symlink 权限的 Linux/WSL 或受控 Windows 环境中补测。

---

## 12. 未解决风险与限制

### 12.1 TOCTOU 不能完全消除

检查点与后续操作之间存在时间窗口：

- `is_symlink()` / `is_junction()` 检查之后；
- `root.resolve()` 之前；
- `root.mkdir()` 之前；
- 叶节点检查与 `os.replace()` / `os.link()` 之间。

恶意并发方理论上可以在窗口内替换目录或文件。本轮只保证“调用时原始 `reports_dir` 本身为 junction/symlink 会被拒绝”，不宣称消除所有并发替换风险。

### 12.2 父级路径组件

本轮只检查 `reports_dir` **自身**，不递归检查其父目录中的 reparse point。若 `reports_dir` 尚不存在而其父级是 junction，解析和创建仍可能发生在重定向目标中。该边界需要在后续设计（例如逐级打开/句柄约束）中处理，不在本轮最小修复范围。

### 12.3 `reports_dir` 不存在时

如果路径尚不存在，无法通过 `is_junction()` 判断未来的目录；检查发生在创建前，随后 `mkdir()` 创建的是普通目录。若创建过程中发生并发替换，仍属于 12.1 的窗口。

### 12.4 叶节点与根目录检查的分工

- 根目录检查：`_resolve_reports_root()`；
- 叶节点检查：现有 `_resolve_leaf_target()` / 路径包含检查；
- 本轮只新增根目录解析前检查，没有放宽叶节点检查；
- 外部叶节点 junction 测试通过，说明原有防护继续有效。

### 12.5 Symlink 权限

当前环境权限不足，symlink 分支为 UNKNOWN；未通过修改系统安全设置来“制造”通过结果。

---

## 13. 停止状态

本轮只完成 SEC-02 最小修复、junction 动态测试、完整回归和数据库只读检查。

未开始：

- SEC-02 之外的 symlink 动态验证；
- PDF、JSON、GUI 开发；
- 正式业务报告生成；
- 任何 C2 后续阶段或下一 Phase。

等待审核。
