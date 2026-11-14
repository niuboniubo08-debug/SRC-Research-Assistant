# Phase 6 — RC-01 关闭后的当前状态复核

## 0. 结论摘要

```text
P6_STATUS_REVIEW = COMPLETED
PHASE6_OVERALL_STATUS = NOT_READY_FOR_FINAL_SEAL
RC01_STATUS = READY_FOR_FINAL_HUMAN_REVIEW
RC01_CLOSED_IN_REPOSITORY = NO
RC01_EXTERNAL_APPROVAL_RECORD = NOT_FOUND
```

当前不能确认 `RC-01 = COMPLETED`。

原因不是 RC-01 代码修复失败，而是当前仓库中：

1. `RC-01` 的最终证据报告明确写的是 `READY_FOR_FINAL_HUMAN_REVIEW`，不是 `COMPLETED`；
2. 生产代码和测试代码仍处于未提交修改状态；
3. 没有找到最终人工验收通过、RC-01 关闭或提交完成的记录；
4. RC-01 修复后的完整测试套件尚未执行。

因此，本报告将 RC-01 记录为“技术证据已齐备、等待最终人工验收和提交”，而不是“已关闭”。

## 1. 当前 Phase 6 总体状态

### 已实施且可定位

- 报告数据层：`core/models/report.py`、`repositories/report_repository.py`、`services/report_service.py`；
- HTML 导出核心：`reports/html_exporter.py` 与四个模板；
- 报告中心 GUI：`ui/report_page.py` 已替换占位页；
- AppContext 注入：`app/bootstrap.py` 已构造 `ReportService`；
- MainWindow 接入：`ui/main_window.py` 已创建 `ReportPage`。

### 已验收/已审查

- Phase 6B：归档并封存，状态为 `sealed_with_recorded_exception`；
- Phase 6C-2A：HTML 安全审查和后续修复完成，结论为带记录的限制；
- Phase 6C-2B：GUI 实现与 Step 3 验收 `PASS_WITH_LIMITATIONS`；
- RC-01：定向测试证据完成，但最终人工审核和提交尚未完成。

### 未完成或未开始

- RC-01 正式关闭/提交；
- RC-01 修复后的完整回归；
- Evidence 根目录与报告父级 reparse point 的 P1 路径加固；
- Phase 6 最终封存；
- JSON 导出：`DEFERRED`，未批准；
- PDF：`CANCELLED`；
- 报告历史/持久化：未实现；
- Phase 6F/6G：未找到实施或验收材料。

### 总体判断

```text
PHASE6_OVERALL_STATUS = NOT_READY_FOR_FINAL_SEAL
```

报告中心功能本身已经达到可用状态，但工程层面仍缺少 RC-01 的正式关闭、完整回归和最终封存证据。

## 2. Phase 6A / 6B 状态

### 2.1 文件与测试

| 对象 | 当前事实 |
|---|---|
| `core/models/report.py` | 存在，7,594 bytes，283 lines |
| `repositories/report_repository.py` | 存在，11,847 bytes，315 lines |
| `services/report_service.py` | 存在，13,179 bytes，336 lines |
| `tests/test_report_service.py` | 存在，18 个测试函数，22,297 bytes |

### 2.2 状态

```text
PHASE6A_STATUS = DESIGN_INVESTIGATION_ONLY
PHASE6A_INDEPENDENT_ARTIFACT = MISSING
PHASE6B_IMPLEMENTED = YES
PHASE6B_TESTED = HISTORICAL_ONLY
PHASE6B_ACCEPTED = YES_WITH_RECORDED_EXCEPTION
```

说明：

- Phase 6A 没有独立的阶段文档/验收记录；它体现为后续报告中心架构调查和设计依据，不应被写成“独立完成验收”。
- Phase 6B 报告数据层已实现；历史定向 18 项测试通过，但不是本步骤重新执行。
- Phase 6B 已归档、已封存，但带两个记录在案的例外：
  - `P6B-EX-001`：`docs/acceptance/code_quality.json` 哈希差异；
  - `P6B-EX-002`：`storage/_rebuild_manifest.py` 缺失。
- 当前 Phase 6B 归档目录有 10 个文件；当前 Manifest 记录 14 个条目；历史 acceptance JSON 仍记录 9 个文件/11 个条目，存在历史文档滞后。

