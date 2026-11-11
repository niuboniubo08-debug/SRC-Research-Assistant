# Phase 6P-2A：PDF 功能关闭后的残留调查（READ-ONLY）

- 日期：2026-11-11（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：`0.5.0`
- 当前 Schema：`v5`
- 产品决策：**PDF = CANCELLED / OUT OF SCOPE**
- 本轮性质：**READ-ONLY INVESTIGATION**
- 最终结论：PDF 功能没有实际实现；存在少量现行文档残留，需要 Phase 6P-2B 做最小文档修订；历史记录全部保留。

```text
PDF_RESIDUE_INVESTIGATION = COMPLETED
ACTIVE_PDF_IMPLEMENTATION = NO
PDF_SPECIFIC_DEPENDENCY = NO
ACTIVE_PDF_UI = NO
ACTIVE_PDF_TESTS = NO
REPORT_FORMAT_PDF_PRESENT = YES
CURRENT_UI_EXPOSES_PDF = NO
CURRENT_SERVICE_ACCEPTS_PDF = YES
CURRENT_DOCUMENT_CONFLICTS = FOUND
HISTORICAL_RECORDS_TO_PRESERVE = YES
PHASE6_P2B_READINESS = CONDITIONAL_GO
```

---

## 1. 调查范围与方法

### 1.1 调查性质

本轮是只读调查，没有修改源码、测试、数据库、Schema、配置、`.gitignore`、HTML 模板或 Git 历史；没有执行 `git add`、`git commit`、`git reset`、`git rebase`、`git remote add` 或 `git push`；没有安装或卸载依赖；没有创建 PDF；没有删除或移动文件。

只新增本报告：

```text
docs/PHASE6_P2A_PDF_RESIDUE_INVESTIGATION.md
```

### 1.2 搜索关键词

使用大小写不敏感搜索，覆盖以下关键词和变体：

```text
PDF / pdf
ReportLab / reportlab
pypdf
PyMuPDF
fitz
QtPdf
QtWebEngine
pdf export / PDF export
generate_pdf
export_pdf
PDF 报告
PDF 导出
生成 PDF
导出 PDF
PDF 功能
PDF 渲染
```

### 1.3 搜索范围

实际扫描的是 Git HEAD 中已跟踪的文本文件，覆盖：

- `README*`
- `docs/`
- `core/`
- `services/`
- `repositories/`
- `ui/`
- `reports/`
- `tests/`
- `requirements.txt`
- `pyproject.toml`（实际不存在）
- 其他文本配置和验收记录

结果：**53 个文本文件存在至少一个关键词命中**。命中数量不等于需要修改；以下逐项区分历史记录、现行文档、代码残留和无行动项。

### 1.4 当前依赖与资源

- `requirements.txt` 没有 ReportLab、Pillow、PyMuPDF、pypdf、pypdfium2 或其他 PDF 专用库。
- 根目录没有 `pyproject.toml`，没有锁文件。
- 没有 PDF 专用字体或资源目录。
- 唯一的 `.pdf` 文件是 `storage/acceptance/authorization.pdf`（44 字节）；它是授权附件占位，不是 PDF 报告，也不是 PDF 功能证据。
- `storage/reports` 只有 HTML 报告和 `.gitkeep`，没有 PDF 报告。

---

## 2. 当前 Git 状态

调查开始时：

```text
BRANCH = main
HEAD = 936c61722c29b9f4dca32cd938e8e3ca1c0d1ffb
COMMIT_COUNT = 2
REMOTE_CONFIGURED = NO
TRACKED_MODIFICATIONS = 0
STAGED_CHANGES = 0
```

`git log`：

```text
936c617 (HEAD -> main) docs: archive Git repository establishment audits
5595ef9 chore: establish initial project baseline
```

调查开始时唯一的未预期之外、但已知的未跟踪文件是：

```text
docs/GIT_7_AUDIT_ARCHIVE_AND_COMMIT.md
```

它是 Git-7 的预期未跟踪报告，不是本阶段产生的源码修改。生成本报告后，工作区会再增加本报告这一个未跟踪文件；没有暂存任何文件，没有创建 commit。

---

## 3. PDF 关键词调查结果

### 3.1 现行文档：需要最小修订

