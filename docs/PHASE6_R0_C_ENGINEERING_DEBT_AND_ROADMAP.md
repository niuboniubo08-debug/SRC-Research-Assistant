# Phase 6-R0-C 全工程遗留问题总表与修复路线

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 调查时间：2026-11-13（Asia/Shanghai）
- 性质：只读综合审核与路线规划；未修改代码、测试、README、配置、数据库、Schema、Manifest 或旧归档
- 输入：R0-A、R0-B1、R0-B2、R0-B3 四份报告
- 本次唯一新增：`docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md`
- 当前分支：`main`
- 当前 HEAD：`bffb5ac82bbebe7fef5992f87ff90494c9776ace`
- 提交数：8
- Git 实际状态：staged 0；`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`；R0-C 报告生成前 6 个未跟踪报告，生成后 7 个
- 与 `origin/main`：**ahead 5 / behind 0**

## 0. 结论摘要

**总体交付判断：`NOT_READY`**

工程已经完成了大量真实功能：项目管理、授权与范围控制、Bandit 扫描、pip-audit 依赖审计、漏洞状态与证据中心、HTML 报告中心均有代码、测试和历史验收记录。数据库和备份本身目前没有发现损坏。

但当前仍有一个 **P0 级扫描结果真实性缺陷**：pip-audit 把带 `skip_reason` 的依赖计入“已审计”，全部依赖都跳过时仍可能显示“已审计、0 漏洞”。在安全研究工具里，这会把“没有审计”包装成“没有漏洞”，不能作为可靠交付结论。

此外还有 5 个 P1、7 个 P2、7 个 P3 工程问题；另有 3 项接受限制和 4 项暂缓功能。P0 未修复前，本报告不建议进入最终交付或把扫描结果用于正式授权结论。

**问题总数：20 个工程问题**

| 优先级 | 数量 | 含义 |
|---|---:|---|
| P0 | 1 | 可能产生错误安全结论，必须先修 |
| P1 | 5 | 核心可靠性或重要安全边界 |
| P2 | 7 | 质量、兼容性、测试或运行时边界 |
| P3 | 7 | 文档、归档、历史记录整理 |
| 合计 | 20 | 不含 3 项接受限制和 4 项暂缓功能 |

## 1. 项目当前真实状态

### 1.1 当前 Git 状态

实际只读结果：

```text
BRANCH=main
HEAD=bffb5ac82bbebe7fef5992f87ff90494c9776ace
COMMIT_COUNT=8
STAGED=0
UNSTAGED=M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
AHEAD=5
BEHIND=0
```

`git rev-list --left-right --count HEAD...origin/main` 返回 `5 0`；`origin/main...HEAD` 返回 `0 5`。R0-B3 中的 `AHEAD_BEHIND=0 5` 来自后者，表示 **ahead 5 / behind 0**，不是“behind 5”的矛盾。当前 `git status --short` 显示 6 个既有未跟踪报告；本报告生成后为 7 个：

- D1B-1、D1B-3、R0-A、R0-B1、R0-B2、R0-B3；
- 新增 R0-C 报告。

R0-A/R0-B1/R0-B2/R0-B3 记录的 HEAD 均为 `bffb5ac...`；本次未发现 HEAD 漂移。R0-B3 记录的未跟踪数量从 5 增至 6，是 B3 报告自身新增，不是外部删除或重组。

**分类**：`CURRENTLY_CONFIRMED`。

### 1.2 数据库与 Schema

- 主库 `storage/src_research.db`：147,456 bytes，SHA `ed315656...`，v5，integrity ok，FK 0，11 张业务表/18 个显式索引。
- 主库业务数据为空：0 projects、0 findings、0 evidence、0 reports，仅 6 条项目生命周期 `scan_logs`。
- Phase 5 验收库 `storage/phase5_acceptance/acceptance.db`：352,256 bytes，SHA `03de4950...`，v5，integrity ok，FK 0，41 findings、3 evidence、2 状态历史、59 logs、0 reports。
- 共检查 20 个 `.db`：全部可只读打开，integrity ok、FK 0；含 v2/v3/v4 历史库与 4 个 4 KB 空备份。空文件不能当作可用恢复副本。
- 没有 schema v6；`reports` 仍是 6 列旧结构，`reports=0`；没有报告历史表；PDF/JSON 没有创建表或迁移。
- 主库 SHA 从 Phase 6B 的 `f03cfb81...` 变为 `ed315656...`；高可信原因是 2026-11-09 的测试项目创建/删除留下 6 条 `scan_logs`，不是损坏或 schema 变化。操作者身份 `UNKNOWN`。

### 1.3 已完成能力

| 阶段 | 状态 | 关键能力与证据 |
|---|---|---|
| Phase 1 | 已完成，但历史资料不完整 | 基础框架、10 页 PySide6 外壳、v1 7 表；无独立 Phase 1 源码/数据库/测试快照，Phase 1 由 Phase 2 交付过程补齐并合并验收 |
| Phase 2 | 已完成 | 项目 CRUD、授权状态/历史/到期、ScopeAsset、fail-closed `ScopeValidator`、v2 10 表；历史 40 tests / 31/31 business |
| Phase 3 | 部分通过 | 本地源代码审计、Bandit 1.9.4 真实运行、统一 Finding、v3；Semgrep 已集成但当前 Windows 启动失败，不能伪造 |
| Phase 4 | 已完成，有限制 | pip-audit 2.10.1、requirements/pyproject、JSON 解析、Finding 映射、v4 `metadata_json`；severity 采用保守默认值，无 CVSS/精确 affected range |
| Phase 5 | 已完成 | 漏洞状态/历史/备注、Evidence 中心、v5 11 表/18 索引；历史 41 findings/3 evidence；symlink 动态测试受 Windows 权限限制 |
| Phase 6 | HTML 部分完成 | Report DTO/Repository/Service、HTML exporter/templates、GUI 报告中心、快照新鲜度修复；PDF 取消；JSON 未批准/延期；报告历史和 Evidence 图片嵌入未批准 |

