# SRC Research Assistant 项目历史重建 — 步骤 1：Phase 1-2开发历史

* 生成日期：2026-11-05（Asia/Shanghai）
* 项目路径：`D:\\\\\\\\挖漏洞\\\\\\\\SRC-Research-Assistant`
* 调查范围：项目基本情况、Phase 1、Phase 2
* 调查性质：只读历史重建
* 本步骤明确未调查 Phase 3 及以后阶段的实现细节
* 本文件是本次唯一新增文件

## 0\. 结论先行

1. **项目不是在一份既有的 Phase 1 代码库上继续开发的。** 至少有两份直接文档说明：开始时工作区没有项目、第一阶段源代码、数据库和主窗口；开发先补齐基础框架，再完成第二阶段。`confirmed`（`README.md:9-18`、`docs/PHASE2\\\\\\\_CHANGES.md:3-9`、`docs/ARCHITECTURE.md:12-16`）
2. **“第一阶段”仍然有真实的验收记录和基础代码，但它没有独立的源码快照、独立 Git 历史或独立测试计数。** `confirmed`（`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:20-150`；`backups/` 无 Phase 1 归档）
3. **Phase 2 的项目管理、授权管理、ScopeAsset、ScopeValidator、Service 层、GUI 和 v2 数据库均有实际代码与验收数据。** `confirmed`
4. **Phase 2 没有 Repository 层。** 项目、授权和资产 CRUD 直接由 Service 使用 SQL 访问数据库；`repositories/` 是后续阶段才出现的目录。`confirmed`（`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:285-290`；`docs/PHASE2\\\\\\\_CHANGES.md:83-177`）
5. **Phase 2 测试数量存在时间差造成的记录冲突：初始快照文档写 37 passed，最终验收文档和最终快照写 40 passed。** 最终以 40 为准；差异可由最终快照新增 `tests/test\\\\\\\_ui\\\\\\\_dialogs.py` 的 3 个测试解释。`contradicted`（37 vs 40）；`confirmed`（最终 40）

## 1\. 项目基本信息

### 1.1 名称和版本

|项目|值|证据强度|
|-|-|-|
|名称|`SRC Research Assistant`|`confirmed`：`config.yaml:2-4`、`README.md:1`|
|当前版本|`0.5.0`|`confirmed`：`app/\\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py:3`、`config.yaml:4`|
|Phase 2 快照版本|`0.2.0`|`confirmed`：`backups/src-research-assistant\\\\\\\_phase2\\\\\\\_20261104T145255Z.zip` 内 `app/\\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py` 与 `config.yaml`|
|Phase 1 独立版本号|未找到|`unknown`：没有 Phase 1 快照或独立版本文件|
|当前 schema|`v5`|`confirmed`：`database/schema.py:14`|
|Phase 1 schema|`v1`，7 张表|`confirmed`（代码和报告）；但无有效 v1 数据库快照，见 §8|
|Phase 2 schema|`v2`，10 张表|`confirmed`：`database/schema.py:124-162`；`storage/acceptance/acceptance.db` `user\\\\\\\_version=2`|

### 1.2 Python 与执行环境

实际只读检查结果：

```text
解释器：D:\\\\\\\\挖漏洞\\\\\\\\.venv\\\\\\\\Scripts\\\\\\\\python.exe
Python：3.14.4 (tags/v3.14.4:23116f9, Apr  7 2026, 14:10:54) \\\\\\\[MSC v.1944 64 bit (AMD64)]
SQLite：3.50.4
pip：26.3
```

历史报告记录：

* Phase 1/2 使用 `D:\\\\\\\\挖漏洞\\\\\\\\.venv\\\\\\\\Scripts\\\\\\\\python.exe`；
* 系统 Python 另为 `D:\\\\\\\\Python314\\\\\\\\python.exe`；
* Phase 2 验收时 Python 3.14.4、PySide6 6.12.0、SQLite 3.50.4。

证据：`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:58-67`、`docs/TEST\\\\\\\_REPORT.md:3-20`。

### 1.3 主要依赖：声明与实际安装

`requirements.txt` 是**声明**；下表右列是当前环境的**实际安装版本**。历史 Phase 1/2 的精确安装锁文件不存在。

|依赖|声明|当前实际|
|-|-|-|
|PySide6-Essentials|`>=6.10,<7`|`6.12.0`|
|PyYAML|`>=6.0,<7`|`6.0.3`|
|Jinja2|`>=3.1,<4`|`3.1.6`|
|Bandit|`>=1.9,<2`|`1.9.4`|
|pip-audit|`>=2.10,<3`|`2.10.1`|
|Semgrep|`>=1.100,<2`|`1.183.0`（历史 Windows 运行有限制）|
|pytest|`>=8,<10`|`9.2.0`|
|pytest-qt|`>=4.4,<5`|`4.5.0`|

历史 Phase 2 归档的 `requirements.txt` 只声明 PySide6-Essentials、PyYAML、Jinja2、pytest、pytest-qt，Bandit/pip-audit/Semgrep 仅作为注释中的计划依赖。`confirmed`（`backups/src-research-assistant\\\\\\\_acceptance\\\\\\\_final.zip` 内 `requirements.txt`）

### 1.4 GUI、数据库、入口和测试框架

|项目|实际值|证据|
|-|-|-|
|GUI 框架|PySide6-Essentials 6.12.0|`requirements.txt`、报告 `ACCEPTANCE\\\\\\\_REPORT.md:58-67`|
|数据库|SQLite 3.50.4，schema v5|`database/schema.py:14`、只读 `PRAGMA user\\\\\\\_version`|
|入口|`main.py` → `app.application.main`|`main.py:1-6`|
|启动 UI|`QApplication` → `AppState` → `MainWindow` → `show()` → `app.exec()`|`app/application.py:78-98`|
|测试框架|pytest + pytest-qt，offscreen Qt|`pytest.ini`、`docs/TEST\\\\\\\_REPORT.md:3-18`|

