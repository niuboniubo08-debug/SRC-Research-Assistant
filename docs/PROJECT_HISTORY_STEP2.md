# SRC Research Assistant 项目历史重建——步骤 2：Phase 3–5 开发历史

- 调查日期：2026-11-06（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 调查范围：Phase 3、Phase 4、Phase 5
- 明确排除：Phase 6、当前开发、任何功能实施
- 结论标记：`confirmed` / `inferred` / `unknown` / `contradicted`

> 本文是历史调查文件，不是验收记录，不修改任何生产代码、测试、数据库、Schema、依赖、配置、历史验收报告或 Manifest。本文所有测试数字均来自历史报告、历史数据库或历史归档，不是本次重新执行的结果。

## 1. 结论摘要

| 阶段 | 版本 / Schema | 结论 | 关键证据 |
|---|---|---|---|
| Phase 3 本地 Python 源代码审计 | `0.3.0` / v3 | **部分通过** | Bandit 真实运行；Semgrep 当前 Windows 环境不可用；81 passed |
| Phase 4 Python 依赖漏洞审计 | `0.4.0` / v4 | **通过** | pip-audit 2.10.1 真实运行；19 个唯一漏洞；105 passed |
| Phase 5 漏洞管理与证据中心 | `0.5.0` / v5 | **通过（1 项环境限制）** | 126 passed / 1 skipped；41 findings / 3 evidence / 2 history |

阶段关系：

- Phase 3 建立了统一 `BaseScanner`、`Finding`、`ScanTask`、子进程执行器和源代码审计 UI。
- Phase 4 复用 Phase 3 的接口、任务和 Finding，不新建第二套结果模型；新增 `pip-audit` 和 `metadata_json`。
- Phase 5 首次引入 Repository，但只用于漏洞管理和证据管理；扫描服务仍保留 Phase 3/4 的 Service + Database 模式。
- 三个阶段都保持本地优先、项目范围校验、禁止远程扫描/利用/爆破的边界。

## 2. Phase 3 开发历史

### 2.1 目标

Phase 3 的目标是：在已完成的本地项目、授权和 `ScopeValidator` 基础上，对当前授权项目的本地 Python 源代码执行非破坏性安全审计，并将扫描器结果统一为 `Finding`、扫描过程统一为 `ScanTask`，由 GUI 展示。

明确不做：远程扫描、网站扫描、漏洞利用、自动攻击、任意路径扫描。

### 2.2 开发前基线（confirmed）

`docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md:9-23` 记录了实际基线：

- 原有测试 **40 passed / 0 failed / 0 skipped**，6.71 s；
- 数据库 schema v2，10 张表，外键 ON；
- `ScopeValidator.check_local_path` 已存在，签名 `check_local_path(project_id, path, operation="local_audit", *, at=None) -> AccessDecision`；
- 不存在 `ScanService`、扫描任务模型、扫描结果 Repository 或 Python Finding 模型；
- Bandit、Semgrep 均未安装；
- `evidence`、`findings` 等表只有基础占位字段。

此阶段的取舍是继续复用 `Database`、Service 层、`ScopeValidator`、`AppContext` 和 UI 导航，不重建项目。`confirmed`。

### 2.3 新增能力

- **统一扫描器接口**：`scanners/base.py` 定义 `BaseScanner`、`ScanOptions`、`ScanOutput`，以及 `ScannerUnavailable`、`ScannerExecutionError`、`ScannerParseError`、`ScannerTimeoutError`、`ScanCancelled`。
- **安全子进程**：`scanners/process_runner.py` 使用 `Popen([...], shell=False)`，参数列表调用，后台线程排空 stdout/stderr，超时/取消终止，输出上限 8 MiB。
- **Bandit 集成**：`scanners/bandit_scanner.py`，实际 Bandit 1.9.4，解析 JSON，处理空结果、执行失败、解析失败、超时、取消；B105/B106/B107 原始凭据值不写入统一结果。
- **Semgrep 集成**：`scanners/semgrep_scanner.py` + `scanners/rules/python_security.yml`（7 条本地 Python 规则）；使用本地规则，不访问 Registry，不自动下载。
- **统一 Finding**：`core/models/finding.py`，字段含 `title/category/severity/confidence/description/file_path/line_number/rule_id/recommendation/scanner_name/scanner_version/detected_at/project_id/task_id`。
- **扫描任务**：`services/scan_service.py`，状态 `pending → running → completed/failed/cancelled`，保存进度、当前扫描器、错误、结果汇总、请求的扫描器。
- **数据库 v3**：`scan_tasks` 增加 `current_scanner/progress/error_message/scanners_json/cancel_requested/cancelled_at`；`findings` 增加 `confidence/file_path/line_number/rule_id/scanner_name/scanner_version/detected_at`；新增 3 个索引。
- **源代码审计 UI**：`ui/source_audit_page.py`，QThread 后台扫描，扫描器可用性、开始/取消、进度、结果表、风险/扫描器筛选、详情。

以上新增能力及 v3 变更均有阶段报告、测试和归档支持。`confirmed`。

### 2.4 实际 Semgrep 状态

必须区分四个层次：

| 问题 | 实际结论 | 判定 |
|---|---|---|
| Semgrep 是否安装 | pip wheel 已安装；记录版本 `1.183.0` | `confirmed` |
| 版本号是否可读取 | 验收 JSON 与 UI 记录 `1.183.0` | `confirmed`（来自安装元数据/记录，不等于 CLI 成功） |
| Semgrep 是否成功执行 | `semgrep --version` 退出码 2；原生二进制在 CA 存储初始化失败 | **否定** |
| 是否真实产生 Semgrep Finding | 无；Semgrep-only 任务 `failed`，0 Finding | **否定** |
| 是否在 Linux/WSL 真实运行验证 | 没有历史记录 | `unknown` |

