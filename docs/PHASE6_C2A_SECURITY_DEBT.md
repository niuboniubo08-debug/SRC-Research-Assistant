# Phase 6C-2A 安全遗留问题台账

- 台账日期：2026-11-07
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：0.5.0
- 数据库 Schema：v5
- 台账性质：**只读调查与文档整理**
- 依据：
  - `reports/html_exporter.py`（24,132 bytes，SHA-256 `593E4F67928BAEF698BC52111BB19C868D28F3AB574617A50916C77159BE7C18`）
  - `tests/test_report_html.py`（23,880 bytes，SHA-256 `72755296ED04E1E070AF9A30A418D6E8BCDE7FBF665215E0375F5EC39ACD5C42`）
  - `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md`
  - `docs/PHASE6_C2A_SECURITY_REVIEW_1.md`
  - `docs/PHASE6_C2A_SECURITY_FIX_1.md`
  - `docs/PHASE6_C2A_SECURITY_FIX_1_REVIEW_EVIDENCE.md`
  - `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_REVIEW.md`
  - `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md`
- 本轮未修改生产源码、测试、数据库、Schema、HTML 模板、GUI、配置或既有验收归档；**未运行测试回归**；未生成正式业务报告；未开始 Phase 6C-2B。

---

## 1. 分类与状态约定

### 1.1 验证分类

| 分类 | 含义 |
|---|---|
| **已动态验证** | 当前项目历史中已有实际执行结果，且结果可定位到测试或运行记录 |
| **仅静态确认** | 通过实际源码路径可以确认，但没有对应的动态对抗测试 |
| **UNKNOWN** | 当前环境、权限或本轮限制下无法确认，不能按 PASS 处理 |
| **已知设计限制** | 不是待修复缺陷，而是明确接受的产品/信任边界；仍需在报告中披露 |

### 1.2 当前状态

每个问题使用一个主状态：

- **未修复**：代码或测试仍存在明确缺口；
- **UNKNOWN**：实现可能存在，但动态行为未验证；
- **设计边界**：明确不在当前实现范围内，需产品/安全决策；
- **待评估**：尚未完成影响评估。

### 1.3 风险等级

- **严重 / 高 / 中 / 低**
- 本台账没有“严重”或“高”项。
- “中”表示在特定前置条件下可能造成报告路径越界、完整性或隐私影响；当前均为本地文件场景，不涉及代码执行或远程攻击。

### 1.4 本轮总体结论

```text
遗留问题总数：9
严重：0
高：0
中：4（DEBT-01、DEBT-02、DEBT-03、DEBT-08）
低：5（DEBT-04、DEBT-05、DEBT-06、DEBT-07、DEBT-09）
```

**无绝对阻塞 Phase 6C-2B 的 P0/P1 项。**
其中 DEBT-01、DEBT-02 是**条件性门禁**：只有 C2B 扩大输出路径能力（用户自定义目录、父目录、symlink 路径）时才成为阻塞项。其余问题不阻塞 C2B，但必须保留在风险记录中。

---

## 2. 台账总表

| 编号 | 问题 | 风险 | 状态 | 验证分类 | 阻塞 C2B |
|---|---|---|---|---|---|
| DEBT-01 | SEC-02：父级 reparse point 未检查 | 中 | 未修复 | 静态确认 + UNKNOWN | 条件性 |
| DEBT-02 | SEC-02：root/叶节点 symlink 动态验证不足 | 中 | UNKNOWN | UNKNOWN（部分动态） | 条件性 |
| DEBT-03 | SEC-02：检查与发布之间的 TOCTOU | 中 | 未修复 | 静态确认 + UNKNOWN | 否（并发场景重评） |
| DEBT-04 | SEC-04：`CountView` 未统一限长/控制字符 | 低 | 未修复 | 仅静态确认 | 否 |
| DEBT-05 | SEC-05：临时文件清理失败被静默忽略 | 低 | 未修复 | 仅静态确认（部分动态） | 否 |
| DEBT-06 | SEC-01：缺少真实双进程并发测试 | 低 | 未修复（测试缺口） | 仅静态确认 | 否 |
| DEBT-07 | SEC-03：尚未增加 CSP | 低 | 未修复 | 仅静态确认 | 否 |
| DEBT-08 | SEC-06：自由文本无语义脱敏 | 中 | 设计边界 | 已知设计限制 | 否 |
| DEBT-09 | SEC-07：Windows 设备名实际写入未验证 | 低 | UNKNOWN | UNKNOWN（校验动态通过） | 否 |

---

## 3. DEBT-01：SEC-02 父级 reparse point 未检查

### 3.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:627-640` `_resolve_reports_root()`：
  - 检查 `root.is_absolute()`；
  - 检查 `root.is_symlink()`；
  - 检查 `root.is_junction()`；
  - 然后执行 `root = root.resolve()`；
  - 再检查存在性和目录类型。