| 文件与位置 | 上下文 | 分类 | 动作 | 原因 |
|---|---|---|---|---|
| `README.md:160-171`（命中第 166 行） | “本阶段明确未实现”仍列出 `HTML / PDF / JSON 报告` | CURRENT_DOCUMENT_PDF_RESIDUE | `CANDIDATE_FOR_UPDATE` | PDF 已取消；同时 HTML 报告已在 C2B 实现，当前表述已过时。 |
| `README.md:331-339`（命中第 333 行） | “下一阶段建议”第 1 条仍写“实现 HTML/PDF/JSON 报告” | CURRENT_DOCUMENT_PDF_RESIDUE | `CANDIDATE_FOR_UPDATE` | 把已取消的 PDF 仍列为未来任务；HTML 也已完成。 |
| `reports/__init__.py:1` | docstring：`HTML/PDF/JSON planned for a later phase` | CURRENT_DOCUMENT_PDF_RESIDUE | `CANDIDATE_FOR_UPDATE` | “PDF planned”与正式取消决定冲突。 |
| `docs/PHASE6_C2A_SECURITY_DEBT.md:673` | 待决策项第 6 条：“评估 PDF/JSON 导出是否沿用同一策略（C2B 之后）” | CURRENT_DOCUMENT_PDF_RESIDUE | `CANDIDATE_FOR_UPDATE` | 该条仍把 PDF 作为后续评估对象；应删除 PDF，保留 JSON 的产品决策讨论。 |

上述四处是**唯一被判定为现行文档 PDF 残留**的位置。它们都只需要文档修订，不需要恢复或新增 PDF 功能。

### 3.2 历史记录：保留，不得篡改

以下文件是在 PDF 取消决定之前形成的阶段记录、设计记录、验收记录或 Git 过程记录。它们如实记录了当时的状态，继续保留：

| 文件类别 | 代表文件 | 分类 | 动作 | 理由 |
|---|---|---|---|---|
| Phase 5 架构/验收 | `docs/PHASE5_ARCHITECTURE.md`、`docs/acceptance/phase5_final/*` | HISTORICAL_RECORD | `PRESERVE` | 已完成阶段的事实记录；PDF 只是历史计划/限制。 |
| Phase 6B 设计与验收 | `docs/PHASE6_B_REPORT.md`、`docs/acceptance/phase6_b_final/*` | HISTORICAL_RECORD | `PRESERVE` | 当时明确记录“PDF 未实现、等待字体/技术验证”。 |
| C1/C2A/C2B 设计与安全记录 | `docs/PHASE6_C1_HTML_INVESTIGATION.md`、`docs/PHASE6_C2A_*`、`docs/PHASE6_C2B_STEP*` | HISTORICAL_RECORD | `PRESERVE` | 记录 HTML 范围、PDF 不纳入、依赖不可用等实际决策。 |
| Phase 6 PDF 关闭审计 | `docs/PHASE6_PDF_CLOSURE_AUDIT.md`（107 处关键词） | DECISION_RECORD | `PRESERVE` | 它本身就是 PDF 取消的正式调查记录；不能为了“清理字样”而改写。 |
| Phase 6 项目历史 | `docs/PROJECT_HISTORY_PHASE6.md` | HISTORICAL_RECORD | `PRESERVE` | 历史重建材料。 |
| 历史验收材料 | `docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md`、`docs/acceptance/project_tree.txt`、`docs/TEST_REPORT.md` | HISTORICAL_RECORD | `PRESERVE` | 历史事实和验收证据。 |
| Git 过程记录 | `docs/GIT_*`、`docs/GITIGNORE_FINAL_AUDIT.md`、`docs/GIT_REPOSITORY_PREPARATION_AUDIT.md` | HISTORICAL_PROCESS_RECORD | `PRESERVE` | 其中大多数 `pdf` 命中是 `authorization.pdf` 附件路径、文件清单或审计说明，不是 PDF 报告功能。 |
| 历史审计日志 | `storage/acceptance/logs/audit.jsonl` | HISTORICAL_RECORD | `PRESERVE` | 历史操作记录。 |

> 历史记录中出现 PDF 不等于当前仍计划 PDF。  
> 取消功能不等于抹除历史。

### 3.3 明确无需行动的代码/测试/资源命中

