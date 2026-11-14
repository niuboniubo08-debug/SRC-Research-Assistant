# Phase 6 — 全局进度盘点与 Windows 打包路线调查

- 调查日期：2026-11-14（Asia/Shanghai）
- 项目：SRC-Research-Assistant
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 调查性质：只读；不运行测试、不运行扫描器、不修改代码/数据库/Schema/Git
- 报告文件：`docs/PHASE6_GLOBAL_STATUS_AND_WINDOWS_PACKAGING_ROADMAP.md`

## 1. 调查范围、方法与限制

### 1.1 范围

本次盘点覆盖：

1. 当前 Git 与工作区状态；
2. 项目版本、目录、入口、配置和数据库 Schema；
3. Phase 1–5 已完成能力的现状；
4. Phase 6 全部可定位阶段、子阶段和调查报告；
5. 报告中心、扫描器、Finding、Evidence 与 RC-01 的实际状态；
6. Windows 打包、运行时数据目录、资源、字体、扫描器部署和安装条件；
7. 从当前状态到首个 Windows 可交付版本的最短合理路线。

### 1.2 方法

- 读取当前源码、配置、测试文件、阶段报告和 Git 元数据；
- 只读查询 SQLite 的 `user_version`、`integrity_check`、`foreign_key_check` 和表清单；
- 用静态代码位置核验功能，而不是只依赖报告里的 `COMPLETED` 字样；
- 不运行 pytest、pip-audit、Bandit、Semgrep 或 GUI。

### 1.3 限制

- 本次没有重新执行完整测试；
- 没有在干净 Windows 虚拟机中运行；
- 没有实际生成 EXE；
- PyInstaller 与 Python 3.14.4 的兼容性没有在本机验证；
- 没有验证安装包、升级、卸载和代码签名。

## 2. Git 与项目真实状态

### 2.1 Git

```text
BRANCH = main
HEAD = 6137b5af22a50d266fc4ac7327f9baf8ae4294da
HEAD_SUBJECT = docs: add C4 post-commit verification for RC-01 closure docs
STATUS = clean
STAGED_FILES = 0
UNSTAGED_FILES = 0
UNTRACKED_FILES = 0
REMOTE = origin (GitHub: niuboniubo08-debug/SRC-Research-Assistant)
```

最近提交：

```text
6137b5a docs: add C4 post-commit verification for RC-01 closure docs
1e5163b docs: correct RC-01 approval time precision and add C3 report
7edc8fc docs: formally approve and close RC-01 with final C2 report
de4a639 docs: add RC-01 post-commit verification report
6e615db docs: add R2 verification and update RC-01 closure draft
4fd41b8 docs: add RC-01 formal closure draft for review
```

当前工作区是干净的。RC-01 的正式关闭文档已经进入当前 HEAD；此前 C4 报告中的“尚未提交”状态已经由本次 Git 事实取代。

### 2.2 版本与 Schema

```text
PROJECT_VERSION = 0.5.0
SCHEMA_VERSION = 5
DATABASE = storage/src_research.db
DB_USER_VERSION = 5
DB_INTEGRITY = ok
DB_FOREIGN_KEY_VIOLATIONS = 0
DB_APPLICATION_TABLES = 11
REPORTS_TABLE_ROWS = 0
```

应用表：

```text
app_settings
authorization_history
authorizations
evidence
finding_status_history
findings
projects
reports
scan_logs
scan_tasks
scope_assets
```

`reports` 表虽然存在，但当前没有报告历史持久化记录。HTML 导出不会自动写入该表。

### 2.3 关键目录

```text
app/            配置、启动、依赖装配
core/           模型、错误、枚举、日志、时间
database/       连接、Schema、迁移
repositories/   Vulnerability/Evidence/Report 只读仓库
reports/        HTML exporter + 4 个模板
scanners/       Bandit、Semgrep、pip-audit、进程执行器
security/       ScopeValidator 等
services/       业务服务
ui/             PySide6 页面与对话框
tests/          26 个测试文件
docs/           128 个 Markdown 文档及验收材料
storage/        数据库、日志、证据、报告、临时目录
tools/          辅助脚本
```

