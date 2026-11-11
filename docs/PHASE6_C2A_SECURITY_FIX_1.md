# Phase 6C-2A 安全审查第一轮最小修复报告

日期：2026-11-07  
阶段：Phase 6C-2A Security Fix 1  
状态：**修复完成，测试通过，等待下一轮审查**

## 1. 范围与依据

本次修复依据 `docs/PHASE6_C2A_SECURITY_REVIEW_1.md`，只处理其中四个问题：

- SEC-01：`overwrite=False` 的并发覆盖竞态。
- SEC-04：`title`、`warnings`、`data_scope`、`known_limitations` 的长度与控制字符限制。
- SEC-05：包括 `KeyboardInterrupt` 在内的异常中断临时文件清理。
- SEC-07：Windows 保留设备名与非法文件名字符。

本次不处理 SEC-02（Windows junction/symlink 动态验证）、SEC-03（CSP）和 SEC-06（自由文本语义脱敏）。不开始 PDF、JSON、GUI、数据库或正式业务报告开发。

## 2. 修改文件

本次只修改两个已有文件，并新增本报告：

| 文件 | 性质 | 说明 |
|---|---|---|
| `reports/html_exporter.py` | 修改 | 四个安全问题的实现修复 |
| `tests/test_report_html.py` | 修改 | 每个问题新增针对性测试，共新增 19 个测试用例 |
| `docs/PHASE6_C2A_SECURITY_FIX_1.md` | 新增 | 本报告 |

未修改数据库、Schema、`ReportService`、`ReportRepository`、GUI、模板、依赖或 Phase 5 / Phase 6B 封存文件。未降低或删除已有测试断言。

## 3. SEC-01：`overwrite=False` 原子排他发布

### 3.1 关键实现

实现位置：`reports/html_exporter.py:673-696`、`:699-734`。

- `overwrite=True` 保持原有行为：完整写入临时文件、`flush`、`fsync`、关闭后使用 `os.replace()` 替换目标。
- `overwrite=False` 不再依赖“先检查 `exists()` 再 `os.replace()`”的 TOCTOU 流程：
  1. 仍先写入同目录临时文件并完成 `flush` / `fsync` / 关闭。
  2. 使用 `os.link(temporary, target)` 发布。
  3. POSIX `link(2)` 和 Windows `CreateHardLinkW` 在目标已存在时会原子失败，因此不会覆盖已有文件。
  4. 链接成功后再删除临时文件名；目标成为已完整写入文件的硬链接。
- 若 `os.link` 不可用或文件系统不支持硬链接，抛出 `ReportExportError`，明确失败，**不会退回 `os.replace()` 或其他不安全方案**。
- 保留了写入前 `target.exists()` 的快速拒绝，但该检查只用于尽早反馈；最终安全性由 `os.link` 的原子语义保证。
- 目标存在、目标目录被并发创建、目标为符号链接/悬空链接等情况下，最终均由排他链接失败保护，不会被覆盖。
- `FileExistsError` 继续作为“目标已存在”的调用方可识别异常；其他排他发布失败转换为 `ReportExportError`。
- 临时文件在 `finally` 中清理，覆盖成功与失败路径均不遗留 `.tmp`。

### 3.2 兼容性记录

`overwrite=False` 现在要求目标目录所在文件系统支持硬链接。Windows NTFS 和常见 POSIX 文件系统支持；FAT/exFAT、部分网络共享或其他不支持硬链接的文件系统会明确抛出 `ReportExportError`，报告不会写入，目标不会覆盖。这是刻意的 fail-closed 设计，没有不安全回退。

## 4. SEC-04：文本长度与控制字符

### 4.1 关键实现

实现位置：`reports/html_exporter.py:71-83`、`:574-599`、`:396-403`。

- 新增统一控制字符正则：移除 C0 控制字符和 DEL（`\x00-\x08`、`\x0b-\x1f`、`\x7f`）。
- `_bounded_text()`：
  - 清理控制字符；
  - 按限制截断，截断结果包含省略号，总长度不超过限制。
- `_single_line_text()`：在限制后再折叠所有空白，用于标题和列表项，避免换行、制表符等影响版面。
- `_bounded_sequence()`：对列表逐项清理、截断并限制最多 100 项。
- `title` 最大 200 字符；`warnings`、`data_scope`、`known_limitations` 每项最大 2,000 字符，最多 100 项。
- 报告请求中的 `title`、快照中的 `warnings`、`data_scope`、`known_limitations` 统一经过上述边界处理；`image_notice` 和“未包含人工备注”提示也经过边界处理。
- 模板输出仍由 Jinja2 `autoescape=True` 负责 HTML 转义；本修复不改变模板转义策略。

### 4.2 测试

- `test_untrusted_text_fields_are_bounded_and_control_chars_removed`：验证标题、警告、数据范围、已知限制的长度上限，以及 NUL、SOH、STX、US、TAB、换行等控制字符被清理。
- `test_warning_list_is_bounded`：验证超过 100 条警告时只保留 100 条。

## 5. SEC-05：异常中断清理

### 5.1 关键实现

实现位置：`reports/html_exporter.py:699-734`。

- 从“仅捕获 `Exception`”改为 `try ... finally`。
- 无论普通异常、`KeyboardInterrupt` 还是 `SystemExit`，都会执行：
  - 关闭尚未交给 `os.fdopen` 的文件描述符；
  - 删除仍存在的临时文件；
  - 保留已有目标文件（如果替换尚未成功）。