### 1.5 启动流程

`confirmed`，按实际代码：

```text
main.py
  └─ app.application.main()
       ├─ \\\\\\\_parse\\\\\\\_args()                        # --config/--init-db/--version
       ├─ build\\\\\\\_context(config\\\\\\\_path)
       │    ├─ AppConfig.load()
       │    ├─ config.ensure\\\\\\\_directories()
       │    ├─ configure\\\\\\\_logging(config.logs\\\\\\\_dir)
       │    ├─ Database.initialize()
       │    ├─ AuditLogService
       │    ├─ ProjectService
       │    ├─ AuthorizationService
       │    ├─ ScopeAssetService
       │    ├─ ScopeValidator
       │    └─ ... 后续阶段的扫描器与 Service
       ├─ \\\\\\\_install\\\\\\\_exception\\\\\\\_hook()
       ├─ AppState(context.project\\\\\\\_service)
       ├─ MainWindow(context, state)
       ├─ window.show()
       └─ app.exec()
```

证据：`main.py:3-6`、`app/application.py:60-98`、`app/bootstrap.py:56-142`。

`main.py --init-db` 在 `app/application.py:74-76` 输出数据库摘要；Phase 1/2 验收报告记录了实际 `schema\\\\\\\_version=2` 和 10 张表。`confirmed`（`ACCEPTANCE\\\\\\\_REPORT.md:69-106`）

### 1.6 配置管理

`confirmed`：

* 配置文件：`config.yaml`；
* 类型化、不可变配置：`app/config.py:43-129` 的 `AppConfig`；
* 路径解析：相对路径相对配置文件目录，`app/config.py:36-40`；
* 安全默认值强制：`default\\\\\\\_remote\\\\\\\_access` 只允许 `deny`，`app/config.py:105-107`；
* 存储目录由 `AppConfig.ensure\\\\\\\_directories()` 创建，`app/config.py:131-142`；
* `--config` 可指定其他配置，`app/application.py:17-26`。

`config.yaml` 的关键值：

```text
app.name = SRC Research Assistant
app.version = 0.5.0
database.path = storage/src\\\\\\\_research.db
storage.root = storage
security.default\\\\\\\_remote\\\\\\\_access = deny
security.require\\\\\\\_exact\\\\\\\_remote\\\\\\\_match = true
security.allow\\\\\\\_redirect\\\\\\\_following = false
```

### 1.7 日志与异常处理

日志 `confirmed`：

* `core/logging\\\\\\\_setup.py:10-27` 配置 `src\\\\\\\_assistant` logger；
* 写入 `storage/logs/app.log`；
* `RotatingFileHandler`，2,000,000 字节，3 个备份，UTF-8；
* 审计日志另由 `AuditLogService` 写入 SQLite `scan\\\\\\\_logs` 与 `storage/logs/audit.jsonl`（历史报告 `ACCEPTANCE\\\\\\\_REPORT.md:47-48`）。

异常 `confirmed`：

* 业务异常基类和分类：`core/errors.py:13-47`；
* `ValidationError`、`NotFoundError`、`ConflictError`、`StorageError`、`AuthorizationDenied`；
* GUI 全局异常钩子：`app/application.py:39-57`，记录到日志并显示错误对话框；
* 启动失败返回非零退出码，`app/application.py:68-72`。

## 2\. 项目目录结构

### 2.1 当前结构（只列与 Phase 1/2 相关的骨架）

`confirmed`：

```text
SRC-Research-Assistant/
├── main.py
├── config.yaml
├── requirements.txt
├── pytest.ini
├── app/
│   ├── \\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py
│   ├── application.py
│   ├── bootstrap.py
│   └── config.py
├── core/
│   ├── errors.py
│   ├── logging\\\\\\\_setup.py
│   ├── timeutil.py
│   └── models/
│       ├── enums.py
│       ├── project.py
│       ├── authorization.py
│       ├── scope.py
│       └── system.py
├── database/
│   ├── schema.py
│   └── connection.py
├── security/
│   ├── scope\\\\\\\_rules.py
│   └── scope\\\\\\\_validator.py
├── services/
│   ├── audit\\\\\\\_service.py
│   ├── project\\\\\\\_service.py
│   ├── authorization\\\\\\\_service.py
│   └── scope\\\\\\\_asset\\\\\\\_service.py
├── ui/
│   ├── main\\\\\\\_window.py
│   ├── project\\\\\\\_page.py
│   ├── dashboard.py
│   ├── history\\\\\\\_page.py
│   ├── settings\\\\\\\_page.py
│   └── placeholder.py
├── tests/
├── tools/
├── docs/
├── storage/
└── backups/
```

当前目录还包含后续阶段加入的 `scanners/`、`repositories/`、报告/证据页面等；这些不属于 Phase 1/2 历史结论，本步骤不展开。

### 2.2 Phase 1 报告中的结构

`confirmed`（`ACCEPTANCE\\\\\\\_REPORT.md:34-56`）：

* `app/`：配置、组合根、Qt 启动；
* `core/`：模型、错误、时间；
* `database/`：统一连接、schema；
* `security/`：`ScopeValidator`；
* `services/`：项目/授权/资产/审计；
* `ui/`：主窗口与 10 个页面；
* `scanners/`、`reports/`：未启用边界；
* `storage/`：数据库、验收库、日志；
* `tests/`：6 个测试文件（这是 Phase 1/2 合并验收时的结构描述）；
* `tools/`、`docs/`、`backups/`。