## 3. Phase 6 全阶段状态表

状态使用本任务规定的词汇。`COMPLETED` 只用于有代码、测试或验收证据且结论明确的项目；仅有设计报告的项目标为 `INVESTIGATED`。

| 阶段/步骤 | 原定目标 | 当前状态 | 代码/报告证据 | 验收结论 | 未完成事项 | Windows 首版必要条件 |
|---|---|---|---|---|---|---|
| Phase 6A 报告中心架构调查 | 调查数据流与可行性 | `INVESTIGATED` | `docs/PHASE6_C1_HTML_INVESTIGATION.md`；无独立 6A 文档 | 设计依据存在，非独立验收 | 无独立 6A 验收材料 | 否 |
| Phase 6B 报告数据层 | ReportSnapshot/Repository/Service | `COMPLETED` | `core/models/report.py`、`repositories/report_repository.py`、`services/report_service.py`、`docs/PHASE6_B_REPORT.md` | 已实现并归档；`sealed_with_recorded_exception` | P6B-EX-001/002 已记录 | 间接需要 |
| Phase 6C-1 HTML 调查 | 环境、依赖、安全与模板策略 | `INVESTIGATED` | `docs/PHASE6_C1_HTML_INVESTIGATION.md` | 调查完成；后被 C2A 继承 | 无 | 否 |
| Phase 6C-2A HTML 导出核心 | 安全 Jinja2 导出、模板、原子写入 | `COMPLETED` | `reports/html_exporter.py`、4 个模板、`tests/test_report_html.py`；`docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md` | 安全审查 `PASS_WITH_LIMITATIONS`；已关闭 | 父级 reparse、TOCTOU、CSP、动态 symlink | 是 |
| Phase 6C-2B GUI 集成 | 报告中心页面、预览、导出 | `COMPLETED` | `ui/report_page.py`、`app/bootstrap.py`、`ui/main_window.py`、`tests/test_ui_report.py`；`docs/PHASE6_C2B_STEP3_ACCEPTANCE.md` | `PASS_WITH_LIMITATIONS` | 无完整浏览器排版；无证据图嵌入 | 是 |
| Phase 6P-1 PDF 关闭审计 | 只读审计 PDF 残留 | `COMPLETED` | `docs/PHASE6_PDF_CLOSURE_AUDIT.md` | PDF `CANCELLED` | 不开发 | 否 |
| Phase 6P-2B 文档清理 | README/初始化文档/债务文案 | `COMPLETED` | `PHASE6_P2B_1..5B`、`P2B_6A`、`P2B_FINAL_ACCEPTANCE` | `P2B_FINAL_ACCEPTANCE=PASS` | 无 | 否 |
| Phase 6D-1A JSON 架构调查 | JSON 输出适配层调查 | `INVESTIGATED` | `docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md` | 只读调查，不等于批准 | 无实现 | 否 |
| Phase 6D-1B JSON 业务需求 | 判断是否有真实需求 | `COMPLETED` | `PHASE6_D1B_1...`、`PHASE6_D1B_3...` | `DEFERRED`，未批准 | 无消费者/契约 | 否 |
| Phase 6R0-A 历史盘点 | 历史文档与状态索引 | `COMPLETED` | `docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md` | 历史资料 PARTIAL | 历史差异保留 | 否 |
| Phase 6R0-B1/B2/B3 | 报告、扫描器、数据库/测试/文档审计 | `COMPLETED` | `PHASE6_R0_B1...`、`B2...`、`B3...` | 多个 `NOT_READY`/限制 | 部分问题未修 | 部分是 |
| Phase 6R0-C 债务与路线 | 合并问题、优先级、路线 | `COMPLETED` | `docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md` | 20 项债务；总体 `NOT_READY` | 修复未开始 | 部分是 |
| RC-01 pip-audit 真实性 | 修复假成功/不完整审计 | `COMPLETED` | `scanners/pip_audit_scanner.py`、`services/dependency_audit_service.py`、两份测试、C2/C3/C4 文档 | 正式关闭；C4 `PASS` | 真实跨层/网络未验证 | 是 |
| Stage 1B-5B Step 1.1–1.3 | 扫描器审计事实调查 | `INVESTIGATED` | `PHASE6_STAGE1B5B_STEP1_1..1_3` | 报告已存在；人工审核状态未确认 | Step 1.3 后续审核 | 否（调查） |
| Stage 1B-2C 最终统计契约 | 最终统计字段/完整性规则 | `APPROVED_NOT_EXECUTED` | 只有旧 `PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md`；没有“最终统计契约”报告 | 未执行最终提示词 | 需补最终只读报告或明确取消 | 否 |
| Phase 6F/6G | 未找到明确阶段材料 | `UNKNOWN` / `NOT_STARTED` | 无独立文档 | 不能声称完成 | 需人工确认范围 | 否 |
| Windows 打包与分发 | EXE/可交付包 | `NOT_STARTED` | 无 spec/icon/installer；README:168 仍列为未实现 | 无 | 全部打包工作 | 是 |
| Phase 6 最终封存 | 最终验收、归档、发布 | `NOT_STARTED` | 无 | `PHASE6_OVERALL_COMPLETION=NOT_DECLARED` | 依赖打包与最终验收 | 是 |

