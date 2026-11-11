# Phase 6C-R：pytest 临时目录权限诊断与恢复报告

- 日期：2026-11-05（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 任务：Phase 6C-R，仅处理测试临时目录权限
- 结论：**测试在“独立临时目录 + 全访问测试进程”下恢复为 144 passed / 1 skipped；普通 workspace-write 进程仍受 DSH 低完整性限制。**
- Phase 6C-2：**not started**

## 1. 环境信息

| 项目 | 实际值 |
|---|---|
| 操作系统 | Windows 11 `10.0.26300` |
| Python 完整版本 | `3.14.4 (tags/v3.14.4:23116f9, Apr 7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]` |
| pytest | `9.2.0` |
| pytest-qt | `4.5.0` |
| PySide6 | `6.12.0` |
| 当前 Windows 用户 | `lenovo` |
| 当前工具文件策略 | `workspace-write` |
| 进程完整性级别 | `Mandatory Label\Low Mandatory Level`，SID `S-1-16-4096` |
| `TEMP` | `C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs` |
| `TMP` | `C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs` |
| `TMPDIR` | 未设置 |
| `tempfile.gettempdir()`（普通 workspace-write 进程） | `D:\挖漏洞\SRC-Research-Assistant`（回退到当前工作目录） |
| `tempfile.gettempdir()`（全访问测试进程 + 专用目录） | `D:\挖漏洞\pytest_c1r_tmp` |

关键事实：当前 DSH 工具进程不是普通 Medium integrity 进程，而是 **Low Mandatory Level** 进程。普通 workspace-write 下，Python 可以创建 `mkdtemp()` 目录，但对目录内新文件写入和对目录的清理会被拒绝；这与 ACL 中的 `Everyone:(CI)(DENY)(DC)` 和 Low Mandatory Level `(NW)` 同时存在。

## 2. 原始错误与调用栈摘要

### 2.1 Phase 6C-1 的完整测试结果

```text
1 failed, 7 passed, 137 errors in 1.71s
```

出现的两个路径：

```text
PermissionError: [WinError 5] 拒绝访问。:
'C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs\pytest-of-lenovo'

PermissionError: [WinError 5] 拒绝访问。:
'D:\挖漏洞\SRC-Research-Assistant\storage\_c1_pytest_tmp\pytest-of-lenovo'
```

### 2.2 pytest-qt setup 的准确 fixture

用现有测试做只读复现：

```powershell
python -m pytest -q -p no:cacheprovider `
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_norm `
  tests/test_report_service.py::test_dto_is_immutable `
  --setup-show -vv --tb=long
```

普通 workspace-write 下输出关键部分：

```text
SETUP    S tmp_path_factory
        SETUP    F tmp_path (fixtures used: tmp_path_factory)ERROR
        TEARDOWN F tmp_path
TEARDOWN S tmp_path_factory
```

因此：

- pytest-qt 的 `pytest_runtest_setup` 只是包装层；
- 真正失败的是 pytest 的 **`tmp_path` fixture**（其依赖 `tmp_path_factory`），不是 `qtbot` 自身；
- `pytestqt/plugin.py:168-182` 的 `result = yield` 把 fixture 初始化异常重新抛出，所以 C1 的摘要看起来像 pytest-qt setup 错误；
- 错误不是测试代码中的普通 setup 断言，也不是产品 Service/Repository 异常。

### 2.3 sessionfinish 清理栈

普通进程在 fixture 之后还遇到：

```text
_pytest/tmpdir.py:375  cleanup_dead_symlinks(basetemp)
_pytest/pathlib.py:398  for left_dir in root.iterdir()
pathlib/__init__.py:836  os.scandir(root_dir)
PermissionError: [WinError 5] 拒绝访问。: '<basetemp>'
```

说明 basetemp 目录在创建/清理链路上已不可访问。

### 2.4 TemporaryDirectory 清理栈

`test_pip_audit_actual_available` 使用：

```python
with tempfile.TemporaryDirectory() as tmp:
    scanner = PipAuditScanner(
        cache_dir=Path(tmp) / "cache", temp_dir=Path(tmp) / "temp"
    )
