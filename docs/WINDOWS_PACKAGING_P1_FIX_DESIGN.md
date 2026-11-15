# Windows 打包前 P1 必要安全修复最小方案设计

## 1. 调查范围、环境与结论摘要

### 1.1 调查范围

本报告只调查并设计以下三项已由 P1 安全核验标记为 `REQUIRED_FIX` 的问题：

- **P1-01**：Evidence 证据目录的 reparse point / junction / symlink 边界；
- **P1-02**：Bandit `env` 排除规则过宽；
- **P1-04**：HTML 报告输出目录祖先链的 reparse point 边界。

P1-03（ScopeValidator 的 symlink/TOCTOU 语义）已被前一阶段接受为首版 `ACCEPTABLE_LIMITATION`，本报告不扩大其范围，也不设计其修复。

本阶段为**只读设计调查**：

- 不修改生产代码；
- 不修改测试；
- 不修改数据库或 Schema；
- 不运行 pytest、Bandit、pip-audit 或 GUI；
- 不执行 Git 写操作；
- 不创建 symlink、junction 或 reparse point；
- 不实施 P1-F2、P1-F3、P1-F4。

### 1.2 环境

| 项目 | 实际值 |
|---|---|
| 当前项目 | `D:\挖漏洞\SRC-Research-Assistant` |
| 当前 HEAD | `21b8f23f4d5123bdb9b8b3f60cce9413dd28caec`（本报告开始时为 `d6e326b`；之后用户外部提交了 P1 安全核验报告） |
| 分支 | `main` |
| Python | 3.14.4 |
| PySide6 | 6.12.0 |
| Bandit | 1.9.4（已安装，未运行） |
| pytest | 9.2.0（未运行） |
| 工作区 | 只有本次新报告；没有修改既有文件 |

### 1.3 结论摘要

1. **P1-01 和 P1-04 都不能只在原消费方内部修复。** 根因之一是 `app/config.py` 的 `_resolve()` 在配置加载阶段已经调用 `.resolve()`；如果 `storage`、`evidence` 或 `reports` 的原始路径本身或父级是 junction，后续服务拿到的已经是重定向后的路径，再检查“叶节点”已经看不到原始 reparse 点。因此设计必须包含**配置层的一次原始路径检查**。
2. **P1-02 可以独立修复。** 最小改动是删除 `"env"` 这一过宽字面项，保留明确的虚拟环境目录，不引入新的路径匹配系统。
3. **推荐一个小型共享路径安全工具**，只包含 reparse 检测与“可信目录内安全创建/验证”两个能力；不做大规模路径架构重构。
4. **发布路径的原子写入机制不改**：仍使用同目录 `mkstemp` → `write` → `flush` → `fsync` → `close` → `os.replace`/`os.link`。
5. 本阶段没有代码、测试、数据库或 Schema 修改；没有运行测试或扫描器。

---

## 2. P1-01：Evidence 路径边界最小修复设计

### 2.1 当前真实调用链

| 环节 | 文件/位置 | 当前行为 |
|---|---|---|
| 配置加载 | `app/config.py:93` | `_resolve(base, storage.get("evidence"), "storage/evidence")` |
| 路径解析 | `app/config.py:36-40` | 相对路径拼到 `base`，随后 **`candidate.resolve()`** |
| 目录初始化 | `app/config.py:131-142` | `ensure_directories()` 对 `evidence_dir` 调用 `mkdir(parents=True, exist_ok=True)` |
| 服务构造 | `app/bootstrap.py:118-127` | 把已经解析的 `config.evidence_dir` 传给 `EvidenceService` |
| 服务初始化 | `services/evidence_service.py:61-63` | 再次 `.resolve()`，然后 `mkdir(parents=True, exist_ok=True)` |
| 项目目录 | `services/evidence_service.py:253-269` | `project_<id>` 直接 `mkdir(parents=True, exist_ok=True)` |
| 复制后检查 | `services/evidence_service.py:266-268` | 用 `target.parent.resolve() != project_dir.resolve()` 判断越界 |
| 删除 | `services/evidence_service.py:271-284` | 先 `path.resolve()`，再按解析后的路径判断/删除 |