注意：该目录树来自**第一、二阶段合并验收报告**，不是 Phase 1 独立快照。`unknown`：Phase 1 完成瞬间的精确文件清单。

## 3\. Phase 1 开发历史

### 3.1 直接证据与关键事实

|事实|结论|证据|
|-|-|-|
|开始时工作区没有项目、第一阶段源码、数据库、主窗口|`confirmed`|`README.md:9-18`；`docs/PHASE2\\\\\\\_CHANGES.md:3-9`；`docs/ARCHITECTURE.md:12-16`|
|先补齐基础框架，再实现第二阶段|`confirmed`|同上|
|存在“第一阶段验收”章节并判定通过|`confirmed`|`ACCEPTANCE\\\\\\\_REPORT.md:14,20-150,327-341`|
|不存在独立的 Phase 1 源码快照|`confirmed`|`backups/` 仅有 Phase 2 及之后的 zip；无 `phase1` 归档|
|不存在独立 Phase 1 Git 历史|`confirmed`|`.git` 不存在；`git log` 无输出|
|Phase 1 精确开发起止时间|`unknown`|报告只给出合并验收时间 `2026-11-04 23:03` 起|
|Phase 1 独立测试数量|`unknown`|没有 Phase 1 独立 pytest 记录；只有合并验收的 40 项|
|Phase 1 独立版本号|`unknown`|无 Phase 1 快照；Phase 2 快照为 0.2.0|

### 3.2 开发目标

`confirmed`（来自 `ACCEPTANCE\\\\\\\_REPORT.md:20-150`）：

1. 建立可运行的 Windows 桌面项目骨架；
2. 建立真实入口 `main.py`；
3. 建立深色主窗口和 10 个导航页；
4. 建立 SQLite 数据库和 7 张基础表；
5. 建立配置、日志、异常处理和存储目录；
6. 验证页面切换、窗口关闭和事件循环退出。

`unknown`：这次“第一阶段”是否有独立于合并验收报告的原始需求文档。未找到 `PHASE1\\\\\\\_\\\\\\\*` 报告、文件清单或测试记录。

### 3.3 建立的基础架构

`confirmed`：

* 入口：`main.py` → `app.application.main`；
* 应用组合根：`app.bootstrap.build\\\\\\\_context`；
* 类型化配置：`app.config.AppConfig`；
* 数据库连接和 schema：`database.connection.Database`、`database.schema.SCHEMA\\\\\\\_V1`；
* 10 页导航：`ui.main\\\\\\\_window.MainWindow`；
* 页面壳：`DashboardPage`、`ProjectPage`、`SourceAuditPage`、`DependencyPage`、`ConfigAuditPage`、`VulnerabilityPage`、`EvidencePage`、`ReportPage`、`HistoryPage`、`SettingsPage`；
* 深色主题：`ui.theme`；
* 错误类型：`core.errors`；
* 日志：`core.logging\\\\\\\_setup`。

`inferred`：哪些具体文件是在 Phase 1 而不是 Phase 2 创建。由于没有 Git 和 Phase 1 快照，只能根据文件职责和合并报告推断；不能精确到“每个文件的首次创建时间”。

### 3.4 目录和核心文件

Phase 1 基础七表及代码位置：

|表|用途|代码证据|
|-|-|-|
|`projects`|项目基础信息|`database/schema.py:17-28`|
|`authorizations`|授权记录|`database/schema.py:30-45`|
|`scan\\\\\\\_tasks`|扫描任务占位|`database/schema.py:47-60`|
|`findings`|漏洞占位|`database/schema.py:62-79`|
|`evidence`|证据占位|`database/schema.py:81-93`|
|`reports`|报告占位|`database/schema.py:95-104`|
|`scan\\\\\\\_logs`|审计/扫描日志|`database/schema.py:106-121`|

`confirmed`：`SCHEMA\\\\\\\_V1` 注释写明“Version 1 is the phase-1 foundation (seven tables)”（`database/schema.py:3-4`）。

### 3.5 GUI 启动机制

`confirmed`：

* `main.py` 导入 `app.application.main`，并由 `SystemExit` 承载返回码（`main.py:3-6`）；
* `main()` 解析参数、构建 `AppContext`，再创建 `QApplication`；
* `AppState` 绑定 `ProjectService`；
* `MainWindow` 构建固定侧边栏、顶部项目选择器和 `QStackedWidget`；
* `window.show()` 后进入 `app.exec()`；
* 关闭窗口后事件循环返回，退出码为 0。

证据：`app/application.py:78-98`、`ui/main\\\\\\\_window.py:34-50`、`docs/acceptance/entrypoint\\\\\\\_acceptance.json`（该 JSON 当前记录的是 0.5.0，不是 Phase 1 快照；Phase 1/2 的启动记录见 `ACCEPTANCE\\\\\\\_REPORT.md:108-144`）。

`confirmed`：Phase 1 验收实际执行了生产入口、10 个导航点击、窗口关闭和 offscreen 截图；`started=true`、`closed\\\\\\\_normally=true`、`application\\\\\\\_exit\\\\\\\_code=0`。

### 3.6 数据库是否建立

`confirmed`：

* `SCHEMA\\\\\\\_V1` 定义了 7 张表；
* 合并验收报告明确列出七张第一阶段表（`ACCEPTANCE\\\\\\\_REPORT.md:106`）；
* Phase 2 验收库 `storage/acceptance/acceptance.db` 的 schema v2 保留了这些表（只读检查：`projects`、`authorizations`、`scan\\\\\\\_tasks`、`findings`、`evidence`、`reports`、`scan\\\\\\\_logs` 全部存在）。