```

C1 观察到其 cleanup 在 `tempfile.py` 的 `_rmtree` / `_resetperms` 链上失败，涉及：

```text
chmod(..., follow_symlinks=False)
```

Python 3.14.4 相关实现：

- `tempfile.py:916-955`：`TemporaryDirectory._rmtree()`；
- 遇到 `PermissionError` 时调用 `_resetperms()`，再 `unlink`/递归清理；
- Windows 上 ACL 拒绝会导致 `chmod`/删除继续失败。

### 2.5 失败阶段判定

| 阶段 | 实际结果 |
|---|---|
| 创建 `tmp_path`/临时目录 | 目录创建可以成功 |
| 在临时目录写入文件 | **失败**：`PermissionError: [Errno 13]` / `WinError 5` |
| pytest `tmp_path` fixture setup | **失败**，fixture 为 `tmp_path` |
| `TemporaryDirectory` cleanup | **失败**，在 `_rmtree`/`_resetperms`/`chmod` 链上 |
| pytest-qt `qtbot` teardown 本身 | 不是首因；仅在包装层暴露 |

## 3. 根因分析

### 3.1 主因：DSH 低完整性测试进程与临时目录 ACL

- 当前工具进程为 **Low Mandatory Level**，不是普通桌面 Medium integrity 进程。
- DSH 临时目录 `C:\Users\lenovo\AppData\Local\Temp\dsh-ZncoXs` 的 ACL 含：

```text
Everyone:(CI)(DENY)(DC)
Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)
```

- 项目目录和 `storage` 继承了 `Everyone:(I)(CI)(DENY)(DC)` 与 Low Mandatory Level 标记。
- 普通 workspace-write 下，Python `mkdtemp()` 能创建目录，但随后写 `probe.txt` 得到：

```text
PermissionError: [Errno 13] Permission denied:
'D:\挖漏洞\SRC-Research-Assistant\tmp...\probe.txt'
```

- 因此 pytest 的 `tmp_path` fixture 无法完成文件准备；`TemporaryDirectory` 也无法可靠 cleanup。
- 这是 **测试进程完整性/文件系统权限环境问题**，不是 Phase 6B 产品逻辑失败，也不是 pytest-qt 自身 bug。

### 3.2 ACL 单独修复不足以恢复普通进程

对新建的 `D:\挖漏洞\.pytest-c1r-env` 执行了仅针对该目录的 `icacls`：

```powershell
icacls $root /inheritance:r /grant:r `
  "LAPTOP-D1CQ3MQK\lenovo:(OI)(CI)F" `
  "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
  "BUILTIN\Administrators:(OI)(CI)F" /C