### 3.1 状态说明

- Phase 6A 没有独立阶段文档；它是 C1/B 报告中的设计依据，不能写成“已独立验收”。
- Phase 6B 已封存，但带两个记录例外；这不等于打包完成。
- Phase 6C-2A/2B 的功能和验收证据存在；但当前完整测试没有在本次调查中重跑。
- RC-01 的关闭文档已经提交；C4 核验为 PASS。RC-01 的跨层真实执行和真实 pip-audit 网络执行仍是未执行项。
- Stage 1B-2C 的“最终统计契约”提示词没有产生新的最终报告；旧 B2C 统计契约报告不能自动等同于该最终任务已完成。
- Phase 6F/6G 没有找到可定位的实施/验收材料，不能凭名称推断完成。

## 4. 核心功能完成度

| 能力 | 当前实现 | 验证状态 | 证据 |
|---|---|---|---|
| 项目管理 | 新建/编辑/删除/搜索/活动项目 | 代码与历史测试 | `ui/project_page.py`、`services/project_service.py`、`tests/test_project_service.py` |
| 授权与范围 | 授权状态、有效期、ScopeValidator | 代码与历史测试 | `services/authorization_service.py`、`security/scope_validator.py`、`tests/test_scope_validator.py` |
| Bandit 源代码审计 | 真实本地 Bandit 集成 | 历史实际执行 | `scanners/bandit_scanner.py`、`tests/test_bandit_scanner.py` |
| Semgrep | 接口、规则、解析存在 | 当前 Windows 不可用 | `scanners/semgrep_scanner.py`、`scanners/rules/python_security.yml`；`semgrep --version` 在 CA 初始化阶段失败 |
| pip-audit 依赖审计 | requirements/pyproject、JSON、Finding | RC-01 修复后已关闭 | `scanners/pip_audit_scanner.py`、`services/dependency_audit_service.py`、测试 12+34 函数 |
| 漏洞管理 | 过滤、状态、历史、备注、隔离 | 代码与历史测试 | `ui/vulnerability_page.py`、`services/vulnerability_service.py` |
| 证据中心 | 文本/文件、复制、SHA-256、路径约束 | 代码与历史测试；动态 symlink 跳过 | `services/evidence_service.py`、`tests/test_evidence_service.py` |
| HTML 报告 | 数据快照、ViewModel、模板、原子写入 | 代码；历史 28 个 HTML 测试 | `reports/html_exporter.py`、`reports/templates/*.html`、`tests/test_report_html.py` |
| 报告中心 GUI | 当前项目、类型、标题、备注、预览、导出 | 代码；历史 16 个 UI 测试 | `ui/report_page.py`、`tests/test_ui_report.py` |
| PDF | 已取消 | 无实现 | `docs/PHASE6_PDF_CLOSURE_AUDIT.md` |
| JSON | 延期/未批准 | 无实现 | `docs/PHASE6_D1B_3_JSON_DECISION.md` |
| 报告历史 | 表存在，无写入 | 未实现 | `database/schema.py:95-98`；`reports` 0 行 |
| 数据持久化 | SQLite v5，11 表 | 只读检查 integrity ok | `storage/src_research.db` |