**Phase 6F/6G**：没有独立实施或验收材料，标记 `MISSING/UNKNOWN`；本路线不启动它们。

### 1.4 当前测试状态

- 结构：23 个 `test_*.py`，189 个 `test_` 函数；参数化后历史收集为 210。
- 历史结果：Phase 5 `127/126/1`；Phase 6B `145/144/1`；C2B/P2B `210/203/7`。
- 当前完整 pytest **未运行**，因此当前 pass/fail/skip 为 `UNKNOWN`，不能把历史 203/7 写成当前结果。
- 历史 skip 均为 Windows 文件 symlink `WinError 1314`；本次没有用 skip 掩盖失败。

## 2. 统一问题清单

### 2.1 去重说明

- R0-B1 的 Evidence 根目录问题与 R0-B2 的 B2-02 合并为 `RC-02`。
- R0-B1 的父级 reparse 与 R0-B2 的 B2-07 合并为 `RC-03`。
- R0-B2 的 B2-01 与 R0-B3 的 B3-11 合并为 `RC-01`。
- R0-B1 的 CountView、CSP、清理失败、公共写入 API 合并为 `RC-11` 的四个子项，避免拆成重复条目。
- R0-A/B3 的 README、测试数字、Phase 6B acceptance 计数、Phase 5 Manifest 分别归入 `RC-14` 至 `RC-17`。
- R0-B3 的“Manifest 中文路径乱码”和“`requirements.txt` 注释乱码”经 Unicode/hex 复核为 PowerShell 控制台显示造成的**假阳性**，不登记为工程问题；见第 5.4 节。

### 2.2 总表