真实错误（`docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md:49-50,96-101`）：

```text
Fatal error: exception Failure:
ca_certs_iter_on_anchors: CertOpenSystemStore returned NULL
```

因此 Phase 3 的 Semgrep 结论只能是：接口、本地规则文件、JSON 解析器和不可用状态处理已完成；**没有真实 Semgrep 扫描结果**。UI/Service 显示真实不可用原因，未伪造成功。`confirmed`。

### 2.5 调用链与失败语义

```text
SourceAuditPage
  → ScanService
    → ProjectService（当前项目本地路径）
    → ScopeValidator.check_local_path(project_id, path, "source_audit")
    → BaseScanner 注册表
       ├─ BanditScanner → process_runner → python -m bandit
       └─ SemgrepScanner → process_runner → semgrep.exe（当前不可用）
    → Database（scan_tasks / findings）
    → AuditLogService（scan_logs / audit.jsonl）
```

语义（`docs/PHASE3_ARCHITECTURE.md:102-113`）：

- `completed`：至少一个扫描器成功执行；0 Finding 仍是 completed；
- `failed`：所有所选扫描器不可用、执行/解析失败或超时；
- `cancelled`：用户取消；不标记 completed；
- 部分成功：已成功扫描器的结果保留，任务最终状态可为 failed；取消时已产生结果也保留。

## 3. Phase 3 核心文件与架构

| 文件 | 作用 |
|---|---|
| `scanners/base.py` | 统一扫描器接口、选项、输出、异常 |
| `scanners/process_runner.py` | `shell=False` 参数列表子进程、超时、取消、输出上限 |
| `scanners/bandit_scanner.py` | Bandit 1.9.4 适配与 JSON 解析 |
| `scanners/semgrep_scanner.py` | Semgrep 适配器；当前环境不可运行 |
| `scanners/rules/python_security.yml` | 7 条本地规则；未完成 Semgrep 运行时校验 |
| `core/models/finding.py` | 统一 Finding |
| `core/models/scan_task.py` | ScanTask |
| `services/scan_service.py` | 任务状态机、路径校验、扫描器编排、Finding 入库、查询 |
| `ui/source_audit_page.py` | QThread 审计页面 |
| `database/schema.py` / `connection.py` | v3 字段、索引、迁移 |

**Repository 关系**：Phase 3 没有 Repository。`services/scan_service.py:294-314` 直接 `INSERT INTO scan_tasks`，`services/scan_service.py:466-500` 左右直接 `INSERT INTO findings`；查询也直接使用 SQL。项目此时是 **UI → Service → SQLite**，不是 UI → Service → Repository → SQLite。`confirmed`。

**UI 边界**：`ui/source_audit_page.py` 只调用 `ScanService`；代码质量报告记录 `UI_SCANNER_IMPORTS=0`、`UI_SQL_STATEMENTS=0`（`docs/acceptance/PHASE3_TEST_REPORT.md:112-132`）。`confirmed`。

## 4. Phase 3 测试与真实运行

### 4.1 历史测试结果

来源：`docs/acceptance/PHASE3_TEST_REPORT.md:4-17,54-75`。

```text
81 passed / 0 failed / 0 skipped in 16.74s
```

| 指标 | 结果 |
|---|---:|
| collected / total | 81 |
| passed | 81 |
| failed | 0 |
| skipped | 0 |
| 耗时 | 16.74 s |
| 基线 | 40 passed in 6.71s |
| 真实远程目标 | 0 |

新增测试（`PHASE3_TEST_REPORT.md:60-75`）：

- `test_local_path_audit.py` 7；
- `test_finding_models.py` 3；
- `test_process_runner.py` 3；
- `test_bandit_scanner.py` 7；
- `test_semgrep_scanner.py` 6；
- `test_scan_service.py` 13；
- `test_ui_source_audit.py` 1。

### 4.2 真实验收

验收库：`storage/phase3_acceptance/acceptance.db`，schema v3，2 projects / 4 scan_tasks / 12 findings / 27 scan_logs / 0 evidence，外键 0 违规（本次只读查询）。

| 运行 | 状态 | 结果 |
|---|---|---|
| Bandit 扫 unsafe | completed | 6 Finding：B602、B307、B301、B404、B105、B403 |
| Bandit 扫 safe | completed / 0 Finding | 证明“无结果 ≠ 失败” |
| Semgrep-only 扫 unsafe | failed / 0 Finding | 真实不可用；未伪造 |
| Bandit + Semgrep 组合 | completed | Bandit 6；Semgrep 跳过并记录 warning |

注意：数据库中的 **12 findings 是 6 条问题在两次 Bandit 任务中的重复行**（task 3 的单独 Bandit 与 task 4 的 Bandit+Semgrep 组合各 6 条），不是 12 个不同漏洞。`confirmed`；报告未明确说“唯一漏洞数”，数据库行数不能当作唯一漏洞数。

凭据脱敏：`phase3-acceptance-secret` 未出现在统一 Finding 标题/说明中；`phase3_acceptance.json` 的 `safety.secret_in_findings=false`。`confirmed`。

Semgrep 没有真实 Finding；`test_semgrep_scanner.py` 的解析结果来自 fixture，不是真实工具输出。`confirmed`。

## 5. Phase 4 开发历史

### 5.1 目标

Phase 4 的目标是：只审计当前授权本地项目根目录的 Python 依赖文件，通过 `pip-audit` 查询公开漏洞数据，将依赖漏洞转换为统一 Finding，复用 ScanTask、项目隔离、审计和 UI 模式。

明确不做：远程目标扫描、网站扫描、漏洞利用、自动攻击。`pip-audit` 只访问公开漏洞服务/包索引。

### 5.2 开发前基线（confirmed）

`docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md:10-24`：

