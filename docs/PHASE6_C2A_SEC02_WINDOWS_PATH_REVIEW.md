# Phase 6C-2A SEC-02 Windows 路径安全专项验证

## 0. 结论摘要

- **结论：PASS_WITH_RISK / FAIL（root reparse point）**
- 外部叶节点 junction：**PASS（拒绝，不写出 root）**。
- 内部叶节点 junction：**PASS（当前目录目标被拒绝；没有外部写入）**；内部文件 symlink 仍为 **UNKNOWN**。
- 断链叶节点 junction：**PASS（拒绝，不写出 root）**；断链 symlink 为 **UNKNOWN**。
- `reports_dir` 自身为 junction：**FAIL/RISK**。代码先 `resolve()`，未拒绝 reparse point；实际将报告写入 junction 的真实目标目录，而不是拒绝该配置。
- 原生 symlink 创建在当前 Windows 会话因权限不足失败（“此操作需要管理员权限。”）；未通过修改 ACL/安全策略绕过，因此 symlink 专属路径标记 **UNKNOWN**，不能标记 PASS。
- 本次未修改生产代码、测试、数据库、Schema、模板或 GUI；只新增本报告。

## 1. 验证范围与依据

参考：

- `docs/PHASE6_C2A_SECURITY_REVIEW_1.md`
- `docs/PHASE6_C2A_SECURITY_FIX_1.md`
- `docs/PHASE6_C2A_SECURITY_FIX_1_REVIEW_EVIDENCE.md`

检查对象：

- `reports/html_exporter.py`
- 运行时 Windows 文件系统行为；临时目录中的无害测试文件、junction 和测试报告

验证原则：

- 不修改系统 ACL、权限或安全策略。
- 不修改 `reports/html_exporter.py`、测试、数据库、模板或 GUI。
- 无法验证的 symlink 项目标记 **UNKNOWN**，不写成 PASS。
- 只使用独立临时目录：`D:\挖漏洞\pytest_c1r_tmp\sec02_paths`。
- 测试文件内容仅为 `OUTSIDE_MARKER` 等无害标记，不含真实业务数据。

## 2. 静态源码分析

### 2.1 root 解析

`reports/html_exporter.py:627-638`：

```python
def _resolve_reports_root(reports_dir: str | Path) -> Path:
    root = Path(reports_dir).expanduser()
    if not root.is_absolute():
        raise ValidationError("报告输出目录必须是绝对路径")
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

- `root.resolve()` 会跟随 `reports_dir` 自身的 symlink/junction。
- 没有检查 `Path(reports_dir).is_symlink()` 或 `Path(reports_dir).is_junction()`。
- 因此，`reports_dir` 若是 reparse point，代码会把真实目标当作 root，而不是拒绝它。

### 2.2 目标路径检查

`reports/html_exporter.py:341-360`：

```python
    if not isinstance(request, ReportRequest):
        raise ValidationError("报告请求类型无效")
    html = render_html(snapshot, request)
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

关键点：

- 叶节点通过 `(root / target_name).resolve()` 解析；目标若指向 root 外的 junction/symlink，`target.relative_to(root)` 会失败并抛出 `ValidationError`。
- 该检查依赖 `root` 已经是 `root.resolve()` 后的真实路径；它没有保留“用户传入的 lexical root”用于比较。
- 对断链 reparse point，Windows `Path.resolve()` 的返回值可能落在 `\\?\Global\...` 命名空间；`relative_to(root)` 会因字符串路径前缀不同而失败，这是实际观察到的情况。

### 2.3 最终发布

`reports/html_exporter.py:673-696` 的 `_publish_exclusive()`：

- `overwrite=False` 使用 `os.link(temporary, target)` 原子发布；
- 目标已存在时失败；
- 不支持硬链接时抛 `ReportExportError`，没有 `os.replace()` 回退。

`reports/html_exporter.py:699-734` 的 `_atomic_write()`：