`contradicted`：

* `storage/backups/src\\\\\\\_research\\\\\\\_v1\\\\\\\_20261104T143150Z.db` 文件名声称 v1，但只读检查得到：

  * 文件大小约 4 KB；
  * `PRAGMA user\\\\\\\_version = 0`；
  * 无业务表。
* 因此它**不能作为“Phase 1 七表数据库已落库”的直接快照**，更像初始化前或占位备份。
* 结论：Phase 1 schema 由代码/报告确认，但“Phase 1 当时生成了有效 v1 数据库文件”没有直接快照证据。`unknown`

### 3.7 配置、日志和异常处理

`confirmed`（代码和合并报告）：

* 配置：`config.yaml` + `AppConfig`，安全默认拒绝；
* 日志：`core/logging\\\\\\\_setup.py` 的滚动文件日志；
* 异常：`core/errors.py` 的业务异常分类 + `app/application.py` 的全局异常钩子；
* 存储目录：`AppConfig.ensure\\\\\\\_directories()`。

`inferred`：这些机制在 Phase 1 时的具体代码版本。当前文件已经随后续阶段增加字段/服务，不能把当前每一行都视为 Phase 1 原始行。

### 3.8 Phase 1 测试内容

`confirmed`（合并验收层面）：

* 生产入口启动；
* 10 个导航页切换；
* 窗口最大化/关闭能力；
* 事件循环退出码 0；
* 7 张基础表 + 第二阶段表存在；
* `schema\\\\\\\_version=2`、外键违规 0；
* 主库无演示数据。

证据：`ACCEPTANCE\\\\\\\_REPORT.md:108-150`、`entrypoint\\\\\\\_acceptance.json`（当前文件版本 0.5.0，不能直接反推 Phase 1 窗口标题；Phase 1/2 的 10 页导航记录在报告中）。

`unknown`：

* Phase 1 是否有独立的 pytest 文件/数量；
* Phase 1 单独执行的测试通过数；
* 合并报告中的 40 项 pytest 是否包含“只属于 Phase 1”的测试。40 项主要覆盖 Phase 2 的项目/授权/资产/范围/数据库/UI，因此不能把它归为 Phase 1 测试。

### 3.9 Phase 1 最终验收

`confirmed`：通过。

报告原文（`ACCEPTANCE\\\\\\\_REPORT.md:146-150`）：

> 已完成：项目骨架、真实入口、10 页导航、深色主窗口、数据库 10 表、页面切换、正常关闭、运行截图。
> 未完成：无本阶段范围内未完成项；原生桌面窗口无法在当前自动化会话中截图，属于环境限制。

（说明：引文中的“数据库 10 表”是合并验收时 schema v2 的表数，包含第二阶段新增三表；Phase 1 基础七表见 §3.6。）

环境限制：`confirmed`，自动化会话无法取得原生 `MainWindowHandle`，使用 offscreen Qt 执行同一生产入口并截图；报告没有声称原生桌面窗口已经可见。

## 4\. Phase 2 开发历史

### 4.1 时间线

|时间（本地）|事件|证据强度|
|-|-|-|
|2026-11-04 22:52:55|初始 Phase 2 快照 zip（0.2.0，72 个归档条目，文档写 37 passed）|`confirmed`：zip 文件名/内容|
|2026-11-04 23:03 起|第一、二阶段合并验收开始|`confirmed`：`ACCEPTANCE\\\\\\\_REPORT.md:3`|
|2026-11-04 23:06:21|`phase2\\\\\\\_acceptance.json` 生成；31/31 PASS|`confirmed`：JSON `generated\\\\\\\_at`|
|2026-11-04 23:16:42|最终验收快照 zip（0.2.0，92 个归档条目，40 passed）|`confirmed`：zip 文件名/内容|

`unknown`：每个源文件的具体创建/修改时间，以及 Phase 2 的逐日开发顺序；没有 Git。

### 4.2 项目管理

`confirmed`：

* 服务方法：`ProjectService.create\\\\\\\_project`、`update\\\\\\\_project`、`delete\\\\\\\_project`、`get\\\\\\\_project`、`list\\\\\\\_projects`、`set\\\\\\\_active\\\\\\\_project`、`get\\\\\\\_active\\\\\\\_project`（`services/project\\\\\\\_service.py:78-193,196-219,230-264`）。
* 字段：`project\\\\\\\_id`、`project\\\\\\\_name`、`project\\\\\\\_type`、`description`、`local\\\\\\\_path`、`status`、`created\\\\\\\_at`、`updated\\\\\\\_at`（`core/models/project.py:13-22`）。
* GUI：`ProjectPage` 的 4 个标签页“项目列表 / 项目详情 / 授权管理 / 授权资产”（`ui/project\\\\\\\_page.py:551-592`）。
* 功能：新建、编辑、删除、查询、详情、搜索、状态筛选、创建时间排序、设为当前项目。
* 删除：事务内删除项目，`app\\\\\\\_settings.active\\\\\\\_project\\\\\\\_id` 清理；审计记录保留（`services/project\\\\\\\_service.py:169-187`）。
* 当前项目：`app\\\\\\\_settings` 键值持久化（`services/project\\\\\\\_service.py:229-264`）。

验收：`phase2\\\\\\\_acceptance.json` 的“创建、查询、修改、设置当前、删除、删除后清理”6 个步骤全部 PASS。`confirmed`

### 4.3 授权管理

`confirmed`：