## 3. Phase 6C-1 状态

```text
PHASE6C1_STATUS = INVESTIGATION_COMPLETED
PHASE6C1_IMPLEMENTATION = NONE
PHASE6C1_SUPERSEDED_BY = PHASE6C2A
```

事实：

- C1 完成的是 HTML 导出环境、依赖、安全和模板策略调查；
- 当时没有 `reports/html_exporter.py`、没有模板、没有 HTML 导出测试；
- 后续 C2A 已实现该功能，因此 C1 不再是一个独立待实现阶段；
- C1 的安全设计建议（autoescape、无远程资源、no `|safe`、证据图像默认关闭等）已被 C2A 延续。

## 4. Phase 6C-2A 当前真实状态

### 4.1 实现事实

| 检查项 | 当前事实 |
|---|---|
| HTML 导出核心 | 存在：`reports/html_exporter.py`，24,953 bytes，754 lines |
| 模板 | `base.html`、`vulnerability.html`、`evidence.html`、`project_summary.html` |
| Jinja2 autoescape | 已启用：`autoescape=True`，`StrictUndefined` |
| View Model allowlist | 已存在：`build_report_view_model()` |
| 路径 containment | 存在根目录/叶节点检查，但父级 reparse point 未覆盖 |
| 临时文件 | `_atomic_write()` 使用同目录临时文件 |
| fsync | 存在 |
| os.replace | 存在（`overwrite=True`） |
| 排他发布 | `_publish_exclusive()` 使用 `os.link()`，无 `os.replace` 回落 |
| HTML 进入 `storage/reports` | 已有 2 个历史 HTML 文件；本次未生成 |
| HTML 测试 | `tests/test_report_html.py`，28 个测试函数，28,055 bytes |
| 后续安全修复 | SEC-01/04/05/07 已修复；SEC-02 根目录检查已补 |

### 4.2 状态

```text
PHASE6C2A_IMPLEMENTED = YES
PHASE6C2A_TESTED = HISTORICAL_ONLY
PHASE6C2A_SECURITY_REVIEWED = YES
PHASE6C2A_ACCEPTED = ACCEPTED_WITH_RECORDED_LIMITATIONS
PHASE6C2A_FULLY_COMPLETED = NO
```

### 4.3 关键安全边界

已确认存在：

- `ReportSnapshot` 不被直接序列化；导出的数据先经过 View Model allowlist；
- `Project.local_path`、`Project.description`、任务 target/error/result、Finding 原始绝对路径、Evidence 原始/托管路径不进入 HTML；
- Jinja2 自动转义实际启用；
- 路径检查覆盖输出根目录和叶节点；
- 原子写顺序为临时文件 → 写入 → flush → fsync → close → publish；
- `overwrite=False` 使用 `os.link` 排他发布。

仍存在/未完全验证：

- 父级目录 reparse point/junction 未做完整运行时验证；
- Evidence 根目录 `project_<id>` 为 junction/symlink 时，`ReportService._annotate_evidence()` 没有显式拒绝；
- TOCTOU 窗口仍存在；
- CSP 未定义；
- `CountView` 未知标签宽度未设上限；
- Windows 文件 symlink 动态测试因 `WinError 1314` 未执行。

这些是“已记录的限制”，不是“完全安全”的证明。

## 5. RC-01 当前状态

### 5.1 技术证据

当前 RC-01 的相关生产文件和测试文件：

```text
scanners/pip_audit_scanner.py        13,391 bytes
services/dependency_audit_service.py 28,981 bytes
tests/test_pip_audit_scanner.py      10,952 bytes
tests/test_dependency_audit_service.py 31,910 bytes
```

已知定向结果（历史证据，不是本步骤重跑）：

```text
Scanner: 12 passed, 1.37s, exit 0
Service: 60 passed, 12.85s, exit 0
Cross-layer: WAIVE_CROSS_LAYER_TEST
Confirmed interface mismatch: NONE
```

### 5.2 关闭状态

