# 第二阶段交付说明

## 0. 前置事实

开始第二阶段前检查发现：`D:\挖漏洞` 中**不存在** `SRC-Research-Assistant` 项目、第一阶段源代码、数据库、主窗口或七张数据表。工作区只有空目录。

因此本阶段没有“既有第一阶段代码”可以直接扩展。为了交付可运行且可验证的第二阶段，先补齐基础框架，再实现项目管理与授权系统。未删除或覆盖任何用户文件。

这项差异已如实记录，而不是声称第一阶段原本已经存在。

## 1. 功能验收

| 要求 | 状态 | 实现 |
|---|---|---|
| 新建项目 | 完成 | `ProjectService.create_project` + `ProjectDialog` |
| 编辑项目 | 完成 | `update_project`，记录变更审计 |
| 删除项目 | 完成 | 事务级联删除，审计保留，活动项目清理 |
| 查看详情 | 完成 | “项目详情”子页、授权/资产计数 |
| 搜索项目 | 完成 | 名称/说明/路径 LIKE 查询 |
| 创建时间排序 | 完成 | 最新/最早切换 |
| 状态筛选 | 完成 | 进行中/暂停/完成/归档 |
| 设置当前项目 | 完成 | `app_settings` 持久化，顶部选择器同步 |
| 项目字段 | 完成 | 题目要求的 8 个字段全部落库 |
| 项目类型 | 完成 | 本地代码审计 / 授权安全测试 / 综合安全研究 |
| 授权记录增改查 | 完成 | 来源、文件、起止、状态、备注 |
| 授权有效性 | 完成 | 状态 + 当前时间 + 来源/文件完整性 |
| 过期检测 | 完成 | 启动持久化过期 + 校验器实时判断 |
| 授权文件路径 | 完成 | 字符串路径保存，确认授权强制非空 |
| 授权变更历史 | 完成 | `authorization_history` + 审计双写 |
| 授权状态四种 | 完成 | pending / confirmed / expired / revoked |
| 不得凭项目名认定授权 | 完成 | 无任何自动确认；确认需来源和文件 |
| 新增 scope_assets | 完成 | v2 迁移新增表 |
| 域名/IP/本地目录/本地项目 | 完成 | 四种类型；本地远程严格分开 |
| 远程资产需有效授权 | 完成 | 服务层写时校验；校验器读时再次校验 |
| 精确范围匹配 | 完成 | 规范化后等值匹配；无后缀匹配 |
| 禁止通配符 | 完成 | 纯函数拒绝 `*`、URL、端口、CIDR |
| 禁止自动跟随未授权重定向 | 设计并测试 | 无 HTTP 客户端；`check_redirect_target` 双端校验 |
| 第三方域名自动入范围 | 不存在 | 没有任何自动发现/加入代码 |
| DNS/IP 变化复核 | 校验 API 完成 | 传入解析快照时拒绝私有地址/空结果/不一致 |
| AuthorizationService | 完成 | `services/authorization_service.py` |
| ScopeValidator | 完成 | `security/scope_validator.py` |
| 过期拒绝远程 | 完成 | 时间窗口实时检查 |
| 撤销立即拒绝 | 完成 | revoked 状态拒绝 |
| 范围外拒绝 | 完成 | 精确资产查询失败即拒绝 |
| 无权限操作拒绝 | 完成 | `allowed_operations` 白名单 |
| 默认拒绝/异常不放行 | 完成 | fail closed + 审计失败转拒绝 |
| 授权检查日志 | 完成 | `scan_logs` + `audit.jsonl` |
| 非前端控件安全 | 完成 | 服务层强制校验，测试直接调用服务 |
| 深色现代界面 | 完成 | 10 页、4 个子页、深色 QSS |
| 表单校验 | 完成 | 前端提示 + 服务端验证 |
| 过期明显提示 | 完成 | 红色行/状态 + 顶部警告 |
| pytest 测试 ≥10 项 | 完成 | 40 项通过 |
| 不进行真实目标测试 | 完成 | 临时数据库 + 模拟目标，无网络调用 |

## 2. 数据库结构变化

### v1（第一阶段基础，补齐）

`projects`、`authorizations`、`scan_tasks`、`findings`、`evidence`、`reports`、`scan_logs`。

### v2（第二阶段新增）

- `scope_assets`
  - `asset_id` PK
  - `project_id` FK → projects，CASCADE
  - `asset_type` CHECK：domain/ip/local_folder/local_project
  - `asset_value` 规范化值
  - `authorization_id` FK → authorizations，RESTRICT
  - `allowed_operations` JSON 数组文本
  - `asset_status` CHECK：active/inactive
  - `notes`、`created_at`、`updated_at`
  - UNIQUE(project_id, asset_type, asset_value)
