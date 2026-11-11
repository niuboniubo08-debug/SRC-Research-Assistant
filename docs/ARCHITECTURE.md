# SRC Research Assistant 架构说明（第二阶段）

> 第三阶段新增本地扫描器、扫描任务和统一 Finding 架构，见
> [PHASE3_ARCHITECTURE.md](PHASE3_ARCHITECTURE.md)。
> 第四阶段新增 pip-audit 依赖文件发现、依赖审计服务和 metadata 字段，见
> [PHASE4_ARCHITECTURE.md](PHASE4_ARCHITECTURE.md)。
> 第五阶段新增漏洞/证据 Repository、工作流状态、状态历史和受控证据文件，见
> [PHASE5_ARCHITECTURE.md](PHASE5_ARCHITECTURE.md)。本文保留第二阶段历史架构。

## 1. 现状与阶段边界

接手时的 `D:\挖漏洞` 没有第一阶段项目文件，因此本次实际交付为：

1. 补齐可运行的第一阶段基础框架（配置、数据库、主窗口、十页导航、占位状态）；
2. 在其上完成第二阶段项目管理、授权管理、授权资产和后端范围校验；
3. 不实现任何扫描器、网络检测、漏洞利用或报告导出。

当前运行版本 `0.2.0`，schema `v2`。任何“扫描器 / 依赖漏洞 / 远程检查 / 报告”页面都明确标记未开发，避免把占位功能伪装为已完成功能。

## 2. 分层架构

```text
┌────────────────────────────────────────────────────────────┐
│ Presentation (PySide6)                                     │
│ main_window / dashboard / project_page / history / ...     │
│ 只负责展示、表单体验和调用服务；不能作为安全边界            │
└──────────────────────────────┬─────────────────────────────┘
                               │ AppContext + AppState
┌──────────────────────────────▼─────────────────────────────┐
│ Application composition                                    │
│ app.config     类型化 YAML 配置，强制 deny-by-default       │
│ app.bootstrap  Database + Audit + Services 组合根           │
│ app.application Qt 生命周期、异常处理、CLI                  │
└───────────────┬──────────────────────────────┬─────────────┘
                │                              │
┌───────────────▼──────────────┐  ┌────────────▼─────────────┐
│ Services                     │  │ Security                 │
│ ProjectService               │  │ scope_rules（纯函数）     │
│ AuthorizationService         │  │ ScopeValidator（fail closed）│
│ ScopeAssetService            │  │ 精确匹配 / 时间窗口 / DNS  │
│ AuditLogService              │  │ 重定向辅助校验             │
└───────────────┬──────────────┘  └────────────┬─────────────┘
                │                              │
┌───────────────▼──────────────────────────────▼─────────────┐
│ Core / Persistence                                         │
│ core.models  core.errors  core.timeutil                    │
│ database.connection（短连接 + 外键 + IMMEDIATE 事务）       │
│ database.schema（v1 七表 → v2 范围/历史/设置）              │
└────────────────────────────────────────────────────────────┘
```

### 依赖方向

```text
main
 └─ app.application
     └─ app.bootstrap
         ├─ app.config
         ├─ database.connection ── database.schema
         ├─ services.audit_service
         ├─ services.project_service
         ├─ services.authorization_service
         ├─ services.scope_asset_service
         │    ├─ security.scope_rules
         │    └─ services.authorization_service
         └─ security.scope_validator
              ├─ security.scope_rules
              ├─ services.audit_service
              └─ database.connection

ui.main_window
 ├─ ui.* pages
 ├─ ui.app_state
 ├─ app.bootstrap.AppContext
 └─ core.models / core.errors

services / security / database 不导入 ui。
```

关键设计：`ui` 不直接写 SQL，也不自己判断授权是否有效。UI 只调用服务并显示结果，因此隐藏按钮不能绕过安全控制。

## 3. 模块职责

