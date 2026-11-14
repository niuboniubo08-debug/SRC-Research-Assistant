# Phase 6-R0-B2 扫描器、漏洞管理与证据中心只读核查

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 调查时间：2026-11-13（本地时区 Asia/Shanghai）
- 调查性质：只读代码与测试核查；未运行扫描器、GUI 或 pytest
- 当前分支：`main`
- 当前 HEAD：`bffb5ac82bbebe7fef5992f87ff90494c9776ace`
- 调查前工作区：staged 0；`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`；4 个既有未跟踪报告（D1B-1、D1B-3、R0-A、R0-B1）
- 本次唯一新增：`docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md`

## 1. 调查范围、方法、证据分类与 Git 状态

### 1.1 调查范围

本次只读核查覆盖：

1. Bandit、Semgrep、pip-audit 三个扫描器的执行入口、命令参数、进程调用、超时、取消、退出码和错误处理。
2. `ScanService` 与 `DependencyAuditService` 的任务状态、结果保存和错误传递。
3. Finding 的创建、查询、状态变更、状态历史和项目过滤。
4. Evidence 的添加、文件复制、哈希、读取、删除、路径约束和项目过滤。
5. `ScopeValidator` 的本地路径授权和项目隔离。
6. 相关测试文件和历史测试报告；只检查是否覆盖，不运行测试。

本次没有启动 GUI、扫描器、数据库写入或任何 pytest。所有“当前行为”结论来自当前源码和测试代码的静态阅读；“历史运行结果”只作为历史证据，不自动等同于当前环境运行结果。

### 1.2 证据分类

本报告使用以下标签：

- `CURRENTLY_CONFIRMED`：当前源码/测试代码直接支持的行为或结构事实。
- `HISTORICAL_ONLY`：只在历史报告中记录，当前未重新运行。
- `REQUIRES_RUNTIME_TEST`：代码路径存在，但实际工具/Windows/文件系统行为尚未在当前环境验证。
- `UNKNOWN`：现有材料不足，不能判断。

### 1.3 Git 状态

调查开始时只读记录：

- 分支 `main`，HEAD `bffb5ac82bbebe7fef5992f87ff90494c9776ace`。
- staged 文件 0。
- 未暂存修改：`docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`（既有，未由本任务修改）。
- 未跟踪：D1B-1、D1B-3、R0-A、R0-B1 四份既有报告。
- 与 `origin/main`：ahead 5 / behind 0。

本次没有执行 `git add`、`commit`、`push`、`reset`、`restore` 或 `clean`，没有修改、暂存或删除上述既有文件。

## 2. 三个扫描器的当前实现

### 2.1 Bandit

**入口与可用性**

`scanners/bandit_scanner.py:74-260`：

- `is_available()` 检查 Bandit 模块可导入、`python -m bandit --version` 可启动，并缓存探测结果。
- `scan(target, options)` 要求目标为已存在的目录；目标先 `resolve()`；不可用时抛出 `ScannerUnavailable`。
- 命令参数：

```text
[sys.executable, -m, bandit, -r, <target>,
 -x, .venv,.git,__pycache__,venv,env,node_modules,build,dist,
 -f, json, -q]
```

- `run_command(..., cwd=target, shell=False)`；不使用 shell。
- 取消抛 `ScanCancelled`，超时抛 `ScannerTimeoutError`。
- 退出码接受 `0` 和 `1`（Bandit 发现问题时通常返回 1）；其他退出码视为执行失败。
- 空 stdout 抛 `ScannerParseError`；JSON 缺少 `results` 列表也抛解析错误。
- 解析时把目标根目录之外的路径忽略并产生 warning；B105/B106/B107 的问题文本被替换为“具体值未写入结果”，避免把疑似凭据原文写入 Finding。
- 输出被截断时追加“结果可能不完整”的 warning。

**分类**：核心执行和错误处理 `CURRENTLY_CONFIRMED`；真实 Bandit 在当前环境的执行结果 `HISTORICAL_ONLY`。