### 2.2 为什么当前检查不足

**CONFIRMED**：

- `EvidenceService.__init__` 的 `.resolve()` 会跟随一个指向项目外部的根目录 symlink/junction；
- `_copy_into_evidence_store()` 的 `project_<id>.mkdir(parents=True, exist_ok=True)` 会接受一个已经存在、且指向外部的 junction；
- 当根目录和 `project_<id>` 都通过同一个外部 junction 重定向时，`target.parent.resolve()` 与 `project_dir.resolve()` 可能都得到同一个外部路径，比较结果仍为“相等”，从而绕过边界；
- 现有测试 `tests/test_evidence_service.py:197-236` 覆盖的是“源文件为 junction”的路径，不是“Evidence 根目录或 `project_<id>` 本身为 junction”的路径；
- `app/config.py:40` 的 `.resolve()` 使得后续服务无法仅凭 `config.evidence_dir` 判断原始配置路径是否被重定向。

因此，仅修改 `EvidenceService` 的局部比较不足以覆盖配置层已经发生的重定向。

### 2.3 根目录策略

**建议策略：拒绝，不解析后接受。**

具体规则：

1. Evidence 根目录的**配置原始路径**必须被检查；
2. 根目录自身如果是 symlink、junction 或其他 reparse point，拒绝启动/拒绝构造 `EvidenceService`；
3. 根目录与其可信根之间的已存在路径组件也不得是 reparse point；
4. 不使用“先 `resolve()`，再看解析结果是否在某个目录内”的方式作为唯一判断；
5. 根目录不存在时允许后续创建，但创建后必须再次用 `lstat` 验证不是 reparse point。

拒绝而不是自动解析的理由：

- Evidence 是应用管理的安全资产目录，不是用户选择的普通工作目录；
- 静默解析会把“用户选择的目录”与“实际写入目录”分离，后续路径和审计记录会指向不可解释的位置；
- 自动接受 junction 会扩大删除、复制和报告引用的边界；
- 需要保留旧数据时，应由人工迁移到普通目录，不应让程序静默接受重定向。

### 2.4 `project_<id>` 子目录策略

对已存在的 `project_<id>`：

- 使用 `lstat` 检查它自身是否为 reparse point；是则拒绝；
- 检查其父级（已通过根目录校验）到该目录之间的组件；
- 不先 `resolve()` 再比较；
- 若目录不存在，使用**单层** `os.mkdir()`/`Path.mkdir(exist_ok=False)` 创建；
- 捕获 `FileExistsError` 后重新检查已存在目录，不能盲目继续；
- 创建后再次 `lstat` 检查，防止创建后立即被替换（仍有不可避免的 TOCTOU 窗口，必须记录）。

对于目标文件：

- 目标必须是 `project_dir` 的**直接子项**；
- 用 `target.parent == project_dir` 的原始路径判断，不用 `target.parent.resolve() == project_dir.resolve()`；
- 目标叶节点若是 symlink/junction，拒绝；
- 目标文件应采用独占创建（例如 `os.open(..., O_CREAT | O_EXCL)` 或等价方式）或至少确保 UUID 文件名不会被已有链接截获；
- 任何失败均不得留下已复制但未登记的文件，失败清理也必须只删除本次创建的对象。

### 2.5 后续访问和删除

`_unlink_managed()` 当前先 `resolve()` 再按解析后路径判断，存在“删除链接目标而不是链接本身”的风险，也可能绕过根目录比较。建议：

- 使用 `lstat` 获取原始节点；
- 先验证原始父目录在 Evidence 根目录内；
- 如果原始叶节点是 symlink/junction/reparse point，拒绝或仅删除链接本身（不能删除链接目标）；
- 普通文件才调用 `unlink`；
- 读、复制、删除、报告引用都复用同一个“根目录/项目目录校验”入口，避免每个业务函数各自复制边界逻辑。