- 原有测试 **81 passed / 0 failed / 0 skipped**，19.36 s；
- schema v3；
- 已有 `BaseScanner`、Bandit、Semgrep、`ScanService`、`ScanTask`、`Finding`、项目/任务隔离；
- `pip-audit` 未安装；
- **项目中不存在独立 Repository 层，继续 Service + Database**；
- 依赖页面是占位页。

### 5.3 新增能力

- `scanners/pip_audit_scanner.py`：pip-audit 2.10.1 适配器、可用性、命令构造、JSON 解析、去重。
- `services/dependency_audit_service.py`：依赖文件发现、requirements/pyproject 支持、任务编排、结果保存。
- `requirements.txt` / `pyproject.toml` 只检查项目根目录直接文件，不递归。
- `pyproject.toml` 仅提取 PEP 621 `[project].dependencies`；在项目自有临时目录生成 requirements 输入，任务结束清理。
- 两者同时存在时优先 `requirements.txt`。
- 无依赖文件：不创建任务，UI 明确显示“未发现可审计依赖”。
- 有文件但无有效依赖、零 audited dependencies：`failed`，不伪装“无漏洞”。
- 数据库 v4：`findings.metadata_json`。
- UI `ui/dependency_page.py`：依赖文件、可用性、开始/取消、状态、完成时间、结果与详情。

### 5.4 命令与安全边界

`scanners/pip_audit_scanner.py:145-177` 实际构造参数列表：

```text
pip-audit -r <requirements>
  --format json
  --progress-spinner off
  --timeout <socket timeout>
  --desc on
  --aliases on
  --vulnerability-service pypi
  --cache-dir <project-owned cache>
```

`scanners/process_runner.py:88-94`：

```python
subprocess.Popen(
    list(argv),
    ...
    shell=False,
)
```

结论：

- **无 shell 字符串拼接，无 `shell=True`**；
- 用户可选择依赖文件，但最终路径经过项目根目录、符号链接和 `relative_to(root)` 校验（`services/dependency_audit_service.py:124-211`）；
- `requirements.txt` 只从项目根目录直接读取；
- `pyproject.toml` 解析失败/缺少 `[project].dependencies` 明确不可审计；
- pip-audit 的临时目录、`TMP`/`TEMP`、`PIP_CACHE_DIR`、`--cache-dir` 都指向应用/项目自有目录，避免默认用户缓存问题；
- 网络仅用于 pip-audit 的公开漏洞服务和包解析，不扫描远程目标。`confirmed`。

命令注入风险评估：未发现将用户输入拼入 shell 命令的路径；参数通过 `argv` 列表传递；`target_path` 来自项目根目录内的文件。`confirmed`（基于代码与测试；不是运行时渗透测试）。

### 5.5 severity / affected range 真实性

实际查询 `storage/phase4_acceptance/acceptance.db`（只读）：

```text
findings = 38
risk_level: medium = 38
metadata_json severity_source: conservative-default = 38
metadata 缺失 = 0
metadata 含 cvss 字段 = 0
affected_versions 为同一类泛化文本：
  “当前审计版本 <version> 命中；具体受影响范围见漏洞公告”
```

`scanners/pip_audit_scanner.py:256-265,267-292`：

- 若 JSON 有 `severity`/`cvss`/`cvss_score`，才尝试映射；
- 当前 pip-audit JSON 没有这些字段时，显式使用 `Severity.MEDIUM`；
- `severity_source = "conservative-default"`；
- `affected_versions` 仅在 JSON 提供时使用，否则写“当前审计版本命中；具体范围见公告”；
- 不伪造 CVSS，不把公告提示写成精确受影响范围。

结论：**没有把 pip-audit 未提供的 CVSS 伪装成真实数据**。`confirmed`。

## 6. Phase 4 核心文件与架构

```text
DependencyPage (QThread)
  → DependencyAuditService
    → ProjectService
    → ScopeValidator.check_local_path(..., "dependency_audit")
    → 依赖文件发现（requirements.txt / pyproject.toml）
    → PipAuditScanner → process_runner → pip-audit
    → Database（scan_tasks / findings）
    → AuditLogService
```

**Repository 关系**：Phase 4 仍没有 Repository。`services/dependency_audit_service.py:463-650` 直接 `INSERT/UPDATE scan_tasks`、`INSERT findings`、`SELECT`；项目仍是 **UI → Service → SQLite**。Phase 4 归档 `backups/src-research-assistant_phase4_final.zip` 中 `repositories/` 文件数为 0（本次 ZIP 只读列表检查）。`confirmed`。

**复用而非重建**：复用 `ScanTask`、`Finding`、`BaseScanner`、`process_runner`、`ScopeValidator`、`AuditLogService`、`ProjectService`、QThread 模式；没有第二套任务/结果表。`confirmed`。

## 7. Phase 4 测试与真实运行

### 7.1 历史测试结果

来源：`docs/acceptance/PHASE4_TEST_REPORT.md:11-17,37-61`。

```text
105 passed / 0 failed / 0 skipped in 25.16s
```

| 指标 | 结果 |
|---|---:|
| total | 105 |
| passed | 105 |
| failed | 0 |
| skipped | 0 |
| 耗时 | 25.16 s |
| 基线 | 81 passed in 19.36s |
| 新增 | 24 项（pip-audit 8 + 依赖服务 15 + 依赖 UI 1） |
| 真实远程目标 | 0 |

### 7.2 真实 pip-audit 验收

`docs/acceptance/phase4_acceptance.json` 与只读数据库查询：

| 项目 | 输入 | 审计依赖 | 唯一漏洞 | 任务 |
|---|---|---:|---:|---|
| requirements | `requests==2.19.0` | 5 | 19 | completed |
| pyproject | PEP 621 dependencies | 5 | 19 | completed |
| safe | `six==1.16.0` | 1 | 0 | completed |

数据库：

```text
projects=3
scan_tasks=3（全部 dependency_audit）
findings=38
findings_with_metadata=38
scan_logs=33
foreign_key_violations=0
```

