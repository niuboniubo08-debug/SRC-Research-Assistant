# 第二阶段测试报告

## 1. 执行信息

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-11-04（Asia/Shanghai） |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| Python | 3.14.4 |
| pytest | 9.2.0 |
| pytest-qt | 4.5.0 |
| PySide6 | 6.12.0 |
| 数据库 | SQLite 3.50.4 |
| Qt 平台 | offscreen |
| 测试命令 | `python -m pytest -q -p no:cacheprovider` |
| **结果** | **40 passed / 0 failed / 0 skipped** |
| 耗时 | 6.14 s |
| 真实远程目标 | 0 个；未发起网络请求 |

本机虚拟环境：`D:\挖漏洞\.venv\Scripts\python.exe`。

## 2. 覆盖矩阵

| 编号 | 验收要求 | 测试位置 | 结果 |
|---|---|---|---|
| 1 | 项目创建 | `test_project_service.py::test_create_project` | PASS |
| 2 | 项目修改 | `test_project_service.py::test_update_project` | PASS |
| 3 | 项目删除 | `test_project_service.py::test_delete_project`、`test_delete_missing_project_raises` | PASS |
| 4 | 授权创建 | `test_authorization_service.py::test_create_authorization` | PASS |
| 5 | 授权过期判断 | `test_expiry_is_checked_and_persisted`、`test_expired_authorization_immediately_denies` | PASS |
| 6 | 授权撤销 | `test_revoke_authorization`、`test_revoked_authorization_immediately_denies` | PASS |
| 7 | 授权范围匹配 | `test_exact_scope_match_allows`、`test_subdomain_is_not_covered_by_parent_domain` | PASS |
| 8 | 未授权目标拒绝 | `test_unauthorized_target_denied`、`test_asset_must_belong_to_same_project` | PASS |
| 9 | 不同项目数据隔离 | `test_cross_project_authorization_cannot_be_modified`、`test_asset_must_belong_to_same_project` | PASS |
| 10 | 数据库异常处理 | `test_database_path_failure_is_wrapped`、`test_foreign_keys_are_enabled_on_every_connection` | PASS |

## 3. 按文件统计

| 测试文件 | 数量 | 覆盖内容 |
|---|---:|---|
| `tests/test_database.py` | 4 | schema 版本、十张表、外键、项目级联、数据库路径异常 |
| `tests/test_project_service.py` | 7 | 项目 CRUD、校验、搜索/筛选/排序、当前项目、跨项目授权隔离 |
| `tests/test_authorization_service.py` | 8 | 授权 CRUD、确认条件、待审核、过期、撤销、历史、删除保护、跨项目隔离 |
| `tests/test_scope_validator.py` | 16 | 精确匹配、子域拒绝、IP 精确、通配符拒绝、过期/撤销/待审核拒绝、操作白名单、DNS、重定向、本地资产、审计、fail-closed、资产更新 |
| `tests/test_ui.py` | 2 | 主窗口启动、10 页切换、4 个子页、窗口最大化/关闭、项目筛选、当前项目切换 |
| `tests/test_ui_dialogs.py` | 3 | 项目/授权/资产对话框真实控件输入、保存、必填校验 |
| **合计** | **40** | |

## 4. 实际执行结果

```text
........................................                                 [100%]
40 passed in 6.14s
```

最终未通过测试：**0**。跳过测试：**0**。

验收期间曾实际发现并修复 1 个产品缺陷：资产对话框构造时缺少 `AssetStatus` 导入，首次真实控件测试报 `NameError`。补齐导入后对话框测试 3/3 通过，全量回归 40/40 通过。另有验收脚本自身漏调用 `window.show()` 导致一次 `visible_after_show=false`，修复脚本后入口启动验收通过，这不是产品缺陷。

## 5. 关键安全测试说明

### 授权过期

- 使用固定时钟 `2030-01-01` 创建有效授权；
- 将时钟推进 31 天；
- 校验器在授权状态仍为 `confirmed` 时仍拒绝（实时窗口检查）；
- 再调用 `expire_overdue_authorizations`，数据库状态变为 `expired` 并写入历史。

### 授权撤销

- 撤销后状态立即变为 `revoked`；
- 校验器的远程检查返回 `authorization_revoked`；
- 已撤销记录禁止修改（`ConflictError`）。

### 精确范围

- `example.com` 授权不会覆盖 `sub.example.com`；
- `*.example.com`、URL、端口、CIDR 均被拒绝；
- `203.0.113.10` 不会覆盖 `.11`；
- 远程资产跨项目绑定被拒绝；
- 本地目录与域名资产不同表内混用被拒绝。

### 授权检查审计

- 每次 allow/deny 都写入 `scan_logs`；
- 同时写入 `audit.jsonl`，测试检查至少两行；
- 模拟审计存储故障时，本来允许的访问转为 `deny / audit_unavailable`。

### UI

- 10 个导航页面全部可切换；
- 项目管理页 4 个子页存在；
- 窗口具备最大化与关闭能力；
- 项目筛选、有效授权显示、当前项目切换行为正确。

## 6. 数据库初始化验证

执行：

```powershell
& 'D:\挖漏洞\.venv\Scripts\python.exe' main.py --init-db
```

实际输出：

```text
数据库: D:\挖漏洞\SRC-Research-Assistant\storage\src_research.db
架构版本: 2
健康状态: SQLite 3.50.4 · 外键 ON
数据表:
  - app_settings
  - authorization_history
  - authorizations
  - evidence
  - findings
  - projects
  - reports
  - scan_logs
  - scan_tasks
  - scope_assets
```

结构检查：

```text
schema_version=2
foreign_key_violations=0
indexes=12
所有表初始行数=0（全新安装，不含演示数据）
```

项目表、授权表、扫描任务表、漏洞表、证据表、报告表、审计日志表、授权资产表、授权历史表和设置表均存在。

## 7. 测试环境说明

DSH 的 Windows workspace-write 沙箱会拦截 pytest/Qt 在系统临时目录创建的 ACL，导致测试在 setup 阶段无法创建临时目录。最终测试在**完整权限**下执行，以排除该执行环境限制。这不是产品代码失败，也没有放宽产品运行时的授权控制。

截图命令为 offscreen Qt；截图使用临时演示数据库，生成后删除。正式应用数据库 `storage/src_research.db` 保持空数据状态。

## 8. 本阶段未测试

以下能力尚未实现，因此没有“通过”或“伪造通过”的测试结果：

- 源代码静态扫描；
- 依赖漏洞审计；
- 远程 HTTPS/响应头检查；
- 漏洞与证据管理；
- HTML/PDF/JSON 报告；
- Windows EXE 打包。

这些必须在后续阶段实现并通过真实测试后，才能从占位状态移除。