### 2.6 最小测试集合

**可稳定执行（普通目录）**：

1. 正常 Evidence 根目录存在时，添加文本/文件证据成功；
2. 根目录不存在时，按配置创建普通目录成功；
3. 普通 `project_<id>` 子目录存在时成功；
4. 正常删除不会删除其他项目或其他文件；
5. `_copy_into_evidence_store` 目标始终直接位于 `project_dir`；
6. 失败清理不会删除已有证据。

**Windows junction（可实际创建时）**：

7. Evidence 根目录本身是 junction，构造/使用服务被拒绝；
8. `project_<id>` 是 junction，添加证据被拒绝且目标外部目录没有文件；
9. 删除路径中的项目目录是 junction，删除被拒绝。

**Windows symlink（权限不足时跳过，不能伪造 PASS）**：

10. 根目录是 symlink：在 `os.symlink` 可用的环境中断言拒绝；权限不足时使用明确 `pytest.skip`，记录 `WinError 1314`；
11. `project_<id>` 是 symlink：同上；
12. 目标叶节点是 symlink：拒绝，不跟随。

**配置层测试**：

13. 原始配置路径组件中存在 junction 时，`AppConfig.load()` 拒绝；
14. 普通 `%LOCALAPPDATA%` 风格的绝对数据目录不被无理由拒绝；
15. 根目录/项目目录检查失败时，服务不创建数据库记录。

测试约束：

- 不得把创建 junction 失败设计成必然通过；
- 不得用 monkeypatch `is_symlink` 代替 junction 测试并宣称真实 junction 已通过；
- 只能把“静态分支测试”和“真实 junction 测试”分开标记。

---

## 3. P1-02：Bandit `env` 排除规则最小修复设计

### 3.1 当前实现

`scanners/bandit_scanner.py:136-148` 构造：

```text
-x .venv,.git,__pycache__,venv,env,node_modules,build,dist
```

已安装 Bandit 1.9.4 的 `bandit/core/manager.py:413-415` 使用：

```python
any(x in path for x in excluded_path_strings)
```

这意味着被排除的不是“目录名等于 env”，而是**路径中任意位置包含 `env` 子串**。例如：

- `environment/`；
- `myenv/`；
- `environmental_checks/`；
- 甚至文件名或上级目录名中包含 `env` 的路径。

因此当前 `env` 会造成异常宽泛的静默漏扫。

### 3.2 最小修复方案

**推荐：只删除 `"env"` 这一项，保留其他明确的排除项。**

修复后的字面值建议为：

```text
.venv,.git,__pycache__,venv,node_modules,build,dist
```

理由：

- `env` 是 P1-02 直接确认的过宽项；
- 其他项是明确的项目/工具目录，不应在本修复中一起重写；
- 不引入新的 glob/路径匹配层，不改变 Bandit 的核心调用；
- 回归风险最低，修复可以独立实施。

保留 `venv` 的说明：

- `venv` 仍会被 Bandit 的 `x in path` 语义匹配到 `myvenv` 等路径；
- 这是遗留的“宽匹配”共性，但当前 P1-02 只确认了 `env` 的具体漏扫问题；
- 不应在本步骤中把整个 `-x` 参数改造成新的路径系统，否则会把一个低风险修复扩大为路径架构重构；
- 若后续需要处理 `venv` 的宽匹配，应作为独立问题登记，不在 F3 中夹带。

### 3.3 兼容性影响

**CONFIRMED**：

- 修复后，包含 `env` 的普通业务目录会重新进入 Bandit 扫描；
- 可能增加少量扫描时间，尤其是大型源码树；
- 不改变 Finding schema、数据库、报告格式或 GUI；
- 不增加第三方依赖；
- 不需要 Schema migration。

**UNKNOWN**：

- 具体增加多少扫描时间取决于目标项目结构；
- 当前没有真实用户项目可以量化；
- Bandit 自身默认排除（`bandit/core/constants.py:30-40`）仍会排除 `.git`、`__pycache__` 等标准目录。

### 3.4 最小测试