`38` 条 Finding 是 19 + 19 + 0；不是 38 个全局唯一漏洞。两个项目各自真实审计出同一组 19 个漏洞 ID，测试没有跨项目去重。`confirmed`。

真实 Finding 示例（`PHASE4_ACCEPTANCE_REPORT.md:100-110`）：

```text
requests 2.19.0 · PYSEC-2018-28
依赖：requests 2.19.0
漏洞编号：PYSEC-2018-28
别名：CVE-2018-18074
修复：升级 requests 至 2.20.0 或更高版本
来源：pip-audit/PyPI
文件：requirements.txt 第 1 行
```

### 7.3 真实 / 模拟区分

- 真实：pip-audit 2.10.1 执行、requirements/pyproject 审计、19/0 结果、数据库保存、真实截图。
- 模拟/夹具：`test_ui_dependency_audit.py` 的端到端 UI 测试使用模拟扫描器（`PHASE4_TEST_REPORT.md:61`），不是真实 pip-audit；UI 实际验收截图来自真实验收数据。
- 未真实验证：离线漏洞库、Poetry/可选依赖组、pip-audit 的 CVSS/精确 affected range。`confirmed`。

### 7.4 已知问题

`PHASE4_ACCEPTANCE_REPORT.md:205-215`、`PHASE4_TEST_REPORT.md:141-147`：

1. pip-audit JSON 无 CVSS/severity；保守 medium，`severity_source` 标记。
2. 无精确 affected version range；只记录“当前命中 + 见公告”。
3. 依赖公开漏洞服务，需网络；离线未实现。
4. pyproject 仅 PEP 621 `[project].dependencies`。
5. 未审计到任何依赖 → failed。
6. Semgrep Windows 验证仍待办。
7. 异常强杀后的 running 任务不自动恢复。

## 8. Phase 5 开发历史

### 8.1 目标

Phase 5 将 Phase 3/4 产生的 Finding 统一为可管理资产，并建立项目证据中心：

- 统一读取 Bandit/Semgrep/pip-audit；
- 漏洞处理状态、状态历史、人工备注；
- 证据添加、受管复制、SHA-256、项目隔离；
- 不删除 Finding、不执行/上传证据；
- 不实现报告、远程检查、利用。

### 8.2 开发前基线（confirmed）

`PHASE5_ACCEPTANCE_REPORT.md:11-24`：

- 105 passed / 0 failed / 0 skipped，24.89 s；
- schema v4；
- 统一 Finding、ScanTask、项目隔离、`check_local_path` 已有；
- `evidence` 表只有旧字段；
- `findings.status` CHECK 不允许 `reviewing`；
- **没有 Repository 层**；
- 漏洞管理、证据中心仍是占位页。

### 8.3 新增能力

**漏洞管理**

- 统一列表、风险/扫描器/状态/项目/关键词筛选；
- 六种状态：`open/reviewing/confirmed/false_positive/fixed/accepted_risk`（`core/models/enums.py:158-195`）；
- `status_changed_at`；状态历史 `finding_status_history`；人工备注 `manual_notes`；
- 详情包含任务、项目、首次/最近发现、源码/依赖信息、metadata、证据、历史；
- 变更按 `project_id + finding_id` 限定。

**证据中心**

- 六种类型（`core/models/enums.py:198-235`）：代码片段、扫描器摘要、依赖信息、截图、人工备注、其他本地文件；
- 一个 Finding 多证据；一个证据只属于一个项目和一个 Finding；
- 文件复制到 `storage/evidence/project_<id>/<uuid>_<name>`；
- SHA-256、来源相对路径、原文件名、创建时间；
- 路径：绝对路径 → 项目本地资产 → `check_local_path` → 项目根目录 → 拒绝符号链接/目录联接越界 → 50 MB 上限；
- 删除先确认；删除受管副本，不删除源文件/Finding；
- 不执行、不上传；
- UI 添加对话框、详情、跨页跳转。

**架构新增**

- `repositories/vulnerability_repository.py`
- `repositories/evidence_repository.py`
- `services/vulnerability_service.py`
- `services/evidence_service.py`
- `ui/vulnerability_page.py`
- `ui/evidence_page.py`
- `ui/evidence_dialog.py`

以上 Phase 5 功能、数据模型与文件均有 `PHASE5_ACCEPTANCE_REPORT.md`、`PHASE5_TEST_REPORT.md`、v5 DB 和归档支持。`confirmed`。

## 9. Phase 5 核心文件与架构

### 9.1 分层

```text
VulnerabilityPage / EvidencePage / EvidenceDialog
  → VulnerabilityService / EvidenceService
    → VulnerabilityRepository / EvidenceRepository
      → Database
```

- `VulnerabilityRepository`：统一查询、项目过滤、状态更新、状态历史、任务读取（`repositories/vulnerability_repository.py:12-215`）。
- `EvidenceRepository`：证据 CRUD、项目/Finding 过滤。
- `EvidenceService`：项目/Finding 校验、绝对路径/`ScopeValidator`/项目根目录/符号链接/50 MB、复制、SHA-256、删除受管副本（`services/evidence_service.py:21-303`）。
- `VulnerabilityService`：筛选、详情、状态、备注、审计（`services/vulnerability_service.py:32-194`）。
- `app/bootstrap.py` 注入两个 Repository 和两个 Service。

### 9.2 单条操作的项目约束

- `VulnerabilityRepository.get_finding(project_id, finding_id)` 的 SQL 同时带 `f.project_id = ? AND f.finding_id = ?`（`repositories/vulnerability_repository.py:69-76`）。
- `update_status` 在事务内先按 `project_id + finding_id` 查旧状态，再更新/写历史（同上 `:106-151`）。
- `EvidenceService.add_evidence` 先 `get_project`、再 `get_finding(project_id, finding_id)`（`services/evidence_service.py:116-118`）。
- 跨项目读取/更新/添加证据在测试中拒绝（`PHASE5_ACCEPTANCE_REPORT.md:234-243`）。