## 5. 报告中心完成度

### 5.1 已实现

```text
reports/html_exporter.py       24,953 bytes, 754 lines
reports/templates/base.html
reports/templates/vulnerability.html
reports/templates/evidence.html
reports/templates/project_summary.html
tests/test_report_html.py      28,055 bytes, 28 test functions
tests/test_ui_report.py        13,254 bytes, 16 test functions
```

已确认：

- `ReportSnapshot` 先经 `build_report_view_model()` 白名单投影；
- Jinja2 `autoescape=True`、`StrictUndefined`；
- 模板不使用 `|safe`/`Markup`；
- 不引入脚本或远程资源；
- 输出目录固定为 `context.config.reports_dir`；
- 默认 `overwrite=False`；
- `overwrite=True` 需要用户明确确认；
- 原子写为临时文件 → `flush` → `fsync` → `close` → 发布；
- 正式导出只调用 `write_html_report()`。

### 5.2 已知限制

| 限制 | 影响 | 首版判断 |
|---|---|---|
| Evidence `project_<id>` 根目录可被 junction/symlink 重定向 | 报告证据路径可能越出项目证据根 | 必须在发布前决定修复或记录接受 |
| `reports_dir` 父级 reparse point 未完全检查 | 输出路径可被父级重定向 | 与上项同属路径边界 |
| 检查与发布之间存在 TOCTOU | 并发/恶意本地进程可改变目标 | 本地单用户风险较低，但不能称为完全安全 |
| 无 CSP | HTML 以本地文件打开时缺少额外防线 | 无脚本/远程资源，首版可接受但需记录 |
| 动态 Windows symlink 测试因 `WinError 1314` 跳过 | 符号链接行为只有静态/目录联接证据 | 必须在干净 Windows 环境补验证或记录跳过 |
| `QTextBrowser` 预览非浏览器排版 | CSS grid/flex 可能退化 | 已标注“安全文本预览”，首版可接受 |
| 证据图片不嵌入 | 报告只引用元数据 | 已延期，不影响 HTML 基本导出 |

## 6. 安全与可靠性缺口

结合 R0-B1/B2/B3/C 与 RC-01：

| 编号 | 缺口 | 级别 | 当前状态 | 首版处理 |
|---|---|---|---|---|
| RC-01 | pip-audit 跳过依赖被计数为已审计，可能假成功 | P0 | 已修复并正式关闭 | 已验证 |
| B2-02 | Evidence 根目录 reparse 未拒绝 | P1 | 未修复 | 发布前决定修复/接受 |
| B2-03 | Bandit 排除列表含 `env`，路径名含 `env` 时可假阴性 | P1 | 未修复 | 发布前修复或记录 |
| B2-05 | 进程终止只终止直接子进程 | P2 | 未修复 | 可接受但需记录 |
| B2-06 | ScopeValidator `resolve()` 后再匹配，symlink 语义需验证 | P1 | 未修复 | 发布前验证/修复 |
| R0-B1 | 报告父级 reparse 未检查 | P1 | 未修复 | 发布前决定 |
| R0-B1 | TOCTOU | P2 | 未修复 | 可接受限制 |
| R0-B1 | 无 CSP | P2 | 未修复 | 可接受限制 |
| R0-C | README/Manifest/Phase1 历史差异 | P3 | 部分未清理 | 不阻塞打包，但发布文档需修正 |
| 环境 | Semgrep Windows CA 初始化失败 | 已知限制 | 当前不可用 | 首版可作为已知限制 |
| 环境 | 7 个 symlink 测试跳过 | 测试限制 | 当前环境 | 干净 Windows 上复验 |