- `reports/html_exporter.py:344-356` 使用解析后的 root：

```python
root = _resolve_reports_root(reports_dir)
target = (root / target_name).resolve()
try:
    target.relative_to(root)
except ValueError as exc:
    raise ValidationError("报告目标路径越界") from exc
```

**缺口：**

- 只检查 `reports_dir` 自身是否为 symlink/junction；
- **没有检查 `reports_dir` 的父目录或更高层路径是否为 reparse point**；
- `Path.resolve()` 会跟随父级 junction/symlink，最终写入真实路径；
- 如果配置值本身是 `D:\trusted\reports`，但 `D:\trusted` 已被替换为 junction，当前代码无法识别。

### 3.2 风险等级

**中。**

前置条件：

- 本机低权限用户能够替换 `reports_dir` 的父目录或创建父级 reparse point；
- 或应用配置被指向不可信目录。

影响：

- 报告可能写入非预期的物理目录；
- 可能覆盖/暴露目标目录中的同名报告；
- 不涉及代码执行、提权或远程利用。

### 3.3 当前状态与验证分类

- **状态：未修复**
- **验证分类：仅静态确认 + UNKNOWN**
  - “未检查父级”由源码静态确认；
  - 父级 reparse 的实际输出路径没有动态测试。

### 3.4 已有测试证据

- `tests/test_report_html.py:502` `test_normal_real_reports_dir_still_exports`：正常目录 PASS；
- `tests/test_report_html.py:520` `test_reports_dir_itself_junction_is_rejected`：只验证 **root 自身** junction，PASS；
- `tests/test_report_html.py:560` `test_external_junction_leaf_is_rejected`：只验证 **叶节点** 外部 junction，PASS；
- **没有父级 reparse point 测试**；
- 没有“父目录 junction + 正常 root 名称”的测试。

### 3.5 尚缺少的验证

1. 构造 `parent_junction\reports`，其中 `parent_junction` 指向外部目录；
2. 验证 `_resolve_reports_root()` 是否应拒绝、还是继续跟随；
3. 验证外部目标目录不会产生文件；
4. 验证父目录为 symlink 与 junction 的差异；
5. 验证多层父目录 reparse point；
6. 验证当父目录在检查后被替换时的行为（与 TOCTOU 合并评估）。

### 3.6 建议处理阶段

- **若 C2B 仍使用固定、受信任的 `reports_dir`：** 可保持现状，作为已记录设计边界；
- **若 C2B 引入用户自定义输出目录、目录选择器或路径参数：** 必须在 C2B 前补充父级策略；
- **若不扩大路径能力：** 建议在 C2B 后 路径加固中统一处理。

### 3.7 是否阻塞 C2B

**条件性阻塞。**

- 当前固定配置、受信任父目录：不阻塞；
- C2B 允许用户选择/输入输出目录，或允许父级路径来自不可信来源：阻塞，必须先定义并实现父级 reparse 策略；
- 不能把“当前不阻塞”写成“父级路径已安全”。

---

## 4. DEBT-02：SEC-02 root 与叶节点 symlink 动态验证不足

### 4.1 当前事实与证据

**代码位置：**

- root 检查：`reports/html_exporter.py:627-640`；
- 叶节点检查：`reports/html_exporter.py:344-356`；
- 当前逻辑：
  - root 在 `resolve()` 前检查 `is_symlink()` / `is_junction()`；
  - 叶节点 `target = (root / name).resolve()`；
  - `target.relative_to(root)`；
  - `target.parent == root`；
  - `target.exists()` / `target.is_dir()`。

**已验证：**

- root junction：动态拒绝 PASS；
- 正常真实目录：PASS；
- 外部叶节点 junction：动态拒绝 PASS；
- 断链 junction：动态拒绝、无写入 PASS。

**未验证：**

- root symlink：测试在 `WinError 1314` 时 skip；
- 外部叶节点 symlink：当前会话无法创建；
- 内部叶节点文件 symlink：没有动态测试；
- 内部目录别名/内部 junction：没有显式 reparse 类型断言测试；
- 断链 symlink：没有动态测试；
- root 为 symlink 且 target 存在/不存在两种分支。

### 4.2 风险等级

**中。**

- 若路径 containment 逻辑存在未发现的绕过，报告可能写到 root 外；
- 当前静态逻辑具备 `resolve()` + `relative_to()` + parent 检查，但没有足够的动态证明；
- 不能因为静态逻辑看起来正确就标记 PASS。

### 4.3 当前状态与验证分类

- **状态：UNKNOWN**
- **验证分类：UNKNOWN（部分动态通过）**
  - root junction、外部叶节点 junction 是动态 PASS；
  - root symlink、叶节点 symlink、内部别名是 UNKNOWN。

