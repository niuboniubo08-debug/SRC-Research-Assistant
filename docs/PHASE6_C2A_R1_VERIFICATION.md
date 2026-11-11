# Phase 6C-2A-R1 步骤三：专项边界验证报告

**项目：** `D:\挖漏洞\SRC-Research-Assistant`  
**阶段：** Phase 6C-2A-R1 / 步骤三  
**日期：** 2026-11-08  
**当前版本：** 0.5.0  
**数据库 Schema：** v5  
**验证对象：** R1 步骤二的叶节点 symlink/junction 最小修复  
**验证性质：** 只读验证；不新增功能、不修改生产代码、不修改测试、不开始 C2B。

---

## 1. 最终结论

```text
R1_STEP3_STATUS = completed
FINAL_CALL_CHAIN = PASS
LEAF_RESOLVE_AS_TARGET = absent
BYPASS_WRITE_ENTRY = none_found_in_current_production_code
OSERROR_FAIL_CLOSED_TEST = PARTIAL_PASS (is_symlink branch only)
LEAF_JUNCTION_DYNAMIC = PASS
ROOT_JUNCTION_DYNAMIC = PASS
LEAF_SYMLINK_DYNAMIC = UNKNOWN (WinError 1314)
TOCTOU = UNKNOWN / unresolved
C2B_RECOMMENDATION = CONDITIONAL_GO
```

结论摘要：

1. 当前 `write_html_report()` 不再把叶节点 `resolve()` 后的路径作为写入目标；
2. 当前生产代码中只发现 `write_html_report()` 这一条报告写入入口，未发现绕过 `candidate` symlink/junction 检查的公开写入入口；
3. `OSError` 测试的 Mock 位置与真实调用链一致，但它只覆盖了 `candidate.is_symlink()` 抛错，没有独立覆盖 `candidate.is_junction()` 抛错；
4. 当前 Windows 环境实际创建 leaf junction 和 root junction 均成功，二者均被拒绝，且拒绝后没有生成报告文件；这是**动态 PASS**；
5. 文件 symlink 仍因 `WinError 1314` 无法动态创建，相关拒绝行为只能标记为 **UNKNOWN**，不能写成动态 PASS；
6. 仍存在 TOCTOU、父级 reparse point、symlink 链/循环等限制；C2B 只能在明确的调用边界下启动。

---

## 2. 最终调用链结论

### 2.1 唯一公开写入入口

当前 `reports/html_exporter.py` 的写入入口是：

```python
def write_html_report(
    snapshot: ReportSnapshot,
    request: ReportRequest,
    reports_dir: str | Path,
    *,
    overwrite: bool = False,
    filename: str | None = None,
) -> ReportArtifact:
```

位置：`reports/html_exporter.py:327-390`。

当前生产代码中没有其他模块调用 `write_html_report()`：

- `reports/html_exporter.py` 内部只有定义；
- `services/report_service.py:322-336` 的 `artifact_stub()` 只返回元数据，不写文件；
- `ui/report_page.py` 仍是占位页；
- `app/bootstrap.py` 未注入 exporter；
- 只发现测试调用 `html_exporter.write_html_report()`。

因此当前没有“生产 GUI/Service 已经接入 exporter”的事实；C2B 需要新建调用链，而不是复用现有 GUI 入口。

### 2.2 写入顺序

`write_html_report()` 的真实顺序：

```text
1. 校验 request 类型                         :345-346
2. render_html(snapshot, request)            :347
3. _resolve_reports_root(reports_dir)        :348
4. _validate_filename(...)                   :349
5. candidate = root / target_name            :350
6. candidate.parent != root                  :351-352
7. candidate.is_symlink()/is_junction()      :353-356
8. OSError -> ValidationError                :357-358
9. 命中 symlink/junction -> ValidationError   :359-360
10. target = candidate                       :364
11. target.relative_to(root)                 :365-368
12. target.parent != root                    :369-370
13. 已存在且 overwrite=False -> FileExists   :371-372
14. 已存在且是目录 -> ValidationError        :373-374
15. _atomic_write(target, payload, ...)      :376-378
16. 返回 ReportArtifact                      :380-390
```