| 模块 | 职责 |
|---|---|
| `app/config.py` | 解析、校验 `config.yaml`；拒绝非 `deny` 的默认远程策略；解析存储路径 |
| `app/bootstrap.py` | 构造数据库、审计和全部服务；组合根；注入可测试时钟 |
| `app/application.py` | 参数解析、数据库初始化、Qt 应用启动、全局异常 |
| `database/connection.py` | 连接统一管理、外键、WAL、事务、迁移前备份、健康检查 |
| `database/schema.py` | v1 七表与 v2 增量 schema |
| `core/models` | 不可变 dataclass：Project / Authorization / ScopeAsset / 历史 / ScanLog |
| `core/timeutil.py` | 强制 aware UTC；数据库时间格式化；本地展示 |
| `core/errors.py` | 可预期业务异常与 `AuthorizationDenied` |
| `security/scope_rules.py` | 纯函数：域名/IP/本地路径规范化、操作白名单、DNS 快照校验 |
| `security/scope_validator.py` | 远程/本地范围判定、审计、fail-closed |
| `services/project_service.py` | 项目 CRUD、搜索筛选排序、活动项目 |
| `services/authorization_service.py` | 授权 CRUD、有效窗口、撤销终态、到期持久化、变更历史 |
| `services/scope_asset_service.py` | 资产 CRUD、远程授权绑定、本地/远程隔离 |
| `services/audit_service.py` | SQLite + JSONL 双写审计，写失败抛出错误 |
| `ui/project_page.py` | 项目列表、详情、授权、资产四个子页和表单校验 |
| `ui/history_page.py` | 审计记录只读查询 |
| `ui/settings_page.py` | 运行环境、存储路径、安全策略只读展示 |

## 4. 数据模型

```text
projects 1 ─── N authorizations
    │ 1                 │ 1
    │                   │
    ├── N scan_tasks    └── N scope_assets  (远程资产必须绑定有效授权)
    ├── N findings
    ├── N evidence
    ├── N reports
    ├── N scan_logs             (项目删除后 project_id ⇒ NULL，日志保留)
    └── N authorization_history (项目删除级联)

scope_assets.authorization_id ──N:1── authorizations
authorization_history.authorization_id ──N:1── authorizations (授权删除后 ⇒ NULL)
```

### 表结构

#### phase 1 基础七表

| 表 | 关键内容 |
|---|---|
| `projects` | 名称、类型、路径、状态、创建/更新时间；状态和类型 CHECK |
| `authorizations` | 来源、文件、起止时间、状态、项目外键、时间窗口 CHECK |
| `scan_tasks` | 扫描任务占位模型（当前不创建任务） |
| `findings` | 漏洞条目占位模型（当前不写入） |
| `evidence` | 证据元数据占位模型（当前不写入） |
| `reports` | 报告元数据占位模型（当前不写入） |
| `scan_logs` | 审计日志：事件、目标、操作、allow/deny、JSON 详情 |

#### phase 2 增量三表

| 表 | 关键内容 |
|---|---|
| `scope_assets` | 类型、规范化值、授权外键、操作白名单、启用状态；`UNIQUE(project_id, asset_type, asset_value)` |
| `authorization_history` | 变更动作、摘要、before/after JSON、项目与授权关联 |
| `app_settings` | 当前活动项目等键值设置 |

### 索引

- `projects(status, created_at DESC)`
- `authorizations(project_id, authorization_status, end_time)`
- `scope_assets(project_id, asset_status, asset_type)`
- `scope_assets(authorization_id)`
- `authorization_history(project_id, created_at DESC)` / `(authorization_id, created_at DESC)`
- `scan_logs(project_id, created_at DESC)` / `(event_type, created_at DESC)`

### 迁移安全

- 每条连接 `PRAGMA foreign_keys = ON`，不依赖 SQLite 默认关闭状态。
- 版本从 1 → 2 前复制 `storage/backups/<db>_v1_<UTC>.db`。
- 数据库版本高于程序支持版本时拒绝启动，不进行降级。
- 迁移 SQL 使用 `CREATE TABLE IF NOT EXISTS`，失败则事务/连接关闭并返回明确错误。

## 5. 授权状态机

```text
              审核通过（已确认 + 有效来源/文件）
  pending ─────────────────────────────────────► confirmed
     │                                              │
     │                                              ├── 到达 end_time ──► expired
     │                                              └── 用户撤销 ───────► revoked
     │
     └── 用户撤销 ─────────────────────────────────► revoked
```

- `pending`、`expired`、`revoked` 均不能支撑远程检测，即使资产绑定关系存在。
- `revoked` 是终态：后端禁止修改；重新授权必须新增记录并留下历史。
- “已确认”还要求 `authorization_source` 与 `authorization_document` 非空。
- `ScopeValidator` 还会实时比较当前时间与起止时间，不依赖过期字段已经被刷新。

## 6. 远程授权检查调用链（后续扫描器必须复用）