- `authorization_history`
  - `history_id` PK
  - `project_id` FK CASCADE
  - `authorization_id` FK SET NULL
  - `action`、`change_summary`、`details_json`、`created_at`
- `app_settings`
  - `setting_key` PK、`setting_value`、`updated_at`

迁移前自动备份旧库到 `storage/backups/`。schema 版本写入 `PRAGMA user_version=2`。

## 3. 新增文件清单

```text
main.py
config.yaml
requirements.txt
pytest.ini
README.md
app/
  __init__.py
  config.py
  bootstrap.py
  application.py
core/
  __init__.py
  errors.py
  timeutil.py
  logging_setup.py
  models/
    __init__.py
    enums.py
    project.py
    authorization.py
    scope.py
    system.py
database/
  __init__.py
  schema.py
  connection.py
security/
  __init__.py
  scope_rules.py
  scope_validator.py
services/
  __init__.py
  audit_service.py
  project_service.py
  authorization_service.py
  scope_asset_service.py
scanners/__init__.py
reports/__init__.py
ui/
  __init__.py
  theme.py
  widgets.py
  app_state.py
  main_window.py
  dashboard.py
  project_page.py
  source_audit_page.py
  dependency_page.py
  config_audit_page.py
  vulnerability_page.py
  evidence_page.py
  report_page.py
  history_page.py
  settings_page.py
  placeholder.py
tests/
  __init__.py
  conftest.py
  test_database.py
  test_project_service.py
  test_authorization_service.py
  test_scope_validator.py
  test_ui.py
  test_ui_dialogs.py
tools/
  acceptance_ui.py
  capture_ui.py
  code_quality_check.py
  create_backup.py
  entrypoint_acceptance.py
  generate_project_tree.py
  inspect_db.py
  run_acceptance.py
docs/
  acceptance/
    ACCEPTANCE_REPORT.md
    code_quality.json
    entrypoint_acceptance.json
    entrypoint_runtime.png
    phase2_acceptance.json
    project_tree.txt
    ui_acceptance.json
    ui_runtime.png
  ARCHITECTURE.md
  PHASE2_CHANGES.md
  TEST_REPORT.md
  screenshots/*.png
storage/projects/.gitkeep
storage/evidence/.gitkeep
storage/reports/.gitkeep
storage/logs/.gitkeep
```

**修改文件**：无原有用户文件可修改。上述文件均为本次新建；后续本阶段内部修正见测试报告“已修复问题”。

## 4. 验证结果

- 全量 pytest：40 passed，0 failed。
- 数据库：10 张表，schema v2，外键 ON。
- 界面：主窗口启动、10 页切换、4 个子页、窗口最大化/关闭能力通过。
- 截图：项目列表、授权管理、授权资产、总览四张，使用临时演示数据生成。
- 真实 SRC 目标：0 个，未发起网络请求。

## 5. 已修复问题

1. SQLite `PRAGMA user_version = ?` 不允许参数绑定，导致首次初始化失败；改为受控整数写入。
2. 界面测试使用 2030 年固定时钟，而 UI 使用真实时间，导致实际有效授权显示“未生效”；把注入时钟加入 `AppContext`，并让页面使用同一时钟。
3. 项目/授权表格按内容自适应导致列宽溢出和日期截断；改为固定关键列 + 最后一列拉伸。
4. offscreen Qt 缺少字体导致截图乱码；截图工具显式注册 Windows 字体。
5. Windows DSH 沙箱会阻止 pytest 临时目录 ACL；测试执行时使用完整权限。该问题来自执行环境，不是业务代码缺陷。

## 6. 未通过测试

无。所有自动化测试均实际执行并通过。

## 7. 本阶段明确未开发

- 源代码扫描、依赖审计、远程配置检查；
- 漏洞/证据/报告功能；
- 远程网络请求、漏洞利用、爆破、DoS；
- EXE 打包。

## 8. 下一阶段建议

1. 先做 **本地 Python 源码审计**：`check_local_path` → Bandit → 本地 Semgrep 规则 → 统一 finding 入库 → UI。
2. 再做 **pip-audit 依赖审计**。
3. 最后做远程配置检查：强制 `require_remote_access`、DNS 快照和逐跳重定向校验。
4. 报告/证据与 EXE 打包放到功能稳定后。