### 2.3 叶节点 `resolve()` 检查

对 `reports/html_exporter.py` 的 `.resolve()` 检查：

| 位置 | 用途 | 是否作为最终写入目标 |
|---|---|---|
| `:51` | 计算模板目录 `Path(__file__).resolve().parent / "templates"` | 否 |
| `:651` | `_resolve_reports_root()` 解析根目录 | 否；只用于目录根 |

**未发现**类似 `target = (root / target_name).resolve()` 的叶节点解析，也未发现 `target = candidate.resolve()`。

`target` 始终来自第 10 步的原始 `candidate`：

```python
candidate = root / target_name
...
target = candidate
```

因此“叶节点 resolve 后作为最终写入目标”的旧问题已消除。

### 2.4 根目录检查

`_resolve_reports_root()` 位置 `reports/html_exporter.py:645-658`，仍然：

- 要求绝对路径；
- 检查 root 自身 `is_symlink()` / `is_junction()`；
- 之后 `root.resolve()`；
- 检查存在时必须是目录；
- 必要时 `mkdir(parents=True, exist_ok=True)`。

本次没有修改该函数；根目录 junction 动态拒绝见第 4 节。

### 2.5 最终发布逻辑

`_atomic_write()` 位于 `reports/html_exporter.py:719-754`：

- `tempfile.mkstemp()` 在目标同目录创建临时文件；
- `write` → `flush` → `os.fsync`；
- `overwrite=True` → `os.replace(temporary, target)`；
- `overwrite=False` → `_publish_exclusive()`；
- `finally` 关闭 fd、清理临时文件。

`_publish_exclusive()` 位于 `:693-716`：

- 使用 `os.link()` 做排他发布；
- 目标存在时 `FileExistsError`；
- 不支持硬链接时 `ReportExportError`；
- 没有 `os.replace` 回退。

因此，当前公开入口的写入必然经过 `_atomic_write()`，没有第二条“直接写目标”的生产路径。

---

## 3. 是否存在绕过叶节点检查的路径

### 3.1 公开入口

在当前生产代码中：

```text
write_html_report()  -> 唯一公开函数写入路径
```

`render_html()` 明确只渲染字符串，不写文件；`_atomic_write()` 和 `_publish_exclusive()` 是内部函数。

### 3.2 内部函数绕过

Python 没有真正的私有函数。内部代码理论上可以直接调用：

```python
html_exporter._atomic_write(target, payload, overwrite=True)
```

或直接调用 `_publish_exclusive()`，从而绕过 `candidate` 检查。但：

- 当前仓库中没有这样的生产调用；
- 当前 `_atomic_write()` 只被 `write_html_report()` 调用；
- 当前 `_publish_exclusive()` 只被 `_atomic_write()` 调用；
- 任何未来的直接调用都属于越过安全入口的内部误用，不能视为“当前已有绕过入口”。

**结论：**

```text
CURRENT_PUBLIC_BYPASS = none_found
PRIVATE_FUNCTION_MISUSE_RISK = future_internal_risk
```

### 3.3 任意 `reports_dir`

`write_html_report()` 接受调用方传入的 `reports_dir`，只要求绝对路径且不是 symlink/junction 根。它**不检查该目录是否等于 `AppConfig.reports_dir`**。

这意味着：

- 当前函数本身不能保证“只能写入配置目录”；
- 如果 C2B 允许用户输入任意绝对目录，就绕过了“固定输出根”的产品边界；
- 这不是 R1 叶节点检查的绕过，但属于 C2B 必须继承的调用方边界。

### 3.4 `filename` 参数

`filename` 受 `_validate_filename()` 约束：

- 拒绝 `/`、`\`、`:`;
- 拒绝 `?*<>|"`、控制字符、DEL；
- 拒绝 `.`、`..`；
- 要求 `.html` 后缀；
- 长度 ≤180；
- 拒绝 Windows 保留设备名。