- 同目录创建临时文件；
- `write` → `flush` → `fsync` → 关闭；
- `overwrite=False` 调用 `_publish_exclusive()`；
- 失败路径在 `finally` 清理临时文件。

最终发布逻辑本身不会重新解析或逃出 `target`；本次风险集中在 `target` 如何由 root 和叶节点解析出来。

## 3. 动态测试环境与限制

### 3.1 临时目录

```text
D:\挖漏洞\pytest_c1r_tmp\sec02_paths\
├── reports\                 # 正常 reports_dir
│   ├── internal_dir\        # 内部目录
│   ├── junction_external.html   # junction → outside
│   ├── junction_internal.html   # junction → reports\internal_dir
│   ├── broken_external.html     # 先建 junction，再删除外部目标
│   └── broken_internal.html     # 先建 junction，再删除内部目标
├── outside\                 # 外部目录，含 outside_file.html
├── outside_root\            # 外部 root 目标
└── root_junction\           # junction → outside_root
```

### 3.2 Windows 链接创建结果

Junction 创建成功：

```text
mklink /J reports\junction_external.html outside
JUNCTION_EXIT=0

mklink /J reports\junction_internal.html reports\internal_dir
INTERNAL_JUNCTION_EXIT=0

mklink /J root_junction outside_root
ROOT_JUNCTION_EXIT=0
```

Symlink 创建失败：

```text
New-Item -ItemType SymbolicLink ...
SYMLINK_CREATE=FAILED: 此操作需要管理员权限。
```

未尝试 `takeown`、ACL 重置、开发者模式或提权；因此：

- **junction 动态结果可用**；
- **symlink 专属结果标记 UNKNOWN**，不能把 junction 结果当成 symlink 结果；
- 断链 junction 的构造方式是先创建指向有效目录的 junction，再删除目标目录；对断链 symlink 的同样构造未执行成功。

## 4. 四种路径情况的实际验证

测试调用统一为：

```python
html_exporter.write_html_report(
    _snapshot(ReportType.PROJECT_SUMMARY),
    _request(ReportType.PROJECT_SUMMARY),
    reports_dir,
    filename=filename,
)
```

使用测试模块中的内存快照/请求 fixture；不访问数据库、scanner 或真实证据。

### 4.1 情况一：reports_dir 内指向外部的 symlink/junction

测试对象：

```text
reports\junction_external.html  ->  outside\
```

实际结果：

```text
case=external_junction_leaf
outcome=ERROR
exception_type=ValidationError
exception_message=报告目标路径越界
outside_before=['outside_file.html']
outside_after=['outside_file.html']
```

结论：

- **junction：PASS（containment 拒绝）**。目标解析到 `outside`，被 `relative_to(root)` 拒绝；外部目录没有新增报告文件。
- **symlink：UNKNOWN**。当前会话无法创建 symlink；静态逻辑同样是 `resolve()` 到外部后被拒绝，但没有动态证据。
- 该结果只覆盖“叶节点为目录 junction”的情况；外部**文件 symlink** 未动态验证。

### 4.2 情况二：reports_dir 内指向内部位置的 symlink/junction

测试对象：

```text
reports\junction_internal.html  ->  reports\internal_dir
```

实际结果：

```text
case=internal_junction_leaf
outcome=ERROR
exception_type=FileExistsError
exception_message=目标报告已存在，未覆盖: ...\reports\internal_dir
outside_before=['outside_file.html']
outside_after=['outside_file.html']
```

结论：

- **内部目录 junction：PASS（没有外部写入）**，但拒绝原因是目标目录已存在（`overwrite=False`），不是“识别并拒绝 reparse point”。
- **内部文件 symlink：UNKNOWN**。没有可用的文件 symlink，无法验证“链接指向内部另一个文件”时最终写到哪个路径。
- 不能把“目录 junction 被 FileExistsError 拒绝”描述成“所有内部 symlink 都被安全拒绝”。

### 4.3 情况三：指向不存在目标的断链 symlink/junction

测试对象：