结论：Phase 5 的单条操作不是只按 `finding_id` 或 `evidence_id` 操作，而是带 `project_id`；这是本阶段最重要的隔离约束之一。`confirmed`。

## 10. Phase 5 测试与真实运行

### 10.1 历史测试结果

来源：`docs/acceptance/PHASE5_TEST_REPORT.md:3-17,34-50` 和 `docs/acceptance/phase5_final/PHASE5_TEST_REPORT.md:62-122`。

| 运行 | collected | passed | failed | skipped | 耗时 |
|---|---:|---:|---:|---:|---:|
| 阶段验收 | 127 | 126 | 0 | 1 | 38.61 s |
| 最终收尾 | 127 | 126 | 0 | 1 | 36.25 s |

两次都是 127 collected / 126 passed / 0 failed / 1 skipped；耗时差异是不同运行，不是结果冲突。`confirmed`。

跳过项：

```text
tests/test_evidence_service.py::test_symlink_to_outside_is_rejected
当前 Windows 会话无法创建文件符号链接：
WinError 1314 客户端没有所需的特权
```

未把 skip 计为 passed，也未删除测试/降低断言。`confirmed`。

测试分布（`phase5_final/PHASE5_TEST_REPORT.md:98-122`）中，与第五阶段直接相关的新增：

- `test_vulnerability_service.py` 6；
- `test_evidence_service.py` 11（10 pass + 1 skip）；
- `test_phase5_migration.py` 2；
- `test_ui_phase5.py` 3；
- 既有回归 100（`test_database.py` 5 项有 v5 断言，仍通过）。

### 10.2 真实验收数据

阶段验收库：`storage/phase5_acceptance/acceptance.db`；最终备份：`storage/backups/phase5_acceptance_final_20261105T061441Z.db`。

只读查询结果：

```text
schema=5
projects=3
scan_tasks=4
findings=41
evidence=3
finding_status_history=2
scan_logs=59
foreign_key_violations=0
integrity_check=ok
```

按扫描器：

```text
bandit=3
pip-audit=38
```

按项目：

```text
project 1: 22（19 pip-audit + 3 Bandit）
project 2: 19（pip-audit）
project 3: 0
```

按状态：

```text
open=39
reviewing=1
confirmed=1
```

真实/迁移/夹具的准确区分：

| 数据 | 性质 | 说明 |
|---|---|---|
| project 1 的 3 条 Bandit | **真实本地扫描**（Phase 5 新增） | `task 4` completed；本阶段本地授权项目 |
| project 1 的 19 条 pip-audit | **历史迁移数据** | 来自 Phase 4 真实验收库；不是 Phase 5 重新跑 pip-audit |
| project 2 的 19 条 pip-audit | **历史迁移数据** | 同上 |
| `finding_status_history` 2 条 | **真实 Service 操作** | finding 19 open→reviewing；finding 41 open→confirmed |
| 3 条 Evidence | **真实本地证据记录** | 截图、依赖摘要、代码片段；不是扫描器自动生成 |
| Semgrep Finding | **测试夹具** | `test_vulnerability_service.py`/UI 测试插入；没有真实 Semgrep 运行 |
| 符号链接拒绝分支 | **单元模拟** | 当前 Windows 会话无法创建真实文件符号链接 |

### 10.3 真实证据文件

Evidence #1：

```text
title: 依赖漏洞验收截图
type: screenshot
file_path: storage/phase5_acceptance/evidence/project_1/1062362eb51642dead2aaeffbdd3bacb_phase5_evidence_screenshot.png
file_name: phase5_evidence_screenshot.png
sha256: d049b0c128fee9f2195887c65b3b1b7acb896f9252142a8561841c0e784e8d64
actual_sha256: d049b0c128fee9f2195887c65b3b1b7acb896f9252142a8561841c0e784e8d64
```

本次只读检查确认文件存在且实际哈希与 DB 记录一致。`confirmed`。

Evidence #2/#3 是文本证据，无文件路径/hash；分别关联 finding 19（依赖摘要）和 finding 41（Bandit 代码片段），不是额外的扫描结果。

### 10.4 真实验收结论

`PHASE5_ACCEPTANCE_REPORT.md:7`：**通过**，唯一环境限制是真实文件符号链接创建被 Windows 拒绝；目录联接越界为实际测试，`is_symlink` 分支为模拟测试。

## 11. Schema v3–v5 演进

### 11.1 版本与表/索引

本次只读查询 `storage/backups` 和验收库：

| Schema/证据 | 表数 | 索引数 | 关键变化 |
|---|---:|---:|---|
| v3 备份 `src_research_v3_20261105T024055Z.db` | 10 | 15 | scan_tasks/findings 的 v3 字段；3 个新索引 |
| v4 备份 `src_research_v4_20261105T034341Z.db` | 10 | 15 | findings 增加 metadata_json |
| v5 最终备份 `src_research_phase5_final_20261105T061441Z.db` | 11 | 18 | findings 重建；evidence 三字段；status history |
| phase3 验收库 | 10 | 15 | v3；实际 12 findings |
| phase4 验收库 | 10 | 15 | v4；实际 38 findings |
| phase5 验收库 | 11 | 18 | v5；实际 41 findings/3 evidence/2 history |

`sqlite_sequence` 未计入业务表；v3/v4 是 10 张业务/审计表，v5 是 11 张。

### 11.2 v3

`database/schema.py:166-193`：

