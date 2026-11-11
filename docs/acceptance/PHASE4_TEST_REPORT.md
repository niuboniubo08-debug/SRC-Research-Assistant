# 第四阶段测试报告：Python 依赖漏洞审计

## 1. 执行信息

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-11-05（Asia/Shanghai） |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| Python | 3.14.4 |
| PySide6 | 6.12.0 |
| SQLite | 3.50.4 |
| pip-audit | 2.10.1（实际安装并运行） |
| schema | v4 |
| 测试命令 | `python -m pytest -q -p no:cacheprovider` |
| **最终结果** | **105 passed / 0 failed / 0 skipped** |
| 耗时 | 25.16 s |
| 真实远程目标 | 0 个 |

## 2. 开发前基线

实际执行：

```text
81 passed in 19.36s
```

基线状态：

- schema v3；
- 已有统一 `BaseScanner`、Bandit、Semgrep、`ScanService`；
- 已有 `ScanTask` / `Finding`；
- 已有项目/任务隔离；
- 没有 pip-audit；
- `DependencyPage` 仍是明确占位页。

## 3. 测试结果

```text
........................................................................ [ 68%]
.................................                                        [100%]
105 passed in 25.16s
```

| 测试文件 | 数量 | 主要覆盖 |
|---|---:|---|
| `test_database.py` | 5 | v4 字段、v2→v3→v4 迁移与备份 |
| `test_project_service.py` | 7 | 既有项目回归 |
| `test_authorization_service.py` | 8 | 既有授权回归 |
| `test_scope_validator.py` | 16 | 既有范围回归 |
| `test_ui.py` | 2 | 10 页主窗口回归 |
| `test_ui_dialogs.py` | 3 | 既有 Qt 对话框回归 |
| `test_local_path_audit.py` | 7 | 本地路径权限/目录/遍历 |
| `test_finding_models.py` | 3 | 统一 Finding 风险/置信度 |
| `test_process_runner.py` | 3 | 超时、取消、无 shell |
| `test_bandit_scanner.py` | 7 | 既有 Bandit 回归 |
| `test_semgrep_scanner.py` | 6 | 既有 Semgrep 解析回归 |
| `test_scan_service.py` | 13 | 既有源码扫描任务回归 |
| `test_pip_audit_scanner.py` | 8 | pip-audit 可用性、JSON、去重、失败、超时、取消、真实可用性 |
| `test_dependency_audit_service.py` | 15 | 文件识别、pyproject、任务状态、空结果、零依赖、隔离、元数据 |
| `test_ui_source_audit.py` | 1 | 既有源码审计 UI 回归 |
| `test_ui_dependency_audit.py` | 1 | 依赖审计页面端到端（模拟扫描器） |
| **合计** | **105** | |

## 4. 需求覆盖

| 要求 | 结果 |
|---|---|
| requirements.txt 识别 | PASS |
| pyproject.toml 识别 | PASS（PEP 621） |
| 两者同时存在优先级 | PASS（requirements 优先） |
| 无依赖文件 | PASS（无任务、UI 明确提示） |
| pip-audit 可用性检查 | PASS（真实 2.10.1） |
| JSON 解析 | PASS |
| 漏洞发现 | PASS（真实 19 个唯一漏洞） |
| 空结果 | PASS（safe `six==1.16.0` 真实 0 Finding） |
| 工具执行失败 | PASS（模拟退出码） |
| 超时 | PASS（进程执行器与服务测试） |
| 取消任务 | PASS（cancelled，不是 completed） |
| Finding 转换 | PASS |
| Finding 元数据 | PASS（数据库 metadata_json 回读） |
| ScanTask 状态变化 | PASS |
| 项目数据隔离 | PASS |
| 数据库存储 | PASS |
| UI 显示依赖/版本/漏洞/修复建议 | PASS |
| 无结果不等于失败 | PASS（有审计依赖且 0 Finding） |
| 未审计到任何依赖 | PASS（failed，不伪造成功） |
| 不访问远程目标 | PASS（只调用 pip-audit 公开漏洞服务） |

## 5. 实际工具验证

pip-audit：

```text
pip-audit 2.10.1
```

真实依赖项目：

| 项目 | 输入 | 审计依赖 | 唯一漏洞 | 状态 |
|---|---|---:|---:|---|
| requirements 项目 | `requests==2.19.0` | 5 | 19 | completed |
| pyproject 项目 | PEP 621 `dependencies` | 5 | 19 | completed |
| safe 项目 | `six==1.16.0` | 1 | 0 | completed |

pyproject 输入由服务在项目自有临时目录转换为 requirements，任务结束后临时目录清理。

数据库核验：

```text
schema_version=4
projects=3
scan_tasks=3（dependency_audit）
findings=38
foreign_key_violations=0
```

每条 Finding 的 `metadata_json` 均非空，包含依赖名、当前版本、漏洞编号、别名、修复版本、来源与依赖文件。

## 6. 代码质量

```text
EMPTY_FUNCTIONS=0
PASS_STATEMENTS=16 (11 ExceptHandler + 5 exception classes, OUTSIDE=0)
TODO=0
UI_SCANNER_IMPORTS=0
UI_SQL_STATEMENTS=0
SUSPICIOUS_CONFIRMED_ALLOW=0
```

## 7. 验收中发现并修复的问题

1. `DependencyAuditService._requirements_line_map` 调用静态名称规范化函数时漏写类名，触发 `NameError`；修复后真实 pip-audit 首次数据入库成功。
2. 依赖结果映射/保存阶段异常没有终止任务，可能留下 `running`；增加结果保存异常分支，统一更新为 `failed`。
3. 依赖审计 UI 忘记调用 `QTableWidget.insertRow`，导致任务完成但表格 0 行；修复后真实 19 行显示。
4. 本机 pip-audit 默认缓存父目录不存在导致启动失败；应用改为项目自有 `--cache-dir` 和 `TMP/TEMP`。
5. 初步使用 `packaging==26.3` 时 pip-audit 未审计到任何依赖（0 audited）。该状态不能等价于“无漏洞”，已改为 `failed`；改用实际审计到 1 个依赖且无漏洞的 `six==1.16.0` 验证空结果。
6. 初版 UI 列宽造成工具列截断，已调整固定列和修复建议伸缩列。

最终失败测试为 0。

## 8. 限制

- pip-audit JSON 不返回 CVSS/severity，应用保守使用 medium 并保留 `severity_source`。
- pip-audit JSON 不提供精确 affected range；元数据记录命中版本和公告提示。
- 网络依赖公开漏洞服务；离线模式未实现。
- pyproject 仅支持 PEP 621 `[project].dependencies`。
- Semgrep 的 Windows 运行时验证仍待后续补做，不影响第四阶段。