### 4.4 已有测试证据

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_reports_dir_itself_symlink_is_rejected_when_available` | `tests/test_report_html.py:537` | **SKIP**（`WinError 1314`） |
| `test_reports_dir_itself_junction_is_rejected` | `tests/test_report_html.py:520` | PASS |
| `test_external_junction_leaf_is_rejected` | `tests/test_report_html.py:560` | PASS |
| `test_normal_real_reports_dir_still_exports` | `tests/test_report_html.py:502` | PASS |
| `test_write_rejects_path_escape_and_non_html` | `tests/test_report_html.py:432` | PASS（普通 `..`/绝对路径，不是 symlink） |

`test_reports_dir_itself_symlink_is_rejected_when_available` 的 skip 是环境权限限制，不是产品通过。

### 4.5 尚缺少的验证

1. 在具备 `SeCreateSymbolicLinkPrivilege` 或开发模式的隔离环境中创建 root symlink；
2. 创建外部叶节点 symlink，断言拒绝且外部目录为空；
3. 创建内部叶节点文件 symlink，验证不会替换链接目标；
4. 创建内部目录别名/junction，验证拒绝或安全失败关闭；
5. 创建断链 symlink，验证不会因 `resolve()` 行为绕过；
6. 验证 root symlink 指向不存在目标时的行为；
7. 验证检查与 `resolve()` 之间替换路径的竞态（与 DEBT-03 合并）。

### 4.6 建议处理阶段

- **若 C2B 不扩大路径能力：** C2B 后 测试加固；
- **若 C2B 引入用户路径/目录选择：** C2B 前必须补齐 root/叶节点 symlink 动态验证；
- 不建议为了测试而要求普通用户开启 symlink 权限；应使用隔离测试环境或显式 skip 并保留 UNKNOWN。

### 4.7 是否阻塞 C2B

**条件性阻塞。**

- 当前固定 `reports_dir`、无 symlink 输入：不阻塞，但 UNKNOWN 必须保留；
- C2B 开放 symlink 路径、用户目录或依赖 containment 作为安全承诺：阻塞，必须先补动态验证；
- 不得把“有静态检查”写成“symlink 已动态验证”。

---

## 5. DEBT-03：SEC-02 检查与文件发布之间的 TOCTOU

### 5.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:344-356`：
  1. `_resolve_reports_root()`；
  2. `_validate_filename()`；
  3. `target = (root / target_name).resolve()`；
  4. `target.relative_to(root)`；
  5. `target.parent != root` 检查；
  6. `target.exists()` / `target.is_dir()`；
  7. 最终调用 `_atomic_write()`。
- `reports/html_exporter.py:701-736` 再执行 `mkstemp`、写临时文件、`os.replace()` 或 `_publish_exclusive()`。

**缺口：**

- 检查与使用之间没有目录句柄约束；
- 没有 `openat`-style 固定路径；
- root、父目录或叶节点可以在检查后、发布前被替换；
- `target.exists()` 与 `os.link()` 之间也存在窗口；
- 这不是“代码没检查”，而是检查结果可能已经过期。

### 5.2 风险等级

**中。**

- 本地竞争条件；
- 影响主要是报告写入位置/覆盖完整性；
- 不涉及代码执行或权限提升；
- 需要本地写权限和精确时序，实际可利用性有限。

### 5.3 当前状态与验证分类

- **状态：未修复**
- **验证分类：静态确认（路径检查与发布分离）+ UNKNOWN（没有对抗动态验证）**
- TOCTOU 是结构性的；不能把并发验证缺失写成 PASS。

### 5.4 已有测试证据

- `tests/test_report_html.py:579` `test_overwrite_false_race_is_rejected_by_exclusive_publish`：
  - 测试的是“目标已存在时 `os.link()` 失败”；
  - 不是“检查 root/父目录/叶节点后被替换”的路径 TOCTOU；
  - 通过 monkeypatch 写入目标，属于模拟；
- `tests/test_report_html.py:609` `test_no_overwrite_fails_closed_without_hardlink_support`：
  - 验证不支持硬链接时失败关闭；
  - 不覆盖路径检查竞态；
- `tests/test_report_html.py:432` `test_write_rejects_path_escape_and_non_html`：
  - 验证普通路径逃逸；
  - 不覆盖并发替换。

### 5.5 尚缺少的验证

1. 在 root 检查后、`_atomic_write()` 前替换 root/父目录；
2. 在 `target.resolve()` 后、`os.link()`/`os.replace()` 前替换叶节点；
3. 验证旧报告、目标目录和临时文件的最终状态；
4. 验证 Windows junction 替换和 symlink 替换的差异；
5. 验证 `overwrite=True` 和 `overwrite=False` 两条路径；
6. 验证多进程而非单进程 monkeypatch 的时序。