- `finally` 本身不捕获、不替换原始异常；原始异常继续向调用方传播。
- 清理动作中的 `OSError` 被局部忽略，避免清理失败掩盖原始异常。

### 5.2 测试

`test_keyboard_interrupt_cleans_temp_and_preserves_old_file` 将 `os.replace` 替换为抛出 `KeyboardInterrupt` 的函数，验证：

- `KeyboardInterrupt` 原样传播；
- 旧目标文件内容不变；
- 没有遗留 `.tmp` 文件。

## 6. SEC-07：Windows 文件名限制

### 6.1 关键实现

实现位置：`reports/html_exporter.py:641-660`。

`_validate_filename()` 现在拒绝：

- Windows 非法字符：`? * < > | "`；
- 路径分隔符：`/`、`\`、`:`；
- 控制字符和 DEL；
- `.`、`..`；
- 不以 `.html` 结尾的名称；
- 超过 180 字符的名称；
- Windows 保留设备名的扩展形式（大小写不敏感，去除首段尾部空格/点后判断）：
  - `CON`、`PRN`、`AUX`、`NUL`、`CLOCK$`、`CONIN$`、`CONOUT$`；
  - `COM1` 至 `COM9`；
  - `LPT1` 至 `LPT9`。

例如 `NUL.html`、`con.html`、`COM1.html`、`LPT9.html`、`CONIN$.html`、`report?.html` 都会被 `ValidationError` 拒绝。

### 6.2 测试

`test_write_rejects_windows_reserved_names_and_invalid_chars` 使用 14 个参数化文件名，验证：

- 调用抛出 `ValidationError`；
- 输出目录保持为空；
- 不创建目标文件或临时文件。

## 7. 测试结果

### 7.1 HTML 专项测试

命令（使用已验证的独立临时目录与 DSH full-access 测试进程）：

```text
python -m pytest -q tests\test_report_html.py \
  --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_security_fix2 \
  -p no:cacheprovider
```

结果：

```text
37 passed in 0.30s
EXIT_CODE=0
```

原有 HTML 测试 18 个，本次新增 19 个；没有删除或弱化原有断言。

### 7.2 完整回归

```text
182 tests collected in 0.24s
```

```text
181 passed, 1 skipped in 40.49s
EXIT_CODE=0
```

唯一跳过项：

```text
tests/test_evidence_service.py:184
当前 Windows 会话无法创建符号链接：[WinError 1314] 客户端没有所需的特权。
```

该跳过是既有 Windows 环境限制，与本次修复无关；没有通过跳过或修改断言来掩盖失败。

## 8. 数据库完整性检查

测试完成后以只读方式检查，未执行迁移、写入或 Schema 修改：

| 数据库 | 大小 | SHA-256 | Schema | integrity_check | foreign_key_check | 表数 | reports 行数 |
|---|---:|---|---:|---|---|---:|---:|
| `storage/src_research.db` | 147,456 | `F03CFB81BF0CF4CEE3367E1413E26919E30FA763C2D1B792AA03B5300E3128BB` | 5 | ok | 0 | 11 | 0 |
| `storage/phase5_acceptance/acceptance.db` | 352,256 | `03DE49509B43428EB303F7DC38E1FF749CC58D1B3F186070C63706BBA4CEB4C8` | 5 | ok | 0 | 11 | 0 |

两个数据库的哈希与修复前基线一致；`storage/reports/` 仍只有 `.gitkeep`，没有生成报告文件。

## 9. 未解决问题与限制

1. **SEC-02 仍未关闭**：没有新增 Windows junction/symlink 的动态对抗测试；`reports_dir` 本身为 reparse point 的情况仍只做静态路径检查。
2. **SEC-03 仍未修复**：HTML 没有 CSP；当前模板没有脚本和远程资源，因此仍属于纵深防御缺口，不是本轮授权范围。
3. **SEC-06 仍未修复**：自由文本字段保持 HTML 转义，但没有语义级敏感信息脱敏；不得把自动转义误称为内容脱敏。
4. **硬链接兼容性**：`overwrite=False` 在不支持硬链接的文件系统上会明确失败；这是有意的安全行为，不是静默回退。常规 NTFS 测试已通过。
5. **未实现 PDF/JSON/GUI**：本轮没有生成 PDF、JSON 或 GUI 报告，也没有写入 `reports` 表。
6. **测试环境限制**：完整回归仍需独立临时目录和 full-access 测试进程；普通 workspace-write 下的 pytest 临时目录 ACL 限制仍是既有环境问题，不属于本次代码修改。
7. **未生成正式业务报告**：本文件只是工程修复记录。

## 10. 结论

- SEC-01、SEC-04、SEC-05、SEC-07 已按最小范围修复。
- `overwrite=False` 的最终发布由原子硬链接完成；不支持硬链接时明确失败，没有不安全回退。
- 专项测试 37 passed；完整回归 181 passed / 1 skipped / 0 failed / 0 errors。
- 数据库 Schema 仍为 v5，两个数据库 integrity ok、FK 0、reports 0，哈希未变化。
- 修改范围严格限定为 `reports/html_exporter.py` 和 `tests/test_report_html.py`，另新增本报告。
- 停止于本轮修复，不自动开始第二步，等待审查。
