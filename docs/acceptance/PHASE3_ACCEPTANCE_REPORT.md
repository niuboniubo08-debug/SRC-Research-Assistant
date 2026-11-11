# 第三阶段验收报告：本地 Python 源代码安全审计

- 验收日期：2026-11-05（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 版本：`0.3.0`
- 数据库 schema：v3
- 结论：**部分通过**（Bandit、扫描任务、Finding、UI 全部通过；Semgrep 因当前 Windows 会话的真实运行时错误不可用）

## 1. 开发前基线（实际检查）

| 项目 | 实际结果 |
|---|---|
| 原有测试 | **40 passed / 0 failed / 0 skipped**，6.71s |
| 主窗口 | 生产入口启动成功，10 页切换，退出码 0 |
| 数据库 | schema v2，10 张表，外键 ON |
| `check_local_path` | 位于 `security/scope_validator.py`，签名 `check_local_path(project_id, path, operation="local_audit", *, at=None) -> AccessDecision` |
| ScanService | 不存在 |
| 扫描任务模型 / Repository | 不存在；只有 `scan_tasks` 占位表与直接 SQL 服务模式 |
| Finding 模型 | 不存在；只有 `findings` 基础占位表 |
| Bandit | 未安装 |
| Semgrep | 未安装 |

没有在旧项目上做无意义重构；继续沿用 `Database`、Service 层、`ScopeValidator`、`AppContext` 和现有 UI 导航。

## 2. 已完成功能

1. **本地路径校验复用**
   - 继续调用现有 `ScopeValidator.check_local_path`。
   - 仅做必要扩展：不存在路径、非目录、读取权限不足、异常路径均拒绝。
   - 原有精确资产匹配和项目归属校验保持不变。
   - 路径越界 `..` 会被规范化后拒绝。

2. **统一扫描器接口**
   - `scanners/base.py` 定义 `BaseScanner`。
   - 统一 `name`、`display_name`、`version`、`is_available`、`scan(target, options)`、`ScanOutput`、异常类型。
   - 外部工具通过 `scanners/process_runner.py` 以参数列表启动，`shell=False`，有超时、取消和输出上限。
   - UI 不导入 `scanners`，只调用 `ScanService`。

3. **Bandit 集成**
   - 实际安装并运行 Bandit **1.9.4**。
   - JSON 解析为统一 Finding。
   - 处理有结果、空结果、工具缺失、执行失败、JSON 失败、超时、取消、非法路径。
   - 排除 `.venv`、`.git`、`__pycache__` 等目录。
   - Bandit B105/B106/B107 的原始凭据值不会写入统一结果。

4. **Semgrep 集成**
   - 完成 `SemgrepScanner`、本地规则文件 `scanners/rules/python_security.yml`、JSON 解析和统一 Finding。
   - 不访问 Semgrep Registry，不自动下载规则。
   - 真实环境探测结果：Semgrep 1.183.0 已安装，但二进制启动即因
     `ca_certs_iter_on_anchors: CertOpenSystemStore returned NULL` 退出，退出码 2。
   - UI 将其标记为不可用并显示原因；服务层不执行伪造扫描。

5. **统一 Finding**
   - `core/models/finding.py`。
   - 字段：`project_id`、`task_id`、`title`、`category`、`severity`、`confidence`、`description`、`file_path`、`line_number`、`rule_id`、`recommendation`、`scanner_name`、`scanner_version`、`detected_at`。
   - 数据库复用 `findings` 表，新增 v3 字段，不建立重复结果表。

6. **扫描任务**
   - `services/scan_service.py`。
   - `pending → running → completed / failed / cancelled`。
   - 保存目标、开始/结束时间、进度、当前扫描器、错误、汇总、请求的扫描器。
   - 取消不标记 completed；空结果标记 completed；超时/工具失败标记 failed。
   - 每个成功扫描器的 Finding 立即保存；后续失败/取消时已经得到的结果仍保留。
   - 项目和任务双维度查询隔离。

7. **数据库**
   - schema v3 迁移。
   - `scan_tasks` 新增：`current_scanner`、`progress`、`error_message`、`scanners_json`、`cancel_requested`、`cancelled_at`。
   - `findings` 新增：`confidence`、`file_path`、`line_number`、`rule_id`、`scanner_name`、`scanner_version`、`detected_at`。
   - 新增 3 个索引。
   - v2→v3 前自动备份；实际备份：`storage/backups/src_research_v2_20261105T020152Z.db`。

8. **源代码审计 UI**
   - 当前项目、本地路径、路径校验状态。
   - Bandit/Semgrep 可用性、版本、不可用原因。
   - 启用/禁用扫描器、超时、开始、取消。
   - 状态、当前扫描器、进度、错误。
   - 风险、标题、分类、文件、行号、扫描器、置信度表格。
   - 风险等级筛选、扫描器筛选、点击查看说明与修复建议。
   - 后台 `QThread` 执行，主窗口关闭时取消并等待扫描线程。
   - 实际截图：`docs/acceptance/phase3_source_audit.png`。

## 3. 实际扫描验证

实际验收库：`storage/phase3_acceptance/acceptance.db`，schema v3，外键 0 违规。

| 运行 | 结果 | 说明 |
|---|---|---|
| Bandit 扫 unsafe 本地项目 | **completed** | 6 个 Finding：B602、B307、B301、B404、B105、B403；全部来自 `unsafe.py` |
| Bandit 扫 safe 本地项目 | **completed / 0 Finding** | 证明无结果不等于失败 |
| Semgrep-only 扫 unsafe | **failed / 0 Finding** | 真实不可用原因，未伪造成功 |
| Bandit + Semgrep 组合 | **completed** | Bandit 6 个结果；Semgrep 被明确跳过并记录警告 |
| 项目隔离 | PASS | safe 项目 0 Finding；unsafe 项目任务/结果与 safe 隔离 |
| 凭据脱敏 | PASS | `phase3-acceptance-secret` 未出现在 Finding 标题或说明中 |