### 5.6 建议处理阶段

- 当前单写者、固定受信任目录：可记录为残余风险，不要求 C2B 前修复；
- 若 C2B 引入并发导出、后台导出队列、用户自定义目录或覆盖策略：C2B 前重新评估；
- 若未来要求“强路径安全”，建议使用目录句柄/`openat` 或先固定父目录的受控写入方案（本轮不实施）。

### 5.7 是否阻塞 C2B

**否（当前单写者场景）/ 条件性（并发或路径能力变化）。**

- 当前 C2B 若不改变单写者和固定目录：不阻塞；
- 若 C2B 增加并发导出或用户路径：应升级为门禁项；
- 不能宣称已消除 TOCTOU。

---

## 6. DEBT-04：SEC-04 `CountView` 未统一限长/控制字符处理

### 6.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:502-518` `_stats_view()`：
  - `task_scanner_counts=_named_count_views(data.task_scanner_counts)`；
  - `scanner_counts=_named_count_views(data.scanner_counts)`；
  - `severity_counts` 等使用 `_count_views()`。
- `reports/html_exporter.py:521-538` `_count_views()`：
  - 已知枚举项使用 `CountView(item.label, count)`；
  - 未知键使用 `CountView(str(key), count)`（第 537 行）；
- `reports/html_exporter.py:541-546` `_named_count_views()`：
  - 直接 `CountView(str(key), ...)`（第 543 行）。
- 模板渲染：
  - `reports/templates/base.html:146-154` 渲染 `severity_counts`、`scanner_counts`；
  - `reports/templates/project_summary.html:58-72` 渲染状态/证据类型/任务状态计数。

**缺口：**

- 未知统计键没有经过 `_bounded_text()` 或 `_single_line_text()`；
- 可能包含超长字符串或控制字符；
- 模板有 Jinja2 autoescape，因此不是 HTML 注入；
- 但长度/控制字符卫生与 SEC-04 指定字段不一致；
- 这是 SEC-04 修复范围之外的附加残余。

### 6.2 风险等级

**低。**

- autoescape 仍阻止脚本注入；
- 影响主要是报告展示异常、超长 HTML、日志/界面噪声；
- 不构成路径逃逸或代码执行；
- 统计键通常来自受控枚举/扫描器，但仍应按不可信输入处理。

### 6.3 当前状态与验证分类

- **状态：未修复**
- **验证分类：仅静态确认**
  - 代码路径可直接确认；
  - 没有 CountView 未知键的限长/控制字符测试。

### 6.4 已有测试证据

- `tests/test_report_html.py:666` `test_untrusted_text_fields_are_bounded_and_control_chars_removed`：
  - 只覆盖 `title`、`warnings`、`data_scope`、`known_limitations`；
  - **不覆盖** `CountView`。
- `tests/test_report_html.py:702` `test_warning_list_is_bounded`：
  - 只覆盖 warnings 数量；
  - **不覆盖** 统计键。
- 没有 `task_scanner_counts` / `scanner_counts` / 未知枚举键的 XSS/长度测试。

### 6.5 尚缺少的验证

1. 构造未知 `task_scanner_counts` 键（超长、含 NUL/控制字符）；
2. 构造未知 `scanner_counts` 键；
3. 验证 View Model 中的 label 已限长/清理；
4. 验证模板输出仍 autoescape；
5. 验证统计总数/排序不受清理影响。

### 6.6 建议处理阶段

- 建议在 Phase 6C-2B 的展示层收尾或 C2B 后 卫生加固中统一处理；
- 不要求本轮修改，也不影响 C2B 主流程；
- 处理时应统一走 `_bounded_text()`，不要只截断 HTML。

### 6.7 是否阻塞 C2B

**否。**

- 不影响 HTML 导出主流程；
- 不要求本轮修复；
- 但 C2B 不应声称“所有统计标签均已限长”。

---

## 7. DEBT-05：SEC-05 临时文件清理失败被静默忽略

### 7.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:720-725`：
  - `_publish_exclusive()` 成功后执行 `temporary.unlink()`；
  - `except OSError: pass`；
- `reports/html_exporter.py:732-736`：
  - `finally` 中再次 `temporary.unlink(missing_ok=True)`；
  - `except OSError: pass`；
- 优点：
  - 旧文件不会被截断；
  - 失败不会覆盖目标；
  - `KeyboardInterrupt` 模拟路径已动态通过。
- 缺口：
  - 清理失败没有日志、计数或返回标记；
  - 成功发布后 unlink 失败会留下临时文件；
  - `finally` 的清理失败也被静默忽略；
  - 没有磁盘空间/权限不足的专门测试。

