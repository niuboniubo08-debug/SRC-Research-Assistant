# Windows 打包前 P1 安全问题最终核验

- 调查时间：2026-11-14 21:12 +08:00（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前 Git：branch `main`；HEAD `d6e326b42675d56c5d6523a68f87bc78cd9bef45`；提交主题 `docs: add global status audit and Windows packaging roadmap`
- 工作区：`git status --porcelain` 为空（干净）
- 版本：`0.5.0`；Schema：v5
- 调查性质：只读源码、测试与安装包实现核验
- 实际修改：仅新增本报告
- 运行测试 / 扫描器 / GUI：均未运行
- 构造 symlink / junction / reparse point：未进行

> 本文只核验代码与现有证据，不把历史测试结论当作当前运行结果，也不把 monkeypatch 测试当作真实 Windows 文件系统验证。

## 1. 调查范围与方法

本轮只核验全局进度报告提出的四项 P1：

1. Evidence 根目录路径安全；
2. Bandit `env` 排除规则；
3. ScopeValidator 符号链接语义；
4. HTML 报告输出路径安全。

方法：

- 读取当前生产代码的调用链、路径规范化、目录创建、文件写入和删除逻辑；
- 读取现有测试的断言、skip 条件和真实/模拟边界；
- 读取已安装 Bandit 1.9.4 的排除规则实现；
- 仅执行只读 Git 查询与文件哈希；
- 不运行 pytest、Bandit、pip-audit、GUI，也不创建恶意链接。

证据级别标记：

- `CONFIRMED`：当前代码或已有真实测试直接证明；
- `NOT_REPRODUCED`：当前没有证据证明问题成立；
- `MITIGATED`：已有防护，但存在明确限制；
- `OPEN`：已确认且尚未解决；
- `UNKNOWN`：现有证据不足。

## 2. P1-01：Evidence 根目录路径安全

### 2.1 代码事实

`services/evidence_service.py` 的构造：

```python
self._root = Path(evidence_root).expanduser().resolve()
self._root.mkdir(parents=True, exist_ok=True)
```

- `services/evidence_service.py:61-63`：证据根目录在启动时被 `resolve()`，但**没有拒绝**根本身是 symlink / junction / reparse point；只解析到目标并创建。
- `services/evidence_service.py:253-269`：每个项目的证据目录是
  `project_dir = self._root / f"project_{project_id}"`；
  `project_dir.mkdir(parents=True, exist_ok=True)` **不检查它是否已是 junction/symlink**。
- `services/evidence_service.py:260-268`：随后用 `shutil.copy2(source, target)` 写入 `project_dir / uuid_name`；
  最后只比较：

```python
if target.parent.resolve() != project_dir.resolve():
    ...
```

  如果 `project_dir` 本身是指向外部目录的 junction，则 `target.parent.resolve()` 与 `project_dir.resolve()` **都等于外部目录**，比较通过，文件已经写到证据根目录之外。
- `services/evidence_service.py:271-284`：删除时 `_unlink_managed()` 用 `relative_to(self._root)` 限制删除范围；但上述越界副本的最终 `resolve()` 在 `_root` 外，删除会失败，形成“写入成功、删除失败”的不一致状态。

### 2.2 风险成立条件

1. 攻击者/本地用户能在证据根目录下创建或替换 `project_<id>` 为 junction / symlink / 其他 reparse point；
2. 应用随后以同一用户或更高权限运行；
3. 用户导入一个位于已授权项目根目录内的合法证据文件。

满足后，证据副本会被写到证据根目录之外。该路径不是任意用户可控的完整输出路径，文件名由 UUID 生成，因此主要风险是**证据存储边界逃逸、意外写入和删除失败**，不是任意覆盖已有文件。

### 2.3 现有防护与测试

已有防护：

- `_validate_source_file()` 拒绝源文件是 symlink，且要求最终 `resolve()` 位于项目授权根目录内；
- `_copy_into_evidence_store()` 对最终父目录做了一次 `resolve()` 比较；
- `_unlink_managed()` 拒绝删除证据根目录之外的路径。

但这些防护没有覆盖“证据根目录下的项目目录本身是 junction”的情况。

现有测试：

- `tests/test_evidence_service.py:168-194`：源文件 symlink，实际创建失败则 skip；
- `tests/test_evidence_service.py:197-236`：源目录内 junction 指向外部，实际 `mklink /J` 测试；
- `tests/test_evidence_service.py:239-267`：monkeypatch 模拟 symlink metadata；
- **没有** `evidence_root/project_<id>` 本身为 junction 的测试；
- **没有** evidence root 本身为 symlink/junction 的测试。