```text
reports\broken_external.html  ->  outside\broken_ext_target   （目标已删除）
reports\broken_internal.html  ->  reports\broken_int_target   （目标已删除）
```

两个 junction 均保持为 `is_junction() == True`、`exists() == False`。

实际结果：

```text
case=broken_external_junction_leaf
outcome=ERROR
exception_type=ValidationError
exception_message=报告目标路径越界
outside_before=['outside_file.html']
outside_after=['outside_file.html']

case=broken_internal_junction_leaf
outcome=ERROR
exception_type=ValidationError
exception_message=报告目标路径越界
outside_before=['outside_file.html']
outside_after=['outside_file.html']
```

内部断链 junction 的解析细节：

```text
lexical   = D:\...\reports\broken_internal.html
resolved  = \\?\Global\D:\...\reports\broken_int_target
parent    = \\?\Global\D:\...\reports
relative_to(root) -> ValueError
```

结论：

- **断链 junction：PASS（拒绝，未写文件）**；外部和内部断链 junction 都被拒绝。
- 内部断链 junction 的拒绝来自 Windows `resolve()` 返回 `\\?\Global\...` 命名空间导致 `relative_to()` 失败，而不是显式的“断链检测”；这是 fail-closed 的副作用，不应被当成稳定的显式策略。
- **断链 symlink：UNKNOWN**；当前会话无法创建 symlink，无法确认其 `resolve()` 返回形式与 junction 一致。

### 4.4 情况四：reports_dir 自身是 junction/reparse point

测试对象：

```text
root_junction  ->  outside_root
reports_dir 参数 = root_junction
filename = root_junction.html
```

实际结果：

```text
case=reports_dir_is_junction
outcome=SUCCESS
artifact_path=D:\挖漏洞\pytest_c1r_tmp\sec02_paths\outside_root\root_junction.html
artifact_exists=true
resolved_reports_dir=D:\挖漏洞\pytest_c1r_tmp\sec02_paths\outside_root
outside_root_before=[]
outside_root_after=['root_junction.html']
```

结论：

- **FAIL/RISK**：代码没有拒绝 `reports_dir` 自身的 junction；它先 `root.resolve()` 到 `outside_root`，随后在该真实目录中写入报告。
- 文件在物理上写入了 junction 的目标目录 `outside_root`，而不是停留在 lexical 路径 `root_junction` 下。
- 这不是 filename 穿越：`target.relative_to(root)` 仍通过，因为 `root` 已经被解析为 `outside_root`。
- 可利用性取决于攻击者是否能控制或替换 `reports_dir`；如果配置目录来自可信配置，风险较低；如果该目录可被低权限用户替换为 junction，输出可被重定向到攻击者选择的可写目录。
- **root symlink 的同类行为：UNKNOWN**（无法创建 symlink）；静态路径与 junction 相同，都是 `root.resolve()` 后继续写入，没有 reparse 拒绝。

## 5. 结果分类

| 情况 | 动态结果 | 分类 |
|---|---|---|
| 外部叶节点 junction | `ValidationError`，外部无新增文件 | PASS（containment） |
| 外部叶节点 symlink | 无法创建 symlink | UNKNOWN |
| 内部叶节点目录 junction | `FileExistsError`，无外部写入 | PASS（无外部写入） |
| 内部叶节点文件 symlink | 无法创建 symlink | UNKNOWN |
| 外部断链 junction | `ValidationError`，无写入 | PASS（拒绝） |
| 内部断链 junction | `ValidationError`，无写入 | PASS（拒绝，依赖 `\\?\Global` 解析行为） |
| 断链 symlink（外部/内部） | 无法创建 symlink | UNKNOWN |
| reports_dir 自身 junction | 成功写入 junction 目标目录 | FAIL/RISK |
| reports_dir 自身 symlink | 无法创建 symlink；静态同类风险 | UNKNOWN |

## 6. 风险与建议

### 6.1 已确认的风险