**已确认限制**：`-x` 使用 `.venv,...,env,...` 路径组件排除。历史 Phase 6-C1-R 曾观察到：当临时 basename 包含 `env` 时，Bandit 返回 0 findings，导致两个真实扫描测试失败；改名后才恢复。因此如果合法项目路径本身含有名为 `env` 的目录组件，可能出现**静默漏报**。该行为是当前参数设计的一部分，不能仅凭历史成功结果忽略。

### 2.2 Semgrep

**入口与可用性**

`scanners/semgrep_scanner.py:39-270`：

- `is_available()` 要求：本地规则文件存在、Semgrep 模块可导入、`semgrep` 可执行文件可启动、`semgrep --version` 成功。
- 扫描命令使用本地规则目录，`--json --quiet --metrics=off --disable-version-check`，并显式排除 `.git`、缓存和虚拟环境目录。
- `run_command(..., shell=False)`，环境变量强制关闭 metrics/version check。
- 退出码必须为 `0`；非零即执行失败。
- 空 stdout 为解析错误；JSON 必须含 `results` 列表。
- 目标根目录外的文件路径被忽略；严重度按本地规则映射。

**分类**：接口、命令构造、解析路径 `CURRENTLY_CONFIRMED`；当前 Windows 真实运行 `HISTORICAL_ONLY` + `REQUIRES_RUNTIME_TEST`。

**历史状态**：Phase 3 记录 Semgrep 1.183.0 在 Windows 启动时报：

```text
Fatal error: exception Failure: ca_certs_iter_on_anchors: CertOpenSystemStore returned NULL
```

因此历史 Semgrep 真实结果不存在；当时只有 Bandit 真实结果。当前源码仍保留 Semgrep 接口和本地规则，但本次未运行，不能确认它在当前 Windows 会话可用。Semgrep 不可用时 `ScanService` 会把它标为不可用并继续其他扫描器；只有 Semgrep 一个可用扫描器时任务应失败，而不是“无发现成功”。

### 2.3 pip-audit

**入口与可用性**

`scanners/pip_audit_scanner.py:51-311`：

- 构造参数包含项目自有 `cache_dir` 和 `temp_dir`，两者均 `resolve()`。
- `is_available()` 检查模块、可执行文件和版本。
- `scan()` 要求输入依赖文件存在，检查可用性，创建 cache/temp 目录。
- 命令：

```text
pip-audit -r <dependency-file> --format json --progress-spinner off
  --timeout <1..30> --desc on --aliases on
  --vulnerability-service pypi --cache-dir <cache>
```

- 环境变量设置 `TMP`、`TEMP`、`PIP_CACHE_DIR`，避免使用不可写的用户默认缓存。
- 退出码接受 `0` 和 `1`（发现漏洞时为 1）；其他退出码为失败。
- 空 stdout 为执行错误；JSON 必须有 `dependencies` 列表。
- 依赖项按 `(lower(name), vuln_id)` 去重。
- 缺失严重度时使用 `Severity.MEDIUM`，并写 `severity_source=conservative-default`；不伪造 CVSS。
- `metadata` 保留依赖名、当前版本、漏洞编号、别名、受影响版本、修复版本、数据源、依赖文件和 severity source。
- Finding 的 `file_path` 初值为依赖文件绝对路径，随后由 `DependencyAuditService._map_findings` 映射为项目内相对路径。

**分类**：命令、解析、去重和字段映射 `CURRENTLY_CONFIRMED`；当前真实 pip-audit 网络执行 `HISTORICAL_ONLY`。

**已确认语义缺陷**：`parse_output()` 最后返回 `len(dependencies)` 作为 `audited`，见 `scanners/pip_audit_scanner.py:311`。循环中虽然对带 `skip_reason` 的依赖追加 warning，但仍把该对象计入 `len(dependencies)`。因此“依赖对象数”被当成“完成审计的依赖数”。详见第 8 节 B2-01。

## 3. 扫描任务执行与错误处理链路

### 3.1 `ScanService`

`services/scan_service.py:114-289` 的实际顺序：