`RC-01` 的假成功问题已经修复；`RC-01_FORMAL_CLOSURE=CLOSED`。但 `P1` 路径问题尚未全部修复，不能把当前安全状态描述为“无已知风险”。

## 7. Windows 打包准备情况

### 7.1 当前实际状态

| 项目 | 当前状态 | 证据 | 缺失 |
|---|---|---|---|
| 打包工具 | 未安装/未配置 | `PyInstaller` import spec 为 `None` | PyInstaller 构建依赖 |
| 打包配置 | 无 `.spec` | `glob` 未找到 `.spec` | spec、hidden imports、datas |
| 图标 | 无 `.ico` | `glob` 未找到 `.ico` | 产品图标/版本资源 |
| 安装器 | 无 | 无 Inno Setup/NSIS 配置 | 安装、快捷方式、卸载 |
| 入口 | 有 | `main.py:1-6` → `app.application.main` | 无 |
| Qt 运行时 | 有 | `PySide6-Essentials`；`QTextBrowser` 可用 | PyInstaller Qt hooks/打包验证 |
| SQLite | 有 | `database/schema.py:14`，`user_version=5` | 首次运行/用户目录初始化策略 |
| 配置 | 相对程序目录 | `config.yaml:1-26`；`app/config.py:90-95` | 冻结后用户可写配置路径 |
| 日志 | 相对 storage | `core/logging_setup.py:10-23` | 用户数据目录 |
| 报告目录 | 相对 storage | `app/config.py:94`；`reports_dir` | 用户数据目录、权限 |
| 中文显示 | 依赖系统字体 | `ui/theme.py:28` 使用 Microsoft YaHei UI | 干净 Windows 字体验证；无自带字体 |
| Bandit 部署 | 依赖当前 Python | `scanners/base.py:118-120`、`bandit_scanner.py:136-140` 使用 `sys.executable -m bandit` | 冻结后无 Python 解释器 |
| pip-audit 部署 | 依赖 `pip-audit.exe`/PATH | `scanners/pip_audit_scanner.py:69-76` | 冻结后找不到 sidecar |
| Semgrep 部署 | 依赖外部 semgrep 可执行文件 | `semgrep_scanner.py:50-53` | 体积、CA、二进制分发 |
| 用户数据分离 | 无 | `app/config.py:17-26` 冻结时用 exe 同级目录 | 安装到 Program Files 时不可写 |
| 安装/升级/卸载 | 无 | 无安装器/更新机制 | 全部 |
| 干净 Windows 验证 | 未执行 | 无记录 | 全部 |
| 代码签名 | 无 | 无签名材料 | 可选但影响 SmartScreen |

### 7.2 关键打包阻塞

#### 阻塞 A：冻结应用中的扫描器启动

`BaseScanner._module_command()` 使用：

```python
[sys.executable, "-m", module, *args]
```

在源码运行时 `sys.executable` 是 Python；在 PyInstaller 冻结后通常变成应用 EXE，不能再执行 `-m bandit`。Bandit 扫描路径直接使用 `sys.executable`，因此打包后很可能显示“Bandit 不可用”或启动失败。

pip-audit 通过 `shutil.which("pip-audit")` 或 `Path(sys.executable).with_name("pip-audit.exe")` 查找；冻结后这两个位置通常不存在。

因此，打包前必须明确选择：

1. 随包附带独立 Python/扫描器 sidecar 环境；
2. 将 Bandit/pip-audit 改为库内调用，并把 Semgrep 作为真正的外部 sidecar；
3. 或其他经过验证的隔离扫描器方案。

这是首个交付版本的必要条件，不是可延期项。

#### 阻塞 B：运行时数据目录

`app/config.py:17-26`：

```python
if getattr(sys, "frozen", False):
    return Path(sys.executable).resolve().parent
return Path(__file__).resolve().parent.parent
```

`config.yaml` 的 `storage`/`database` 都是相对路径，最终落在程序目录下。若安装到 `Program Files` 或只读目录，数据库、日志、证据和报告无法创建。