### 2.4 结论

- 状态：`OPEN / CONFIRMED`
- 影响：证据文件可能被写到证据根目录之外；删除可能失败；不会自动获得跨项目读取权限。
- 首版 Windows 便携版影响：存在，需本地文件系统前置条件。
- 是否必须在打包前修复：**是（REQUIRED_FIX）**。这是明确的存储边界缺陷，修复不需要新增业务功能。

## 3. P1-02：Bandit `env` 排除规则

### 3.1 代码事实

`scanners/bandit_scanner.py:136-148`：

```python
excludes = ".venv,.git,__pycache__,venv,env,node_modules,build,dist"
command = [
    sys.executable, "-m", "bandit",
    "-r", str(root),
    "-x", excludes,
    "-f", "json", "-q",
]
```

`env` 被作为逗号分隔的 `-x` 项传给 Bandit。不是项目自定义的路径过滤。

### 3.2 Bandit 实际匹配语义

已安装 Bandit 1.9.4 的实现：

- `D:\挖漏洞\.venv\Lib\site-packages\bandit\core\manager.py:392-418`：
  `_is_file_included()` 在排除判断中使用：
  `not any(x in path for x in excluded_path_strings)`
- 同文件 `:421-425`：`_matches_glob_list()` 使用 `fnmatch.fnmatch(filename, glob)`。

因此 `env` 不只是“名为 env 的目录”，而是**路径字符串中包含 `env` 子串**的文件都会被排除。例如：

- `src/environment/app.py`
- `myenv/tool.py`
- `envs/service.py`
- 任何完整的 `...env...` 路径

这些不一定是虚拟环境，可能是合法源码目录。

### 3.3 现有测试与真实证据

- `tests/test_bandit_scanner.py` 只覆盖 Bandit JSON 解析、严重度、空结果、失败等；搜索 `env`/`exclude` 未发现路径排除测试。
- 没有实际项目目录包含 `environment`/`myenv` 的回归测试。
- 因此“会误排除”是由 Bandit 1.9.4 的源码语义直接推导的 `CONFIRMED`，不是运行时复现。

### 3.4 影响

- Bandit 可能静默漏扫合法 Python 文件；
- UI 和任务可能显示“完成、未发现”或“只发现较少问题”，而实际覆盖不完整；
- 这是扫描结果真实性问题，不是远程权限问题。

### 3.5 结论

- 状态：`OPEN / CONFIRMED`
- 影响：扫描遗漏/假阴性。
- 是否必须在打包前修复：**是（REQUIRED_FIX）**。应改为精确的目录/路径模式，或只使用明确的虚拟环境根，不把 `env` 作为任意子串排除。

## 4. P1-03：ScopeValidator 符号链接语义

### 4.1 代码事实

本地路径规范化：`security/scope_rules.py:77-85`：

```python
path = Path(candidate).expanduser()
if not path.is_absolute():
    raise ValidationError("本地路径必须使用绝对路径")
resolved = path.resolve(strict=False)
return os.path.normcase(str(resolved))
```

`security/scope_validator.py:459-518`：

- 先 `normalize_local_path(path)`；
- `candidate = Path(normalized)`；
- 检查 `exists()`、`is_dir()`、`os.access(..., R_OK)`；
- 用规范化后的 `normalized` 查询当前项目的 `scope_assets`，要求精确匹配，且资产 `ACTIVE`；
- 没有直接使用未经规范化的用户路径做范围比较。

### 4.2 静态语义

- 如果授权资产是一个普通目录，而调用者传入指向该目录的 symlink，`resolve()` 会把二者统一到同一目标，匹配成功；这是预期语义。
- 如果调用者传入指向授权目录之外的 symlink，`resolve()` 会把目标变成外部路径，使用该外部路径查不到当前项目授权资产，拒绝。
- 因此**没有发现静态的“symlink 目标在授权根之外但仍通过 exact match”的路径**。
- Windows 大小写由 `os.path.normcase()` 统一；UNC 路径也会被 `resolve`/`normcase` 处理，但系统没有显式禁止 UNC 本地资产。

### 4.3 残余风险