### 7.2 风险等级

**低。**

- 影响为临时文件残留、磁盘占用和潜在的敏感内容残留；
- 临时文件位于目标目录，后缀 `.tmp`；
- 不会导致目标覆盖或代码执行；
- 若临时文件包含报告内容，长期残留属于清洁性/隐私风险。

### 7.3 当前状态与验证分类

- **状态：未修复**
- **验证分类：仅静态确认（清理失败分支）+ 部分动态（`KeyboardInterrupt` 成功清理）**
- 清理失败路径没有动态验证。

### 7.4 已有测试证据

- `tests/test_report_html.py:637` `test_keyboard_interrupt_cleans_temp_and_preserves_old_file`：
  - 模拟 `os.replace` 抛 `KeyboardInterrupt`；
  - 断言旧文件不变、无 `.tmp` 残留；
  - **PASS**；
- `tests/test_report_html.py:447` `test_failed_replace_preserves_old_file_and_cleans_temp`（历史）：
  - 普通替换失败路径；
  - 断言旧文件保留、临时文件清理；
- **没有** unlink 失败测试；
- **没有** 磁盘满/权限拒绝测试；
- **没有** 进程强杀清理测试。

### 7.5 尚缺少的验证

1. monkeypatch `Path.unlink` 抛 `OSError`，验证不会误删目标、不会抛未处理异常；
2. 验证清理失败是否应记录审计/日志（当前没有）；
3. 验证 `overwrite=True` 成功替换后的临时清理失败；
4. 验证 `.tmp` 文件不会进入后续报告列表；
5. 验证强制终止后的残留是否可被启动清理策略发现（若未来增加）。

### 7.6 建议处理阶段

- C2B 后 清洁性/运维加固；
- 不要求 C2B 前修复；
- 若报告包含敏感内容，应把临时文件残留纳入隐私评估；
- 不应把 `except OSError: pass` 静默失败描述为“清理保证”。

### 7.7 是否阻塞 C2B

**否。**

- 不影响正确性/路径安全的核心流程；
- 需要在 C2B 风险说明中保留；
- 不要求本轮改代码。

---

## 8. DEBT-06：SEC-01 缺少真实双进程并发测试

### 8.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:675-698` `_publish_exclusive()`：
  - 使用 `os.link(temporary, target)`；
  - 目标存在时抛 `FileExistsError`；
  - 不支持硬链接时抛 `ReportExportError`；
  - 无 `os.replace()` 回退。
- `reports/html_exporter.py:701-736` `_atomic_write()`：
  - `overwrite=False` 调用 `_publish_exclusive()`；
  - 成功后删除临时文件。

**已验证：**

- 模拟竞态：monkeypatch 在 `os.link()` 前写入目标，断言 `FileExistsError`，并保留并发内容；
- 不支持硬链接：断言失败关闭，无目标、无 `.tmp`。

**缺口：**

- 没有两个真实进程同时调用 `write_html_report()`；
- 没有多进程/多线程真正竞争同一目标；
- 没有在真实 Windows 文件系统上验证 `CreateHardLinkW` 的并发语义；
- 当前 PASS 是“核心排他原语 + 模拟测试”，不是“真实并发测试通过”。

### 8.2 风险等级

**低。**

- 核心实现使用操作系统原子 `link`，风险低于 `exists()` + `replace()`；
- 缺少测试本身不是已确认漏洞；
- 但测试缺口可能掩盖平台差异/错误映射问题。

### 8.3 当前状态与验证分类

- **状态：未修复（测试缺口）**
- **验证分类：仅静态确认 + 模拟动态**
- 不是 UNKNOWN 的核心安全状态；核心排他发布已实现，真实并发行为未验证。

### 8.4 已有测试证据

| 测试 | 位置 | 结果 |
|---|---|---|
| `test_overwrite_false_race_is_rejected_by_exclusive_publish` | `tests/test_report_html.py:579` | PASS（模拟） |
| `test_no_overwrite_fails_closed_without_hardlink_support` | `tests/test_report_html.py:609` | PASS |
| `test_write_refuses_overwrite_and_preserves_old_file` | `tests/test_report_html.py:398` | PASS（顺序） |

### 8.5 尚缺少的验证

1. 两个独立 Python 进程几乎同时写同一目标；
2. 验证只有一个成功，另一个得到 `FileExistsError`；
3. 验证最终文件内容属于成功者；
4. 验证无 `.tmp` 残留或明确记录残留；
5. 验证 Windows 文件系统和 CI 临时目录上的行为；
6. 验证 `overwrite=False` 和 `overwrite=True` 的差异（后者允许替换，不是排他）。

### 8.6 建议处理阶段