| ID | 类型 | 问题、证据与位置 | 当前状态 | 影响与修复必要性 | 验证方式 | 优先级理由 |
|---|---|---|---|---|---|---|
| **RC-01** | 扫描真实性 / 代码缺陷 | `scanners/pip_audit_scanner.py:311` 用 `len(dependencies)` 作为 `audited`，把带 `skip_reason` 的依赖计入；`services/dependency_audit_service.py:325-338` 只判断 `audited != 0`；`tests/test_pip_audit_scanner.py:53-78` 固定了 `skipped-package` 仍 `audited == 3` 的旧行为。全部依赖跳过时，任务可显示 COMPLETED/0 漏洞。 | `CURRENTLY_CONFIRMED`（静态代码 + 测试断言） | **错误安全结论**：用户会把“未完成审计”当成“没有漏洞”。必须优先修复。 | 构造全部 `skip_reason`、部分跳过、正常三组 pip-audit JSON，断言 `audited`、跳过数、任务状态、UI 结果和错误/警告；真实离线网络失败也要验证。 | **P0**：这是唯一直接制造“无漏洞”假保证的问题，其他问题都不能抵消它。 |
| **RC-02** | 安全边界 / 代码缺陷 | `services/evidence_service.py:253-269` 对 `evidence_root/project_<id>` 没有拒绝 root/project 目录本身是 symlink/junction；`report_service.py:129` 对 `project_<id>` 直接 `resolve()` 后使用；B1-01/B2-02 均记录。 | `CURRENTLY_CONFIRMED`（静态）；动态 junction 部分历史 PASS，symlink 动态 `UNKNOWN`（`WinError 1314`）。 | 条件性把受管 Evidence/报告读取写到证据根之外；需要管理员/同机攻击者先放置 junction。不是已证实的远程越权，但属于重要文件边界。 | 创建 root junction、project junction、外部目标、普通目录四组；断言拒绝/不写出根；symlink 不可创建时必须 skip 并记录，不得伪造 PASS。 | **P1**：安全边界，但需要本地前置条件；低于 P0 的直接假结论。 |
| **RC-03** | 安全边界 / 代码缺陷 | `reports/html_exporter.py:645-658` 只检查 `reports_dir` 自身，不逐级检查父目录 reparse；B1-02/B2-07。`write_html_report` 的叶子检查已存在，但父级仍可被 junction 重定向。 | `CURRENTLY_CONFIRMED`（静态）；父级 junction 运行时 `UNKNOWN`。 | 报告可能被写到非预期目录，泄露项目内容或覆盖文件。 | 在父目录创建 junction/symlink，验证拒绝并保留旧文件；检查 root、父级、叶子三层。 | **P1**：与 RC-02 同类路径边界，影响报告文件。 |
| **RC-04** | 扫描漏报 / 代码缺陷 | `scanners/bandit_scanner.py` 的 `-x` 固定排除 `.venv,.git,__pycache__,venv,env,node_modules,build,dist`；子串 `env` 会排除合法项目路径组件。B2-03。 | `CURRENTLY_CONFIRMED`（静态）；真实回归 `UNKNOWN`。 | 合法源码目录被静默跳过，可能产生假阴性。 | 构造路径含 `env` 的临时项目，运行真实 Bandit，断言目标文件被扫描；修复排除规则为精确目录名/路径边界。 | **P1**：直接造成扫描漏报。 |
| **RC-05** | 授权边界 / 代码缺陷 | `security/scope_rules.py:77-85` `normalize_local_path()` 先 `Path.resolve()`，再与精确资产匹配；`security/scope_validator.py` 使用规范化结果。B2-06。 | `CURRENTLY_CONFIRMED`（静态）；junction/alias 运行时 `UNKNOWN`。 | 可能把“解析后的别名路径”当成授权资产，绕过“精确路径”语义；也可能误拒绝合法资产。 | 用 symlink/junction、大小写差异、`..`、尾随分隔符测试授权匹配和拒绝；确认是否应在解析前保留原始路径做比较。 | **P1**：授权精确匹配是核心安全边界。 |
| **RC-06** | 验证缺口 / 发布门禁 | 四份 R0 报告均未运行当前完整 pytest、GUI 工作流或真实扫描；R0-B3 明确当前测试 `UNKNOWN`。 | `UNKNOWN`（按任务约束未运行） | 不能确认当前代码在本次修改后仍可交付；这不是代码缺陷，但会阻止最终验收。 | 专用临时目录 + full-access 运行完整 pytest；执行真实 Bandit/pip-audit；执行报告中心创建/预览/导出/覆盖确认；记录原始退出码和 skip。 | **P1**：没有当前运行证据就不能给 READY。 |
| **RC-07** | 并发 / 安全边界 | `reports/html_exporter.py:675-698` 的 `overwrite=False` 先检查 `target.exists()`，再 `os.link`；检查与发布之间存在 TOCTOU；`overwrite=True` 使用 `os.replace`。B1-03。 | `CURRENTLY_CONFIRMED`（静态）；双进程竞争 `UNKNOWN`（测试为模拟，不是真实双写）。 | 并发写者可能覆盖目标或产生竞态失败；不导致 root escape，但威胁“默认不覆盖”保证。 | 两进程真实竞争；验证 `FileExistsError`、旧文件不被替换、临时文件清理；必要时改成原子独占创建/锁。 | **P2**：需要并发前置条件，影响可控。 |
| **RC-08** | 进程管理 / 代码缺陷 | `scanners/process_runner.py` 只终止直接子进程；未创建进程组/JobObject；扫描器若再启动子进程，取消/超时可能残留。B2-05。 | `CURRENTLY_CONFIRMED`（静态）；真实子进程树 `UNKNOWN`。 | 取消/超时后残留扫描进程，可能继续占用资源或访问目标。 | 构造启动子进程的假扫描器，取消/超时后枚举进程树；Windows 断言无残留。 | **P2**：需要特定扫描器行为，非默认路径。 |
| **RC-09** | 业务规则 / 质量 | Finding 状态枚举完整，但没有允许的状态转移矩阵；任意目标状态可从任意旧状态设置（B2 §4.2）。 | `CURRENTLY_CONFIRMED`（静态）；业务期望 `UNKNOWN`。 | 可能把 confirmed 直接改回 open 或产生不合理的审计历史；不影响项目隔离。 | 明确状态机（open/reviewing/confirmed/false_positive/fixed/accepted_risk），测试非法转移；UI 仅展示允许项。 | **P2**：产品规则/数据质量，不是越权。 |
| **RC-10** | 项目隔离 / 设计边界 | `VulnerabilityService`/`EvidenceService` 的全局列表允许读所有项目；写操作依赖调用方传入 `project_id`，没有多用户/当前用户上下文。B2-08。 | `CURRENTLY_CONFIRMED`（设计事实）；越权 `UNKNOWN`（无多用户模型）。 | 单用户桌面工具中风险较低；若未来多用户/远程，可能跨项目写入。 | 增加“当前项目”写操作校验/服务端上下文；UI 测试伪造 project_id 时拒绝或限制。 | **P2**：当前单用户场景可接受，但接口设计应明确。 |
| **RC-11** | 输出加固 / 质量 | 四项合并：`CountView` 未知标签不统一限长（B1-05）；`_atomic_write` 清理失败静默（B1-06）；无 CSP（B1-04）；公共 `write_html_report` 接受任意 `reports_dir`（B1-07）。位置：`reports/html_exporter.py:534-546`、`:701-736`、`:645-658`、`:327-389`。 | `CURRENTLY_CONFIRMED`（静态）；浏览器/资源消耗 `REQUIRES_RUNTIME_TEST`。 | 影响资源消耗、运维可观测性和纵深防御；不直接造成 XSS（autoescape 存在）或 root escape。 | 增加长度上限/CSP header、清理失败日志/返回、在 API 层限制输出根；测试长标签、清理失败、响应头。 | **P2**：低/中风险加固，不应抢占 P0/P1。 |
| **RC-12** | 备份恢复 / 验证 | E 盘备份 `247 files / 12,952,436 bytes`，Manifest 计数匹配；主库副本 `mode=ro&immutable=1` integrity ok；普通 `mode=ro` 打开失败。当前 `Get-Partition` 被拒，物理独立性只能引用历史。 | `PASS_WITH_LIMITATIONS`（备份可读/完整性）；普通只读打开 `UNKNOWN`；物理独立 `HISTORICAL_ONLY`。 | 备份存在不等于可恢复；没有本轮完整恢复演练。 | 用独立媒体复制；隔离恢复主库/验收库；用普通 SQLite 客户端验证；记录 SHA/大小/Schema/FK。 | **P2**：数据保护缺口；不是当前代码功能缺陷。 |
| **RC-13** | 测试缺口 | 无全部 skip 的 pip-audit 用例；无 Evidence root/project junction；无 Bandit `env` 回归；无 Semgrep 当前 Windows 运行；无进程树取消；无 Manifest/文档一致性测试。B2 §7、B3 §3.3。 | `CURRENTLY_CONFIRMED`（测试代码静态） | 上述 P0/P1 问题缺少回归网；修复后容易复发。 | 每个缺口补一个最小测试；Windows 权限失败必须 skip，不得改断言。 | **P2**：测试覆盖问题，和具体缺陷分开登记，避免把“没有测试”当成“代码已坏”。 |
| **RC-14** | 文档 | `README.md:5` 仍说“不包含...报告生成能力”，与 `README.md:3/18/43/162` 的 HTML 已实现冲突。 | `CURRENTLY_CONFIRMED` | 用户会误判报告能力；不影响运行。 | 只改 README 文案，扫描“报告生成/HTML/PDF/JSON”关键词；人工复核。 | **P3**：文档错误，低风险。 |
| **RC-15** | 文档 | `README.md:34` 与 `:216` 仍写 `126 passed / 1 skipped`；这是 Phase 5 数字，历史 Phase 6 为 203 passed / 7 skipped。 | `CURRENTLY_CONFIRMED`（过期文本）；当前数字 `UNKNOWN`。 | 用户误判测试状态。 | 运行当前 pytest 后更新；若未运行，明确标为“历史值”。 | **P3**：需要真实运行，不能凭空改数字。 |
| **RC-16** | 归档 | `PHASE6_B_ACCEPTANCE.json` 的 `archive.file_count=9`、`manifest_entries=11`、`manifest_covers_seal_documents=false`；当前实际 10 文件/14 Manifest 条目，Manifest 覆盖 seal 文档；`PHASE6_B_FINAL_SUMMARY.md` 也保留 9 files。 | `CURRENTLY_CONFIRMED`（当前文件 vs 内部记录）；历史时点 `HISTORICAL_ONLY`。 | 归档元数据不可信；不影响代码/数据库。 | 只追加 reconciliation 说明或更新当前 acceptance 元数据；不得重写历史 Manifest 条目。 | **P3**：归档整理。 |
| **RC-17** | Manifest | Phase 5 Manifest 253 条 / 200 唯一 / 53 重复；190 匹配、9 mismatch、1 missing（`storage/_rebuild_manifest.py`）。mismatch 包含 README、bootstrap、report_page、main_window、settings、`.gitignore`、reports init、main DB、code_quality。 | `CURRENTLY_CONFIRMED`（当前文件计数）；历史时点 `HISTORICAL_ONLY`。 | 不能把 Phase 5 Manifest 当作当前工作区精确快照；不能据此回滚。 | 以只读方式重新生成当前清单/差异报告；旧 Manifest 保留；修复 `_rebuild_manifest` 缺失需重新确认来源，不能伪造。 | **P3**：历史归档债务，不影响运行。 |
| **RC-18** | 历史资料 | Phase 1 没有独立源码/数据库/测试快照；只有 Phase 1–2 合并验收与重建说明。 | `HISTORICAL_ONLY`；无法补造。 | 影响历史可追溯性，不影响当前功能。 | 保留重建标记；最终验收清单明确“Phase 1 独立快照 MISSING”；不得新建伪历史。 | **P3**：历史事实，不是当前代码缺陷。 |
| **RC-19** | 归档计数 | `PHASE6_B_FINAL_SUMMARY.md` / seal 文档写 phase5_final 10 files；实际 16 文件（10 普通 + 2 db + 2 shm + 2 wal，含 Manifest）。 | `CURRENTLY_CONFIRMED`（计数口径冲突）；是否为错误取决于“core archive”定义 `UNKNOWN`。 | 读者会误判归档规模。 | 定义“core archive”与“all files”两种口径并写清楚；不修改旧文件内容。 | **P3**：文档/归档口径。 |
| **RC-20** | 数据溯源 | 主库 SHA `ed315656...` 与 Phase 6B `f03cfb81...` 不同；6 条 `scan_logs` 和两份 HTML 报告形成时间线；未发现 schema/完整性异常。 | `CURRENTLY_CONFIRMED`（当前状态）；原因 `HISTORICAL_ONLY`/高可信推断；操作者 `UNKNOWN`。 | 历史哈希记录不能直接复用；没有业务数据损坏。 | 保留当前哈希与 6 条日志；不恢复 f03；后续备份记录新哈希。 | **P3**：已解释的漂移，登记避免误判为损坏。 |

