# 第三阶段测试报告（本地 Python 源代码审计）

## 1. 真实执行信息

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-11-05（Asia/Shanghai） |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| Python | 3.14.4 |
| PySide6 | 6.12.0 |
| SQLite | 3.50.4 |
| Bandit | 1.9.4（实际安装并可运行） |
| Semgrep | 1.183.0（已安装，当前环境运行失败） |
| 数据库 schema | v3 |
| 测试命令 | `python -m pytest -q -p no:cacheprovider` |
| **最终结果** | **81 passed / 0 failed / 0 skipped** |
| 耗时 | 16.74 s |
| 真实远程目标 | 0 个 |

## 2. 开发前基线

实际执行基线：

```text
40 passed in 6.71s
```

基线事实：

- schema 为 v2，主库 10 张表；
- 已有 `check_local_path`，签名为 `check_local_path(project_id, path, operation="local_audit", *, at=None)`，返回 `AccessDecision`；
- 没有 `ScanService`、扫描任务模型、扫描结果 Repository 或 Python Finding 模型；
- `findings` / `scan_tasks` 只有基础占位字段；
- Bandit 和 Semgrep 都未安装；
- 主窗口实际启动/10 页切换/关闭通过。

## 3. 依赖与工具状态

| 工具 | 安装结果 | 实际运行 |
|---|---|---|
| Bandit 1.9.4 | pip 安装成功 | `python -m bandit --version` 成功 |
| Semgrep 1.183.0 | pip wheel 安装成功 | `semgrep --version` 退出码 2 |

Semgrep 实际错误：

```text
Fatal error: exception Failure: ca_certs_iter_on_anchors: CertOpenSystemStore returned NULL
```

这是当前 Windows 会话中 Semgrep 原生二进制在证书存储初始化阶段失败，不是测试伪造，也不是程序捕获后忽略。应用将其标记为不可用，不产生任何 Semgrep Finding。

## 4. 测试结果

```text
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 16.74s
```

| 测试文件 | 数量 | 主要覆盖 |
|---|---:|---|
| `tests/test_database.py` | 5 | schema、v2→v3 迁移、备份、外键 |
| `tests/test_project_service.py` | 7 | 既有项目回归 |
| `tests/test_authorization_service.py` | 8 | 既有授权回归 |
| `tests/test_scope_validator.py` | 16 | 既有远程范围回归 |
| `tests/test_ui.py` | 2 | 既有主窗口回归 |
| `tests/test_ui_dialogs.py` | 3 | 既有 Qt 对话框回归 |
| `tests/test_local_path_audit.py` | 7 | 本地路径存在/目录/权限/遍历/非法路径/复用/审计 |
| `tests/test_finding_models.py` | 3 | Finding 字段、风险映射、置信度映射 |
| `tests/test_process_runner.py` | 3 | 参数列表、超时、取消 |
| `tests/test_bandit_scanner.py` | 7 | Bandit 解析、空结果、错误、不可用、超时、真实扫描、数据库 |
| `tests/test_semgrep_scanner.py` | 6 | 本地规则结构、解析、空结果、异常、不可用 |
| `tests/test_scan_service.py` | 13 | 状态机、空结果、失败、超时、取消、隔离、筛选、路径拒绝 |
| `tests/test_ui_source_audit.py` | 1 | 源代码审计页面真实 Bandit 扫描、筛选、详情 |
| **合计** | **81** | |

## 5. 需求覆盖矩阵