```

结果：

- 在 workspace-write 下该 `icacls` 本身被拒绝（`Access is denied`）；
- 在 full-access 测试模式下 ACL 修改成功，目录不再含 `Everyone` Deny；
- 但普通 workspace-write Python 仍无法在该目录写入文件，说明问题不只在继承 ACL，低完整性进程/DSH 沙箱还施加了额外限制。

### 3.3 次因：Bandit 排除路径名中的 `env`

第一次在 `D:\挖漏洞\.pytest-c1r-env` 的完整测试出现 2 个真实失败：

```text
FAILED tests/test_bandit_scanner.py::test_actual_bandit_scan_persists_results
FAILED tests/test_ui_source_audit.py::test_source_audit_page_runs_real_local_bandit_scan
assert 0 >= 3
assert 0 > 0
```

原因不是 Bandit 产品回归，而是 `BanditScanner.scan()` 固定使用：

```text
-x .venv,.git,__pycache__,venv,env,node_modules,build,dist
```

临时 basetemp 路径包含 `...pytest-c1r-env`，Bandit 将 `env` 目录名视为排除项，扫描目标被排除，返回 0 findings。

改用不含 `env`、不以 `.` 开头的：

```text
D:\挖漏洞\pytest_c1r_tmp
```

后，两个 Bandit 测试均通过，完整套件恢复绿色。

这是一个重要发现：**临时目录名不能包含 Bandit 的排除段 `env`/`venv` 等**，否则会得到“completed 但 0 findings”的伪阴性；这不是产品数据伪造，但测试环境必须避开。

## 4. 实际采用的恢复措施

### 4.1 专用临时目录

最终路径：

```text
D:\挖漏洞\pytest_c1r_tmp
```

选择理由：

- 位于工作区内，可由 DSH 工具访问；
- 不以 `.` 开头，避免隐藏目录工具行为；
- 路径不含 `env`、`venv` 等 Bandit 排除段；
- 与项目源码、Phase 5/6B 封存文件、数据库完全分离。

实际 pytest basetemp：

```text
D:\挖漏洞\pytest_c1r_tmp\bt_full
```

### 4.2 环境变量与命令

最终完整测试命令使用：

```text
TEMP=D:\挖漏洞\pytest_c1r_tmp
TMP=D:\挖漏洞\pytest_c1r_tmp
TMPDIR=D:\挖漏洞\pytest_c1r_tmp
PYTEST_DEBUG_TEMPROOT=D:\挖漏洞\pytest_c1r_tmp
QT_QPA_PLATFORM=offscreen

python -m pytest -q -p no:cacheprovider `
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_full
```

### 4.3 测试进程的全访问模式

普通 workspace-write 的低完整性进程仍不能写入临时目录。最终完整测试使用 DSH 的 **full-access 测试进程模式** 执行；这是测试执行层的临时措施，不是产品代码、测试代码或数据库变更。

在该模式下：

- `tempfile.gettempdir()` 返回 `D:\挖漏洞\pytest_c1r_tmp`；
- `tempfile.mkdtemp()` 创建目录成功；
- 写入 `probe.txt`、读取、`shutil.rmtree`、`TemporaryDirectory` 清理全部成功；
- pytest-qt fixture setup/teardown 成功；
- 独立目录的读写删除已实际验证，不只是根据错误摘要推断。

## 5. 权限修改范围

### 5.1 实际修改

只对新建的测试候选目录执行过一次 ACL 调整：

```text
D:\挖漏洞\.pytest-c1r-env
```

修改方式：

```powershell
icacls $root /inheritance:r /grant:r `
  "LAPTOP-D1CQ3MQK\lenovo:(OI)(CI)F" `
  "NT AUTHORITY\SYSTEM:(OI)(CI)F" `
  "BUILTIN\Administrators:(OI)(CI)F" /C