1. 从 `ProjectService` 取项目；目标为 `project.local_path`。
2. 调用 `ScopeValidator.check_local_path(..., operation="source_audit")`；未通过则拒绝，不创建任务。
3. 从注册表解析请求的扫描器；未知扫描器报错。
4. 创建扫描任务，记录 `scanners_json`、当前扫描器、进度和开始时间。
5. 对每个可用扫描器执行；不可用扫描器记录为 skipped/warning。
6. 每个扫描器成功后立即保存其 Finding；如果后续扫描器失败，已完成扫描的 Finding 仍保留。
7. 任一扫描器执行错误/超时，最终任务为 `FAILED`，错误写入 `error_message`；不会把失败伪装成“无发现成功”。
8. 全部扫描器不可用时任务为 `FAILED`，错误信息包含“均不可用”。
9. 用户在开始前取消，任务为 `CANCELLED`；扫描中取消，`run_command` 返回 cancelled，服务转为取消终态。
10. 所有扫描器成功且没有 Finding 时，任务为 `COMPLETED`，摘要为“未发现匹配的安全问题”。这是对**成功执行且结果为空**的正确表达，不等同于工具失败。

**分类**：`CURRENTLY_CONFIRMED`（静态代码）；真实 Bandit/Semgrep 运行 `HISTORICAL_ONLY`。

**已确认限制**：

- `ScanService` 对单个扫描器失败保留其他扫描器 Finding，但最终任务仍是 `FAILED`。这避免把部分失败当成功，但用户在 UI 中需要同时看到“部分结果”和“失败”两个事实；本报告未验证 UI 是否始终同时展示。
- `run_command` 只终止直接子进程，不保证终止其子进程树；在扫描器自行启动子进程的情况下，取消/超时后可能残留进程。见 B2-05。

### 3.2 `DependencyAuditService`

`services/dependency_audit_service.py:124-373` 的实际顺序：

1. `discover()` 只查看 `project.local_path` 下的直接 `requirements.txt` 和 `pyproject.toml`，不递归搜索。
2. 调用 `ScopeValidator.check_local_path(..., operation="dependency_audit")`。
3. 拒绝符号链接依赖文件；解析后要求仍位于项目根目录内。
4. `requirements.txt` 只读取普通依赖行，忽略注释和 `-` 开头的选项行；`pyproject.toml` 只读取 PEP 621 `[project].dependencies`，不读取 optional dependencies、dependency groups 或 Poetry 依赖。
5. 没有可审计依赖文件时返回 `ValidationError`，不创建成功任务。
6. 选中文件只能来自 `discover()` 的结果。
7. pyproject 使用临时 requirements 文件交给 pip-audit，结束后清理。
8. pip-audit 不可用、超时、执行错误、零 `audited` 都转为 `FAILED`。
9. 成功后 Finding 映射到项目内相对依赖文件路径，并写入项目 ID 和任务 ID。

**分类**：`CURRENTLY_CONFIRMED`（静态代码）；实际 pip-audit 行为 `HISTORICAL_ONLY`。

**已确认限制**：

- `audited != 0` 是唯一成功阈值；没有把 `skip_reason` 数量与完成数量分开，导致 B2-01。
- 只支持直接依赖文件、PEP 621 依赖和普通 requirements 行；嵌套 requirements、constraints、可选依赖组、Poetry 依赖不在当前范围内。

## 4. Finding 生命周期与状态历史

### 4.1 创建与查询

- `ScanService._save_findings`（`services/scan_service.py:456`）接收扫描器 Finding，写入项目 ID、任务 ID 和受影响范围；保存 SQL 显式带 `project_id`。
- `DependencyAuditService._map_findings` 把绝对依赖路径转为项目内相对路径，再保存。
- `VulnerabilityRepository.list_findings(project_id=...)` 在 SQL 中加入 `f.project_id = ?`；`get_finding(project_id, finding_id)` 同时按两列过滤。
- `VulnerabilityService.list_findings(project_id=None)` 可以返回所有项目；这是全局漏洞列表的**只读聚合视图**，不等于跨项目写权限。UI 的全局视图需要用户明确选择项目后执行写操作。