- `scan_tasks`：`current_scanner`、`progress`、`error_message`、`scanners_json`、`cancel_requested`、`cancelled_at`；
- `findings`：`confidence`、`file_path`、`line_number`、`rule_id`、`scanner_name`、`scanner_version`、`detected_at`；
- 索引：`idx_findings_task`、`idx_findings_scanner`、`idx_scan_tasks_status`；
- 迁移方式：`PRAGMA table_info` 检查后逐列 `ALTER TABLE ... ADD COLUMN`，可安全重试；迁移前备份。

### 11.3 v4

`database/schema.py:195-201`：

- `findings.metadata_json TEXT NOT NULL DEFAULT '{}'`；
- 没有新增表；
- 保留 10 表 / 15 索引；
- 依赖漏洞 metadata 存在此字段，不新建重复结果表。

### 11.4 v5

`database/schema.py:203-293`：

- 重建 `findings`：
  - 状态 CHECK 增加 `reviewing`；
  - 新增 `manual_notes`；
  - 新增 `status_changed_at`；
  - 新增 `last_seen_at`；
  - 通过 `MIGRATION_V5_COPY` 按 `finding_id` 复制全部旧列，保留行；
  - `MIGRATION_V5_BACKFILL` 回填 `last_seen_at = COALESCE(detected_at, created_at)`。
- `evidence` 增加 `evidence_type/title/source`；
- 新增 `finding_status_history`（project_id/finding_id 外键、from/to、note、changed_by、changed_at）；
- 新索引：`idx_findings_project`、`idx_findings_task`、`idx_findings_scanner`、`idx_findings_status`、`idx_finding_status_history_finding`、`idx_evidence_finding`；
- 总表 11、索引 18。

### 11.5 迁移安全

`database/connection.py:92-216`：

- v1→v2→v3→v4→v5 顺序迁移；
- 每步迁移前 `_backup_before_migration(version)`，复制到 `storage/backups/`；
- v5 先 `PRAGMA wal_checkpoint(FULL)`，再备份；
- v5 使用 `PRAGMA foreign_keys=OFF` + `BEGIN IMMEDIATE`，重建/copy/backfill/history/evidence ALTER/index 全部在一个事务；
- 异常 `rollback`，最后恢复 `foreign_keys=ON`；
- 备份是第二恢复路径。

本次只读检查：v3/v4/v5 备份和验收库 `integrity_check=ok`、外键 0 违规；v3/v4 备份数据为 0 行（是迁移前空库快照，不是阶段验收数据）。`confirmed`。

## 12. Repository 架构演进

### 12.1 时间线

| 阶段 | 架构 | Repository |
|---|---|---|
| Phase 2（基线） | UI → Service → SQLite | 无 |
| Phase 3 | UI → Service → SQLite | **无** |
| Phase 4 | UI → Service → SQLite | **无** |
| Phase 5 | 漏洞/证据：UI → Service → Repository → SQLite；扫描/项目/授权等仍 Service → SQLite | **首次引入** |

证据：

- Phase 3 归档 `backups/src-research-assistant_phase3_final.zip` 中 `repositories/` 路径命中 0；
- Phase 4 归档 `backups/src-research-assistant_phase4_final.zip` 中 `repositories/` 路径命中 0；
- Phase 5 归档 `backups/src-research-assistant_phase5_final.zip` 含 `repositories/__init__.py`、`vulnerability_repository.py`、`evidence_repository.py`。
- 当前 `repositories/` 也只有这两个业务 Repository 文件。

### 12.2 当前哪些模块仍直接访问数据库

仍直接 `Database`/SQL：

- `ProjectService`
- `AuthorizationService`
- `ScopeAssetService`
- `ScanService`（Phase 3）
- `DependencyAuditService`（Phase 4）
- `AuditLogService`
- Phase 5 的 `VulnerabilityService`/`EvidenceService` 仍持有 `Database` 用于事务/审计，但主要业务读写走 Repository。

### 12.3 架构一致性判断

- **存在混合架构**：Phase 5 只把漏洞/证据领域抽到 Repository；没有进行全项目 Repository 重构。这是有意的低风险演进，不是遗漏。`inferred`（意图来自阶段文档“没有重构第三/第四阶段”）。
- **UI 边界一致**：Phase 3/4/5 代码质量检查均记录 `UI_SCANNER_IMPORTS=0`、`UI_SQL_STATEMENTS=0`；UI 不直接调扫描器或 SQL。
- **数据访问风格不完全一致**：部分 Service 直接 SQL，部分走 Repository。短期可接受；长期增加新领域时应避免继续复制两套模式。`inferred`。

## 13. 三个阶段的历史时间线

| 时间（UTC / Asia/Shanghai） | 事件 | 证据 |
|---|---|---|
| 2026-11-05 02:11:59Z / 10:11 | Phase 3 验收数据生成 | `phase3_acceptance.json:2` |
| 2026-11-05 02:53:48Z / 10:53 | Phase 4 验收数据生成 | `phase4_acceptance.json` `generated_at` |
| 2026-11-05 03:37:03Z / 11:37 | Phase 5 验收数据生成 | `phase5_acceptance.json` / DB rows |
| 2026-11-05 06:14:41Z / 14:14 | Phase 5 最终数据库备份 | `PHASE5_ACCEPTANCE.json:47,58` |
| 2026-11-05 14:16+08:00 | Phase 5 最终收尾 | `PHASE5_ACCEPTANCE.json:4` |
| 2026-11-06 | 本步骤 2 只读历史调查 | 本文 |

阶段开始/结束的精确开发起止时刻没有独立记录；只能从基线测试、验收生成时间和报告推断。`inferred`。

## 14. 测试与验收对照表

| 阶段 | collected | passed | failed | skipped | 耗时 | 真实工具 | 验收 DB |
|---|---:|---:|---:|---:|---:|---|---|
| Phase 3 | 81 | 81 | 0 | 0 | 16.74 s | Bandit 1.9.4 真实；Semgrep 1.183.0 不可运行 | 2 projects / 4 tasks / 12 findings |
| Phase 4 | 105 | 105 | 0 | 0 | 25.16 s | pip-audit 2.10.1 真实 | 3 projects / 3 tasks / 38 findings |
| Phase 5 | 127 | 126 | 0 | 1 | 38.61 s（验收）/36.25 s（收尾） | Bandit 真实 3；pip-audit 仅迁移 19；Semgrep 无 | 3 projects / 4 tasks / 41 findings / 3 evidence |