1. **root reparse point 未拒绝（主要风险）**
   - `_resolve_reports_root()` 只做 `root.resolve()`，没有检查 `is_symlink()` / `is_junction()`。
   - 若攻击者可替换 `reports_dir`，报告会被写入攻击者选择的真实目录。
   - 当前测试使用无害目录；未测试对敏感目录的写入，也未尝试提权或 ACL 修改。

2. **内部叶节点链接的语义未被显式定义**
   - 目录 junction 当前因 `overwrite=False` 且目标已存在而失败；这不是专门的 reparse 拒绝。
   - 内部文件 symlink 若解析到 root 内另一个文件，静态上会通过 `relative_to` 和 `parent` 检查；是否允许这种别名写入需要产品决策。
   - 本次没有文件 symlink，标记 UNKNOWN。

3. **断链检测依赖 `\\?\Global` 解析副作用**
   - 断链 junction 被拒绝是实际结果，但拒绝原因不是显式 `lexists`/断链检查，而是 `resolve()` 返回命名空间路径后 `relative_to()` 失败。
   - 不同 Python/Windows 版本是否保持同样解析形式，本次未验证；断链 symlink 仍为 UNKNOWN。

### 6.2 建议

- 如果要求 `reports_dir` 必须是真实目录：在 `_resolve_reports_root()` 中显式拒绝 `Path(reports_dir).is_symlink()` 和 `Path(reports_dir).is_junction()`（或显式允许并记录信任边界）。
- 如果允许 root reparse point：在文档中明确“reports_dir 的真实目标即信任根”，不要把它描述为“不会写出 reports_dir”。
- 对叶节点可另行考虑显式拒绝 reparse point，或明确只允许解析后的 root 内部目标；当前外部叶节点已被拒绝，内部别名行为需要产品决策。
- 增加可在 CI 运行的 Windows junction 测试；symlink 测试在没有 `SeCreateSymbolicLinkPrivilege` 的环境中应标记 skip/UNKNOWN，而不是伪造 PASS。
- 对断链入口使用显式 `lexists`/`is_symlink`/`is_junction` 策略，避免依赖 `\\?\Global` 字符串行为。

## 7. 是否需要下一轮最小代码修复

**需要，但本轮不执行。**

建议下一轮只做一个最小修复：

1. 在 `_resolve_reports_root()` 拒绝 `reports_dir` 自身为 symlink/junction（如果产品要求 root 必须是真实目录）；并增加对应 Windows junction 测试。
2. 若要覆盖内部叶节点别名，增加显式叶节点 reparse 检查/测试；这属于行为定义扩展，不应与 root 修复混在一起。

本轮不修改 `reports/html_exporter.py`，不自动修复；等待审核决定是否进入下一轮。

## 8. 只读性与环境确认

- 未修改 `reports/html_exporter.py`、`tests/test_report_html.py`、数据库、Schema、模板或 GUI。
- 未打开或写入 SQLite；未执行迁移；未运行 pytest。
- 未修改系统 ACL、权限或安全策略；symlink 创建失败后没有尝试提权。
- 临时目录：`D:\挖漏洞\pytest_c1r_tmp\sec02_paths`；测试文件为无害标记文件。
- 新增文件仅为：`docs/PHASE6_C2A_SEC02_WINDOWS_PATH_REVIEW.md`。

## 9. 最终分类

| 项目 | 结果 |
|---|---|
| 外部叶节点 junction containment | **PASS** |
| 外部叶节点 symlink containment | **UNKNOWN** |
| 内部叶节点 junction 无外部写入 | **PASS**（仅当前目录目标 fixture） |
| 内部叶节点文件 symlink | **UNKNOWN** |
| 断链 junction 拒绝 | **PASS** |
| 断链 symlink 拒绝 | **UNKNOWN** |
| reports_dir 自身 junction | **FAIL/RISK** |
| reports_dir 自身 symlink | **UNKNOWN**（静态同类风险） |

**总体：PASS_WITH_RISK；root reparse point 需要下一轮最小修复审查，symlink 专属行为仍不能声称已通过。**