```text
Scanner / future network checker
        │
        │ require_remote_access(project_id, target, operation, resolved_ips=...)
        ▼
ScopeValidator
  1. 项目存在？                         否 → deny + audit
  2. 操作在 RemoteOperation 白名单？     否 → deny + audit
  3. 目标是精确域名/IP（拒绝 URL/通配）？ 否 → deny + audit
  4. scope_assets 中精确命中且启用？     否 → deny + audit
  5. 绑定 authorization_id？            否 → deny + audit
  6. 授权属于当前项目？                  否 → deny + audit
  7. 状态 = confirmed 且来源/文件齐全？  否 → deny + audit
  8. start_time ≤ now ≤ end_time？      否 → deny + audit
  9. operation ∈ allowed_operations？   否 → deny + audit
 10. 若提供 resolved_ips：
       全部公网、非空、与目标一致？       否 → deny + audit
 11. 写 allow 审计；审计写失败 → deny
        │
        ▼
   返回 AccessDecision(allowed=True)
```

当前项目没有调用任何远程网络 API，因此第 6 节的扫描器尚不存在。这个调用链是第三阶段实现远程配置检查时必须遵守的唯一入口。

### DNS / IP 变化

- `ScopeValidator` 支持传入 DNS 解析快照 `resolved_ips`。
- 快照为空、包含私有/回环/保留/组播地址、或与目标 IP 不一致时拒绝。
- 本阶段不主动解析 DNS，因为本阶段不执行远程检测。后续网络请求必须先解析并把结果交给校验器，禁止先连接再校验或自动扩大范围。

### 重定向

`check_redirect_target(source_url, redirect_url, operation)` 会对来源和目标分别执行完整精确范围检查。项目没有自动跟随重定向的 HTTP 客户端；后续实现也必须逐跳校验，任一目标不在范围立即停止。

## 7. 审计

每次 `check_remote_access` / `check_local_path` 生成一条：

- 数据库：`scan_logs`；
- 文件：`storage/logs/audit.jsonl`，每行一个 JSON 对象；
- 字段：时间、事件、项目、目标、操作、allow/deny、原因、资产 ID、授权 ID、DNS 相关详情；
- 安全语义：审计写入失败时，任何 `allow` 结果都转换为 `deny(audit_unavailable)`。

项目/授权/资产修改也在业务事务内写审计。项目删除后审计保留，`project_id` 置 NULL。

## 8. UI 结构

```text
MainWindow
├── Sidebar：10 个固定导航按钮
├── Header：软件名、当前项目选择器、运行状态
└── QStackedWidget
    ├── DashboardPage：统计、最近项目、安全基线
    ├── ProjectPage：QTabWidget
    │   ├── 项目列表（搜索/筛选/排序/CRUD/当前项目）
    │   ├── 项目详情（字段、授权/资产统计）
    │   ├── 授权管理（CRUD/撤销/有效性提示/变更历史）
    │   └── 授权资产（远程/本地隔离、精确范围、操作白名单）
    ├── SourceAuditPage ... ReportPage：明确未开发占位
    ├── HistoryPage：scan_logs 审计轨迹
    └── SettingsPage：只读环境、存储与安全策略
```

界面仅用于交互，安全决策在服务层重复执行。表格焦点、选中行和筛选状态不参与授权判断。

## 9. 测试策略

- 固定 `MutableClock` 注入服务，验证授权窗口、过期、撤销，不依赖真实时间。
- 每个测试使用临时 SQLite 文件，验证外键和项目隔离。
- ScopeValidator 使用模拟目标与解析快照，不解析真实域名、不发起网络请求。
- UI 使用 offscreen Qt，验证 10 页切换、4 个子页、窗口能力。
- 详细结果见 `docs/TEST_REPORT.md`。

## 10. 下一阶段（建议，不在本阶段实施）

1. 先做本地 Python 源码审计：
   - 调用 `check_local_path`；
   - Bandit + 本地 Semgrep 规则 + 归一化 finding；
   - 扫描任务和结果入库、日志、取消。
2. 再做依赖审计（pip-audit 公开数据）。
3. 最后做远程配置检查：
   - UI 必须展示目标、检测方式、授权状态；
   - 强制 `require_remote_access`，传入 DNS 快照；
   - 禁止自动重定向、禁止 DoS/利用/爆破；
   - 每一步审计。
4. 报告与证据模块；最后再做 EXE 打包。