### 14.1 类型分解

| 类型 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|
| 单元测试 | 路径、Finding、process_runner、Semgrep 解析等 | pip-audit 解析、依赖服务、迁移 | 状态、证据、迁移、隔离 |
| 集成测试 | ScanService、Bandit、UI | DependencyAuditService、数据库 | Vulnerability/Evidence Service、Repository、DB |
| GUI 测试 | `test_ui_source_audit.py` 1 | `test_ui_dependency_audit.py` 1（模拟扫描器） | `test_ui_phase5.py` 3（临时 DB） |
| 工具真实运行 | Bandit 真实，Semgrep 无 | pip-audit 真实 | Bandit 真实；pip-audit 历史数据；Semgrep 无 |
| 数据库验收 | 12 findings（6 唯一问题重复） | 38 findings（19/项目） | 41 findings / 3 evidence / 2 history |
| 模拟数据 | Semgrep 解析夹具、缺失工具 | UI 扫描器模拟 | Semgrep fixture、符号链接分支 |
| 手工构造/操作 | 无扫描器伪造 | 无 CVSS 伪造 | 状态历史/文本证据为真实 Service 操作；截图真实验收文件 |

## 15. 安全限制和未解决问题

### 15.1 三阶段共同边界

- 仅本地已授权项目；路径经 `ScopeValidator.check_local_path`。
- 不实现远程扫描、网站扫描、漏洞利用、密码爆破、自动攻击。
- 子进程参数列表 + `shell=False`；超时/取消终止。
- 扫描结果按 `project_id/task_id` 隔离；Phase 5 单条操作强制 `project_id`。
- UI 不直接调用扫描器、不直接写 SQL。

### 15.2 未解决问题

1. **Semgrep 仍不可用**：1.183.0 已安装，但 Windows CA 存储 `CertOpenSystemStore` 失败；无 Linux/WSL 真实验证；Semgrep 规则未做运行时 validate。
2. **Phase 3 部分通过**：唯一原因是 Semgrep；不能把“已安装/版本可读”写成“已成功扫描”。
3. **Phase 4 漏洞元数据不完整**：pip-audit 无 CVSS/severity；应用保守 medium；无精确 affected range；需人工复核公告。
4. **Phase 4 网络依赖**：无离线漏洞库；网络失败不得当作“无漏洞”。
5. **pyproject 范围有限**：仅 PEP 621 `[project].dependencies`；不处理 Poetry、optional groups、build dependencies。
6. **Phase 5 符号链接真实创建未验证**：Windows 权限 `WinError 1314`；目录联接和路径越界实际测试，`is_symlink` 分支为模拟。
7. **无跨扫描逻辑去重**：Phase 3 的 12 行 = 6 条问题重复；Phase 4 的 38 行 = 两个项目各 19 条；Phase 5 的 41 行包含项目 1/2 相同漏洞 ID，以及 3 条 Bandit。
8. **Phase 5 列表上限 1000**；无分页。
9. **证据必须在项目根目录内**；项目外截图需先人工复制到项目内。
10. **running 任务异常恢复未实现**（Phase 3/4 文档记录）。
11. **Phase 5 scan_logs 差异**：阶段验收报告写 56，当前验收库实查 59；推断为后续收尾/回归操作增加了审计记录，不是 finding 数据差异。`inferred`。

除第 11 条外，本节其余限制均直接来自阶段报告/数据库/归档，标记为 `confirmed`；没有证据支持的限制不写成既成事实。

## 16. 历史证据索引

### 16.1 文档 / JSON

- `docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md`
- `docs/acceptance/PHASE3_TEST_REPORT.md`
- `docs/PHASE3_ARCHITECTURE.md`
- `docs/acceptance/phase3_acceptance.json`
- `docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md`
- `docs/acceptance/PHASE4_TEST_REPORT.md`
- `docs/PHASE4_ARCHITECTURE.md`
- `docs/acceptance/phase4_acceptance.json`
- `docs/acceptance/PHASE5_ACCEPTANCE_REPORT.md`
- `docs/acceptance/PHASE5_TEST_REPORT.md`
- `docs/acceptance/phase5_final/PHASE5_TEST_REPORT.md`
- `docs/acceptance/phase5_final/PHASE5_FINAL_SUMMARY.md`
- `docs/acceptance/phase5_final/PHASE5_ACCEPTANCE.json`

### 16.2 数据库

- `storage/backups/src_research_v3_20261105T024055Z.db` — v3，0 行，integrity ok
- `storage/backups/src_research_v4_20261105T034341Z.db` — v4，0 行，integrity ok
- `storage/backups/src_research_phase5_final_20261105T061441Z.db` — v5，0 行，integrity ok
- `storage/phase3_acceptance/acceptance.db` — v3，12 findings
- `storage/phase4_acceptance/acceptance.db` — v4，38 findings
- `storage/phase5_acceptance/acceptance.db` — v5，41 findings / 3 evidence / 2 history
- `storage/backups/phase5_acceptance_final_20261105T061441Z.db` — v5 最终备份 352256 bytes，SHA-256 `4f12065263f91c5402a1630b5f6c48912c6a059f0e2608936be6ffeb50184259`
- `storage/backups/src_research_phase5_final_20261105T061441Z.db` — v5 主库备份 147456 bytes，SHA-256 `a2423fa7a81f95889f2211e6823b132cb1a3ae7cfc776f93246fbd6902569a1e`

### 16.3 ZIP 归档（本次只读）