- Phase 6C-2B 测试加固或 C2B 后；
- 不要求 C2B 前修复；
- 不应为了让测试变绿而把模拟测试描述成真实并发。

### 8.7 是否阻塞 C2B

**否。**

- 核心排他发布逻辑已实现；
- 测试缺口不影响 C2B 主流程；
- 若 C2B 引入并发导出，必须升级为阻塞项并补真实并发测试。

---

## 9. DEBT-07：SEC-03 尚未增加 CSP

### 9.1 当前事实与证据

- `reports/templates/base.html:1-6` 只有：
  - `<!DOCTYPE html>`；
  - `<html lang="zh-CN">`；
  - `<head>`；
  - `<meta charset="utf-8">`；
  - `<meta name="viewport" ...>`；
  - `<title>{{ view.title }}</title>`。
- **没有** `<meta http-equiv="Content-Security-Policy" ...>`。
- 模板中没有 `<script>`、没有远程 `src`/`href`、没有事件属性；样式为内联 `<style>`。
- 因此当前风险是“纵深防御缺失”，不是已确认的脚本注入。

### 9.2 风险等级

**低。**

- 没有脚本/远程资源，autoescape 仍生效；
- 若未来模板或富文本扩展引入脚本/外部资源，缺少 CSP 会增加影响；
- 当前报告是本地文件，不是远程 HTTP 服务。

### 9.3 当前状态与验证分类

- **状态：未修复**
- **验证分类：仅静态确认**
  - 模板静态可确认没有 CSP；
  - 没有 CSP 相关测试；
  - 没有浏览器加载测试。

### 9.4 已有测试证据

- 模板静态检查（历史 `tests/test_report_html.py` 中无脚本/无远程资源测试）覆盖“没有脚本/远程资源”；
- **没有** CSP 断言；
- **没有** 浏览器/HTTP 头测试。

### 9.5 尚缺少的验证

1. 为报告 HTML 增加 CSP 后，验证样式和排版仍正常；
2. 验证 CSP 不依赖外部字体/图片；
3. 验证 `script-src 'none'`、`object-src 'none'`、`base-uri 'none'` 等策略；
4. 验证本地文件 `file://` 与未来可能的本地 HTTP 预览行为差异；
5. 验证历史报告仍可打开。

### 9.6 建议处理阶段

- C2B 后 纵深防御加固；
- 不要求 C2B 前修复；
- 不得声称“CSP 已存在”；
- 若 C2B 引入脚本/交互/远程资源，必须重新评估并升级。

### 9.7 是否阻塞 C2B

**否。**

- 当前无脚本/远程资源，CSP 是增强项；
- C2B 不应因为“没有 CSP”被描述为“已完全安全”；
- 若 C2B 改变内容模型，需重新评估。

---

## 10. DEBT-08：SEC-06 报告自由文本没有语义脱敏

### 10.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:450-481` `_finding_view()`：
  - `title`、`category`、`description`、`recommendation`、`manual_notes` 等均走 `_bounded_text()`；
- `reports/html_exporter.py:484-499` `_evidence_view()`：
  - `description`、`source_text`、`file_name` 等走 `_bounded_text()`/`_safe_relative_path()`；
- `_bounded_text()` 只做：
  - 删除控制字符；
  - `.strip()`；
  - 截断到 2,000 字符；
- **没有**：
  - 密钥/令牌/密码识别；
  - 邮箱/手机号/身份证脱敏；
  - 自定义敏感词策略；
  - 用户确认/遮盖步骤。

**已有保护：**

- Jinja2 autoescape 阻止 HTML 注入；
- 报告是本地文件，不上传；
- 证据中心已有“可能包含密钥、凭据、个人信息”的提示（产品层）。

**缺口：**

- 自由文本按原样进入 HTML；
- 语义敏感信息（例如描述中的 token、密码、内网路径、个人数据）不会被自动遮盖；
- 自动脱敏可能破坏安全证据的可读性，因此当前是设计边界，不是简单 bug。

### 10.2 风险等级

**中（隐私/数据暴露）。**

- 报告可能包含扫描结果中的敏感片段；
- 报告被分享/归档时可能扩大暴露面；
- 不是远程上传或代码执行；
- 当前默认本地生成，风险取决于用户后续分发。

### 10.3 当前状态与验证分类

- **状态：设计边界**
- **验证分类：已知设计限制（静态确认）**
- 不是“已脱敏”，也不是“待修复的注入漏洞”。

### 10.4 已有测试证据

- `tests/test_report_html.py` 中的 XSS/autoescape 测试覆盖 HTML 转义；
- **没有** 语义脱敏测试；
- **没有** 敏感字段遮盖测试；
- **没有** 导出前提示/确认测试（当前报告层没有该交互）。

### 10.5 尚缺少的验证/决策