* 服务：`AuthorizationService.create\\\\\\\_authorization`、`update\\\\\\\_authorization`、`revoke\\\\\\\_authorization`、`delete\\\\\\\_authorization`、`get\\\\\\\_authorization`、`list\\\\\\\_authorizations`（`services/authorization\\\\\\\_service.py:135-324`）。
* 四种状态：pending / confirmed / expired / revoked。
* “已确认”必须有来源和授权文件（`\\\\\\\_validate\\\\\\\_status\\\\\\\_requirements`，`services/authorization\\\\\\\_service.py:77-90`）。
* 时间窗口校验、撤销终态、删除保护、历史写入。
* 每次变更写 `authorization\\\\\\\_history` 与审计；撤销后禁止修改（`services/authorization\\\\\\\_service.py:214-215`）。
* 启动时持久化过期：`app/bootstrap.py:140-142` 调用 `expire\\\\\\\_overdue\\\\\\\_authorizations()`。
* 资产关联时拒绝删除授权：`services/authorization\\\\\\\_service.py:289-294`。

验收：`phase2\\\\\\\_acceptance.json` 中授权创建/确认/文件必填/过期/撤销/历史/删除保护均 PASS；`ACCEPTANCE\\\\\\\_REPORT.md:167-189` 给出 4 条授权、7 条历史、33 条日志的验收库状态。`confirmed`

### 4.4 授权范围与 ScopeAsset

`confirmed`：

* 模型：`ScopeAsset`（`core/models/scope.py:14-25`）。
* 类型：域名、IP、本地目录、本地项目（`database/schema.py:128`）。
* 字段：`asset\\\\\\\_id`、`project\\\\\\\_id`、`asset\\\\\\\_type`、`asset\\\\\\\_value`、`authorization\\\\\\\_id`、`allowed\\\\\\\_operations`、`asset\\\\\\\_status`、`notes`、时间戳。
* 服务：`ScopeAssetService.create\\\\\\\_asset`、`update\\\\\\\_asset`、`delete\\\\\\\_asset`、`get\\\\\\\_asset`、`list\\\\\\\_assets`（`services/scope\\\\\\\_asset\\\\\\\_service.py:96-294`）。
* 远程资产必须绑定当前有效授权；本地资产不能绑定远程授权或远程操作（`services/scope\\\\\\\_asset\\\\\\\_service.py:111-119`）。
* 唯一性：`UNIQUE(project\\\\\\\_id, asset\\\\\\\_type, asset\\\\\\\_value)`（`database/schema.py:136`）。
* 精确范围匹配：`ScopeValidator.check\\\\\\\_remote\\\\\\\_access` 使用规范化目标等值查询（`security/scope\\\\\\\_validator.py:196-210`），不是子域后缀匹配。
* 本地路径范围：`ScopeValidator.check\\\\\\\_local\\\\\\\_path` 要求本地资产、目录存在、可读、路径精确匹配（`security/scope\\\\\\\_validator.py:437-529`）。
* 默认拒绝、审计、fail-closed：`security/scope\\\\\\\_validator.py` 的 `\\\\\\\_deny`/`\\\\\\\_finish` 链路；报告 `ACCEPTANCE\\\\\\\_REPORT.md:292-307`。

验收：`phase2\\\\\\\_acceptance.json` 中 `example.test` 允许、`authorized.example.test` 允许、`other.example.test` 拒绝、通配符拒绝、范围外拒绝、过期/撤销拒绝、URL 拒绝、无授权资产拒绝均 PASS。`confirmed`

### 4.5 Service 和 Repository 的真实状态

|层|Phase 2 状态|证据强度|
|-|-|-|
|Service|存在 `ProjectService`、`AuthorizationService`、`ScopeAssetService`、`AuditLogService`|`confirmed`|
|Repository|**不存在**|`confirmed`|
|SQL 位置|直接写在 Service 中|`confirmed`：`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:285-290` 明确“尚未抽出独立 repository 层”|
|UI 直连数据库|无|`confirmed`：报告静态检查；当前 UI 也使用 Service|

`inferred`：如果只看当前目录，会看到 `repositories/`，但其中的 `vulnerability\\\\\\\_repository.py` / `evidence\\\\\\\_repository.py` 属于后续阶段，不是 Phase 2 的 Repository 层。Phase 2 的 `PHASE2\\\\\\\_CHANGES.md` 文件清单没有 `repositories/`。

### 4.6 GUI 页面

`confirmed`：

* 主窗口 10 个导航页（`ui/main\\\\\\\_window.py:108-119`）。
* 项目管理页 4 个标签页（`ui/project\\\\\\\_page.py:588-592`）：

  1. 项目列表；
  2. 项目详情；
  3. 授权管理；
  4. 授权资产。
* 三个真实对话框：

  * `ProjectDialog`（`ui/project\\\\\\\_page.py:80-198`）；
  * `AuthorizationDialog`（`ui/project\\\\\\\_page.py:200-352`）；
  * `ScopeAssetDialog`（`ui/project\\\\\\\_page.py:354-549`）。
* 顶部当前项目选择器和侧边栏由 `MainWindow` 构建；项目切换通过 `AppState` 信号同步（`ui/main\\\\\\\_window.py:34-50`，后续方法）。
* 验收：`ui\\\\\\\_acceptance.json` 记录版本 0.2.0、10 页切换、最大化/关闭、事件循环退出码 0；`tests/test\\\\\\\_ui.py` 2 项、`tests/test\\\\\\\_ui\\\\\\\_dialogs.py` 3 项。

### 4.7 数据库结构

Phase 2 最终 schema v2，共 10 张业务/审计表：

```text
projects, authorizations, scan\\\\\\\_tasks, findings, evidence, reports,
scan\\\\\\\_logs, scope\\\\\\\_assets, authorization\\\\\\\_history, app\\\\\\\_settings
```