**可靠单元测试（命令参数层）**：

1. monkeypatch `run_command` 捕获 `BanditScanner.scan()` 的 argv；
2. 断言 `-x` 的值不再包含独立项 `env`；
3. 断言 `.venv`、`venv`、`.git`、`__pycache__` 等明确项仍存在；
4. 断言其他参数（`-r`、`-f json`、`-q`）不变。

这个测试只能证明“传给 Bandit 的排除参数不含 `env`”，**不能**单独证明 Bandit 最终不会误伤 `environment`。

**真实 Bandit 集成测试（当前不运行）**：

5. 在临时目标中创建 `environment/app.py`，内含一个可稳定触发的 Bandit 规则（例如 `subprocess` 使用 `shell=True`）；
6. 修复前预期该 Finding 因 `env` 子串被静默漏掉，修复后预期可发现；
7. 在同一目标创建 `.venv/` 或 `venv/` 示例，确认明确虚拟环境目录仍被排除；
8. Bandit 不可用时明确 skip，不得伪造 PASS；
9. 该测试应标记为 `REQUIRES_RUNTIME_TEST`，不能把历史人工结果当成当前运行结果。

**不得声称**：

- 仅靠静态检查就能证明 Bandit 的最终匹配语义；
- 没有运行扫描器时已经验证了漏报修复。

---

## 4. P1-04：HTML 报告路径边界最小修复设计

### 4.1 当前实现与真实问题

| 环节 | 文件/位置 | 当前行为 |
|---|---|---|
| 配置解析 | `app/config.py:94` | `_resolve(base, storage.get("reports"), "storage/reports")`，内部 `.resolve()` |
| 目录初始化 | `app/config.py:131-142` | `ensure_directories()` 创建 `reports_dir` |
| 写入入口 | `reports/html_exporter.py:327-390` | `write_html_report()` |
| 根目录解析 | `reports/html_exporter.py:645-658` | 检查 `reports_dir` 自身 symlink/junction，然后 `.resolve()` |
| 叶节点 | `reports/html_exporter.py:350-368` | 原始 `candidate` 检查 symlink/junction，保留原始叶节点 |
| 原子写入 | `reports/html_exporter.py:719-754` | `mkstemp` → write → flush → fsync → close → `os.replace`/`os.link` |

**CONFIRMED**：

- `_resolve_reports_root()` 只检查 `reports_dir` 自身，不检查其父级；
- `AppConfig._resolve()` 更早调用 `.resolve()`，因此如果 `storage` 或 `reports` 的原始父级是 junction，导出器拿到的 `reports_dir` 已经是重定向后的路径，导出器无法再看到原 junction；
- 因此“仅修改 `_resolve_reports_root()`”无法完全覆盖配置层重定向；
- 当前测试覆盖根目录自身 junction/leaf junction，但不覆盖父级重定向和配置原始路径重定向。

### 4.2 可信根定义