但它允许调用方指定文件名；C2B 不应把任意用户输入直接当作完整路径。只应传文件名，不应传完整目录。

---

## 4. OSError 失败关闭测试真实性

### 4.1 测试代码

`tests/test_report_html.py:683-707`：

```python
def test_leaf_type_check_oserror_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "reports"
    output_dir.mkdir()
    target = output_dir / "report.html"
    real_is_symlink = Path.is_symlink

    def failing_is_symlink(self: Path) -> bool:
        if self == target:
            raise OSError("simulated leaf stat failure")
        return real_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", failing_is_symlink)

    with pytest.raises(ValidationError):
        html_exporter.write_html_report(
            _snapshot(ReportType.PROJECT_SUMMARY),
            _request(ReportType.PROJECT_SUMMARY),
            output_dir,
            filename="report.html",
        )

    assert not target.exists()
    assert not list(output_dir.glob(".*.tmp"))
```

### 4.2 Mock 位置与真实调用链

真实调用链：

```text
write_html_report()
  -> candidate = root / "report.html"
  -> candidate.is_symlink()          # 测试 Mock 命中
  -> raise OSError
  -> except OSError                  # :357
  -> raise ValidationError           # :358
```

Mock 位置：

```python
monkeypatch.setattr(Path, "is_symlink", failing_is_symlink)
```

与真实调用 `candidate.is_symlink()` 对得上；`self == target` 只对叶节点抛错，`_resolve_reports_root()` 检查的是 `output_dir`，因此不会被误触发。

### 4.3 测试结论

```text
OSERROR_TEST_MOCK_LOCATION = correct_for_is_symlink
OSERROR_TEST_IS_SYMLINK_BRANCH = PASS
OSERROR_TEST_IS_JUNCTION_BRANCH = NOT_COVERED
```

具体判断：

- **已覆盖**：`candidate.is_symlink()` 抛 `OSError` → `ValidationError` → 不生成目标文件 → 不留临时文件；
- **未覆盖**：`candidate.is_symlink()` 返回 `False` 后，`candidate.is_junction()` 抛 `OSError` 的分支；
- 由于 `or` 短路，现有测试在 `is_symlink()` 抛错时不会执行 `is_junction()`；
- 代码结构上 `try` 同时包住两个调用（`:353-358`），因此 `is_junction()` 抛 `OSError` 也会被捕获；但这是静态推断，不是该测试的实际覆盖。

因此不能把该测试描述为“同时验证了 is_symlink 和 is_junction 的 OSError”；准确结论是“真实覆盖 is_symlink 分支，is_junction 分支仅有结构性覆盖，未动态测试”。

---

## 5. Junction 动态验证

### 5.1 验证方法

使用现有测试辅助函数：

```python
def _make_windows_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    ...
    assert link.is_junction()
```

位置：`tests/test_report_html.py:512-522`。

该函数实际执行 `cmd /c mklink /J`，不是 mock；创建失败会 `pytest.skip`，不会伪造。

### 5.2 叶节点 junction

测试：`tests/test_report_html.py:590-607`

```text
output_dir/escape.html  --junction-->  outside/
write_html_report(..., filename="escape.html")
```

实际结果：

```text
PASS
ValidationError
outside/ 为空
output_dir 中没有生成的报告
```

这是**叶节点 junction 动态拒绝 PASS**。

### 5.3 根目录 junction

测试：`tests/test_report_html.py:550-565`

```text
reports_link  --junction-->  outside/
write_html_report(..., reports_dir=reports_link)
```

实际结果：

```text
PASS
ValidationError
outside/ 为空
```

这是**root junction 动态拒绝 PASS**。

### 5.4 本次专项运行结果

执行命令：

