# Phase 6 Next-Step Read-Only Continuation Audit

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 调查日期：2026-11-12（Asia/Shanghai）
- 调查性质：只读
- 本轮唯一新增文件：本报告

```text
AUDIT_TYPE = READ_ONLY
PROJECT_FILES_MODIFIED = NO
DATABASE_MODIFIED = NO
GIT_MUTATIONS_BY_AUDIT = NO
EXTERNAL_GIT_COMMIT_OBSERVED = YES
TESTS_RUN = NO
```

本报告区分“文档计划”“实际代码”“历史验收结果”和“推断”，不把计划写成已实现。

---

## 1. 当前 Git 状态

### 1.1 初始审计快照（2026-11-12 22:48）

`git status --short --untracked-files=all`：

```text
?? docs/GIT_8B_1_TRAILING_WHITESPACE_FIX.md
?? docs/GIT_8B_STAGING_AUDIT.md
```

`git status`：

```text
On branch main
Your branch is ahead of 'origin/main' by 1 commit.
  (use "git push" to publish your local commits)

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	docs/GIT_8B_1_TRAILING_WHITESPACE_FIX.md
	docs/GIT_8B_STAGING_AUDIT.md

nothing added to commit but untracked files present (use "git add" to track)
```

最近提交：

```text
635f736 docs: finalize Phase 6 P2B documentation and acceptance
73cb081 docs: 归档 Git-7 及 Phase 6 阶段调查报告
936c617 docs: archive Git repository establishment audits
5595ef9 chore: establish initial project baseline
```

### 1.2 初始快照分类

```text
CURRENT_BRANCH = main
CURRENT_HEAD = 635f736687a8a89117a28699c49bf1fbfcc5d796
RECENT_COMMITS = 4
UPSTREAM = origin/main
LOCAL_AHEAD_BEHIND_STATUS = ahead 1, behind 0

STAGED_FILES = 0
UNSTAGED_TRACKED_MODIFICATIONS = 0
UNTRACKED_FILES = 2
```

两个未跟踪文件：

```text
docs/GIT_8B_1_TRAILING_WHITESPACE_FIX.md
docs/GIT_8B_STAGING_AUDIT.md
```

本报告在初始快照后生成；最终状态见 1.3，外部提交已收录两个 Git-8B 报告。本轮没有执行 `git add`、`commit` 或 `push`。

`origin/main` 存在且本地领先 1 个提交，说明 Git-8C 的提交仍在本地；本轮没有网络写操作。

### 1.3 审计期间的外部 Git 变更（两次）

初始快照之后，最终只读复核观察到两次**本任务未执行**的外部提交。

第一次提交：

```text
HEAD = 5886ed3396d8c3ca08eabcda46f783509e79dd41
PARENT = 635f736687a8a89117a28699c49bf1fbfcc5d796
SUBJECT = docs: add Git-8B staging audit and whitespace fix reports
AUTHOR = niuboniubo08-debug <niuboniubo08@gmail.com>
COMMIT_TIME = 2026-11-12T22:49:47+08:00
FILES = docs/GIT_8B_1_TRAILING_WHITESPACE_FIX.md,
        docs/GIT_8B_STAGING_AUDIT.md
CHANGES = 2 files, 459 insertions
```

第二次提交：

```text
HEAD = 9ca064eeb6038e097960253691a699822c4703ca
PARENT = 5886ed3396d8c3ca08eabcda46f783509e79dd41
SUBJECT = docs: add Git-8B staging audit and whitespace fix reports
AUTHOR = niuboniubo08-debug <niuboniubo08@gmail.com>
COMMIT_TIME = 2026-11-12T22:50:44+08:00
FILES = docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
CHANGES = 1 file, 385 insertions
```

第二次提交的 subject 与第一次相同，但它新增的是本报告的初始版本（385 行），不是 Git-8B 报告。该提交把本报告从“未跟踪”变成了“已跟踪”；当前工作区中本报告又因本次修订变为 `M`。

本任务没有执行 `git add`、`git commit` 或 `git push`；本轮只执行了 `git status`、`git log`、`git show`、`git rev-parse`、`git reflog`、`git diff` 等只读命令。因此：