1. 明确报告是否允许包含原始证据文本；
2. 定义敏感信息类型和遮盖策略；
3. 定义“安全证据完整性”和“隐私脱敏”的优先级；
4. 验证遮盖后报告仍可用于复现；
5. 验证用户确认/审计记录；
6. PDF 导出已取消，不再作为后续评估项；JSON 报告导出是独立决策且尚未获批，不与 SubmissionDraft JSON persistence 混同。

### 10.6 建议处理阶段

- Phase 6C-2B 产品/隐私决策，或生产发布前；
- 不要求本轮修改；
- C2B 不应声称“报告已语义脱敏”；
- 若未来增加远程分享/自动上传，必须重新评估并升级为阻塞项。

### 10.7 是否阻塞 C2B

**否（当前本地 HTML 范围）**，但属于**产品发布前必须明确的风险**。

- 不阻塞 C2B 的 HTML 核心实现；
- 不应把 autoescape 当成脱敏；
- 必须在 C2B 风险说明和用户提示中保留。

---

## 11. DEBT-09：SEC-07 Windows 设备名实际写入行为未验证

### 11.1 当前事实与证据

**代码位置：**

- `reports/html_exporter.py:643-662` `_validate_filename()`：
  - 拒绝 `/`、`\`、`:`；
  - 拒绝 `?*<>|"`；
  - 拒绝空名、`.`、`..`；
  - 要求 `.html` 后缀；
  - 长度 ≤180；
  - 拒绝控制字符；
  - 取第一个 `.` 前主干，去除尾部空格/点，转大写后检查保留设备名；
- `reports/html_exporter.py:74-86` 保留集合：
  - `CON`、`PRN`、`AUX`、`NUL`、`CLOCK$`、`CONIN$`、`CONOUT$`、`COM1..COM9`、`LPT1..LPT9`。

**已有验证：**

- `tests/test_report_html.py:713-746` 参数化 14 个名称，均断言 `ValidationError` 且输出目录为空；
- 覆盖 `NUL.html`、`nul.html`、`CON.html`、`PRN.html`、`AUX.html`、`COM1.html`、`LPT9.html`、`CONIN$.html`、`report?.html`、`report*.html`、`report<.html`、`report>.html`、`report|.html`、`report".html`。

**缺口：**

- 没有真正尝试写 `NUL.html`/`CON.html` 到 Windows 设备；
- 没有验证设备名在大小写、尾部点/空格、Unicode 变体下的系统行为；
- 校验层已经拒绝，因此不应为了测试实际写设备名。

### 11.2 风险等级

**低。**

- 文件名校验已覆盖主要保留名和非法字符；
- 实际设备写入未验证，但不应绕过校验；
- 潜在影响是异常路径/设备访问，而不是已确认的远程漏洞。

### 11.3 当前状态与验证分类

- **状态：UNKNOWN**
- **验证分类：UNKNOWN（校验动态通过；运行时设备行为未验证）**
- 不能写成“设备名已实际验证安全”。

### 11.4 已有测试证据

- `tests/test_report_html.py:713-746`：14 个参数化非法名称，**PASS**（校验层）；
- 没有实际设备写测试；
- 没有 Windows API/文件系统边界测试。

### 11.5 验证边界

1. 保留 `tests/test_report_html.py:713-746` 的校验层测试；
2. 可验证大小写、尾部点/空格、Unicode 归一化变体（仅名称校验层）；
3. 可静态核对 `_validate_filename()` 与实际文件系统错误码的一致性；
4. 不要求、也不建议实际写入 `NUL.html`、`CON.html` 等 Windows 保留设备名；
5. 实际设备行为保持 **UNKNOWN**，不得写成 PASS。

### 11.6 建议处理阶段

- C2B 后 测试加固；
- 不要求 C2B 前修复；
- 不建议为了关闭 UNKNOWN 而在普通开发环境写设备名；
- 实际设备行为保持 UNKNOWN；本轮不安排任何实际设备写入验证。

### 11.7 是否阻塞 C2B

**否。**

- 校验已拒绝保留名；
- C2B 不依赖实际设备写入；
- 但 C2B 文档不得声称“设备名运行时已验证”。

---

## 12. 必须先处理与可后续处理

### 12.1 绝对必须先处理

**无。**

当前 9 项中：

- 没有 Critical/High；
- 没有已确认的远程利用或代码执行；
- 没有必须在 C2B 前无条件修复的 P0/P1。

### 12.2 条件性门禁

以下两项在 C2B **扩大输出路径能力**时升级为必须先处理：

1. **DEBT-01 父级 reparse point**
   - 触发条件：用户自定义 `reports_dir`、目录选择器、路径参数、可配置父目录；
   - 要求：定义并实现父级 reparse 策略，或限制为受信任根目录。