```powershell
$env:TEMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMP='D:\挖漏洞\pytest_c1r_tmp'
$env:TMPDIR='D:\挖漏洞\pytest_c1r_tmp'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q `
  'tests/test_report_html.py::test_normal_real_reports_dir_still_exports' `
  'tests/test_report_html.py::test_write_refuses_overwrite_and_preserves_old_file' `
  'tests/test_report_html.py::test_write_rejects_existing_directory_target' `
  'tests/test_report_html.py::test_reports_dir_itself_junction_is_rejected' `
  'tests/test_report_html.py::test_external_junction_leaf_is_rejected' `
  'tests/test_report_html.py::test_leaf_type_check_oserror_fails_closed' `
  'tests/test_report_html.py::test_internal_file_symlink_leaf_is_rejected' `
  'tests/test_report_html.py::test_broken_symlink_leaf_is_rejected' `
  --basetemp='D:\挖漏洞\pytest_c1r_tmp\bt_r1_verify' --disable-warnings
```

实际输出：

```text
7 passed, 4 skipped in 0.19s
```

通过项：

- 普通不存在文件创建；
- 普通文件覆盖 `overwrite=False/True`；
- 普通目录拒绝（两个参数）；
- root junction 动态拒绝；
- 叶节点 junction 动态拒绝；
- `is_symlink` OSError 失败关闭。

跳过项：

- 内部文件 symlink 两个参数；
- 断链 symlink 两个参数。

跳过原因：

```text
OSError [WinError 1314]
客户端没有所需的特权
```

没有运行完整回归；本步骤按要求只运行专项测试。

---

## 6. C2B 必须遵守的安全边界

C2B 接入报告导出时，必须满足以下边界；这些是**调用方约束**，不能依赖 `write_html_report()` 自动保证：

1. **固定输出根**
   - 必须使用 `AppConfig.reports_dir`；
   - 不得让用户输入完整输出路径；
   - 不得让用户选择任意绝对目录；
   - 不得把用户输入拼接为 `reports_dir`。

2. **只调用现有安全入口**
   - 只能调用 `reports.html_exporter.write_html_report()`；
   - 不得直接调用 `_atomic_write()`、`_publish_exclusive()`；
   - 不得自行 `open(target, "wb")`、`Path.write_text()`、`shutil.copy()` 或 `os.replace()` 写报告；
   - 不得重新实现临时文件/原子发布逻辑。

3. **文件名边界**
   - 只允许传文件名，不允许传路径；
   - 文件名必须经过 `_validate_filename()`；
   - 默认使用 `write_html_report()` 的 `_default_filename()`；
   - 不把用户提供的任意字符串直接作为路径。

4. **覆盖语义**
   - 默认 `overwrite=False`；
   - 只有用户明确确认后才传 `overwrite=True`；
   - 不得为“方便重试”默认覆盖；
   - 不得在 `overwrite=False` 失败后自动改用 `os.replace()`。

5. **串行导出**
   - 一次只允许一个 GUI 导出任务进入 exporter；
   - 导出按钮在任务进行中禁用；
   - 不得并发触发两个导出；
   - 不得把 exporter 放到无锁的线程池并行写同一目录。

6. **错误呈现**
   - `ValidationError`、`FileExistsError`、`ReportExportError` 必须显示给用户；
   - 不得把失败显示为“已生成”；
   - 不得在失败后保留半成品目标文件或临时文件。

7. **不扩大输入面**
   - 不新增 URL、网络路径、UNC 路径、用户自定义模板或用户自定义 CSS；
   - C2B 不改变模板、不改变 exporter 的信任边界；
   - 不把 HTML 导出扩张为任意文件写入功能。

---

## 7. 所有 UNKNOWN 和限制

### 7.1 动态 symlink 仍 UNKNOWN

```text
LEAF_SYMLINK_DYNAMIC = UNKNOWN
BROKEN_SYMLINK_DYNAMIC = UNKNOWN
EXTERNAL_SYMLINK_DYNAMIC = UNKNOWN
ROOT_SYMLINK_DYNAMIC = UNKNOWN
```

原因：当前 Windows 会话没有创建文件 symlink 的权限，所有相关测试 `skip`，错误为 `WinError 1314`。不能把静态检查或代码阅读写成动态 PASS。

### 7.2 `is_junction` OSError 未独立测试

现有 OSError 测试只让 `Path.is_symlink` 抛错；没有让 `Path.is_junction` 抛错。代码结构会捕获它，但测试覆盖不完整。

### 7.3 TOCTOU

检查与发布之间仍存在窗口：

```text
candidate.is_symlink()/is_junction() 检查
        ↓