Semgrep 原始错误：

```text
Semgrep 已安装但当前环境无法运行：Fatal error: exception Failure:
ca_certs_iter_on_anchors: CertOpenSystemStore returned NULL
```

## 4. 测试结果

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
```

```text
........................................................................ [ 88%]
.........                                                                [100%]
81 passed in 16.74s
```

- 总测试数：**81**
- 通过：**81**
- 失败：**0**
- 跳过：**0**

新增测试：

- `test_local_path_audit.py`：7
- `test_finding_models.py`：3
- `test_process_runner.py`：3
- `test_bandit_scanner.py`：7
- `test_semgrep_scanner.py`：6
- `test_scan_service.py`：13
- `test_ui_source_audit.py`：1

覆盖真实 Bandit 扫描、Qt 页面端到端扫描、空结果、失败、超时、取消、路径异常、数据库迁移、数据隔离和敏感值脱敏。

## 5. 代码质量检查

```text
EMPTY_FUNCTIONS=0
PASS_STATEMENTS=14 (9 ExceptHandler + 5 exception classes, OUTSIDE=0)
TODO=0
UI_SCANNER_IMPORTS=0
UI_SQL_STATEMENTS=0
SUSPICIOUS_CONFIRMED_ALLOW=0
sqlite3.connect: 仅 database/connection.py
```

- 空函数伪装：0。
- 大量 pass：14 个，均为异常分支或明确异常类，不是空实现。
- TODO 冒充完成：0。
- UI 直接调用扫描器：0。
- 数据库连接集中：UI 无 SQL，连接只由 `Database` 创建；SQL 仍在既有服务层模式内。
- 硬编码授权状态：没有硬编码 allow；状态来自枚举、数据库和校验器。

## 6. 新增文件

```text
core/models/finding.py
core/models/scan_task.py
scanners/base.py
scanners/process_runner.py
scanners/bandit_scanner.py
scanners/semgrep_scanner.py
scanners/rules/python_security.yml
services/scan_service.py
tests/test_local_path_audit.py
tests/test_finding_models.py
tests/test_process_runner.py
tests/test_bandit_scanner.py
tests/test_semgrep_scanner.py
tests/test_scan_service.py
tests/test_ui_source_audit.py
tools/run_phase3_acceptance.py
tools/capture_phase3_ui.py
docs/acceptance/PHASE3_TEST_REPORT.md
docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md
docs/acceptance/phase3_acceptance.json
docs/acceptance/phase3_source_audit.png
```

## 7. 修改文件

```text
app/__init__.py                  # 版本 0.3.0
app/bootstrap.py                 # 注入 ScanService，保持 AppContext 扩展
app/config.py                    # 默认版本 0.3.0
config.yaml                      # 版本 0.3.0
requirements.txt                 # 增加 Bandit/Semgrep
core/models/enums.py             # Severity/Confidence/ScanTaskStatus/ScanTaskType
core/models/__init__.py          # 导出 Finding/ScanTask/新枚举
database/schema.py               # v3 字段与索引
database/connection.py           # v3 迁移、备份
security/scope_validator.py      # 本地路径存在/目录/权限扩展
ui/source_audit_page.py          # 占位页替换为完整审计页
ui/main_window.py                # 接入真实审计页、关闭时取消线程、PHASE 3
ui/theme.py                      # 进度条/分割线样式
tests/conftest.py                # 本地项目/资产/校验器 fixture
tests/test_database.py           # v3 与迁移测试
tools/code_quality_check.py      # 异常类 pass 分类
README.md                        # 第三阶段说明、测试数与截图
```

## 8. 已知问题

1. **Semgrep 当前环境不可用**：已安装 1.183.0，但原生 CLI 在 CA 证书存储初始化时报错，退出码 2。因此 Semgrep 的本地规则未能在当前 Windows 会话中做实际运行验证，只完成了结构测试、JSON 解析测试和真实不可用状态处理。这是本阶段 **部分通过** 的唯一主要原因。
2. **Semgrep 规则运行时校验缺失**：受同一原因影响，`python_security.yml` 仅通过 YAML 结构测试，未通过 Semgrep 自身 validate。
3. **原生桌面窗口截图限制**：当前自动化会话不能获取原生窗口句柄，界面验收使用生产入口 + offscreen Qt 实际运行并截图。
4. **扫描中断恢复**：应用正常关闭会取消线程；异常强杀导致的残留 `running` 任务没有自动恢复机制（本阶段未要求）。

## 9. 阶段快照

验收完成后的源码、验收数据库、日志、截图和报告将打包为：

```text
backups/src-research-assistant_phase3_final.zip
```

具体 SHA-256 在最终交付回复中提供。

## 10. 下一阶段建议

1. 在支持 Semgrep 的环境（Linux/WSL）中执行 `semgrep --validate --config scanners/rules/python_security.yml`，并跑一次真实 Semgrep 扫描，将本阶段从“部分通过”提升为完整通过。
2. 进入依赖漏洞审计前，保持现有 `ScanService`/`Finding`/任务隔离结构，接入 pip-audit。
3. 后续再实现漏洞管理、证据、报告和远程配置检查；远程功能必须复用 `require_remote_access`。
4. 本阶段结束，不自动进入第四阶段。