```text
RC01_STATUS = READY_FOR_FINAL_HUMAN_REVIEW
RC01_TECHNICAL_EVIDENCE = COMPLETE
RC01_FORMAL_COMPLETION_RECORD = NOT_FOUND
RC01_CODE_COMMITTED = NO
RC01_TEST_CODE_COMMITTED = NO
RC01_HUMAN_APPROVAL = UNKNOWN
RC01_CLOSED = NO
```

当前 Git：

- HEAD：`db6a138307cc42e26d1075dbbee161c735ee5d4a`；
- 分支：`main`；
- staged：0；
- `scanners/pip_audit_scanner.py`、`services/dependency_audit_service.py`、两个测试文件仍是未暂存修改；
- 最终证据报告和其他 Stage 1B 报告仍是未跟踪文件；
- HEAD 上的最新提交只归档了 Stage 1B 文档，不包含 RC-01 生产/测试修复。

### 5.3 是否存在 RC-01 开放阻塞项

代码层：

```text
RC01_CODE_LEVEL_BLOCKER = NONE_FOUND
```

流程层：

```text
RC01_ADMINISTRATIVE_BLOCKER = FINAL_HUMAN_REVIEW_AND_COMMIT_NOT_RECORDED
RC01_FULL_REGRESSION_AFTER_FIX = NOT_RUN
```

因此不能把“技术证据齐备”写成“RC-01 已关闭”。

## 6. Phase 6D / E / F 与相关功能状态

| 功能 | 状态 | 事实 |
|---|---|---|
| PDF 实施 | `CANCELLED` | `reports/pdf_exporter.py` 不存在；无 PDF 依赖/UI；`ReportFormat.PDF` 仅保留枚举 |
| JSON 实施 | `NOT_STARTED / DEFERRED` | `reports/json_exporter.py` 不存在；无 JSON contract；D1B 决策为 DEFERRED |
| GUI ReportPage | `IMPLEMENTED` | `ui/report_page.py` 18,090 bytes；已接入 bootstrap/MainWindow |
| 报告持久化/记录 | `NOT_IMPLEMENTED` | `reports` 表存在但 0 行；无 `INSERT/UPDATE/DELETE reports` 代码 |
| 其他报告格式/导出 | `NONE` | 仅 HTML 导出路径；PDF/JSON 未实现 |
| 报告历史 UI | `NOT_IMPLEMENTED / OUT_OF_SCOPE` | 无历史页、无记录写入 |
| Evidence 图片嵌入 | `NOT_IMPLEMENTED / NOT_APPROVED` | HTML 当前不嵌入证据图片 |

`ReportFormat` 中仍保留 PDF/JSON 枚举属于兼容性/休眠状态，不等于功能已实现。

## 7. 遗留问题分类

### 7.1 Semgrep Windows 问题

```text
SEMGREP_WINDOWS_STATUS = RUNTIME_VALIDATION_PENDING
SEMGREP_PHASE6_BLOCKING = NO
SEMGREP_SOURCE_AUDIT_IMPACT = OPEN_LIMITATION
```

- Semgrep 1.183.0 在本 Windows 会话中仍无真实运行证据；
- 当前没有可验证的 Semgrep 扫描结果；
- 它不是 Phase 6 报告中心的阻塞项；
- 但 Phase 3 源代码审计能力仍不能声称在 Windows 上完整验证。

### 7.2 Phase 5 Manifest / code quality 问题

```text
PHASE5_MANIFEST_STATUS = NON_BLOCKING_BUT_UNRESOLVED_RECORDED_EXCEPTION
```

当前事实：

- `docs/acceptance/code_quality.json`：9,144 bytes，SHA `F0D0FCA2A1F144D9F44891DF76D4BD581B55F52139687C68EDFCDC748CAF2E59`；
- 历史期望 SHA：`5993473A...`；
- `storage/_rebuild_manifest.py`：不存在；
- Phase 5 最终 Manifest 的 253 个条目中，246 个匹配，1 个唯一不匹配文件，1 个缺失文件；
- 该问题已作为 `P6B-EX-001`/`P6B-EX-002` 记录，但没有被修复或恢复；
- 它不阻塞 Phase 6 报告中心功能，但阻止 Phase 5 工作区的“精确可复现封存”。

### 7.3 Windows pytest 临时目录问题