1. **TOCTOU**：`ScanService` 先用 `project.local_path` 做授权检查（`services/scan_service.py:118-121`），随后把同一字符串传给扫描器；`BanditScanner.scan()` 在 `scanners/bandit_scanner.py:127` 再次 `Path(target).resolve()`。如果检查后有人替换 `local_path` 或其 symlink，扫描器可能跟随到新目标。该窗口需要本地文件系统写入权限。
2. **动态 symlink/junction 测试缺失**：`tests/test_scope_validator.py:198-218` 只验证普通目录和未授权目录；没有 symlink、junction、UNC、大小写/盘符变体测试。
3. **未拒绝 UNC**：如果用户显式添加 UNC 本地资产，系统会按本地路径处理；是否有意允许 UNC 属于产品策略，不是跨项目匹配绕过。

### 4.4 结论

- 状态：`MITIGATED`（静态匹配语义正确；动态 TOCTOU 未证实）
- 影响：无已证明的跨项目读取路径；残余为本地 TOCTOU 和 UNC 策略。
- 是否必须在打包前修复：**否（ACCEPTABLE_LIMITATION）**，但应作为首版已知限制记录，并在未来具备 Windows symlink 测试能力时补动态测试。

## 5. P1-04：HTML 报告输出路径安全

### 5.1 代码事实

`reports/html_exporter.py:645-658`：

```python
root = Path(reports_dir).expanduser()
if not root.is_absolute():
    raise ValidationError(...)
if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
    raise ValidationError(...)
root = root.resolve()
...
root.mkdir(parents=True, exist_ok=True)
return root
```

- 只检查 `root` 这一层；
- `root.resolve()` 会解析**父级** junction/symlink；
- 没有检查 `root` 的父级、祖父级是否为 reparse point；
- `reports_dir` 来自 `AppConfig.reports_dir`，GUI 不接受任意输出路径；但没有验证配置路径的祖先链。

`reports/html_exporter.py:719-754` 的 `_atomic_write()`：

- 在 `target.parent` 创建临时文件；
- `flush` + `fsync` + close；
- `overwrite=True` 用 `os.replace`；
- `overwrite=False` 用 `os.link` 排他发布，失败闭锁，不回退到 `os.replace`；
- `finally` 清理临时文件。

如果报告根目录的父级是 junction，根目录本身可能是普通目录（检查通过），但实际写入落在父级指向的外部目录。临时文件和最终文件仍位于同一个解析后的父目录，所以原子性本身不被破坏，但**目录边界**被重定向。

### 5.2 风险成立条件

1. 本地攻击者能在 `storage` 或其祖先创建 junction/symlink；
2. 应用使用固定的 `AppConfig.reports_dir` 启动；
3. 用户导出 HTML 报告。

这不是远程可用漏洞，也不是 GUI 可输入任意路径导致；但属于本地路径边界和打包目录设计问题。

### 5.3 现有测试

`tests/test_report_html.py`：

- `:533-547` 普通目录正常导出；
- `:550-565` 报告根目录本身 junction，实际 `mklink /J`，拒绝；
- `:568-587` 报告根目录本身 symlink，创建失败则 skip；
- `:590-607` 外部 leaf junction，实际 `mklink /J`，拒绝；
- `:610-680` 内部/断链/外部 file symlink，创建失败则 skip；
- `:683-707` leaf `is_symlink` OSError 闭锁；
- `:710-758` 排他发布/无硬链接闭锁。

**没有**父级 junction/symlink 测试。因此“父级重定向”是静态代码结论，不是当前动态验证结果。

### 5.4 结论

- 状态：`OPEN / CONFIRMED`（静态）
- 影响：报告可能写到配置路径之外；文件名由应用生成，不能任意覆盖任意文件名；仍是路径边界缺陷。
- 是否必须在打包前修复：**是（REQUIRED_FIX）**。建议检查 `reports_dir` 祖先链的 reparse point，或将输出绑定到已验证的应用私有目录，并在打包时固定目录布局。

## 6. 测试覆盖与 Windows 限制

| 项目 | 现有测试 | 真实 Windows 证据 | 缺口 |
|---|---|---|---|
| P1-01 Evidence 根/项目目录 | 源文件 symlink、源目录 junction、metadata 模拟 | 源目录 junction 实际创建；symlink 可 skip | 无 evidence root / `project_<id>` junction |
| P1-02 Bandit `env` | 无路径排除测试 | 无 | 无 `environment`/`myenv` 回归 |
| P1-03 ScopeValidator | 普通目录与未授权目录 | 普通路径 | 无 symlink/junction/UNC/TOCTOU |
| P1-04 报告输出 | root junction、root symlink skip、leaf junction/symlink | root junction、external leaf junction 实际；file symlink skip | 无父级 reparse point |