首版必须将用户数据放到可写的 per-user 目录（例如 `%LOCALAPPDATA%`），并把程序资源与用户数据分离。

#### 阻塞 C：资源与模板打包

`reports/html_exporter.py:51`：

```python
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
```

PyInstaller 构建必须显式把 `reports/templates/*.html` 作为 data 打包；否则 HTML 导出会在运行时报模板缺失。当前没有 `.spec` 或打包验证。

#### 阻塞 D：安装与干净机器验证

当前没有安装器、卸载器、升级策略、代码签名或干净 Windows 运行记录。即使能生成 EXE，也不能据此声称“可在其他 Windows 电脑独立安装运行”。

## 8. MVP 与 V1.x 范围

### 8.1 MVP：首个可交付 Windows 版本

目标是“可解压/安装后完成核心业务流程，可靠保存数据并导出 HTML 报告”。

必须包含：

1. 项目、授权、范围校验；
2. 本地 Bandit 源代码审计；
3. 本地 pip-audit 依赖审计（RC-01 已修复）；
4. Finding/Evidence 管理；
5. HTML 报告预览与导出；
6. SQLite 持久化与首次运行初始化；
7. 可写的 per-user 数据目录；
8. 可用的 Qt/PySide6 运行时；
9. 扫描器 sidecar 或等价隔离方案；
10. 中文界面在干净 Windows 上可读；
11. 明确的 Semgrep 不可用提示（不伪造成果）；
12. 可复现的构建/校验记录。

MVP 不包含：

- PDF（已取消）；
- JSON（DEFERRED，未批准）；
- 报告历史/报告表写入；
- Evidence 图片嵌入；
- 远程扫描、漏洞利用、暴力破解；
- 自动更新、在线授权、云同步。

### 8.2 V1.x：首版之后

| 项目 | 延期理由 | 对首版影响 |
|---|---|---|
| 安装器（Inno Setup/NSIS） | 可先用便携 ZIP 验证核心；安装器增加升级/卸载复杂度 | 无；ZIP 可交付 |
| 代码签名 | 需要证书和发布流程 | 无；但 SmartScreen 可能提示 |
| 自动更新 | 需要服务器/签名/回滚 | 无 |
| 报告历史与报告表写入 | 当前导出是一次性文件；不是核心链路 | 无 |
| Evidence 图片嵌入 | 涉及图片安全与体积 | 无 |
| JSON 导出 | 无真实消费者；D1B 结论为 DEFERRED | 无 |
| PDF | 已正式取消 | 无 |
| 更完整的父级 reparse/TOCTOU 加固 | 本地单用户风险；需要专项测试 | 有安全限制，需记录 |
| Semgrep 打包/兼容性 | 体积、Windows CA 环境差异 | 无；Bandit 仍可完成核心源代码审计 |

## 9. 最短合理剩余路线图

### Stage A — 打包基础（必须）

目标：让应用在冻结后仍能启动、写数据、找模板、启动扫描器。

步骤：

1. **A1 用户数据目录**：程序资源与 `%LOCALAPPDATA%` 用户数据分离；迁移 `config.yaml`、DB、logs、evidence、reports。
2. **A2 扫描器 sidecar 决策**：为 Bandit/pip-audit 选择独立 Python 环境或库内调用；Semgrep 作为可选 sidecar。
3. **A3 资源路径**：让 `reports/templates`、`scanners/rules` 等通过冻结资源路径加载。
4. **A4 首次运行/迁移**：在用户数据目录创建 DB，执行 v5 初始化/迁移，提供备份和失败回滚。
5. **A5 包元数据**：版本资源、图标、许可、README、config 模板。

验收：

- 源码模式和冻结模式均能启动；
- DB/logs/evidence/reports 写入用户目录；
- HTML 模板可加载；
- Bandit 和 pip-audit 在冻结模式可用，或明确不可用且不伪造；
- 不写程序安装目录。

### Stage B — 构建可交付包（必须）