```text
GIT_MUTATIONS_BY_AUDIT = NO
EXTERNAL_GIT_COMMIT_OBSERVED = YES
EXTERNAL_COMMIT_COUNT = 2
GIT_STATE_CHANGED_DURING_AUDIT = YES_EXTERNAL
```

最终只读状态：

```text
CURRENT_BRANCH = main
CURRENT_HEAD = 9ca064eeb6038e097960253691a699822c4703ca
RECENT_COMMITS = 6
UPSTREAM = origin/main
LOCAL_AHEAD_BEHIND_STATUS = ahead 3, behind 0

STAGED_FILES = 0
UNSTAGED_TRACKED_MODIFICATIONS = 1
UNSTAGED_TRACKED_PATH = docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
UNTRACKED_FILES = 0
```

最终最近提交：

```text
9ca064e docs: add Git-8B staging audit and whitespace fix reports
5886ed3 docs: add Git-8B staging audit and whitespace fix reports
635f736 docs: finalize Phase 6 P2B documentation and acceptance
73cb081 docs: 归档 Git-7 及 Phase 6 阶段调查报告
936c617 docs: archive Git repository establishment audits
5595ef9 chore: establish initial project baseline
```

这两次外部提交不改变 Phase 6 实现结论，但使本报告的 Git 快照与最终仓库状态不同。报告明确保留初始快照与最终状态，避免把初始快照冒充为最终状态。

---

## 2. Phase 6 实际实施矩阵

| Area | Planned | Actual Implementation | Verification | Status |
|---|---|---|---|---|
| Report Data Layer | Phase 6B：只读 ReportSnapshot、Repository、Service | `core/models/report.py`、`repositories/report_repository.py`、`services/report_service.py` 均存在；Repository 使用单连接、`query_only`、显式列查询；Service 负责统计、warnings、证据校验；无导出写入 | `tests/test_report_service.py` 18 个测试函数；Phase 6B 归档及后续完整测试证据 | `IMPLEMENTED_AND_VERIFIED` |
| HTML Report | Phase 6C：HTML 第一版 | `reports/html_exporter.py` 提供 `render_html()` 与 `write_html_report()`；`reports/templates/` 有 4 个模板；强制 HTML；原子写入、覆盖保护、路径检查、文本边界处理 | `tests/test_report_html.py` 28 个测试函数；C2A/C2B/P2B 验收记录；历史完整测试 203 passed / 7 skipped | `IMPLEMENTED_AND_VERIFIED`（有记录限制） |
| PDF Report | Phase 6B/C1 曾列为后续格式 | **无 PDF exporter、无 PDF writer、无 PDF GUI、无 PDF 模板、无 PDF 测试**；无 ReportLab/Pillow/PyMuPDF/pypdf/PyPDFium；无中文字体资源 | PDF 只出现在 `ReportFormat.PDF` 枚举、`reports` 表 CHECK 和取消说明中 | `CANCELLED`（不是 NOT_STARTED，也不再是待实施计划） |
| JSON Report | Phase 6B/C1 提到 JSON 后续需要 allowlist | **无报告 JSON exporter、无报告 JSON 序列化、无 JSON GUI、无 JSON 测试**；`ReportFormat.JSON` 仅为兼容枚举；`reports` 表 CHECK 允许 `json`，但没有写入代码 | `reports/__init__.py` 明确 `not implemented and has not been approved`；代码检索无 JSON report export | `NOT_IMPLEMENTED / NOT_APPROVED` |
| Report GUI | Phase 6C-2B：最小 HTML 报告中心 | `ui/report_page.py` 的 `ReportPage` 已实现；`app/bootstrap.py` 注入 `ReportService`；`ui/main_window.py:197` 使用 `ReportPage(context, state)`；固定 `AppConfig.reports_dir`；HTML-only 预览/导出；`QTextBrowser` 安全文本预览、无远程资源、无 PDF/JSON 控件 | `tests/test_ui_report.py` 16 个测试函数；C2B Step 3 验收；GUI 不执行 SQL、不直接写文件 | `IMPLEMENTED_AND_VERIFIED`（有记录限制） |
| Report History | 文档曾把报告历史列为后续/单独评审 | `reports` 表存在，但报告服务/导出器/UI 没有 `INSERT/UPDATE/DELETE reports`；GUI 无历史列表；当前不持久化报告记录 | `database/schema.py:95-98` 只有表定义；代码检索报告表写入为 0 | `NOT_IMPLEMENTED / OUT_OF_SCOPE` |