- `backups/src-research-assistant_phase3_final.zip` — 996834 bytes，120 files，SHA-256 `ebee6fe8dc6e964090261393c81c1d7f8e604bac955f591d0dd98f8f34cb4336`
- `backups/src-research-assistant_phase4_final.zip` — 1305451 bytes，139 files，SHA-256 `28617890ffc4ba99efbf91584d0a0e898bc410649cc08d3300ca9fe35399c963`
- `backups/src-research-assistant_phase5_final.zip` — 2313348 bytes，166 files，SHA-256 `e527cd7492c39d1ee042b2069c04d13eb015d3cfe79f0b00ee843e8a0ee557a7`

ZIP 列表检查：

- Phase 3/4 归档无 `repositories/`；
- Phase 4 归档含 `scanners/pip_audit_scanner.py`；
- Phase 5 归档含 `repositories/vulnerability_repository.py`、`repositories/evidence_repository.py`、`services/vulnerability_service.py`、`services/evidence_service.py`。

### 16.4 代码证据

- `database/schema.py:164-293` — v3/v4/v5 定义
- `database/connection.py:92-216` — 迁移/备份/v5 事务
- `core/models/finding.py:19-196` — Finding/状态历史
- `core/models/evidence.py:13-87` — Evidence
- `core/models/enums.py:158-235` — FindingStatus/EvidenceType
- `scanners/pip_audit_scanner.py:130-311` — pip-audit 命令/解析/metadata
- `scanners/process_runner.py:88-154` — `shell=False`/超时/取消
- `services/scan_service.py:294-409` — 任务 SQL/状态
- `services/dependency_audit_service.py:124-243,461-650` — 依赖发现/任务/保存
- `services/vulnerability_service.py:32-166` — 状态/备注/详情
- `services/evidence_service.py:21-303` — 证据路径/复制/哈希
- `repositories/vulnerability_repository.py:12-215` — 项目过滤/状态历史

**本次实际检查对象数量：34 个**（13 个文档/JSON + 12 个代码文件 + 6 个 SQLite 数据库 + 3 个 ZIP）。均只读打开；未执行测试套件。

## 17. unknown、contradicted 与证据限制

### 17.1 unknown

- Phase 3 的精确开发起止时刻：只有验收生成时间和测试耗时，没有独立时间线记录。
- Semgrep 是否在 Linux/WSL 或其他环境真实成功运行：当前历史材料没有成功记录；不能推断。
- Phase 5 `scan_logs` 从 56 增至 59 的具体每一条来源：`inferred` 为后续收尾操作，未逐条核对。
- Phase 5 证据文件源在复制前的完整操作链：只确认最终受管文件和哈希；源项目文件路径在验收数据中未完整保留。

### 17.2 contradicted / 需要纠正的说法

- 不能把“Semgrep 已安装、版本号可读”说成“Semgrep 已成功执行/已产生真实结果”。历史证据明确否定后两者。
- 不能把 Phase 3 的 12 条 findings 说成 12 个唯一漏洞；是 6 条问题在两个任务中的重复行。
- 不能把 Phase 4 的 38 条 findings 说成 38 个全局唯一漏洞；是两个项目各 19 条。
- 不能把 Phase 5 的 19 条 pip-audit 说成 Phase 5 新扫描结果；它们是 Phase 4 真实数据的迁移。
- 不能把 Phase 5 测试中的 Semgrep 行说成真实 Semgrep 扫描；它是测试夹具。
- 不能把 Phase 5 的符号链接测试 skip 说成真实通过；目录联接和路径越界是实际测试，`is_symlink` 分支是模拟。

### 17.3 证据限制

- 本文的测试数字均为**历史结果**，本次没有重新运行完整 pytest。
- 当前工作区代码相对历史版本可能已有 Phase 5 后续/Phase 6 改动；历史结论优先使用归档、验收 JSON、历史 DB 和阶段报告，当前代码只用于确认最终形态的字段/边界。
- Phase 3/4 归档 ZIP 是阶段快照，但本次只检查文件列表和哈希，没有逐文件 diff。
- 没有 Git 仓库，无法提供提交级 diff；历史以阶段报告、备份、ZIP 和数据库为准。

## 18. 最终结论

1. **Phase 3 是“部分通过”**：Bandit 真实运行、ScanTask/Finding/UI 和 v3 完成；Semgrep 已安装但当前 Windows 不能执行，未产生真实 Semgrep 结果，也没有 Linux/WSL 验证记录。81 passed。
2. **Phase 4 通过**：pip-audit 2.10.1 真实运行，requirements 与 PEP 621 pyproject 均审计 19 个唯一漏洞，safe 项目 0；38 条 Finding 均有 metadata；105 passed；无 CVSS 伪造，severity 为保守 medium + `severity_source`。
3. **Phase 5 通过（1 项环境限制）**：状态管理、历史、备注、证据受管复制/SHA-256/路径隔离和 UI 完成；126 passed / 1 skipped；41 findings（3 真实 Bandit + 38 迁移 pip-audit）、3 evidence、2 history；符号链接真实创建 skip，目录联接/路径越界实际测试。
4. **架构演进**：Phase 3/4 为 UI → Service → SQLite；Phase 5 首次为漏洞/证据引入 Repository，但扫描/项目/授权等仍直接 SQL，形成有意的混合架构；UI 始终不直接访问扫描器或 SQL。
5. **数据库演进**：v3 增加扫描字段；v4 增加 metadata_json；v5 重建 findings（reviewing/manual_notes/status_changed_at/last_seen_at）、扩展 evidence、新增 status history；迁移有备份、事务和回滚。
6. 本步骤未修改生产代码、测试、数据库、Schema、依赖、配置、历史验收报告或 Manifest；唯一新增文件是本文。
7. Phase 6 不在本次调查范围，未调查、未实施。

**步骤 2 状态：`completed`。**