| 文件与位置 | 实际含义 | 分类 | 动作 |
|---|---|---|---|
| `core/models/report.py:55-74` | `ReportFormat` 保留 `PDF` 枚举和 label/extension；这是数据模型兼容层，不是导出器 | DORMANT_COMPATIBILITY | `NO_CHANGE`（P2B 不改代码；是否移除枚举需单独人工决策） |
| `database/schema.py:98` | `reports.report_format` 的 CHECK 允许 `pdf`；当前没有报告记录，也没有写 PDF 的代码 | DORMANT_SCHEMA_COMPATIBILITY | `NO_CHANGE`（不改 Schema） |
| `services/report_service.py:104-108`、`:322-336` | `get_snapshot_for_request()` 会校验并保留 `ReportFormat.PDF`；`artifact_stub()` 只返回元数据占位，不写文件 | METADATA_ONLY | `NO_CHANGE`（PDF 无实际渲染路径） |
| `reports/html_exporter.py:405-411` | `_validate_request()` 明确拒绝非 HTML 格式，报“本阶段仅支持 HTML 报告” | ACTIVE_HTML_GUARD | `NO_CHANGE` |
| `ui/report_page.py` | 只构造 HTML 请求，没有 PDF 格式下拉框、按钮或文件写入分支 | NO_PDF_UI | `NO_CHANGE` |
| `tests/test_report_html.py:352-358` | 负向测试：PDF 请求必须被 HTML exporter 拒绝 | NEGATIVE_TEST | `NO_CHANGE` |
| `tests/test_report_service.py:55,321` | `.pdf` 是授权文档路径，不是报告格式测试 | AUTHORIZATION_FIXTURE_PATH | `NO_CHANGE` |
| `tests/test_ui.py:71`、`tests/test_ui_dialogs.py:31`、`ui/project_page.py:301`、`tools/*` | `.pdf` 是授权附件/路径或截图工具文件名，不是 PDF 报告 | AUTHORIZATION_ATTACHMENT | `NO_CHANGE` |
| `services/report_service.py:3` | 声明本模块不做 HTML/PDF/JSON 渲染；这是真实行为描述 | CURRENT_CODE_COMMENT | `NO_CHANGE` |
| `reports/html_exporter.py` 其余命中 | HTML 模板和导出器中的格式/扩展名逻辑，不包含 PDF 写入 | HTML_ONLY | `NO_CHANGE` |

---

## 4. 当前代码与依赖状态

```text
ACTIVE_PDF_IMPLEMENTATION = NO
PDF_SPECIFIC_DEPENDENCY = NO
ACTIVE_PDF_UI = NO
ACTIVE_PDF_TESTS = NO
```

依据：

1. `reports/` 下没有 `pdf_exporter.py`、`render_pdf()`、`generate_pdf()` 或 PDF MIME/写入器。
2. `reports/html_exporter.py:405-411` 对非 HTML 请求直接抛 `ValidationError`。
3. `ui/report_page.py` 只使用 `ReportFormat.HTML`；没有 PDF 选项或 PDF 导出按钮。
4. `requirements.txt` 没有 PDF 专用依赖；没有 `pyproject.toml` 或锁文件。
5. 没有 PDF 专用正测试或 PDF fixture；只有使用授权 `.pdf` 路径的普通测试，以及一条“PDF 应被拒绝”的负向测试。
6. 没有 PDF 报告文件；`storage/acceptance/authorization.pdf` 是 44 字节授权附件占位。

---

## 5. 报告模型和格式定义调查

```text
REPORT_FORMAT_PDF_PRESENT = YES
CURRENT_UI_EXPOSES_PDF = NO
CURRENT_SERVICE_ACCEPTS_PDF = YES
```

### 5.1 为什么 `REPORT_FORMAT_PDF_PRESENT=YES`

`core/models/report.py:55-58` 的 `ReportFormat` 仍有：

```python
class ReportFormat(str, Enum):
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
```

`:60-66` 还定义了 PDF 的 label；`:72-74` 的 `options()` 会把 PDF 一并列出。  
这是**枚举保留**，不是 PDF 功能仍处于活动实现状态。

### 5.2 为什么 `CURRENT_UI_EXPOSES_PDF=NO`

`ui/report_page.py` 没有格式下拉框；它固定构造 HTML 请求。`ui/main_window.py` 只负责页面切换，不暴露 PDF 入口。