### 4.2 状态变更与历史

`services/vulnerability_service.py:107-166`：

1. 校验目标状态枚举和备注长度（2000 字符）。
2. `get_finding(project_id, finding_id)` 先确认 Finding 属于该项目。
3. `update_status` 在数据库事务中读取旧状态、更新 Finding、写入 `finding_status_history`；两者同项目。
4. 只有状态实际变化才写审计日志；更新备注另写一条审计日志。
5. `list_history` 先 `get_finding(project_id, finding_id)`，再按项目/ Finding 查询历史。
6. 状态值由 `FindingStatus` 枚举限制，但当前没有“允许的状态转移矩阵”；任意目标状态都可以从任意旧状态设置。这是产品规则缺口，不是跨项目越权。

**分类**：项目过滤和状态历史写入 `CURRENTLY_CONFIRMED`；状态转移规则缺失 `CURRENTLY_CONFIRMED` 静态事实；实际交互 `REQUIRES_RUNTIME_TEST`。

### 4.3 跨项目风险判断

当前未发现 Finding 的跨项目写路径：

- 查询、详情、历史、状态更新、备注更新都要求 `project_id`，并在 repository 中同时过滤 Finding 和项目。
- 任务查询和 Finding 查询按项目过滤。
- 全局列表可以显示多个项目，但每行携带项目 ID；UI 写操作使用该行项目 ID，需用户选择，不是“当前项目”自动越权。

仍存在的风险是**调用方传错 project_id**；服务层没有“当前会话项目”这一全局上下文，因此正确性依赖 UI 传入与行一致的 ID。该风险属于调用契约，不是已确认的越权缺陷。

## 5. Evidence 生命周期与文件安全

### 5.1 添加与复制

`services/evidence_service.py`：

- 构造函数 `EvidenceService(..., evidence_root, ...)` 在 `:61-62` 执行 `Path(evidence_root).expanduser().resolve()` 并创建根目录。
- `add_evidence()` 先确认项目存在、Finding 属于同一项目；标题/内容/来源有长度限制。
- 文件证据：
  1. `_validate_source_file()` 要求绝对路径。
  2. 通过 `ScopeValidator.check_local_path(project.local_path, operation="evidence_import")`。
  3. 取授权根目录的 `Path(decision.target).resolve()`。
  4. 明确拒绝源文件 `is_symlink()`；再 `resolve(strict=True)`。
  5. 要求 `resolved.relative_to(root)` 成功。
  6. 要求是普通文件，大小不超过 50 MiB。
- `_copy_into_evidence_store()` 创建 `evidence_root/project_<id>/`，用 UUID + 安全化文件名复制；复制后计算 SHA-256；再次检查 `target.parent.resolve() == project_dir.resolve()`。
- 数据库写入失败时删除已复制文件；源文件不被移动或删除。
- 删除证据只删除受管副本；源文件保持；Finding 本身不删除。

**分类**：正常路径、源文件 symlink 拒绝、源文件越界拒绝、复制失败清理 `CURRENTLY_CONFIRMED`；动态 Windows symlink 成功/失败分支 `REQUIRES_RUNTIME_TEST`。

### 5.2 项目隔离

- `get_evidence(project_id, evidence_id)` 和 `delete_evidence(project_id, evidence_id)` 都先确认项目，再由 repository 按 `project_id + evidence_id` 查询/删除。
- `add_evidence()` 要求 Finding 属于同一项目；跨项目 Finding 被拒绝。
- `list_evidence(project_id=None)` 可返回所有项目证据；这是全局证据列表的只读聚合，不是跨项目写权限。
- `EvidencePage` 提供“全部项目”筛选项，并允许从行项目进入添加/删除；写操作使用行项目 ID，而不是当前项目自动覆盖。

### 5.3 已确认的 Evidence 路径风险（与 R0-B1 关联）