### 2.1 关键代码证据

Report DTO / format：

```text
core/models/report.py:55-65   ReportFormat HTML/PDF/JSON
core/models/report.py:243     ReportSnapshot
core/models/report.py:276     ReportArtifact
```

Report data layer：

```text
repositories/report_repository.py:110   load_snapshot
repositories/report_repository.py:138   load_snapshot for request
repositories/report_repository.py:191   builds ReportSnapshot
services/report_service.py:94           get_snapshot
services/report_service.py:104          get_snapshot_for_request
services/report_service.py:323          artifact_stub
```

HTML exporter：

```text
reports/html_exporter.py:310   render_html
reports/html_exporter.py:327   write_html_report
reports/html_exporter.py:382   report_format=ReportFormat.HTML
reports/html_exporter.py:410   rejects non-HTML request
```

Templates：

```text
reports/templates/base.html              8,904 bytes
reports/templates/vulnerability.html     2,878 bytes
reports/templates/evidence.html          2,549 bytes
reports/templates/project_summary.html   3,069 bytes
```

GUI / injection：

```text
ui/report_page.py:39    class ReportPage
ui/report_page.py:51    self._service = context.report_service
ui/report_page.py:136   ReportType.options() only; no PDF/JSON format control
ui/report_page.py:330   generate_preview()
ui/report_page.py:345   export()
ui/report_page.py:387   write_html_report(...)
app/bootstrap.py:129    ReportService(...)
app/bootstrap.py:148    report_service=report_service
ui/main_window.py:197   "reports": ReportPage(self._context, self._state)
```

PDF and JSON boundaries：

```text
PDF_CODE_HITS = 0
JSON_EXPORT_HITS = 0
REPORT_FORMAT_HTML = implemented and used
REPORT_FORMAT_PDF = compatibility metadata only
REPORT_FORMAT_JSON = compatibility metadata only
```

`PDF_CODE_HITS` 检索范围为报告相关 Python 文件中的 ReportLab/WeasyPrint/PyMuPDF/pypdf 及 PDF 生成函数；`JSON_EXPORT_HITS` 检索范围仅为 `reports/*.py`、`services/report_service.py`、`ui/report_page.py` 中的报告 JSON 序列化。

### 2.2 测试证据

本轮没有重新运行 pytest，避免只读调查被误当作新的验收运行。

历史完整回归证据（`docs/PHASE6_P2B_6A_FULL_TEST.md`、`docs/PHASE6_P2B_FINAL_ACCEPTANCE.md`）：

```text
COLLECTED = 210
PASSED = 203
FAILED = 0
SKIPPED = 7
ERRORS = 0
EXIT_CODE = 0
ELAPSED_TIME = 51.92s
```

7 个 skip 全部是 Windows symlink `[WinError 1314]`，不是 PASS，也不是被静默忽略的失败。

报告专项测试函数数量：

```text
tests/test_report_service.py = 18
tests/test_report_html.py    = 28
tests/test_ui_report.py      = 16
```

这里的数量是测试函数定义数，不是最终参数化后的全部测试实例数；历史完整回归的 210 项是实际收集数。

---

## 3. 原计划与实际状态差异

### 3.1 PLANNED_TASKS

文档中可确认的计划来源：

1. `docs/PHASE6_B_REPORT.md:545-556`
   - 阶段 C：HTML 导出；
   - PDF 等待合法中文字体/ReportLab 技术验证；
   - JSON 需要白名单序列化，排除内部原始路径和不允许的 metadata。

2. `docs/PHASE6_C1_HTML_INVESTIGATION.md:594-626`
   - C2a：HTML view model/templates/autoescape/atomic writer；
   - C2b：HTML 安全与文件测试；
   - C2c：可选 UI wiring 与覆盖确认；
   - C1 明确建议先不做 PDF/JSON/GUI 全面接入。