```text
PYTEST_TEMP_STATUS = ENVIRONMENT_LIMITATION
PYTEST_TEMP_BLOCKING_FOR_NORMAL_WORKSPACE = YES
PYTEST_TEMP_BLOCKING_FOR_PRODUCT_FEATURE = NO
```

- 普通 workspace-write 下可能出现 `PermissionError [WinError 5]`；
- 需要专用临时目录 `D:\挖漏洞\pytest_c1r_tmp` 和 full-access 测试进程；
- 这是测试环境限制，不是应用业务故障；
- 不阻塞报告中心或 RC-01 代码本身，但阻塞普通环境下的完整回归。

### 7.4 其他未完成项

- Phase 6C-2A 的父级 reparse/TOCTOU/CSP 等限制；
- Phase 6D JSON：未批准；
- Phase 6E 报告历史：未批准；
- Phase 6F/6G：没有实施/验收材料；
- 当前主数据库已包含真实审计数据，不再是空库；
- 当前工作区有未提交的 RC-01 变更和多个未跟踪报告。

## 8. 当前测试证据边界

本步骤没有执行 pytest。以下全部是历史证据或当前文件结构，不是本步骤重新运行结果。

| 项目 | 结果 | 来源 | 是否本步骤执行 |
|---|---|---|---|
| LAST_KNOWN_FULL_SUITE | 210 collected / 203 passed / 7 skipped / 0 failed / 0 errors / 51.92s | Phase 6 P2B 历史验收 | **否** |
| LAST_KNOWN_SCANNER_TEST | 12 passed / 1.37s / exit 0 | RC-01 Step 7A | **否** |
| LAST_KNOWN_SERVICE_TEST | 60 passed / 12.85s / exit 0 | RC-01 Step 7B | **否** |
| REPORT_SERVICE_TEST_STATUS | 18 个测试函数；历史定向 18 passed | Phase 6B 历史证据 | **否** |
| HTML_RELATED_TEST_STATUS | 28 个测试函数；历史定向 40 passed / 1 skipped | Phase 6C-2A 历史证据 | **否** |
| UI_REPORT_TEST_STATUS | 16 个测试函数；历史 16 passed | Phase 6C-2B 历史证据 | **否** |

关键限制：

```text
CURRENT_FULL_SUITE_AFTER_RC01 = NOT_RUN
CURRENT_TEST_COLLECTION_AFTER_RC01 = NOT_MEASURED_IN_THIS_STEP
```

历史完整套件 `210/203/7` 发生在 RC-01 测试修改之前；不能作为 RC-01 修复后的当前完整回归结论。

## 9. 数据库与 Schema 状态

只读检查当前主数据库：

```text
database/storage/src_research.db
size = 4,354,048 bytes
sha256 = 70E452A98ABED7F8ED7AC7C90B38647A4A1440F556006A223F49051A4BF81148
user_version = 5
integrity_check = ok
foreign_key_check = 0
tables = 11
indexes = 18
```

当前业务数据：

| 表 | 行数 |
|---|---:|
| projects | 1 |
| scan_tasks | 3 |
| findings | 5,430 |
| evidence | 0 |
| reports | 0 |

当前项目：

```text
project_id = 3
project_name = Flask-admin开源审计
project_type = local_audit
status = active
local_path = D:\DeBug\flask-admin-master
```

三个 `scan_tasks` 都是 `source_audit`，目标为同一本地项目，状态均 `completed`；三次 Bandit 扫描各 1,810 findings，合计 5,430。

结论：

- 当前 Schema 仍为 **v5**；
- Phase 6 至今没有 v6 migration；
- RC-01 没有修改数据库或 Schema；
- `reports` 表存在但 0 行，当前只是预留/ dormant 表，不是活跃报告持久化；
- 当前主数据库不再是空库，含真实审计数据；这与早期“主库为空”的历史快照不同，属于当前事实，不应写回旧状态。

## 10. 下一阶段候选项

### CANDIDATE_A

```text
CANDIDATE_A = P6-ACCEPT-01：RC-01 最终人工验收、完整回归与提交/关闭记录
STATUS = READY_TO_RUN
BLOCKING = YES
RISK = LOW
DEPENDENCIES = NO
DATABASE = NO
PRODUCTION_CODE = NO_NEW_SOURCE_CHANGES（提交现有 RC-01 变更）
```

理由：