`_root` 在构造时 `resolve()`，但没有拒绝 `evidence_root` 本身是符号链接/junction。如果部署配置的 `storage/evidence` 根目录本身被替换为 junction，构造后 `_root` 指向外部目标。

更具体地，`_copy_into_evidence_store()`：

- `project_dir = self._root / f"project_{id}"`；
- `project_dir.mkdir(parents=True, exist_ok=True)` 对已存在的 junction 目录会成功；
- `shutil.copy2(source, target)` 会写入该 junction 指向的外部目录；
- 复制后的 `target.parent.resolve() == project_dir.resolve()` 仍然成立，因为两者都解析到同一外部目标；
- `_unlink_managed()` 先做 `resolved.relative_to(self._root)`，若 `_root` 本身已解析到外部目标，它可能把外部目标视为根内。

因此，**如果攻击者能预先在 evidence 根目录下创建 `project_<id>` junction**，证据文件可能被复制到 evidence 根目录之外。当前测试覆盖了“源文件 symlink/junction 指向外部”，但没有覆盖“evidence 根目录或 `project_<id>` 本身是 junction”。该问题与 R0-B1 的“报告导出根目录 reparse”属于同类，但作用对象不同。

**分类**：`CURRENTLY_CONFIRMED` 静态代码路径；动态 junction/ACL 场景 `REQUIRES_RUNTIME_TEST`。

## 6. 授权与项目隔离

### 6.1 `ScopeValidator.check_local_path`

`security/scope_validator.py:437-551`：

1. 确认项目存在；不存在直接拒绝。
2. `normalize_local_path()` 要求绝对路径，`Path.resolve(strict=False)` 后 `normcase`。
3. 检查存在、是目录、`os.access(..., os.R_OK)`。
4. SQL 同时过滤 `project_id`、规范化路径、`asset_type IN ('local_folder','local_project')`。
5. 要求资产状态为 `ACTIVE`。
6. 允许时记录 `authorization_check` 审计；审计存储不可用时把 allow 改成 deny（fail-closed）。

**分类**：`CURRENTLY_CONFIRMED`。

**已确认限制**：

- `normalize_local_path()` 会解析符号链接/junction；授权资产保存的是解析后的目标路径。若用户以为授权的是链接路径，实际授权范围是目标路径。该行为不一定越权，但应在产品语义上明确。
- 当前不检查路径的父级组件是否为 reparse point；只检查 `candidate` 本身的存在/目录/读取和规范化结果。
- 本地资产必须精确匹配；不会因为“同目录”自动授权子路径。

### 6.2 扫描与依赖审计的项目绑定

- `ScanService` 的目标固定为项目 `local_path`，且先通过 ScopeValidator；任务和 Finding 用项目 ID 绑定。
- `DependencyAuditService` 的目标固定为项目 `local_path` 下发现的文件，且文件必须在项目根内。
- 扫描器不可用/失败会产生任务 FAILED 或 warning，不会生成伪造 Finding。
- 当前没有发现“扫描项目 A 却写入项目 B”的静态路径。

### 6.3 Evidence 的项目绑定

- 文件证据要求 Finding 同项目、源文件在项目授权根内。
- 读取/删除要求项目 ID。
- “全部项目”列表是只读聚合；写操作需要行项目 ID。

### 6.4 未发现与仍不能证明的事项

未发现直接的跨项目 SQL 写路径、未发现扫描器可指定任意项目 ID、未发现 GUI 直接 SQL。

但不能仅凭静态代码证明：

- 所有 UI 入口都传入正确项目 ID；
- 所有错误路径都在 UI 中可见；
- Evidence 根目录/project 目录的 junction 在运行时一定被拒绝；
- ScopeValidator 对父级 reparse point 的行为在所有 Windows 版本一致。

这些列为 `REQUIRES_RUNTIME_TEST` 或 `UNKNOWN`，不升级为“已确认安全”。

## 7. 测试覆盖矩阵

### 7.1 现有测试