3. 后续实际执行：
   - C2A 完成 HTML 核心与测试；
   - C2B 完成最小 HTML GUI；
   - P2A/P2B 完成 PDF 取消后的文档一致性清理。

### 3.2 COMPLETED_TASKS

```text
Phase 6A: 设计/可行性调查（无独立阶段文档；只作为后续实施的推断背景）
Phase 6B: Report DTO / Repository / Service
Phase 6C-1: HTML 环境与安全调查
Phase 6C-1R: pytest 临时目录诊断与恢复
Phase 6C-2A: HTML exporter / templates / 安全测试
Phase 6C-2B: HTML 报告中心 GUI / 快照一致性修复 / 验收
Phase 6P-1: PDF closure audit
Phase 6P-2A: PDF residue investigation
Phase 6P-2B: 当前文档一致性清理与最终验收
```

注意：Phase 6B 文档中的“未来 HTML/PDF/JSON”是计划，不代表当时已经存在 exporter；HTML 和 GUI 是后来 C2A/C2B 才真正实现的。

### 3.3 NOT_STARTED_TASKS

```text
JSON report export = NOT_IMPLEMENTED / NOT_APPROVED
Report history persistence = NOT_IMPLEMENTED / OUT_OF_SCOPE
Phase 6D/E/F detailed tasks = UNKNOWN（现有文档未定义具体内容）
```

`docs/PROJECT_HISTORY_PHASE6.md:942` 明确记录：

> Phase 6D/E/F 的详细计划（只有 C1 的停止声明）。

因此不能仅凭“D/E/F”三个字母断言它们分别等于 PDF、JSON 或报告历史。

### 3.4 差异分类

```text
PLANNED_BUT_NOT_IMPLEMENTED
- JSON report export（计划提到，但未实现，未获批准）
- Report history persistence（曾列为后续/单独评审，未实现）

PARTIALLY_IMPLEMENTED
- HTML report 的“证据图片嵌入”仍关闭；这是既定安全边界，不是 exporter 缺失
- HTML 是安全文本预览/QTextBrowser，不是浏览器级排版；这是已知限制

IMPLEMENTED_AND_VERIFIED
- Report data layer
- HTML report core + templates + tests
- Report GUI
- PDF closure/cancellation documentation
```

PDF 不属于“待实现”：它已被正式取消，只保留兼容枚举/Schema CHECK，不应再次作为实现候选。

---

## 4. 下一步唯一推荐

### 4.1 NEXT_RECOMMENDED_TASK

```text
Phase 6D-1（工作名称）
JSON Report Export Approval & Design Gate
类型：READ_ONLY / DECISION + DESIGN
```

这不是 JSON exporter 的代码实现任务。它应先回答：

1. 产品是否正式批准 JSON 报告导出；
2. JSON 面向谁、用于什么消费方；
3. 字段白名单和禁止字段；
4. 是否写 `reports` 历史表；
5. 文件命名、覆盖策略、输出目录和失败处理；
6. 是否需要新增 schema（当前看不需要，但不能预先假设）；
7. 最小测试集和验收边界。

只有该门禁通过后，才应进入 JSON exporter 实现。

### 4.2 RATIONALE

它是当前唯一同时满足以下条件的任务：

- 属于 Phase 6 原计划中“报告格式”范围；`PHASE6_B_REPORT` 和 `PHASE6_C1` 都提到了 JSON；
- 尚未完成；当前没有 JSON exporter、GUI 控件或测试；
- 没有被正式取消；PDF 已取消，HTML/GUI 已完成；
- 不会跳过依赖：必须先确认产品批准和序列化 allowlist，不能直接写代码；
- 不需要修改现有 HTML exporter 或数据库即可先完成决策/设计。

### 4.3 PREREQUISITES

```text
P1. 用户明确批准 JSON 报告导出（当前为 NOT_APPROVED）
P2. 明确 JSON 消费方和使用场景
P3. 确认字段 allowlist / 禁止字段
P4. 确认是否复用 reports 表或保持无历史
P5. 确认文件命名、reports_dir、overwrite 语义
P6. 确认不嵌入原始绝对路径、原始 metadata、凭据或未批准字段
P7. 确认测试与验收标准
```