**设计必须先定义“允许写入的可信根”，而不是无限向上检查到 `C:\`。**

建议：

- 可信根 = `AppConfig.storage_root`（当前版本数据目录）；
- `reports_dir` 必须位于 `storage_root` 之内；
- 只检查从 `storage_root` 到 `reports_dir` 的组件；
- `storage_root` 自身必须在配置加载阶段先验证，不得是 reparse point；
- 不检查 `storage_root` 之上的系统目录，除非未来打包策略明确把用户数据根改为另一个可信根；
- 未来的 `%LOCALAPPDATA%\SRC-Research-Assistant\storage` 只要本身是普通目录，就应被接受，不能因为路径在项目目录之外而拒绝。

**UNKNOWN**：

- 如果未来把 `storage_root` 设为一个父级本身是 junction 的 `%LOCALAPPDATA%` 路径，是否应拒绝该父级，取决于打包策略对“用户数据根”的信任定义；
- 当前版本的数据根在应用目录下，默认配置不需要检查系统级父目录。

### 4.3 祖先链检查

建议新增一个小的 `ensure_trusted_directory(path, trusted_root, create=False)`：

1. 将 `path` 与 `trusted_root` 转为绝对路径，使用**不解析**的 `abspath/normpath/normcase`；
2. 用 `commonpath`/`relative_to` 确认 `path` 在 `trusted_root` 内；
3. 对 `trusted_root` 自身做 reparse 检查；
4. 从 `trusted_root` 的下一级开始，逐级检查到 `path`；
5. 对每个已存在组件调用 `lstat`，检测 `FILE_ATTRIBUTE_REPARSE_POINT`、`is_symlink()`、`is_junction()`；
6. 对不存在的组件，使用单层 `mkdir` 创建，然后立即重新 `lstat`；
7. 任何无法读取、无法判断或 reparse 检测异常，均 fail-closed，不得继续写入；
8. 不把 `.resolve()` 后的叶节点作为写入目标。

### 4.4 与 `%LOCALAPPDATA%` 的兼容性

- 不在代码中硬编码“必须在应用安装目录下”；
- 可信根由配置的数据根提供；
- 对普通 `%LOCALAPPDATA%` 目录不做“路径包含 `AppData` 就拒绝”之类的规则；
- 只拒绝 reparse point 和越出可信根的路径；
- 如果未来需要独立的数据根，新增配置项时必须同时定义其可信根，不能默默信任任意绝对路径。

### 4.5 原子写入保持不变

最小修复**不改变**：

- `mkstemp` 在目标目录创建临时文件；
- `write`、`flush`、`fsync`、`close`；
- `overwrite=True` 的 `os.replace`；
- `overwrite=False` 的 `os.link` 独占发布；
- 失败清理和旧文件保护。

唯一变化是：在 `_resolve_reports_root()` 之前/之中增加可信根和祖先链校验，并使用原始 `target`。不得为了路径检查而改用“先写临时文件、再移动到未验证目录”的方案。

### 4.6 API 影响

建议给 `write_html_report()` 增加**关键字参数**：

```python
trusted_root: str | Path
```

- 由 `ui/report_page.py:387` 传入 `context.config.storage_root`；
- `write_html_report()` 内部调用 `_resolve_reports_root(reports_dir, trusted_root)`；
- 不提供默认的“任意父目录” fallback；
- 同步更新 `tests/test_report_html.py` 和 `tests/test_ui_report.py` 的调用；
- 不在本阶段实施。

理由：

- 公共写入函数的 `reports_dir` 可以是任意绝对路径；仅凭 `reports_dir` 本身无法知道可信根；
- 默认 `trusted_root=None` 会留下不安全的调用路径；
- 该函数是应用内部 API，当前调用方只有 GUI 和测试，增加显式参数是可接受的兼容性变化。

### 4.7 最小测试

**普通目录（稳定）**：

1. 正常 `storage_root/reports` 下写报告成功；
2. `reports_dir` 不存在时按配置创建并成功；
3. 普通 `%LOCALAPPDATA%` 风格的普通目录不被拒绝（使用临时模拟路径，不依赖真实用户目录）；
4. 现有 `overwrite=False/True`、目录拒绝、叶节点 symlink 拒绝、原子写入测试保持通过。

**祖先 junction（Windows 实际可创建时）**：

5. `storage_root/reports` 的父级组件是 junction，写入被拒绝，外部目录没有报告；
6. `storage_root` 本身是 junction，配置加载或写入前被拒绝；
7. 正常目录的父级检查不误伤。

**symlink（权限不足时跳过）**：

8. `reports_dir` 自身 symlink：可用时拒绝，不可用时明确 skip；
9. 父级 symlink：可用时拒绝，不可用时明确 skip；
10. 不得用 monkeypatch 代替真实 symlink 并宣称动态 symlink 已验证。

**原子写入回归**：

11. `os.replace` 失败时旧文件保留；
12. `os.link` 独占失败时不覆盖；
13. 清理失败不伪造成功。

---

## 5. 现有共享安全工具调查

**CONFIRMED**：

- `security/scope_rules.py:77-85` 的 `normalize_local_path()` 使用 `resolve()` + `normcase()`，是 ScopeValidator 的规范化逻辑，不适合作为“拒绝 reparse 的目录创建”工具；
- `services/evidence_service.py`、`reports/html_exporter.py`、`services/report_service.py` 分别有自己的 `is_symlink()`/`is_junction()` 检查；
- 没有统一的 `path_safety` 模块；
- 没有共享的“可信根 + 祖先链 + reparse”验证函数；
- 没有第三方路径安全依赖，也不应为此新增依赖。

因此 P1-01 和 P1-04 需要同一种新能力；P1-02 不需要。

---

## 6. 方案 A / 方案 B 比较

### 方案 A：三个位置各自实现最小检查

**优点**：

- 改动文件少；
- 每个修复独立；
- 不需要新模块。

**风险**：

- P1-01 和 P1-04 会复制同一套 reparse/祖先检查；
- 两处对“可信根”的定义容易漂移；
- 测试重复；
- 后续其他路径入口可能再次复制不完整检查。

### 方案 B：新增一个很小的共享安全工具

建议新增：

```text
security/path_safety.py
```

只提供两个核心函数：

```python
def is_reparse_point(path: Path) -> bool: ...
def ensure_trusted_directory(
    path: Path,
    trusted_root: Path,
    *,
    create: bool = False,
) -> Path: ...
```

可选增加配置专用包装：

```python
def resolve_configured_path(
    base: Path,
    raw: str | Path,
    *,
    trusted_root: Path,
    label: str,
) -> Path: ...
```

职责边界：

- 检测 reparse point；
- 检查路径是否在可信根内；
- 逐级创建/校验目录；
- 不负责 Evidence 业务、不负责报告渲染、不负责 Bandit。

**结论：推荐方案 B，但保持极小。**

不新增抽象基类、不引入路径 DSL、不重构所有服务、不修改数据库。

---

## 7. 推荐的最小架构

### 7.1 配置层

建议在 `app/config.py` 增加一个内部的“先验证、后解析”路径：

1. 计算 `storage_root` 的原始候选路径；
2. 使用 `path_safety` 检查原始 `storage_root` 自身和可检查的组件；
3. 对 `evidence_dir`、`reports_dir` 用原始 `storage_root` 作为可信根检查；
4. 通过后才调用 `.resolve()`；
5. `ensure_directories()` 创建后再次校验目标目录不是 reparse point。

注意：

- 必须保留 `AppConfig` 现有公开字段的语义，不改变数据库路径等行为；
- 不新增 Schema；
- 不把“绝对路径”一律拒绝；
- 未来若使用 `%LOCALAPPDATA%`，可信根由配置明确提供，不硬编码项目目录。

### 7.2 Evidence 层

`EvidenceService`：

- 使用 `ensure_trusted_directory(evidence_root, trusted_root=storage_root, create=True)`；
- `project_<id>` 使用同一 helper，禁止 `parents=True, exist_ok=True` 的盲创建；
- `_copy_into_evidence_store` 使用原始 `target.parent == project_dir`；
- `_unlink_managed` 使用 `lstat`，不跟随叶节点；
- 所有失败清理只针对本次创建的对象。

### 7.3 Report 层

`html_exporter._resolve_reports_root(reports_dir, trusted_root)`：

- 先检查 `trusted_root` 正常；
- 检查 `reports_dir` 在 `trusted_root` 内；
- 逐级检查祖先；
- 保留原始 `candidate` 叶节点；
- 原子写入逻辑不变。

`ui/report_page.py` 的 `_write` 传入 `config.storage_root`；测试同步更新。

### 7.4 Bandit 层

只修改排除字符串；若需要更易测试，可增加一个模块级常量或小的纯函数返回排除项，但不得引入新的路径匹配框架。

---

## 8. 允许修改的具体文件清单（仅作为后续实施建议）

### P1-F2：Evidence 路径安全

- `security/path_safety.py`（新增）
- `app/config.py`
- `services/evidence_service.py`
- `tests/test_evidence_service.py`
- `tests/test_path_safety.py`（新增，若采用共享 helper）
- 如需配置测试，新增/调整 `tests/test_config.py`

禁止：

- `database/schema.py`
- 任何数据库迁移
- GUI
- 报告导出器
- Bandit

### P1-F3：Bandit 排除

- `scanners/bandit_scanner.py`
- `tests/test_bandit_scanner.py`

禁止：

- `security/path_safety.py`
- Evidence
- Report exporter
- DB/Schema

### P1-F4：HTML 报告路径

- `reports/html_exporter.py`
- `security/path_safety.py`（复用 F2 的 helper）
- `app/config.py`（若 F2 尚未加入 reports 原始路径校验）
- `ui/report_page.py`
- `tests/test_report_html.py`
- `tests/test_ui_report.py`

禁止：

- 修改报告模板
- 修改 `ReportService` 业务
- 修改 `ReportRepository`
- DB/Schema
- PDF/JSON

### P1-F5：修复后回归

- 不新增功能代码；只执行全量测试和打包前冻结确认。

---

## 9. 每项修复的最小测试计划

### P1-01

- 普通根/项目目录成功；
- 根目录不存在时创建成功；
- 根 junction 拒绝；
- 项目目录 junction 拒绝且外部无文件；
- 根 symlink 在可创建时拒绝，否则 skip；
- 项目目录 symlink 在可创建时拒绝，否则 skip；
- 删除不跟随 symlink；
- 配置原始路径 junction 在 `AppConfig.load()` 被拒绝；
- 普通绝对数据目录不被误拒绝。

### P1-02

- 捕获命令参数：`env` 不再出现；
- 明确虚拟环境项仍存在；
- 真实 Bandit 集成：`environment/` 可扫描，`.venv`/`venv` 仍排除；
- Bandit 不可用时 skip，不得伪造 PASS。

### P1-04

- 普通 `storage/reports` 写入成功；
- `reports_dir` 自身 junction 拒绝；
- 祖先 junction 拒绝；
- 普通 `%LOCALAPPDATA%` 风格目录接受；
- 原子写入/覆盖/失败清理回归；
- symlink 动态测试 skip 规则明确。

### 共享 helper

- 普通目录；
- 已存在目录；
- 不存在目录创建；
- junction；
- symlink（可用时）；
- 越出 trusted root；
- 不可读取/异常 fail-closed；
- 不改变正常路径语义。

---

## 10. 原子实施步骤建议

### P1-F2：Evidence 路径安全修复

- 前置：本设计批准；
- 允许修改：见第 8 节；
- 必须测试：P1-01 普通 + junction + 配置原始路径；
- 完成标准：根/项目目录 reparse 被拒绝，正常路径行为不变；
- 回滚：只回滚代码/测试，不恢复数据库或删除证据；
- 人工审核后再进入 F3/F4。

### P1-F3：Bandit 排除修复

- 可与 F2 独立实施；
- 允许修改：见第 8 节；
- 必须测试：命令参数 + 真实 Bandit 集成；
- 完成标准：`env` 不再被排除，`environment` 可被发现；明确虚拟环境仍排除；
- 不改变其他扫描器。

### P1-F4：HTML 报告路径修复

- 依赖 F2 的 helper（或先合入 helper）；
- 允许修改：见第 8 节；
- 必须测试：根/祖先 junction、symlink、普通目录、原子写入；
- 完成标准：不越出可信根，正常报告写入和覆盖语义不变；
- 不修改模板/报告业务。

### P1-F5：修复后全量回归与冻结

- 运行完整 pytest（专用临时目录 + full-access，按现有环境限制）；
- 记录 253/7/0 基线是否保持；
- 不运行真实网络扫描；
- 不进入打包，不开始 PDF/JSON；
- 人工审核后才允许进入 Windows 打包阶段。

---

## 11. 兼容性与风险

| 风险 | 影响 | 处理 |
|---|---|---|
| 现有 Evidence 根目录是 symlink | 新修复会拒绝旧配置 | 记录迁移要求；人工迁移到普通目录；不静默接受 |
| 现有报告目录是 symlink/junction | 写入会拒绝 | 同样人工迁移 |
| `%LOCALAPPDATA%` 普通路径 | 不应拒绝 | 以配置 storage root 为可信根，只检查其下；不硬编码项目目录 |
| 扫描范围增加 | Bandit 可能变慢 | 可接受；不是数据/安全回归 |
| 目标文件被竞态替换 | 仍有 TOCTOU 窗口 | 记录为残余风险，不声称完全消除 |
| 父级 reparse/其他 reparse 类型 | 可能仍存在 | 记录 UNKNOWN；不宣称全覆盖 |
| 公共 `write_html_report` 参数变化 | 测试/调用方需要更新 | 显式 `trusted_root`，不提供不安全默认 |
| 配置 `.resolve()` 的早期行为 | 仅改服务层不够 | 配置层原始路径检查是前置条件 |

---

## 12. CONFIRMED / PROPOSED / UNKNOWN 分类

### CONFIRMED

- P1-01 根目录和 `project_<id>` 当前没有 reparse 拒绝；
- P1-01 的 `resolve()` 后比较存在绕过；
- P1-02 的 `env` 通过 Bandit `x in path` 造成过宽排除；
- P1-04 只检查 `reports_dir` 自身，未检查父级；
- `AppConfig._resolve()` 在消费方之前调用 `.resolve()`；
- 现有测试缺少根/项目目录 junction 和父级 junction 覆盖；
- 原子写入机制当前完整存在。

### PROPOSED

- 新增 `security/path_safety.py` 共享 helper；
- 在配置加载阶段先验证原始路径，再 `.resolve()`；
- 根目录和项目目录采用“拒绝 symlink/junction”策略；
- `write_html_report` 增加显式 `trusted_root`；
- P1-02 只删除 `env`，不改匹配机制；
- F2/F3/F4/F5 的拆分顺序。

### UNKNOWN

- 未来 `%LOCALAPPDATA%` 数据根的父级信任策略；
- 其他 reparse point 类型（非 symlink/junction）在实际 Windows 文件系统上的全覆盖；
- 真实 Bandit 环境下的扫描耗时增量；
- 配置路径在应用启动后才被替换的 TOCTOU 完整防护；
- 现有生产数据目录是否存在 reparse point（未检查用户实际目录）。

---

## 13. 未解决问题

1. 是否需要在打包阶段把 `storage_root` 从应用目录迁移到 `%LOCALAPPDATA%`；如果迁移，需要明确新的可信根。
2. 对于“父级是 junction、但 `storage_root` 自身是普通目录”的情况，是否需要检查 `storage_root` 的父级；本设计默认不越过可信根。
3. 现有 Evidence 数据库记录中的绝对路径是否需要迁移检查；本设计不修改数据库。
4. 真实 Bandit 集成测试的运行成本和 CI 可用性。
5. 公共 `write_html_report` 改为显式 `trusted_root` 后，是否有未发现的外部调用方。

---

## 14. 最终建议

**P1_FIX_DESIGN = COMPLETED**

**推荐实施顺序**：

1. **P1-F2**：共享路径 helper + 配置原始路径校验 + Evidence 根/项目目录修复；
2. **P1-F3**：Bandit 排除修复（可独立、可并行）；
3. **P1-F4**：HTML 报告可信根/祖先链修复；
4. **P1-F5**：完整回归和打包前冻结。

关键约束：

- 不新增业务功能；
- 不重新开发 PDF；
- 不重新开发 JSON；
- 不修改数据库或 Schema；
- 不重新打开 RC-01；
- 不扩大到 P1-03；
- 所有正式报告文件仍只通过 `write_html_report()` 发布；
- 不把 junction/symlink 不可创建的测试伪造为通过。

最终状态：

```text
P1_FIX_DESIGN = COMPLETED
CODE_MODIFICATION = NONE
TEST_EXECUTION = NONE
PACKAGING = NOT_STARTED
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```