| 文件 | 测试函数数 | 当前覆盖的事实 |
|---|---:|---|
| `tests/test_bandit_scanner.py` | 7 | 可用性、空结果、解析、路径/敏感字段处理、执行失败/超时等 |
| `tests/test_semgrep_scanner.py` | 6 | 可用性、JSON 解析、空结果、错误路径 |
| `tests/test_pip_audit_scanner.py` | 8 | 可用性、JSON 解析、去重、空结果、执行失败/超时 |
| `tests/test_scan_service.py` | 13 | 成功/空结果/失败/超时/取消/不可用/部分扫描器/项目绑定 |
| `tests/test_dependency_audit_service.py` | 15 | 发现文件、requirements/pyproject、无文件、零审计、失败、项目隔离 |
| `tests/test_vulnerability_service.py` | 6 | 查询、状态、备注、历史、项目隔离 |
| `tests/test_evidence_service.py` | 11 | 文本/文件证据、哈希、重名、路径穿越、symlink/junction、删除、项目隔离 |
| `tests/test_scope_validator.py` | 16 | 项目/路径/授权状态/远程/本地范围 |
| `tests/test_ui_report.py` | 16 | 报告页 GUI；不覆盖扫描器/证据中心 |

### 7.2 已确认的测试缺口

1. **没有“全部依赖均带 `skip_reason`”用例。** `tests/test_pip_audit_scanner.py:53-78` 反而明确把 `skipped-package` 计入 `audited == 3`；`tests/test_dependency_audit_service.py:221-236` 只覆盖 `audited=0`。因此当前测试不会阻止 B2-01 的“全部跳过仍成功”。
2. 没有证据根目录/project 目录 junction 的测试；现有 `test_junction_to_outside_is_rejected` 只覆盖**源文件路径**的 junction。
3. 没有 Bandit 项目路径包含 `env` 组件的回归测试；历史 C1-R 只在手工临时目录观察到。
4. 没有 Semgrep 在当前 Windows 的真实运行测试；历史测试只覆盖不可用/解析路径。
5. 没有 `run_command` 子进程树的取消/超时测试；只验证直接进程返回。
6. 没有“多扫描器时一个成功、一个执行失败”的 UI 展示测试；服务测试只覆盖不可用 scanner 的 warning。
7. 没有 ScopeValidator 对父级 reparse point、路径中间 symlink 的系统性测试。
8. 没有 Evidence “全部项目”视图下写操作必须使用行项目 ID 的 UI 级测试。

### 7.3 测试分类

- 现有测试文件存在和测试函数数量：`CURRENTLY_CONFIRMED`（本次静态检查）。
- 历史 pytest 结果（210 collected / 203 passed / 7 skipped / 49.92s）：`HISTORICAL_ONLY`。
- 当前环境是否仍全绿：`UNKNOWN`；本任务未运行 pytest。

## 8. 当前已确认问题

### B2-01：pip-audit 将“跳过的依赖”计入已审计，可能产生错误的“无漏洞”结论

**严重度**：高（结果真实性）。

**证据**：

- `scanners/pip_audit_scanner.py:210-311`：`skip_reason` 只追加 warning，仍继续处理 `vulns`；函数最后返回 `len(dependencies)`，不是“成功完成审计的依赖数”。
- `tests/test_pip_audit_scanner.py:53-78`：样本包含 `skipped-package`，断言 `audited == 3`，说明当前行为被测试固定。
- `services/dependency_audit_service.py:325-338`：仅当 `audited == 0` 才失败；`audited=3` 且全部被跳过时仍进入成功分支，摘要为“已审计 3 个依赖，未发现已知漏洞”。
- `services/dependency_audit_service.py:355-372`：成功摘要不区分“完成审计的依赖”和“跳过/resolve 失败的依赖”。

**影响**：当依赖解析失败、网络/索引异常或 pip-audit 跳过所有依赖时，任务可标记 `COMPLETED`，用户可能把“未完成审计”理解为“没有漏洞”。这是扫描器层面的假阴性/假保证。

**当前状态**：`CURRENTLY_CONFIRMED` 静态代码和测试断言；当前 pip-audit 实际输出 `REQUIRES_RUNTIME_TEST`。