Windows 限制：

- 当前会话创建文件 symlink 会得到 `WinError 1314`，相关测试被 skip；不能把 skip 写成 pass。
- 目录 junction 通过 `cmd /c mklink /J` 可在部分测试中真实创建；但本轮未创建任何新链接。
- 没有运行 pytest；历史全量结果（`253 passed / 7 skipped / 0 failed`）只作为历史，不作为本轮结果。

## 7. 风险成立条件汇总

| ID | 前置条件 | 直接后果 | 证据级别 |
|---|---|---|---|
| P1-01 | 证据根下的 `project_<id>` 被替换为 reparse point；用户导入合法证据 | 证据副本写到根外；删除失败 | CONFIRMED（静态） |
| P1-02 | 项目路径含 `env` 子串 | Bandit 漏扫合法源码 | CONFIRMED（Bandit 源码语义） |
| P1-03 | 本地攻击者在授权检查后替换 path/symlink | 可能扫描到新目标（TOCTOU） | UNKNOWN（动态未测） |
| P1-04 | 报告目录父级被替换为 reparse point | 报告写到配置根之外 | CONFIRMED（静态） |

## 8. 打包影响评估

| ID | 首版 Windows 便携版 | 源码运行版 | 授权边界/数据安全 | 扫描真实性 | 必须修复 |
|---|---|---|---|---|---|
| P1-01 | 有 | 有 | 有（写入/删除边界） | 无 | 是 |
| P1-02 | 有 | 有 | 无 | 有（假阴性） | 是 |
| P1-03 | 有限 | 有限 | 有残余 TOCTOU | 有限 | 否，记录限制 |
| P1-04 | 有 | 有 | 有（输出边界） | 无 | 是 |

三项 REQUIRED_FIX 都属于**本地路径边界/扫描完整性**，不需要新增业务功能；P1-03 的静态授权匹配没有发现可直接利用的越权路径，但动态证据不足。

## 9. 最终分类

- **A. BLOCKER：0 项**
- **B. REQUIRED_FIX：3 项**
  - P1-01 Evidence 根/项目目录 reparse 边界；
  - P1-02 Bandit `env` 过宽排除；
  - P1-04 报告输出父级 reparse 边界。
- **C. ACCEPTABLE_LIMITATION：1 项**
  - P1-03 ScopeValidator 的静态 symlink 匹配已缓解，但 TOCTOU/UNC/动态 symlink 证据不足；作为首版已知限制。
- **D. FALSE_POSITIVE_OR_ALREADY_MITIGATED：0 项**

## 10. 必须修复事项清单

1. **P1-01（Evidence）**：在创建/使用 `project_<id>` 前拒绝已有 symlink/junction；对证据根自身及项目目录做 reparse 检查；保留“根外不删除”。
2. **P1-02（Bandit）**：移除任意子串 `env`，改用精确的虚拟环境目录/明确路径模式；增加 `environment`/`myenv` 回归测试。
3. **P1-04（Report）**：检查 `reports_dir` 祖先链的 reparse point，或在打包时使用不可被父级重定向的私有目录；增加父级 junction 静态/动态测试。

## 11. 可接受的首版限制

- P1-03 的 TOCTOU 窗口：需要本地文件系统写权限和精确时序；静态授权匹配正确。
- 未验证的 UNC 本地资产策略：如果首版允许 UNC，必须在用户文档中明确其属于本地资产而非远程检测。
- 文件 symlink 动态测试在无 `WinError 1314` 权限的会话中 skip；不能将其报告为通过。
- 本轮未运行完整回归；打包前必须重新运行全量测试并记录 skip。

## 12. 结论与下一步

- `P1_SECURITY_REVIEW = COMPLETED`
- `CODE_MODIFICATION = NONE`
- `PACKAGING = NOT_STARTED`
- `PACKAGING_BASE_ALLOWED = NO`：存在 3 项 REQUIRED_FIX（P1-01、P1-02、P1-04）。
- `NEXT_STEP = HUMAN_REVIEW_REQUIRED`

在完成三项 REQUIRED_FIX、补充对应真实 Windows 测试并重新执行全量回归之前，不应进入 PyInstaller/EXE 打包基础建设。P1-03 可作为首版已知限制保留，但必须与其余限制一起记录，不能宣称“无路径风险”。