2. **DEBT-02 root/叶节点 symlink 动态验证**
   - 触发条件：允许 symlink 路径、用户目录、不可信路径；
   - 要求：补齐 root/叶节点 symlink 动态测试，保留 UNKNOWN 直到验证完成。

### 12.3 可后续处理

| 项目 | 建议阶段 | 理由 |
|---|---|---|
| DEBT-03 TOCTOU | C2B 条件重评 / C2B 后 路径加固 | 当前单写者、固定目录；并发/路径能力变化时升级 |
| DEBT-04 CountView | C2B 收尾或 C2B 后 | 展示层卫生；autoescape 已存在 |
| DEBT-05 清理失败 | C2B 后 运维加固 | 残留/清洁性问题，不影响目标正确性 |
| DEBT-06 真实并发测试 | C2B 测试加固 | 核心原语已实现；测试缺口 |
| DEBT-07 CSP | C2B 后 纵深防御 | 当前无脚本/远程资源 |
| DEBT-08 语义脱敏 | C2B 产品决策 / 生产前 | 设计边界，不是自动修复项 |
| DEBT-09 设备写入 | C2B 后 测试加固 | 校验已拒绝；不建议实际写设备名 |

---

## 13. 与综合收尾审查报告的一致性

与 `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md` 对照，**没有发现实质性状态矛盾**，但有以下范围澄清：

1. **SEC-01**
   - 综合报告：**PASS**（核心排他发布）；
   - 本台账：DEBT-06 记录“缺少真实双进程并发测试”；
   - 关系：核心实现 PASS，测试完整性仍有低风险缺口；不是把 SEC-01 改判为失败。

2. **SEC-02**
   - 综合报告：**PASS_WITH_LIMITATIONS**；
   - 本台账拆成 DEBT-01（父级）、DEBT-02（symlink 动态）、DEBT-03（TOCTOU）；
   - 关系：拆分不改变总体 `PASS_WITH_LIMITATIONS`；三项不能合并成一个 PASS。

3. **SEC-04**
   - 综合报告：**PASS**，但明确限定于 `title`、`warnings`、`data_scope`、`known_limitations`；
   - 本台账：DEBT-04 记录 `CountView` 附加 LOW 残余；
   - 关系：不矛盾；SEC-04 的 PASS 不是“所有文本字段均已覆盖”。

4. **SEC-05**
   - 综合报告：**PASS**（`KeyboardInterrupt` 模拟清理）；
   - 本台账：DEBT-05 记录清理失败被静默忽略；
   - 关系：正常/模拟清理 PASS，失败分支仍是已知残余。

5. **SEC-07**
   - 综合报告：**PASS**（校验逻辑）；实际设备写入 UNKNOWN；
   - 本台账：DEBT-09 保持 UNKNOWN；
   - 关系：一致，没有把 UNKNOWN 写成 PASS。

6. **SEC-03、SEC-06**
   - 综合报告已记录未修复/设计边界；
   - 本台账 DEBT-07、DEBT-08 保持原风险性质，没有宣称已解决。

**结论：无不一致；只是综合报告按“五项修复”汇总，本台账按“九个遗留项”拆分并明确范围。**

---

## 14. 实际修改文件清单

**本轮只新增：**

```text
docs/PHASE6_C2A_SECURITY_DEBT.md
```

**未修改：**

- Python 生产源码：`reports/html_exporter.py` 等；
- 测试：`tests/test_report_html.py` 等；
- 数据库：`storage/src_research.db`、`storage/phase5_acceptance/acceptance.db`；
- Schema：`database/schema.py`；
- HTML 模板：`reports/templates/*.html`；
- GUI：`ui/*`；
- 配置：`app/config.py` 等；
- Phase 5 / Phase 6 既有验收归档。

**文件核对：**

```text
reports/html_exporter.py
  24,132 bytes
  SHA-256 593E4F67928BAEF698BC52111BB19C868D28F3AB574617A50916C77159BE7C18

tests/test_report_html.py
  23,880 bytes
  SHA-256 72755296ED04E1E070AF9A30A418D6E8BCDE7FBF665215E0375F5EC39ACD5C42
```

上述哈希与本轮开始时一致，说明未修改。

**本轮未运行测试回归，未打开或写入业务数据库，未修改 Schema。**

---

## 15. 停止状态

```text
Phase 6C-2A 安全遗留问题台账：completed
Phase 6C-2A 安全加固：记录性关闭建议，CLOSED_WITH_RECORDED_LIMITATIONS
Phase 6C-2B：未开始，未获本轮授权
本轮修改：仅 docs/PHASE6_C2A_SECURITY_DEBT.md
```

本台账是**遗留问题清单**，不是修复完成证明。所有“建议”均未实施；所有 UNKNOWN 均未转成 PASS。