**建议的修复方向（本次未实施）**：

- 分离 `total_dependencies`、`audited_dependencies`、`skipped_dependencies`。
- 只有 `audited_dependencies > 0` 才允许成功；全部跳过时任务为 `FAILED` 或至少 `COMPLETED_WITH_WARNINGS`，不得显示“未发现漏洞”。
- 增加“全部依赖 skip_reason”与“部分跳过”测试，并明确 UI 状态。

### B2-02：Evidence 根目录或 `project_<id>` junction 可导致受管副本写到根目录之外

**严重度**：中（条件性路径越界；需要本地目录预先被替换）。

**证据**：`services/evidence_service.py:61-62`、`:250-269`。`evidence_root` 在构造时 `resolve()`，但没有拒绝根目录本身是 reparse point；`project_dir.mkdir()` 对已有 junction 成功；`shutil.copy2()` 写入 junction 目标；复制后的 parent 解析比较无法识别这种“双方都解析到同一外部目录”的情况。

**分类**：`CURRENTLY_CONFIRMED` 静态路径；Windows 动态行为 `REQUIRES_RUNTIME_TEST`。

### B2-03：Bandit 的 `-x` 路径组件排除可能导致合法项目被静默跳过

**严重度**：中（假阴性；依赖项目路径）。

**证据**：`scanners/bandit_scanner.py` 的命令参数包含 `-x .venv,.git,__pycache__,venv,env,node_modules,build,dist`。历史 Phase 6-C1-R 已观察到临时目录名含 `env` 时 Bandit 返回 0 findings；改名后恢复。当前没有针对该路径形状的回归测试。

**分类**：`HISTORICAL_ONLY` 观察 + `CURRENTLY_CONFIRMED` 参数；当前实际行为 `REQUIRES_RUNTIME_TEST`。

### B2-04：Semgrep 在当前 Windows 环境没有真实运行证据

**严重度**：中（功能覆盖依赖环境；已长期记录）。

**证据**：历史 Phase 3 报告记录 `CertOpenSystemStore returned NULL`；当前源码保留 Semgrep 接口、规则和不可用处理，但本任务不运行。只有 Bandit 时，源码审计不应被描述为“Semgrep 已完成”。

**分类**：`HISTORICAL_ONLY` + `REQUIRES_RUNTIME_TEST`。

### B2-05：取消/超时只终止直接子进程

**严重度**：低到中（取决于扫描器是否启动子进程）。

**证据**：`scanners/process_runner.py` 的 `_terminate` 对 `Popen` 直接进程执行 terminate/kill；没有 Windows Job Object 或进程树终止。Bandit/Semgrep/pip-audit 通常是单进程，但工具内部可能派生进程；不能证明所有子进程都被回收。

**分类**：`CURRENTLY_CONFIRMED` 静态实现；残留进程行为 `REQUIRES_RUNTIME_TEST`。

### B2-06：ScopeValidator 解析 symlink/junction 后才做精确资产匹配

**严重度**：低到中（语义/边界）。

**证据**：`security/scope_rules.py:normalize_local_path` 使用 `Path.resolve(strict=False)`；`ScopeValidator.check_local_path` 用解析后的路径查资产。若用户创建的授权路径本身是链接，实际授权目标是解析后的路径；如果目标在项目目录外，授权语义需要明确记录，不能把“链接路径”误认为受限根。

**分类**：`CURRENTLY_CONFIRMED` 路径规范化行为；具体绕过场景 `REQUIRES_RUNTIME_TEST`/`UNKNOWN`。

### B2-07：Evidence 根目录父级 reparse point 与报告导出根目录问题同类

**严重度**：中（与 R0-B1 关联）。

**证据**：R0-B1 已确认 `reports/html_exporter.py` 只检查 `reports_dir` 本身，不检查父级 reparse；Evidence 同样没有检查 `evidence_root` 的父级组件。两个模块的根目录均可由配置指定，部署时需确保目录链不受不可信替换。