| 用户要求 | 实现与测试 | 结果 |
|---|---|---|
| 复用 `check_local_path` | ScanService 调用现有 ScopeValidator；7 个路径测试 | PASS |
| 路径存在 | `local_path_not_found`；真实测试 | PASS |
| 路径是目录 | `local_path_not_directory`；真实测试 | PASS |
| 权限不足 | `os.access(R_OK)` + `local_path_permission_denied`；测试覆盖 | PASS |
| 防路径遍历 | 规范化后与登记资产精确匹配；`..` 测试 | PASS |
| 统一扫描器接口 | `scanners/base.py` `BaseScanner` | PASS |
| name/version/availability/scan/parse/error | 接口与 Bandit/Semgrep 实现 | PASS |
| 扫描器不直接操作 UI | 静态扫描 UI 对 scanners 导入为 0 | PASS |
| UI 不直接调用扫描器 | UI 只调用 `ScanService` | PASS |
| 禁止 `shell=True` | `process_runner.py` 使用参数列表和 `Popen(shell=False)` | PASS |
| 超时 | 进程执行器 + ScanService 测试 | PASS |
| 统一 Finding 字段 | `core/models/finding.py` + v3 表字段 | PASS |
| 风险等级映射 | Bandit/Semgrep 映射测试 | PASS |
| Bandit JSON | 真实扫描与 fixture 解析 | PASS |
| Bandit 未安装 | 模拟 find_spec 缺失测试 | PASS |
| Bandit 执行失败 | 模拟退出码异常 + 真实错误路径 | PASS |
| Bandit JSON 解析失败 | `ScannerParseError` 测试 | PASS |
| 非法/不存在路径 | 路径测试 + ScanService 不创建任务 | PASS |
| 用户取消 | 进程取消测试 + 任务 cancelled 测试 | PASS |
| 扫描超时 | 进程超时 + 任务 failed 测试 | PASS |
| 不伪造扫描成功 | Semgrep 不可用直接 failed，无 Finding | PASS |
| Semgrep 本地规则 | `scanners/rules/python_security.yml`，YAML 结构测试 | PASS |
| Semgrep JSON | fixture 解析测试 | PASS |
| Semgrep 当前不可用 | UI/Service 显示真实 CA 错误，任务 failed | PASS（不可用状态真实） |
| ScanTask 状态 | pending/running/completed/failed/cancelled | PASS |
| 无结果不等于失败 | `test_empty_scan_result_is_completed` | PASS |
| 取消不标记 completed | `test_cancellation_is_not_completed` | PASS |
| 结果保存 | 真实 Bandit 结果写入 findings，字段回读 | PASS |
| 项目数据隔离 | 任务/结果查询隔离测试 | PASS |
| 源代码审计页面 | 实际 Bandit 扫描、结果表格、风险/扫描器筛选、详情 | PASS |

## 6. 静态检查结果

```text
PRODUCT_FILES=51
EMPTY_FUNCTIONS=0
PASS_STATEMENTS=14
EXCEPT_HANDLERS=9
EXCEPTION_CLASSES=5
OUTSIDE=0
TODO=0
UI_SCANNER_IMPORTS=0
UI_SQL_STATEMENTS=0
SUSPICIOUS_CONFIRMED_ALLOW=0
```

- 5 个类级 pass 全部是明确的异常类型定义；
- 9 个 pass 全部在异常处理/回滚分支；
- 没有空函数、TODO 冒充完成或 UI SQL；
- 扫描器没有导入 UI；
- 唯一 `sqlite3.connect` 仍在 `database/connection.py`；
- Finding 敏感值测试：Bandit 原始 `B105` 值 `phase3-acceptance-secret` 未出现在统一结果中。

## 7. 发现并修复的开发问题

1. `ScanService` 两个提前终止分支向 `_finalize` 多传了一个参数，测试实际捕获 `TypeError`；修正后取消/无可用扫描器测试通过。
2. 进度回调测试发现最后一个进度为单扫描器的 90%，不是 100%；UI 以任务最终进度 100% 展示，测试改为验证回调过程与任务终态。
3. Semgrep 安装后无法运行，按要求改为真实不可用状态，不进行任何结果伪造。

最终没有失败或跳过测试。

## 8. 测试限制

- Semgrep 规则只做了 YAML 结构/解析测试，无法在本机用 Semgrep CLI 做规则运行时校验。
- 扫描 UI 截图使用 offscreen Qt（自动化会话无原生窗口句柄），但运行的是真实生产入口和真实控件。
- 未进行真实互联网目标测试。