### 5.3 为什么 `CURRENT_SERVICE_ACCEPTS_PDF=YES`

`services/report_service.py:104-108` 的 `get_snapshot_for_request()` 会调用 `_coerce_format()`，只验证 `ReportFormat` 枚举有效，不拒绝 PDF。  
`:322-336` 的 `artifact_stub()` 会把 `request.report_format` 原样放进 `ReportArtifact`，但 `path` 和 `sha256` 为空，且不会写文件。

因此准确表述是：

> 当前服务层可以在“数据请求元数据”意义上接受 PDF 枚举，但没有任何 PDF 渲染、文件写入或 GUI 导出路径。

---

## 6. 文档分类结果

### 6.1 `CURRENT_DOCUMENTS_CANDIDATE_FOR_UPDATE`

1. `README.md:166`（`README.md:160-171` 上下文）
2. `README.md:333`（`README.md:331-339` 上下文）
3. `reports/__init__.py:1`
4. `docs/PHASE6_C2A_SECURITY_DEBT.md:673`

### 6.2 `HISTORICAL_RECORDS_TO_PRESERVE`

- `docs/PHASE5_ARCHITECTURE.md`
- `docs/PHASE6_B_REPORT.md`
- `docs/PHASE6_C1_HTML_INVESTIGATION.md`
- `docs/PHASE6_C2A_*`（安全审查/修复/债务记录）
- `docs/PHASE6_C2B_STEP1_GUI_INVESTIGATION.md`
- `docs/PHASE6_C2B_STEP2_IMPLEMENTATION.md`
- `docs/PHASE6_C2B_STEP2_REVIEW.md`
- `docs/PHASE6_C2B_STEP2_SNAPSHOT_FIX.md`
- `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md`
- `docs/PHASE6_PDF_CLOSURE_AUDIT.md`
- `docs/PROJECT_HISTORY_PHASE6.md`
- `docs/acceptance/**`
- `docs/TEST_REPORT.md`
- `docs/GIT_*`、`docs/GITIGNORE_FINAL_AUDIT.md`
- `storage/acceptance/logs/audit.jsonl`

### 6.3 `NO_CHANGE`

- `core/models/report.py` 的 PDF 枚举与 label/extension；
- `database/schema.py:98` 的 `pdf` CHECK 兼容；
- `services/report_service.py` 的格式校验和 metadata-only `artifact_stub()`；
- `reports/html_exporter.py:405-411` 的 HTML 严格拒绝逻辑；
- `ui/report_page.py` 的 HTML-only UI；
- `tests/test_report_html.py:352-358` 的负向测试；
- 所有以 `.pdf` 表示授权附件路径的测试、UI 和工具代码；
- Git 审计记录和验收归档中的 `authorization.pdf` 引用。

### 6.4 `REVIEW_REQUIRED`

- 是否永久保留 `ReportFormat.PDF` 以及 `reports.report_format` 的 `pdf` CHECK，作为将来兼容层；
- `ReportService.get_snapshot_for_request()` 是否应在 API 边界显式拒绝 PDF，避免调用方误以为“可生成 PDF”。

这两项是设计决策，不应在 P2B 中擅自改代码或改 Schema。

---

## 7. 发现的矛盾或风险

### 7.1 `DOCUMENTATION_CONFLICTS = FOUND`

已确认的现行文档矛盾：

1. `README.md:166` 仍把 PDF 列为“本阶段明确未实现”，但 PDF 已被正式取消，不是待实现功能；同一行还把已完成的 HTML 列为未实现。
2. `README.md:333` 仍把“实现 HTML/PDF/JSON 报告”列为下一阶段任务；HTML 已实现，PDF 已取消。
3. `reports/__init__.py:1` 仍写“HTML/PDF/JSON planned”，与 PDF 取消决定直接冲突。
4. `docs/PHASE6_C2A_SECURITY_DEBT.md:673` 仍计划评估 PDF 导出策略，与 PDF 取消决定冲突。

### 7.2 `CODE_DOCUMENTATION_MISMATCHES = FOUND`

- 代码状态是：HTML exporter 已可用；PDF 只有枚举、schema CHECK 和服务层 metadata 接受，没有渲染器、没有 UI、没有正测试。
- 文档状态是：README 把 HTML 和 PDF 一起列为“未实现/下一阶段”，`reports/__init__.py` 把 HTML/PDF/JSON 一起列为“planned”。
- 因此代码与现行文档对 HTML/PDF 的状态描述不一致；这不是 PDF 功能“偷偷实现”，而是文档未随 C2B 和 PDF 取消同步。