### 2.3 已接受限制

| ID | 限制 | 证据 | 处理决定 |
|---|---|---|---|
| **RC-AL-01** | Semgrep 在当前 Windows 会话不可用：`CertOpenSystemStore returned NULL`；没有真实 Semgrep 运行结果 | Phase 3 报告、R0-A、B2 §2.2 | 接受为环境限制；UI 继续显示不可用；不伪造 PASS；需要 Linux/WSL 实机验证后才能改状态 |
| **RC-AL-02** | E 盘本地备份与源项目在**同一物理 SSD**，不是物理独立备份；当前硬件查询被拒，只有历史 Manifest 说明 | `BACKUP_MANIFEST.json`；Git-2A/Git-2B | 接受为当前限制；最终交付前必须另建独立媒体备份，不能把 E 盘称作物理独立保障 |
| **RC-AL-03** | pip-audit 漏洞严重度使用 conservative-default = medium；没有 CVSS 和精确 affected-version range | Phase 4 报告、B2 §2.3 | 接受为产品限制；报告中保留 `severity_source`，不得伪造 CVSS |

### 2.4 取消与暂缓功能

以下项目**不进入本轮修复计划**，也不得被顺手实现：

| 功能 | 决策 | 依据 |
|---|---|---|
| PDF 报告 | **CANCELLED / OUT_OF_SCOPE** | Phase 6P；无 exporter/依赖/UI；`ReportFormat.PDF` 仅兼容元数据 |
| JSON 报告 | **DEFERRED** | D1B-1 证据不足；D1B-3 `JSON_REPORT_STATUS=DEFERRED`；`JSON_DEVELOPMENT_APPROVED=NO` |
| JSON Contract | **NOT_APPROVED** | 同上；没有消费者/字段契约 |
| 报告历史 | **NOT_APPROVED / 未实现** | `reports` 表 0 行，无历史表；不由路线默认扩展 |
| Evidence 图片嵌入 | **NOT_APPROVED** | 当前不嵌入；无新增需求 |