- RC-01 技术证据已齐备；
- 代码/测试仍未提交；
- 没有最终人工关闭记录；
- 完整回归尚未在 RC-01 修复后执行；
- 这是所有后续 Phase 6 封存工作的前置条件。

### CANDIDATE_B

```text
CANDIDATE_B = P6-SEC-02：Evidence 根目录与报告父级 reparse point 路径加固
STATUS = DESIGNED_CANDIDATE_NOT_AUTHORIZED
BLOCKING = NO_FOR_CURRENT_FEATURE / YES_FOR_P1_HARDENING
RISK = MEDIUM
DEPENDENCIES = NO
DATABASE = NO
PRODUCTION_CODE = YES
```

说明：

- 处理 R0-C P1 中的 Evidence 根目录 junction/symlink 和报告父级 reparse；
- 不应在 RC-01 关闭前抢占优先级；
- 涉及新增安全测试和路径边界验证。

### CANDIDATE_C

```text
CANDIDATE_C = P6-SEAL-01：Phase 6 最终文档、Manifest 与归档一致性清理
STATUS = BLOCKED_UNTIL_A
BLOCKING = YES_FOR_FINAL_SEAL
RISK = LOW
DEPENDENCIES = NO
DATABASE = NO
PRODUCTION_CODE = NO
```

说明：

- 修正 README 文案、Phase 6B 历史计数差异、Phase 5 Manifest 记录边界；
- 只做文档/归档，不修复历史文件；
- 必须等 RC-01 正式关闭后再进行。

## 11. 唯一推荐

```text
NEXT_RECOMMENDED_STEP = P6-ACCEPT-01
```

即：

> **先完成 RC-01 的最终人工验收、RC-01 修复后的完整回归，并提交/记录 RC-01 的代码与测试变更。**

为什么现在应该做它：

1. **RC-01 尚未真正关闭**：当前证据报告和 Git 状态都不支持 `RC-01 = COMPLETED`；
2. **它是阻塞项**：未提交的 RC-01 代码和测试会让后续 Phase 6 封存、备份和验收建立在不确定工作区上；
3. **完整回归缺失**：历史完整套件 `210/203/7` 发生在 RC-01 测试修改之前，不能代表当前状态；
4. **风险最低**：不需要新增功能、依赖、Schema 或数据库变更；
5. **其他候选项都依赖它**：P1 路径修复和最终文档/Manifest 清理都需要先有一个可确认、可复现的 RC-01 基线。

不要在本步骤直接执行该推荐步骤。

## 12. UNKNOWN

```text
RC01_EXTERNAL_HUMAN_APPROVAL = UNKNOWN
RC01_EXTERNAL_CLOSURE_RECORD = NOT_FOUND
CURRENT_FULL_SUITE_AFTER_RC01 = UNKNOWN_NOT_RUN
CURRENT_TEST_COLLECTION_AFTER_RC01 = UNKNOWN_NOT_MEASURED
CURRENT_HTML_GUI_END_TO_END_WORKFLOW = UNKNOWN_NOT_RUN
REAL_SCANNER_TO_REAL_SERVICE_RUNTIME = UNKNOWN_NOT_RUN
PRODUCTION_DATABASE_PROVENANCE = PARTIALLY_KNOWN
PHASE6B_MANIFEST_VS_ACCEPTANCE_JSON_COUNTS = CONFLICT_RECORDED
PHASE5_MANIFEST_EXACT_REPRODUCIBILITY = NO
SEMGREP_WINDOWS_RUNTIME = PENDING
```

当前数据库中的 5,430 findings 和 3 个 Bandit 任务来自当前项目数据；本步骤未执行扫描，无法仅凭数据本身确认具体操作者/会话。其存在是已确认事实，来源归因仍需人工确认。

## 13. 本步骤声明

```text
P6_STATUS_REVIEW = COMPLETED
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
PYTEST_EXECUTED = NO
REAL_PIP_AUDIT_EXECUTED = NO
REAL_NETWORK_EXECUTED = NO
ACL_MODIFIED = NO
GIT_WRITE = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤只读检查了源码、测试、文档、Git 状态和数据库元数据，并新增本报告；没有修改任何生产代码、测试、数据库、Schema、ACL 或 Git 状态。