### 7.3 `UNKNOWN`

- `ReportFormat.PDF` 与 schema `pdf` CHECK 是否应永久保留为兼容层，或应在未来版本移除：**UNKNOWN / 需人工决策**。
- 是否需要在服务 API 边界明确拒绝 PDF：**UNKNOWN / 需人工决策**。
- 历史记录中是否存在未跟踪的外部 PDF 计划文档：**UNKNOWN**；本轮只检查当前仓库文本。

### 7.4 额外相关但非 PDF 的现行文档陈旧点

`README.md:339` 仍写“第五阶段在此停止，不进入报告模块”，而 HTML 报告模块已经实现。它不属于 PDF 残留，但属于同一片现行文档的陈旧表述；P2B 若修订 README，应一并核对，不应把 PDF 清理扩大成无关重写。

---

## 8. Phase 6P-2B 最小候选范围

以下只是候选清单，本轮不实施。

### Candidate 1

- 文件：`README.md:166`
- 原因：PDF 已取消，HTML 已实现；当前“本阶段明确未实现”列表包含 PDF，且 HTML 状态也不准确。
- 建议动作：仅修订该条及紧邻说明，明确“HTML 已实现；PDF 已取消；JSON 未实现”；不改其他未实现项。

### Candidate 2

- 文件：`README.md:333`
- 原因：“下一阶段建议”仍要求实现 HTML/PDF/JSON。
- 建议动作：删除 PDF；把 HTML 标注为已实现；只保留 JSON 的未实现状态（若产品仍计划 JSON）。

### Candidate 3

- 文件：`reports/__init__.py:1`
- 原因：docstring 明确写“HTML/PDF/JSON planned”。
- 建议动作：改为“HTML exporter 已实现；PDF 已取消；JSON 未实现”，或只描述当前 HTML 边界。

### Candidate 4

- 文件：`docs/PHASE6_C2A_SECURITY_DEBT.md:673`
- 原因：仍把 PDF 列为 C2B 之后的评估对象。
- 建议动作：删除 PDF，只保留 JSON 导出策略的评估；不改变该债务的其他内容。

### 明确排除在 P2B 之外

- 不修改 `core/models/report.py` 的 PDF 枚举；
- 不修改 `database/schema.py` 的 `pdf` CHECK；
- 不修改 `services/report_service.py` 的 metadata-only 行为；
- 不修改 `reports/html_exporter.py`；
- 不修改任何测试；
- 不删除历史记录、验收报告、Git 记录或证据；
- 不新增 PDF 导出器、依赖或 UI。

---

## 9. 最终状态

```text
PDF_RESIDUE_INVESTIGATION = COMPLETED
ACTIVE_PDF_IMPLEMENTATION = NO
PDF_SPECIFIC_DEPENDENCY = NO
ACTIVE_PDF_UI = NO
ACTIVE_PDF_TESTS = NO

REPORT_FORMAT_PDF_PRESENT = YES
CURRENT_UI_EXPOSES_PDF = NO
CURRENT_SERVICE_ACCEPTS_PDF = YES

CURRENT_DOCUMENT_CONFLICTS = FOUND
DOCUMENTATION_CONFLICTS = FOUND
CODE_DOCUMENTATION_MISMATCHES = FOUND
HISTORICAL_RECORDS_TO_PRESERVE = YES

PHASE6_P2B_READINESS = CONDITIONAL_GO
```

**结论：** PDF 没有被实现，也没有被偷偷恢复；残留主要集中在 4 处现行文档表述和 1 个当前安全债务待决策项。历史记录必须保留。P2B 应只做最小文档修订，并先由人工确认是否保留 PDF 枚举/schema 兼容层。

本轮实际修改文件：

```text
docs/PHASE6_P2A_PDF_RESIDUE_INVESTIGATION.md   （仅新增本报告）
```

没有修改源码、测试、数据库、Schema、配置、`.gitignore` 或 Git 历史；没有执行 `git add`、`git commit`、`git remote add` 或 `git push`；没有开始 Phase 6P-2B 或 Phase 6D。