**重要**：这五项不是“待修 bug”，不能为了清理债务表而把它们变成新功能。

## 3. 优先级与理由

### P0 — 1 项

**RC-01** 是唯一 P0。它不是“测试没覆盖”或“文档过期”，而是会把未审计依赖转换成“无漏洞”的扫描结果。对安全研究工具来说，错误的阴性结论比崩溃更危险；崩溃会阻止用户，假成功会误导用户。必须先修。

### P1 — 5 项

- **RC-02/RC-03**：文件系统 reparse/junction 边界，条件性越界写入/读取。
- **RC-04**：Bandit 合法项目静默漏扫，直接产生假阴性。
- **RC-05**：授权精确路径匹配在 resolve 后执行，影响“精确授权”语义。
- **RC-06**：当前没有完整运行证据；没有它无法证明修复没引入回归。

这些是“核心可靠性或重要安全边界”，但需要本地前置条件或缺少当前运行证据，未达到 P0 的直接假保证。

### P2 — 7 项

- **RC-07** 并发 TOCTOU：需要并发写者，影响默认不覆盖保证。
- **RC-08** 子进程树：需要扫描器再启动子进程。
- **RC-09** 状态转移：产品规则/数据质量。
- **RC-10** 全局列表/项目 ID：单用户桌面场景可接受，接口设计应明确。
- **RC-11** CountView/CSP/清理/公共 API：纵深防御与运维卫生。
- **RC-12** 备份恢复：数据保护验证，不是当前代码功能。
- **RC-13** 测试缺口：修复 P0/P1 后必须补网。

这些重要但不直接制造错误安全结论，不能与 P0 并列。

### P3 — 7 项

- **RC-14/RC-15**：README 文案与测试数字。
- **RC-16/RC-17/RC-19**：Phase 6B acceptance、Phase 5 Manifest、归档计数。
- **RC-18**：Phase 1 独立历史资料缺失。
- **RC-20**：主库哈希漂移的已解释记录。

这些是文档/历史/归档债务，除非最终交付要求“零差异”，否则不应阻塞 P0/P1 修复；但必须在最终验收前处理或明确接受。

## 4. 尚需运行验证的事项

以下均为 `REQUIRES_RUNTIME_TEST` 或 `UNKNOWN`，不能由静态阅读替代：

1. 完整 pytest 当前收集数、passed/failed/skipped、退出码、耗时。
2. 全部 `skip_reason` / 部分跳过 / 正常 pip-audit 的 `audited`、任务状态、页面展示。
3. 真实 Bandit 对含 `env` 路径组件的目标扫描。
4. Semgrep 当前 Windows 可用性；若仍失败，保持不可用状态，不伪造。
5. Evidence 根目录、`project_<id>`、报告父目录的 junction/symlink 动态测试；Windows symlink 权限失败必须 skip。
6. 取消/超时后进程树是否残留。
7. 报告中心真实 GUI 工作流：项目切换、类型切换、预览、导出、默认不覆盖、覆盖确认、失败恢复。
8. E 盘备份普通 SQLite 打开与隔离恢复；当前仅 `immutable=1` 只读成功。
9. 当前 README/Manifest 与真实文件的一致性扫描。
10. 当前数据库在修复前后的完整性、FK 与哈希记录。

## 5. 修复路线

路线按“先真结论、再路径、再扫描可靠性、再回归、再文档、最后备份”排序；每个阶段都必须由人工批准后执行。

### Stage 0：保护基线（只读/准备）