`confirmed`：

* 定义：`database/schema.py:16-162`（v1 七表 + v2 三表）；
* v2 新增表：`scope\\\\\\\_assets`、`authorization\\\\\\\_history`、`app\\\\\\\_settings`；
* 迁移：`database/connection.py:105-113` 在 v1→v2 前调用 `\\\\\\\_backup\\\\\\\_before\\\\\\\_migration(1)`，然后执行 `MIGRATION\\\\\\\_V2`；
* 实际验收库 `storage/acceptance/acceptance.db` 只读检查：

  * `PRAGMA user\\\\\\\_version = 2`；
  * 10 张业务表；
  * `projects=2`、`authorizations=4`、`scope\\\\\\\_assets=7`、`authorization\\\\\\\_history=7`、`scan\\\\\\\_logs=33`；
  * `scan\\\\\\\_tasks=0`、`findings=0`、`evidence=0`、`reports=0`；
  * `PRAGMA foreign\\\\\\\_key\\\\\\\_check` 无输出；
* `storage/backups/src\\\\\\\_research\\\\\\\_v2\\\\\\\_20261105T020152Z.db` 也是 schema 2、10 张表、0 行；时间在 Phase 2 验收之后，不能当作 Phase 2 验收当时的实时快照。

### 4.8 测试情况

最终 Phase 2 测试：**40 passed / 0 failed / 0 skipped，6.14s**。`confirmed`（`docs/TEST\\\\\\\_REPORT.md:9-18,40-47`）

|测试文件|数量|内容|
|-|-:|-|
|`tests/test\\\\\\\_database.py`|4|schema、10 表、外键、级联、数据库路径异常|
|`tests/test\\\\\\\_project\\\\\\\_service.py`|7|项目 CRUD、校验、筛选/排序、当前项目|
|`tests/test\\\\\\\_authorization\\\\\\\_service.py`|8|授权 CRUD、确认条件、过期、撤销、历史、删除保护|
|`tests/test\\\\\\\_scope\\\\\\\_validator.py`|16|精确匹配、拒绝通配符/子域/URL、过期/撤销、DNS、重定向、本地路径、审计、fail-closed|
|`tests/test\\\\\\\_ui.py`|2|主窗口、10 页、4 子页、关闭|
|`tests/test\\\\\\\_ui\\\\\\\_dialogs.py`|3|项目/授权/资产对话框真实输入与校验|
|**合计**|**40**||

`contradicted`（文档时间差）：

* 初始 Phase 2 zip 内 `docs/PHASE2\\\\\\\_CHANGES.md` 与 `docs/TEST\\\\\\\_REPORT.md` 写 **37 passed**；
* 初始 zip 只有 `tests/test\\\\\\\_ui.py` 等 6 个测试文件，没有 `tests/test\\\\\\\_ui\\\\\\\_dialogs.py`；
* 最终验收 zip 增加 `tests/test\\\\\\\_ui\\\\\\\_dialogs.py`（3 个测试），文档改为 **40 passed**；
* 当前工作区 `docs/TEST\\\\\\\_REPORT.md` 和 `docs/PHASE2\\\\\\\_CHANGES.md` 也是 **40**。
* 因此“37 vs 40”不是同一时点的随机矛盾，而是 **初始快照 → 最终验收** 的增量；任何引用都必须注明时点。

### 4.9 Phase 2 验收结论

`confirmed`：通过。

* 合并报告：Phase 2 通过，`pytest 40 passed`，独立业务验收 `31/31 PASS`，代码质量阻断 0；
* 验收库数据：2 项目、4 授权、7 资产、7 历史、33 日志、0 外键违规；
* 验收期间实际修复 1 个产品缺陷：`ScopeAssetDialog` 缺少 `AssetStatus` 导入（`ACCEPTANCE\\\\\\\_REPORT.md:315-323`、`TEST\\\\\\\_REPORT.md:55-58`）；
* 原生窗口截图环境限制仍存在，但没有把 offscreen 截图说成原生窗口。

## 5\. 核心文件清单

### 5.1 Phase 1/2 基础与入口

|文件|作用|历史证据强度|
|-|-|-|
|`main.py`|生产入口，调用 `app.application.main`|`confirmed`|
|`app/application.py`|参数、数据库初始化、Qt 生命周期、全局异常|`confirmed`|
|`app/bootstrap.py`|组合根：配置、日志、数据库、服务|`confirmed`|
|`app/config.py`|YAML 解析、不可变 `AppConfig`、安全默认值|`confirmed`|
|`app/\\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py`|版本号；当前 0.5.0|`confirmed`（当前）/ `unknown`（Phase 1）|
|`config.yaml`|运行配置；当前 0.5.0|`confirmed`|
|`core/errors.py`|业务异常分类|`confirmed`|
|`core/logging\\\\\\\_setup.py`|滚动文件日志|`confirmed`|
|`core/models/project.py`|`Project` 模型|`confirmed`|
|`core/models/scope.py`|`ScopeAsset` 模型|`confirmed`|
|`database/schema.py`|v1 七表、v2 三表、后续迁移|`confirmed`|
|`database/connection.py`|连接、事务、迁移、备份|`confirmed`|

### 5.2 Phase 2 功能