1. **B1 建立 PyInstaller/等价构建配置**：hidden imports、datas、Qt 插件、排除项。
2. **B2 打包扫描器 sidecar**：独立运行时、rules、版本信息、体积/许可证检查。
3. **B3 生成便携 ZIP**：可执行文件、模板、配置样例、说明、校验和。
4. **B4 构建冒烟**：`--version`、`--init-db`、无网络启动、HTML 导出。

验收：

- 构建可重复；
- ZIP 在没有项目源码的目录可启动；
- 模板、图标、版本、扫描器 sidecar 齐全；
- 不包含测试缓存、旧 DB、开发密钥/日志。

### Stage C — 干净 Windows 验收（必须）

1. **C1 干净 Windows 虚拟机/另一台机器**：无 Python、无项目 venv。
2. **C2 核心业务流**：项目→授权→Bandit→Finding→Evidence→HTML。
3. **C3 扫描器与报告**：Bandit/pip-audit 可用性、不可用状态、HTML 文件、中文显示。
4. **C4 数据与安全边界**：重启后数据保留；证据路径拒绝越界；symlink/junction 行为记录；无明文密钥/日志泄露。

验收：

- 核心流程全部通过；
- 7 个 symlink skip 在干净环境的实际结果被记录；
- 数据库 integrity ok，FK 0；
- 报告可在无网络环境打开；
- Semgrep 不可用时有明确说明。

### Stage D — 发布封存（必须）

1. **D1 发布材料**：README、版本、许可、第三方依赖、校验和。
2. **D2 备份与恢复**：源项目、数据库、构建产物、哈希清单。
3. **D3 最终验收/封存**：标记 Phase 6 完成或明确保留已知限制。

验收：

- 发布包哈希可复核；
- 备份可恢复；
- 文档不再声称未实现功能；
- 最终验收记录由人签字/确认。

### 9.1 依赖关系

```text
Stage A → Stage B → Stage C → Stage D
```

- A2（扫描器 sidecar）必须先于 B2；
- A1（用户数据目录）必须先于 B1/B3；
- C 必须使用真实干净 Windows，不接受仅源码 checkout 验证；
- D 不得在 C 之前宣称首版交付。

## 10. 剩余主要阶段和具体步骤数量

```text
REMAINING_MAJOR_STAGES = 4
REMAINING_CONCRETE_STEPS = 16
OPTIONAL_V1X_STEPS = 6 (installer/signing/auto-update/history/images/JSON)
```

- 4 个主要阶段：打包基础、构建、干净 Windows 验收、发布封存；
- 16 个具体步骤：A1–A5（5）+ B1–B4（4）+ C1–C4（4）+ D1–D3（3）；
- 该数量是规划计数，不是历史报告中的既有数字；
- JSON/PDF/报告历史/图片嵌入不计入首版步骤；
- 若临时增加安装器/签名，预计增加 3–5 个步骤，但不属于 MVP。

## 11. 打包前必须解决的阻塞

按优先级：

1. **扫描器在冻结应用中的执行方式**  
   `scanners/base.py:118-120`、`bandit_scanner.py:136-140`、`pip_audit_scanner.py:69-76` 的 `sys.executable`/sidecar 假设必须先解决。

2. **可写用户数据目录**  
   `app/config.py:17-26`、`:90-95` 当前以程序目录为根；安装到只读目录会导致 DB/日志/证据/报告失败。

3. **模板/规则/图标/版本资源打包**  
   `reports/html_exporter.py:51` 与 `scanners/rules` 必须显式入包；当前无 spec/icon。

4. **干净 Windows 首次运行**  
   包括 DB 初始化、配置、字体、Qt 插件、无 Python 环境、无网络环境。

5. **P1 路径边界决策**  
   Evidence 根 reparse、报告父级 reparse、ScopeValidator symlink 语义、Bandit `env` 排除；必须在发布前修复或写入“已接受限制”，不能默认为无风险。

## 12. 可延期任务

可以推迟到 V1.x：

- 安装器、卸载器、升级器；
- 代码签名与自动更新；
- JSON 导出（DEFERRED）；
- 报告历史持久化；
- Evidence 图片嵌入；
- Semgrep 的打包/兼容性完善；
- 更严格的 CSP、完整 TOCTOU 消除、父级 reparse 全链路防护；
- 更完整的浏览器排版预览；
- 多语言、主题扩展、遥测/诊断上传（如有）。