- **目标**：在不改变现有工作区的前提下建立可回退基线。
- **包含问题**：无（准备阶段）。
- **前置条件**：人工确认本路线；保护 `docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 和全部未跟踪报告。
- **允许修改**：无；只读检查；可新增独立备份（使用 SQLite Backup API，不覆盖原库）。
- **必须测试**：主库/验收库 integrity_check、foreign_key_check、user_version、表/行数；E 备份可读性。
- **验收标准**：备份副本可独立打开，schema/表数/FK 与源一致；源库哈希记录；Git 状态记录。
- **回滚/数据保护**：不覆盖、不删除、不恢复 f03；不执行迁移；不修改 Git。

### Stage 1：修复 P0 扫描真实性（RC-01）

- **目标**：让“跳过/未解析依赖”不再被算作已审计；全部跳过必须明确失败或“不完整”，不得显示 0 漏洞成功。
- **包含问题**：RC-01（并为 RC-13 增加回归测试）。
- **前置条件**：Stage 0 基线；确认 pip-audit 输出字段（`skip_reason`）和现有状态模型。
- **允许修改**：`scanners/pip_audit_scanner.py`、`services/dependency_audit_service.py`、`tests/test_pip_audit_scanner.py`、`tests/test_dependency_audit_service.py`，必要时 `ui/dependency_page.py` 的提示文案；不改 Schema/数据库。
- **必须测试**：全部 skip、部分 skip、正常 0 漏洞、正常有漏洞、pip-audit 网络/索引失败、任务 FAILED/COMPLETED 语义、项目隔离。
- **验收标准**：全部 skip 时不得 COMPLETED(0 漏洞)；`audited` 与实际完成数一致；UI 显示“未完成/跳过”而非“安全”；新增测试在旧代码上失败、新代码通过；无跨项目写入。
- **回滚/数据保护**：修复前备份主库/验收库；代码可 revert；不得改写历史 Finding；不迁移 Schema。

### Stage 2：修复 P1 路径与授权边界（RC-02、RC-03、RC-05）

- **目标**：拒绝 root/project/父级 reparse；保持普通文件与普通目录原有语义；明确 ScopeValidator 的“原始路径 vs 解析路径”规则。
- **包含问题**：RC-02、RC-03、RC-05（可拆两个小提交，但同一阶段验收）。
- **前置条件**：Stage 1 完成；在 Windows 上能创建 junction 的测试环境；symlink 无权限时按既有 skip 处理。
- **允许修改**：`services/evidence_service.py`、`services/report_service.py`、`reports/html_exporter.py`、`security/scope_rules.py`/`security/scope_validator.py`、对应测试；不改 Schema/模板/UI 结构。
- **必须测试**：Evidence root junction、project junction、外部目标；报告 root/父级/叶子；普通目录/文件；Symlink 权限失败 skip；ScopeValidator 合法/别名/越界。
- **验收标准**：受管文件不写出证据根/报告根；普通路径行为不回归；动态 junction 测试有 PASS，symlink 不能测试时明确 skip；旧测试不减弱。
- **回滚/数据保护**：不删除已有 Evidence/HTML；失败时保留旧文件；备份 DB；不恢复历史目录。

### Stage 3：修复 P1 扫描可靠性 + P2 运行边界（RC-04、RC-08、RC-09、RC-10）

- **目标**：消除 Bandit `env` 漏扫；确保取消/超时终止进程树；明确 Finding 状态转移；明确项目 ID 写接口。
- **包含问题**：RC-04、RC-08、RC-09、RC-10。
- **前置条件**：Stage 2 完成；测试可启动假扫描器；Windows 进程树 API 可用。
- **允许修改**：`scanners/bandit_scanner.py`、`scanners/process_runner.py`、`services/vulnerability_service.py`、`ui/vulnerability_page.py`、相关服务/测试；不改 Schema。
- **必须测试**：含 `env` 路径真实 Bandit；取消/超时后无子进程；非法状态转移；伪造 project_id 写入；现有扫描状态/项目隔离。
- **验收标准**：合法文件被扫描；取消/超时无残留；非法状态/跨项目写入被拒绝；历史结果不回退。
- **回滚/数据保护**：扫描前备份 DB；不删除历史 Finding；只用临时测试库做破坏性状态测试。

### Stage 4：完整回归与 GUI 工作流（RC-06、RC-13）

- **目标**：证明修复后的当前代码可运行，而不是引用历史数字。
- **包含问题**：RC-06、RC-13（以及 Stage 1–3 的回归）。
- **前置条件**：Stage 1–3 完成；专用临时目录（避开 `env` 路径组件）；full-access 测试进程。
- **允许修改**：只允许修复测试暴露的代码；不允许降低断言/跳过关键测试。
- **必须测试**：完整 pytest；真实 Bandit/pip-audit；报告创建/预览/导出/默认不覆盖/确认覆盖；漏洞状态/证据；Semgrep 探针（不可用则记录）。
- **验收标准**：当前完整测试有明确退出码；除 Windows symlink 权限 skip 外无失败；GUI 工作流实际通过；错误不被吞掉。
- **回滚/数据保护**：测试用临时 DB；不污染主库/验收库；若需 UI 真实数据，使用副本。

### Stage 5：文档、Manifest 与归档（RC-14–RC-19；RC-20 只记录）

- **目标**：当前产品文案与真实能力一致；历史归档差异有解释，不伪造历史。
- **包含问题**：RC-14、RC-15、RC-16、RC-17、RC-18、RC-19；RC-20 只更新记录。
- **前置条件**：Stage 4 完成；确定当前测试数字；人工确认“core archive”口径。
- **允许修改**：`README.md`、当前 acceptance/decision 文档的**追加说明**；不修改 Phase 5 Manifest 的历史内容，不伪造 `_rebuild_manifest.py`。
- **必须测试**：文档关键词/链接/数字一致性检查；Manifest 只读重算；归档文件存在/大小/SHA。
- **验收标准**：README 不再说“无报告生成”；测试数字是当前非历史；Phase 6B acceptance 与当前 10/14 一致或有“历史时点”标注；Phase 5 差异明确记录。
- **回滚/数据保护**：旧文档只追加不改写；保留原 Manifest；备份后再编辑当前文档。

### Stage 6：最终备份、恢复与交付封存（RC-12、RC-AL-02）

- **目标**：最终代码/数据库/归档可恢复，而不是只有文件副本。
- **包含问题**：RC-12；RC-AL-02 记录为限制。
- **前置条件**：Stage 1–5 完成；所有 P0/P1 关闭或有批准记录；独立备份媒体可用。
- **允许修改**：新增备份/验收报告；不改业务代码；不改历史归档。
- **必须测试**：SQLite Backup API 备份主库/验收库；完整性/FK/Schema；隔离恢复；普通 SQLite 客户端打开；独立媒体副本；哈希清单。
- **验收标准**：`RESTORE_VALIDATION=PASS`；备份不在同一物理盘（或明确标注非独立）；主库/验收库可恢复；归档哈希清单匹配。
- **回滚/数据保护**：绝不覆盖 live DB；恢复只写临时副本；不删除旧备份；不重建历史 Manifest。

## 6. 每阶段验收标准汇总

| 阶段 | 必须通过的门禁 | 不通过时的处理 |
|---|---|---|
| 0 基线 | 源库完整性、备份可读、Git 状态记录 | 停止，不开始代码修改 |
| 1 P0 | 全部 skip 不再假成功；目标测试红→绿 | 回滚代码，不进入路径修复 |
| 2 路径 | 受管写入不越界；普通语义不回归 | 保留旧版本，不降低测试 |
| 3 扫描/进程 | 无 Bandit `env` 漏扫；无子进程残留；非法状态/项目写入拒绝 | 回退单点，不合并 |
| 4 回归 | 当前完整 pytest + GUI + 真实扫描 | 不以历史结果替代 |
| 5 文档/归档 | 当前文案一致；历史差异有记录；不伪造 | 只追加说明，不改历史 |
| 6 备份/封存 | 独立备份 + 隔离恢复 + 哈希 | 不宣布交付 |

## 7. 数据库、Git、备份和归档保护方案

### 7.1 数据库

- 任何修复前先使用 SQLite Backup API 生成主库/验收库副本；不使用直接文件复制作为唯一备份。
- 记录源/副本的 size、SHA-256、`user_version`、`integrity_check`、`foreign_key_check`、表数/关键行数。
- 不恢复 `f03cfb81...` 覆盖当前 `ed315656...`；不迁移 Schema；不删除 6 条 `scan_logs`。
- 测试使用临时副本，不写主库/验收库。
- 修复涉及状态/证据时，先在副本上验证，再对 live 数据执行。

### 7.2 Git

- 保持 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 与既有未跟踪报告不被恢复、删除、暂存或提交，除非人工明确批准。
- 不使用 `git add .`/`git add -A`；每阶段只显式暂存已审文件。
- 禁止 `reset --hard`、`restore`、`clean`、覆盖未跟踪报告。
- 每阶段单独 commit，保留可回滚点；不 push，不配置新 remote，除非人工批准。
- 当前 HEAD/分支/ahead/behind 在阶段开始与结束各记录一次。

### 7.3 备份与恢复

- E 盘备份保留；不覆盖、不删除。
- 最终验收前另建**非同一物理盘**的独立副本；E 盘不能被称为物理独立。
- 恢复验证只在隔离目录进行；不覆盖 live 主库。
- 使用普通 SQLite 客户端和 `immutable=1` 两种方式分别测试；记录普通只读失败原因。
- 备份清单记录正常文件、数据库、排除项、失败项和 SHA；不以“文件存在”代替可恢复。

### 7.4 Manifest 与归档

- 已封存的 Phase 5/6B 文件只读；不修改历史 Manifest 条目，不重建 `_rebuild_manifest.py`。
- 当前不一致通过新增 reconciliation 说明或新 acceptance 文档记录；不伪造历史时点。
- Phase 5 Manifest 的 53 条重复、9 mismatch、1 missing 保留为历史事实；Phase 6B 的 10 文件/14 条目作为当前事实。
- 归档更新只追加，不删除旧文件；备份旧清单后再改当前文档。

## 8. 最终交付前验收清单

必须全部满足，缺一不可：

1. RC-01 修复；全部 skip / 部分 skip / 正常三组测试通过；UI 不再显示假成功。
2. RC-02/RC-03/RC-05 路径与授权边界修复；junction/symlink 测试有真实 PASS 或明确 skip。
3. RC-04 Bandit `env` 漏扫修复；真实扫描证明目标文件被覆盖。
4. RC-08 取消/超时无子进程残留（或明确记录未解决）。
5. RC-09/RC-10 状态转移与项目写入策略明确并测试。
6. 当前完整 pytest 有原始退出码、passed/failed/skipped、耗时；不以历史数字替代。
7. 报告中心真实 GUI 工作流通过；默认不覆盖、确认覆盖、失败恢复。
8. 主库/验收库 integrity ok、FK 0、Schema 版本正确；`reports=0` 仍符合当前设计。
9. Phase 6B Manifest 14/14 匹配；Phase 5 Manifest 差异有书面解释；不伪造缺失脚本。
10. README 当前文案与 HTML/PDF/JSON 状态一致；测试数字为当前值或明确标注历史值。
11. E 盘备份可读；独立媒体备份和隔离恢复验证完成；`PHYSICAL_INDEPENDENT_BACKUP` 不得虚报为 YES。
12. Git 工作区无未审查的 staged 文件；预存修改/报告保留；无意外 reset/clean。
13. PDF/JSON/报告历史/Evidence 图片仍保持取消/延期/未批准，不被顺手实现。

## 9. 冲突与不确定事项核对

| 事项 | 核对结果 | 分类 |
|---|---|---|
| R0-B3 的 Git ahead/behind | 实际 ahead 5 / behind 0；`0 5` 是 `origin/main...HEAD` 的输出顺序，不是 behind 5 | `CURRENTLY_CONFIRMED` |
| HEAD 完整哈希差异 | R0-A/B1/B2/B3 与当前均为 `bffb5ac...`；没有发现 HEAD 漂移 | `CURRENTLY_CONFIRMED` |
| 未跟踪报告数量 | B3 开始时 5，B3 报告新增为 6，R0-C 报告新增为 7；是预期增长 | `CURRENTLY_CONFIRMED` |
| Phase 5 Manifest | 53 重复/9 mismatch/1 missing；多数 mismatch 是 Phase 6 后续修改；不能回滚文件修复 Manifest | `HISTORICAL_ONLY` + `CURRENTLY_CONFIRMED` 计数 |
| Phase 6B acceptance 计数 | JSON 9/11 与当前 10/14 冲突；Manifest 本身 14/14 匹配 | `CURRENTLY_CONFIRMED` |
| 主库 SHA 变化 | 6 条 `scan_logs` + 页面变化，高可信；操作者未知；不是损坏 | `CURRENTLY_CONFIRMED` 状态 / `UNKNOWN` 操作者 |
| E 盘物理独立性和恢复 | Manifest 说同一 SSD；当前硬件查询被拒；普通 mode=ro 打开失败；immutable 成功；没有本轮完整恢复 | `HISTORICAL_ONLY` + `UNKNOWN` |
| Semgrep Windows | 历史失败明确；本次未重跑；当前状态 `UNKNOWN` | `HISTORICAL_ONLY` / `REQUIRES_RUNTIME_TEST` |
| TOCTOU、junction/reparse | 静态代码证据明确；动态行为未在当前会话完整复现 | `CURRENTLY_CONFIRMED`（代码）/ `REQUIRES_RUNTIME_TEST`（运行） |

### 9.1 对 R0-B3 两个假阳性的更正

R0-B3 的 `B3-05`（Manifest 中文项目路径乱码）和 `B3-06`（`requirements.txt:10` 注释乱码）经本次 Unicode 码点/hex 复核，实际文件是合法 UTF-8：

- Manifest 项目路径为 `D:\挖漏洞\SRC-Research-Assistant`；
- `requirements.txt:10` 实际为 `"不可用"`；
- `security/scope_rules.py`、`README.md` 中的中文错误字符串同样是合法的。

之前看到的替换字符来自 PowerShell/Python 控制台解码，不是文件内容。**这两项从工程债务表撤回**，不列入 20 个问题。B3 报告本身不做修改（本任务禁止改旧文档），以本节作为更正记录。

## 10. 本次文件变化与 Git 状态

- 新增：`docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md`。
- 生产代码：未修改。
- 测试代码：未修改。
- README/配置/数据库/Schema/Manifest/归档：未修改。
- 测试/GUI/扫描器：未运行。
- Git：未执行 add/commit/push/reset/restore/clean；保留 `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 和全部既有未跟踪报告。