|文件|作用|历史证据强度|
|-|-|-|
|`services/project\\\\\\\_service.py`|项目 CRUD、搜索、活动项目|`confirmed`（当前 + 验收）|
|`services/authorization\\\\\\\_service.py`|授权 CRUD、状态、历史、过期|`confirmed`|
|`services/scope\\\\\\\_asset\\\\\\\_service.py`|ScopeAsset CRUD、授权绑定|`confirmed`|
|`services/audit\\\\\\\_service.py`|SQLite + JSONL 审计|`confirmed`（报告/架构）|
|`security/scope\\\\\\\_rules.py`|规范化、精确匹配、DNS 快照|`confirmed`（架构/测试）|
|`security/scope\\\\\\\_validator.py`|fail-closed 范围校验|`confirmed`|
|`ui/project\\\\\\\_page.py`|4 子页 + 3 对话框|`confirmed`|
|`ui/main\\\\\\\_window.py`|10 页导航与当前项目选择器|`confirmed`|
|`ui/app\\\\\\\_state.py`|活动项目状态|`confirmed`（报告/测试）|

`inferred`：Phase 1 和 Phase 2 各自“首次创建”了上述哪些文件。没有 Git，无法把文件归属精确到阶段；只能确认它们在 Phase 2 验收时存在。

## 6\. 测试结果与验收情况

|对象|结果|证据|
|-|-|-|
|Phase 1 独立 pytest|`unknown`，未找到独立记录|无 Phase 1 测试报告|
|Phase 1 启动/导航/关闭验收|PASS（offscreen，原生窗口截图受限）|`ACCEPTANCE\\\\\\\_REPORT.md:108-150`|
|Phase 2 初始快照 pytest|37 passed / 0 failed / 0 skipped，5.65s|初始 zip 内 `docs/TEST\\\\\\\_REPORT.md`|
|Phase 2 最终 pytest|40 passed / 0 failed / 0 skipped，6.14s|`docs/TEST\\\\\\\_REPORT.md:15-18,40-47`|
|Phase 2 业务验收|31 passed / 0 failed|`phase2\\\\\\\_acceptance.json:5-7`|
|Phase 2 数据库验收|schema 2，10 表，0 外键违规|`acceptance.db` 只读查询；`ACCEPTANCE\\\\\\\_REPORT.md:180-189`|
|Phase 1/2 最终验收|通过（Phase 1 有原生窗口截图限制）|`ACCEPTANCE\\\\\\\_REPORT.md:10-18,325-359`|
|真实远程目标|0|`ACCEPTANCE\\\\\\\_REPORT.md:7,58-67`；`TEST\\\\\\\_REPORT.md:18`|

本次没有重新执行 pytest，以遵守“只读历史调查”要求；以上为历史记录，不是本次新跑结果。当前测试框架仍为 pytest 9.2.0 + pytest-qt 4.5.0，但本次不声称当前测试结果。

## 7\. 历史证据索引

本次实际读取/检查 **34 个文件**（含 2 个 ZIP 归档按 1 个文件计、3 个 SQLite 数据库只读查询）。清单如下：

### 文档与报告

1. `README.md`
2. `docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md`
3. `docs/PHASE2\\\\\\\_CHANGES.md`
4. `docs/TEST\\\\\\\_REPORT.md`
5. `docs/ARCHITECTURE.md`
6. `docs/acceptance/phase2\\\\\\\_acceptance.json`
7. `docs/acceptance/entrypoint\\\\\\\_acceptance.json`
8. `docs/acceptance/ui\\\\\\\_acceptance.json`
9. `docs/acceptance/project\\\\\\\_tree.txt`

### 源码与配置

10. `main.py`
11. `app/\\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py`
12. `app/application.py`
13. `app/config.py`
14. `app/bootstrap.py`
15. `core/logging\\\\\\\_setup.py`
16. `core/errors.py`
17. `core/models/project.py`
18. `core/models/scope.py`
19. `database/schema.py`
20. `database/connection.py`
21. `services/project\\\\\\\_service.py`
22. `services/authorization\\\\\\\_service.py`
23. `services/scope\\\\\\\_asset\\\\\\\_service.py`
24. `security/scope\\\\\\\_validator.py`
25. `ui/project\\\\\\\_page.py`
26. `ui/main\\\\\\\_window.py`
27. `requirements.txt`
28. `pytest.ini`
29. `config.yaml`

### 历史归档

30. `backups/src-research-assistant\\\\\\\_phase2\\\\\\\_20261104T145255Z.zip`
31. `backups/src-research-assistant\\\\\\\_acceptance\\\\\\\_final.zip`

### 数据库

32. `storage/backups/src\\\\\\\_research\\\\\\\_v1\\\\\\\_20261104T143150Z.db`
33. `storage/backups/src\\\\\\\_research\\\\\\\_v2\\\\\\\_20261105T020152Z.db`
34. `storage/acceptance/acceptance.db`

### 关键路径和行号

* Phase 1 验收：`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:20-150,327-341`
* Phase 2 验收：`docs/acceptance/ACCEPTANCE\\\\\\\_REPORT.md:152-251,343-359`
* 测试：`docs/TEST\\\\\\\_REPORT.md:9-58`
* 架构：`docs/ARCHITECTURE.md:10-18,38-48,80,123-157`
* 起点说明：`README.md:9-18`、`docs/PHASE2\\\\\\\_CHANGES.md:3-9`
* 版本：`app/\\\\\\\_\\\\\\\_init\\\\\\\_\\\\\\\_.py:3`、`config.yaml:4`
* 入口：`main.py:3-6`、`app/application.py:60-98`
* 配置：`app/config.py:43-142`
* 日志：`core/logging\\\\\\\_setup.py:10-27`
* 数据库：`database/schema.py:14-162`、`database/connection.py:88-113`
* 项目服务：`services/project\\\\\\\_service.py:78-193,196-219,230-264`
* 授权服务：`services/authorization\\\\\\\_service.py:135-324`
* 资产服务：`services/scope\\\\\\\_asset\\\\\\\_service.py:96-294`
* 范围校验：`security/scope\\\\\\\_validator.py:142-437`
* GUI：`ui/project\\\\\\\_page.py:551-592`、`ui/main\\\\\\\_window.py:108-119`