### 4.4 RISKS

```text
R1. 自由文本/元数据可能包含路径、凭据或 PII
R2. 直接把 DTO 序列化会泄露内部字段
R3. 若把“0 Finding”写成“无漏洞”，会产生真实性错误
R4. reports 表写入会引入新的持久化/保留策略
R5. JSON 消费方可能依赖稳定 schema，需要版本化
R6. 当前 Windows symlink/TOCTOU 限制仍适用于文件发布
R7. PDF 已取消，不得借 JSON 任务恢复 PDF
```

### 4.5 WHY_NOT_OTHER_TASKS_YET

- **HTML report**：已实现并有专项/回归验证；没有未完成的 HTML 核心任务。
- **Report GUI**：已实现 `ReportPage`、Service 注入、固定 reports_dir、单写者、覆盖确认和预览；没有需要立即补做的核心 GUI。
- **PDF**：正式取消；没有 exporter、依赖、字体或测试，不应重新打开。
- **Report history**：未在 Phase 6 原计划中形成明确可执行任务；`reports` 表未使用，且是否持久化需要单独产品决策，不能先于 JSON 决策强行实现。
- **Security debt / hardening**：是已记录限制，不是当前原计划的下一项功能；本轮不做顺手修复。
- **Git / backup / remote**：不属于 Phase 6 报告功能；且用户当前只要求调查，不得执行 Git 或网络写操作。
- **Phase 6D/E/F 直接实现**：详细计划 UNKNOWN；在任务定义缺失时直接写代码会制造新的范围漂移。

---

## 5. 最终状态

```text
PHASE6_CONTINUATION_AUDIT = PASS
RECOMMENDATION_CONFIDENCE = MEDIUM

PROJECT_FILES_MODIFIED = NO
DATABASE_MODIFIED = NO
GIT_MUTATIONS_BY_AUDIT = NO
EXTERNAL_GIT_COMMIT_OBSERVED = YES
EXTERNAL_COMMIT_COUNT = 2
TESTS_RUN = NO

CURRENT_BRANCH = main
CURRENT_HEAD = 9ca064eeb6038e097960253691a699822c4703ca
COMMIT_COUNT = 6
UNTRACKED_FILES = 0
UNSTAGED_TRACKED_MODIFICATIONS = 1
REPORT_WORKTREE_STATUS = MODIFIED

HTML_REPORT = IMPLEMENTED_AND_VERIFIED
REPORT_GUI = IMPLEMENTED_AND_VERIFIED
PDF_REPORT = CANCELLED
JSON_REPORT = NOT_IMPLEMENTED / NOT_APPROVED
REPORT_HISTORY = NOT_IMPLEMENTED / OUT_OF_SCOPE

NEXT_RECOMMENDED_TASK = Phase 6D-1 JSON Export Approval & Design Gate
```

### 置信度说明

`RECOMMENDATION_CONFIDENCE=MEDIUM`，原因不是代码状态不确定，而是 Phase 6D/E/F 的原始任务单在现有文档中没有定义。可确认的事实是：

- HTML/GUI 已完成；
- PDF 已取消；
- JSON 未实现且未批准；
- 报告历史未实现且未形成明确计划。

因此，下一步最合理的是先做 JSON 的审批/设计门禁，而不是直接写 JSON、恢复 PDF 或重新打开 HTML。

---

## 6. 本轮边界声明

本轮：

```text
未修改任何生产代码
未修改任何测试
未修改数据库或 Schema
未执行数据库迁移或业务写入
未执行 git add
未执行 git commit
未执行 git push
未修改 remote
未开始 Phase 6D 实现
```

审计期间观察到两次外部提交（`5886ed3` 与 `9ca064e`），提交命令不是本任务执行的；详情见 1.3。

唯一新增文件为本报告：

```text
docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
```

最终 Git 中本报告处于 `M`（已跟踪但工作区有本次修订），没有其他未跟踪文件。两个 Git-8B 报告已先由 `5886ed3` 收录，本报告初始版本由 `9ca064e` 收录；本次修订等待人工审核。