target.exists()/is_dir() 检查
        ↓
mkstemp + write + fsync
        ↓
os.replace() / os.link()
```

攻击者可在检查后把普通文件替换成 symlink，或替换父目录。`overwrite=False` 的 `os.link()` 在目标已存在时会失败，因此不会写入；`overwrite=True` 使用 `os.replace()`，其最终行为取决于“叶节点被替换”还是“父目录被替换”，以及 Windows 的 `MoveFileExW` 语义。本步骤没有做并发替换动态验证，因此不能断言 `os.replace()` 一定跟随后来出现的叶节点 symlink，也不能断言一定安全；该场景标记为 **UNKNOWN**。

本修复只关闭“调用开始时已经存在”的内部/断链 symlink，不是并发 TOCTOU。

### 7.4 父级 reparse point

`_resolve_reports_root()` 只检查 root 本身；root 的父级目录如果被替换成 junction/symlink，仍未覆盖。

### 7.5 其他边界

- symlink 链/循环未完整验证；
- 其他 reparse point 类型未覆盖；
- Windows 设备名只做了静态文件名拒绝，未实际创建设备；
- `_atomic_write()` 的 `finally` 清理失败仍可能被吞掉；
- `overwrite=False` 依赖硬链接；不支持硬链接的文件系统会失败关闭，不会回退；
- 文档化限制不等于运行时已消除。

---

## 8. 实际执行的测试

本次仅执行专项测试：

```text
7 passed, 4 skipped in 0.19s
```

未执行完整回归；未修改 skip、断言或测试环境。测试进程使用：

```text
TEMP/TMP/TMPDIR = D:\挖漏洞\pytest_c1r_tmp
basetemp        = D:\挖漏洞\pytest_c1r_tmp\bt_r1_verify
DSH mode        = full-access
```

没有修改 ACL，没有使用 `takeown`，没有修改系统权限策略。

---

## 9. 实际修改文件清单

```text
A  docs/PHASE6_C2A_R1_VERIFICATION.md
```

**没有修改生产代码；没有修改测试；没有修改数据库、Schema、GUI、模板、ReportService 或 Repository。**

本次仅新增本报告。

---

## 10. 最终建议

### 10.1 建议

```text
C2B_RECOMMENDATION = CONDITIONAL_GO
```

建议在以下条件下批准启动 C2B：

1. GUI 固定使用 `AppConfig.reports_dir`，不接受任意完整输出路径；
2. 只调用 `write_html_report()`，不直接操作文件系统；
3. 默认 `overwrite=False`，覆盖需明确用户确认；
4. 导出任务串行，导出期间禁用重复触发；
5. 失败时显示真实错误，不显示“已生成”；
6. 接受并记录以下未解决项：动态 symlink UNKNOWN、TOCTOU、父级 reparse point、`is_junction` OSError 测试缺口；
7. C2B 不扩大为任意文件写入、网络导出或自定义模板功能。

### 10.2 不建议无条件 GO 的原因

- 文件 symlink 动态验证仍 UNKNOWN；
- `is_junction` 的 OSError 分支没有独立测试；
- `write_html_report()` 本身接受任意绝对 `reports_dir`，固定配置目录必须由 C2B 调用方保证；
- `overwrite=True` 仍有并发 TOCTOU；
- 父级 reparse point 未覆盖。

**结论：可以启动 C2B，但只能是带有上述调用边界和已知限制的条件性启动；不是“无限制安全通过”。**

---

**报告生成后立即停止。未进入 C2B，未新增功能，未修改生产代码或测试。**