## 8\. 无法确认的信息、冲突与限制

### 8.1 `unknown`

1. Phase 1 的精确开发起止时间、任务拆分、提交顺序；没有 Git。
2. Phase 1 的独立文件清单、独立源码快照、独立测试报告/测试数量。
3. Phase 1 的独立版本号（不能从 Phase 2 的 0.2.0 反推）。
4. Phase 1 每张表是否在“Phase 1 当时”真实初始化并写入过；只有代码/合并报告，没有有效 v1 数据库快照。
5. Phase 1 和 Phase 2 各文件的具体创建时间；当前文件已被后续阶段修改。
6. Phase 1 的原始任务需求文本；只找到合并验收报告，没有 `PHASE1\\\\\\\_\\\\\\\*` 需求/总结文件。
7. 项目完整文件总数：部分测试临时目录因 Windows/DSH 权限无法遍历；本次只报告实际检查的 34 个文件。

### 8.2 `contradicted`

1. **Phase 2 测试数量 37 vs 40**

   * 初始 Phase 2 快照：37 passed，5.65s，无 `tests/test\\\\\\\_ui\\\\\\\_dialogs.py`；
   * 最终验收快照：40 passed，6.14s，新增 3 个对话框测试；
   * 当前文档：40。
   * 处理：分别记录时点，最终验收采用 40；不把 37 说成最终结果，也不把 40 说成初始快照。
2. **`src\\\\\\\_research\\\\\\\_v1\\\\\\\_...db` 文件名 vs 实际内容**

   * 文件名暗示 v1 快照；
   * 只读检查：`user\\\\\\\_version=0`、无业务表、约 4 KB；
   * 处理：不把它作为 Phase 1 数据库证据；Phase 1 schema 以 `SCHEMA\\\\\\\_V1` 和合并验收报告为准。
3. **“第一阶段通过” vs “没有第一阶段代码库”**

   * 不是同一层面的矛盾：前者是合并验收报告对基础框架的验收结论；后者是开发起点的真实状态。
   * 处理：`confirmed` 两者均成立；不能把“Phase 1 通过”误解为“曾经存在独立的 Phase 1 Git/源码历史”。

### 8.3 环境限制

* 本次没有 Git 仓库，无法恢复提交历史。
* 当前目录包含后续阶段文件；不能把当前每个文件的每一行都当作 Phase 1/2 原样代码。
* `pytest-of-lenovo`、`storage/tmpv2ziyrtj`、`storage/\\\\\\\_c1\\\\\\\_pytest\\\\\\\_tmp/...`、`tmpcde5t8kh` 等目录存在 Windows ACL 访问限制；本次没有修改权限，也没有删除这些目录。
* `ACCEPTANCE\\\\\\\_REPORT.md` 和 `project\\\\\\\_tree.txt` 是当前工作区中的合并/后续版本，不能单独作为 Phase 1 快照；本报告同时标注了其使用边界。

## 9\. 当前结论

1. **Phase 1 = 已被验收的基础框架，但不是独立保留下来的历史代码库。** `confirmed`

   * 有合并验收报告，确认入口、10 页、7 表、配置/日志、启动/关闭；
   * 没有 Phase 1 独立源码/数据库/测试快照；
   * 独立测试数量和精确文件创建时间无法确认。
2. **Phase 2 = 实际完成的项目管理、授权、ScopeAsset、范围校验、GUI 和 v2 数据库阶段。** `confirmed`

   * 项目 CRUD、授权四种状态、精确范围、本地资产、审计、跨项目隔离均有代码、测试和 31/31 业务验收；
   * 最终 40 pytest 全通过，0 失败；
   * 初始 37 与最终 40 的差异已定位为对话框测试增量。
3. **Phase 2 没有 Repository 层。** `confirmed`

   * SQL 在 Service 中；
   * 当前 `repositories/` 是后续阶段的代码，不属于 Phase 2。
4. **历史证据的可靠性**：

   * 最高：最终验收 zip + `phase2\\\\\\\_acceptance.json` + `acceptance.db` + 当前源码中未改变的接口；
   * 中等：合并验收报告和架构文档（经过整理）；
   * 最低：Phase 1 的逐文件归属、Phase 1 测试计数、v1 数据库“已生成”结论。
5. **本步骤只完成 Phase 1/2 历史重建**，未调查 Phase 3 及以后阶段的实现，也没有修改任何生产代码、测试、数据库、依赖、历史验收报告或 Manifest。

## 10\. 只读遵守声明

* 新增文件：仅 `docs/PROJECT\\\\\\\_HISTORY\\\\\\\_STEP1.md`；
* 生产代码修改：否；
* 测试代码修改：否；
* 数据库修改：否（3 个 SQLite 均以 `mode=ro` 只读查询）；
* Schema 修改：否；
* 依赖修改/安装：否；
* 历史验收报告修改：否；
* Manifest 修改：否；
* 删除或创建其他项目文件：否；
* 未执行 pytest，未生成新的测试结果。

## 11\. 停止状态

```text
PROJECT\\\\\\\_HISTORY\\\\\\\_STEP1 = completed
PHASE1\\\\\\\_HISTORY = reconstructed\\\\\\\_with\\\\\\\_gaps
PHASE2\\\\\\\_HISTORY = confirmed
PHASE3\\\\\\\_PLUS\\\\\\\_INVESTIGATION = not\\\\\\\_started
NEXT\\\\\\\_STEP = wait\\\\\\\_for\\\\\\\_user\\\\\\\_review
```