**分类**：`CURRENTLY_CONFIRMED` 静态；运行时 `REQUIRES_RUNTIME_TEST`。

### B2-08：全局列表允许查看所有项目，写操作依赖调用方项目 ID

**严重度**：信息/设计边界（不是已确认越权）。

**证据**：`VulnerabilityService.list_findings(project_id=None)`、`EvidenceService.list_evidence(project_id=None)` 可跨项目聚合；UI 有“全部项目”筛选。所有写方法要求显式 `project_id`，并用 Finding/Evidence 的项目列过滤。单用户本机工作台上这是可接受设计；若未来多用户或服务端化，需要重新定义“当前项目”授权。

**分类**：`CURRENTLY_CONFIRMED` 设计事实；越权结论 `UNKNOWN`（没有多用户模型）。

## 9. 需要运行验证与尚无法确认的事项

### 9.1 需要实际运行验证

1. 当前 Windows 上 Semgrep 是否仍因证书存储失败；失败时 `ScanService` 是否只在 Semgrep 单独任务中失败。
2. pip-audit 在网络不可达、索引解析失败、全部依赖 `skip_reason` 时的真实输出和最终任务状态；验证 B2-01。
3. Bandit 扫描路径包含 `env`、`venv`、`build` 等组件时是否产生假零结果。
4. Evidence 根目录/project 目录 junction 的实际行为；测试需在专用临时目录创建 junction，不修改系统 ACL。
5. 取消/超时时扫描器子进程是否残留；需要进程树观察。
6. GUI 中“全部项目”列表的添加/删除/状态更新是否始终使用行项目 ID；需要真实点击或 UI 测试。
7. ScopeValidator 对路径中间 symlink、父级 junction 的实际结果。

### 9.2 当前无法确认

- Semgrep 在任何当前环境（Windows/Linux/WSL）的真实扫描结果。
- 当前 Bandit/Semgrep/pip-audit 版本是否与历史报告一致；本任务没有重新执行 `--version`。
- 当前完整 pytest 结果；没有运行。
- Evidence 根目录是否在部署环境被 reparse；静态代码不能证明运行环境。
- 多用户/远程部署下的项目隔离；当前产品定位是本地单用户工作台，没有多用户身份模型。

## 10. 总体结论

**`OVERALL_DELIVERY_JUDGMENT = NOT_READY`**

理由：

- 结构链路是完整的：项目/授权范围 → 扫描任务 → Finding → 状态/历史 → Evidence；项目 ID 在任务、Finding、历史和 Evidence 写入中均有显式过滤；未发现直接的跨项目写路径。
- 但 B2-01 是扫描结果真实性问题：pip-audit 将 `skip_reason` 依赖计入 `audited`，全部跳过时可以显示“已审计、未发现漏洞”。在安全审计产品中，这种假保证不能接受。
- B2-02（Evidence 根目录/project junction）是条件性路径越界；B2-03（Bandit `env` 排除）可导致假阴性；B2-04（Semgrep 当前无真实运行证据）限制源码审计覆盖。
- B2-01 修复并完成针对性运行验证前，不应把当前扫描结果作为“完整、可靠”的授权安全结论。

**建议**：先修复 B2-01 并增加全部跳过/部分跳过测试；再进行 B2-02、B2-03 的运行时验证；Semgrep 继续标记为环境限制，不伪造成已完成。修复和验证不属于本次 R0-B2 范围，本次未实施。

## 11. 本次实际文件变化与 Git 状态

- 新增：`docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md`。
- 生产代码修改：NO。
- 测试代码修改：NO。
- 数据库/Schema 修改：NO。
- 配置修改：NO。
- 既有文档修改：NO。
- Git add/commit/push/reset/restore/clean：NO。
- 运行 pytest/扫描器/GUI：NO。
- 调查前既有工作区：staged 0，`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`，4 个未跟踪报告。
- 报告写入后新增一个未跟踪报告；既有修改保持不变。

**`PHASE6_R0_B2_STATUS = COMPLETED`**