```

修改后的 ACL：

```text
BUILTIN\Administrators:(OI)(CI)(F)
NT AUTHORITY\SYSTEM:(OI)(CI)(F)
LAPTOP-D1CQ3MQK\lenovo:(OI)(CI)(F)
Mandatory Label\Low Mandatory Level:(I)(OI)(CI)(NW)
```

### 5.2 未做的事

- 未使用 `takeown`；
- 未做全盘 ACL 重置；
- 未递归修改项目、`storage`、Phase 5 或 Phase 6B 封存目录权限；
- 未修改 `requirements.txt`；
- 未安装、升级或卸载依赖；
- 未修改测试、断言、skip 或产品代码；
- 未修改数据库或 Schema；
- 未开始 Phase 6C-2。

### 5.3 最终目录权限

最终目录 `D:\挖漏洞\pytest_c1r_tmp` **没有**做 ACL 修改，仍保留继承 ACL：

```text
Everyone:(I)(CI)(DENY)(DC)
LAPTOP-D1CQ3MQK\lenovo:(I)(OI)(CI)(F)
Mandatory Label\Low Mandatory Level:(I)(OI)(CI)(NW)
```

它只在 full-access 测试进程下使用。这是本次恢复的明确限制。

## 6. 临时目录最终位置

```text
D:\挖漏洞\pytest_c1r_tmp
```

完整测试的实际 basetemp：

```text
D:\挖漏洞\pytest_c1r_tmp\bt_full
```

该目录下的测试产物是测试临时文件，不属于产品数据，也不属于 Phase 5/6B 封存内容。

## 7. 完整 pytest 执行结果

### 7.1 collect-only

```text
145 tests collected in 0.17s
```

### 7.2 最终完整执行

命令退出码：`0`

```text
144 passed, 1 skipped in 40.94s
```

- passed：144
- failed：0
- errors：0
- skipped：1
- collected：145
- 耗时：40.94s
- exit code：0

唯一 skip：

```text
tests\test_evidence_service.py:184
当前 Windows 会话无法创建符号链接：
[WinError 1314] 客户端没有所需的特权。
```

这是既有环境限制，未删除、未弱化、未伪造。

### 7.3 中途失败尝试

第一次在 `D:\挖漏洞\.pytest-c1r-env` 上运行完整测试：

```text
2 failed, 142 passed, 1 skipped in 44.07s
```

失败为上述 Bandit `env` 排除路径造成的 0 findings；改用 `pytest_c1r_tmp` 后消失。最终结果以 7.2 为准。

## 8. 与历史基线对比

| 指标 | 历史基线 | 本次最终 |
|---|---:|---:|
| collected | 145 | 145 |
| passed | 144 | 144 |
| failed | 0 | 0 |
| skipped | 1 | 1 |
| errors | 0 | 0 |
| 测试数量变化 | — | 0 |
| 测试代码修改 | — | 无 |
| 断言弱化 | — | 无 |
| skip 删除 | — | 无 |

历史基线未被降低；Phase 6C-1 的 `1 failed, 7 passed, 137 errors` 是环境阻塞，不是产品回归，已由本次独立复现和恢复验证区分。

## 9. 剩余环境限制

1. **普通 workspace-write 仍不能运行完整 pytest**  
   进程是 Low Mandatory Level；默认 `TEMP` 指向带 `Everyone:(CI)(DENY)(DC)` 的 DSH 临时目录；`tmp_path` 的创建/写入/清理仍会被拒绝。

2. **必须使用专用目录和 full-access 测试进程**  
   当前可用方式是：
   - `TEMP`/`TMP`/`TMPDIR` 指向 `D:\挖漏洞\pytest_c1r_tmp`；
   - `--basetemp` 指向该目录；
   - 测试进程使用 DSH full-access 模式。

   这不是产品代码修复，也不改变用户机器的全局 ACL。

3. **Bandit 路径排除约束**  
   临时目录名不能包含 `env`、`venv` 等被 Bandit `-x` 排除的段；否则真实扫描测试会得到 0 findings 的假阴性。

4. **文件符号链接仍无法在普通 Windows 会话创建**  
   既有 `WinError 1314` skip 保留；目录联接和路径越界测试仍可执行。

5. **未尝试通过 `takeown` 或全局 ACL 重置绕过限制**  
   这符合本阶段禁止项；未把环境限制伪装成产品通过。

## 10. 是否满足 Phase 6C-2 测试前置条件

**条件性满足，不能表述为无条件满足。**

- 在已记录的 **独立临时目录 + full-access 测试进程** 下，145 项全部收集，144 passed / 1 skipped / 0 failed / 0 errors，满足测试执行要求。
- 在普通 `workspace-write` 下，`tmp_path`/`TemporaryDirectory` 仍受 Low Mandatory Level 与 DSH 临时目录 ACL 限制，不能稳定运行完整测试。
- 因此 C2 可以继续，但必须沿用本报告的专用临时目录和 full-access 测试执行方式；如果 C2 要求普通 workspace-write 直接通过，则前置条件**尚未满足**，应先由用户/环境提供可写的普通完整性测试目录。

Phase 6C-2 尚未启动；本报告完成后停止，等待用户审查。