**当前 Git 状态**：

```text
BRANCH=main
HEAD=bffb5ac82bbebe7fef5992f87ff90494c9776ace
COMMIT_COUNT=8
STAGED=0
UNSTAGED=M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
UNTRACKED=7（含本报告）
AHEAD=5
BEHIND=0
```

## 11. 总体交付判断

**`OVERALL_DELIVERY_JUDGMENT = NOT_READY`**

判定依据：

1. 工程能力并不空白：Phase 1–5 有真实实现与历史验收，Phase 6 HTML 报告中心已接入 GUI，数据库/备份当前完整。
2. 但 RC-01 是 P0：pip-audit 在全部依赖 `skip_reason` 时可能给出“已审计、无漏洞”的假结论。任何文档、数据库或备份的完整性都不能抵消这个安全问题。
3. 另有 5 个 P1（Evidence/报告路径、Bandit 漏扫、授权路径、当前运行验证）和 7 个 P2 未关闭。
4. 当前完整 pytest、GUI 实际工作流、真实扫描和独立恢复尚未在本轮重新执行；历史测试结果不能当作当前通过。
5. 因此当前正确状态是 `NOT_READY`，不是 `READY_WITH_LIMITATIONS`；只有在 RC-01 修复、P1 关闭或经人工接受、当前回归通过后，才可重新评估。

**下一步**：人工选择是否批准 Stage 1（仅 RC-01）。本报告不自动开始修复，不进入 Phase 6F/6G，不启动 Phase 7。