PDF 不在 V1.x：它已经被正式取消。

## 13. 当前前三大风险

1. **打包后扫描器不可用**  
   源码运行依赖 `sys.executable -m bandit` 和 `pip-audit.exe`；冻结后很可能失去这两个入口，导致“源代码/依赖审计”核心功能不可用。

2. **安装目录不可写/用户数据混乱**  
   继续把 DB、日志、证据、报告放在程序目录，会让安装在 `Program Files` 的版本无法工作，也会使升级/卸载丢失用户数据。

3. **没有干净 Windows 验证与打包资源**  
   目前没有 `.spec`、图标、安装器或干净机器记录；模板、Qt 插件、字体、扫描器 sidecar 的任何遗漏都可能在目标机器上才暴露。

## 14. 证据不足与 UNKNOWN

| 项目 | 状态 | 说明 |
|---|---|---|
| PyInstaller 与 Python 3.14.4 兼容性 | `UNKNOWN` | 当前未安装/未构建 |
| 冻结后 PySide6 Qt 插件完整性 | `UNKNOWN` | 没有打包验证 |
| 目标 Windows 版本范围 | `UNKNOWN` | 仅本机 Windows 11 环境记录 |
| 安装到 Program Files 的行为 | `UNKNOWN` | 当前未测试；按代码推断会不可写 |
| 代码签名/SmartScreen | `UNKNOWN` | 无证书/无发布流程 |
| Semgrep 在干净 Windows 的可用性 | `UNKNOWN` | 当前环境 CA 初始化失败 |
| 动态 symlink 在目标机器的行为 | `UNKNOWN` | 当前 7 个 skip 因 `WinError 1314` |
| 当前完整测试在 HEAD 的结果 | 未重新执行 | 历史 253 passed/7 skipped 在 `b90d234`；当前 HEAD 仅增加文档 |
| Phase 6F/6G 的原始范围 | `UNKNOWN` | 没有可定位材料 |
| Stage 1B-2C 最终统计契约 | `APPROVED_NOT_EXECUTED` | 只有旧 B2C 报告，没有最终交付报告 |

## 15. 最终结论

```text
GLOBAL_AUDIT = COMPLETED
IMPLEMENTATION = NOT_STARTED
NEXT_STEP = HUMAN_REVIEW_REQUIRED

PROJECT_VERSION = 0.5.0
SCHEMA_VERSION = 5
GIT_HEAD = 6137b5af22a50d266fc4ac7327f9baf8ae4294da
WORKTREE_CLEAN = YES

PHASE6_OVERALL_COMPLETION = NOT_DECLARED
RC01_FORMAL_CLOSURE = CLOSED
WINDOWS_PACKAGE_READY = NO
WINDOWS_PACKAGING_STARTED = NO
MVP_READY = NO
OVERALL_DELIVERY_JUDGMENT = NOT_READY
REMAINING_MAJOR_STAGES = 4
REMAINING_CONCRETE_STEPS = 16
```

结论：

- 当前项目已经具备可运行的 Python/PySide6 本地工作台，核心业务功能、SQLite v5、HTML 报告中心和 RC-01 修复均有实际代码与历史验证证据；
- 但项目还不是可在其他 Windows 电脑独立交付的软件包；
- 最大缺口不是业务功能本身，而是冻结运行时的扫描器、用户数据目录、资源打包和干净机器验收；
- 首个合理可交付版本应优先做“可解压运行的便携包”，安装器/签名/自动更新放入 V1.x；
- PDF 保持取消；JSON、报告历史、图片嵌入不进入 MVP；
- 本报告只完成调查，不实施任何修复或打包。

本次实际修改文件：仅新增本报告。

`docs/PHASE6_GLOBAL_STATUS_AND_WINDOWS_PACKAGING_ROADMAP.md`

未修改既有生产代码、测试、数据库、Schema、配置、README 或 Git 状态。
