# Phase 6P-1：PDF 功能关闭残留审计（READ-ONLY）

- 日期：2026-11-10（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：`0.5.0`
- 当前 Schema：`v5`
- 产品决策：**PDF = CANCELLED / OUT OF SCOPE**
- 本轮性质：**READ-ONLY AUDIT**
- 最终结论：**PDF 功能未实际实现，可以关闭；但当前文档仍把 PDF 写成未来工作，需要最小文档清理。**

```text
AUDIT_STATUS = COMPLETED_READ_ONLY
ACTIVE_PDF_IMPLEMENTATION = NONE
PDF_DEPENDENCY = NONE
PDF_GUI_ENTRY = NONE
SCHEMA_CHANGE_REQUIRED_FOR_CLOSURE = NO
RECOMMEND_6P2 = YES_DOC_ONLY
```

> 本报告不把“枚举里保留了 `pdf`”误判成“PDF 功能已实现”，也不把历史阶段报告里的
> “PDF 暂缓/等待字体”误读成当前产品计划。历史事实保持原样。

---

## 1. 调查范围

本轮只做只读调查，覆盖用户指定的 A–F：

1. **A. 生产代码**：`ReportFormat.PDF`、PDF exporter/renderer、`pdf_exporter.py`、
   `generate_pdf`、`render_pdf`、PDF MIME、`.pdf`、PDF 文件名逻辑、PDF GUI 调用。
2. **B. GUI**：PDF 格式选项、按钮、菜单、提示、占位入口。
3. **C. 依赖与资源**：`requirements.txt`、`pyproject.toml`、锁文件、PDF 专用库、
   PDF 中文字体/资源。
4. **D. 测试**：PDF 专项测试、`ReportFormat.PDF` 测试、PDF fixture。
5. **E. 当前产品文档**：README、ROADMAP、TODO、架构文档、当前开发计划、Phase 6 路线。
6. **F. 历史归档与验收记录**：Phase 6A 调查、PDF 可行性分析、历史验收报告、已关闭阶段文档。

本轮**没有**修改生产代码、测试、数据库或 Schema；**没有**删除文件；**没有**安装依赖；
**没有**运行完整回归；**没有**打开数据库。

---

## 2. 实际检查的文件与目录

### 2.1 生产代码

- `core/models/report.py`
- `services/report_service.py`
- `reports/html_exporter.py`
- `reports/__init__.py`
- `ui/report_page.py`
- `ui/settings_page.py`
- `ui/project_page.py`（仅检查 PDF 文件过滤器，不涉及报告导出）
- `database/schema.py`

### 2.2 测试

- `tests/test_report_html.py`
- `tests/test_report_service.py`
- `tests/test_ui_report.py`
- 以及其他测试中的 `.pdf` 授权文件路径（仅作为授权附件，不是报告 PDF）

### 2.3 文档与历史记录

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/PHASE5_ARCHITECTURE.md`
- `docs/acceptance/phase5_final/PHASE5_ARCHITECTURE.md`
- `docs/TEST_REPORT.md`
- `docs/PHASE6_B_REPORT.md`
- `docs/PHASE6_C1_HTML_INVESTIGATION.md`
- `docs/PHASE6_C2A_SECURITY_DEBT.md`
- `docs/PHASE6_C2B_STEP1_GUI_INVESTIGATION.md`
- `docs/PHASE6_C2B_STEP2_IMPLEMENTATION.md`
- `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md`
- `docs/PROJECT_HISTORY_PHASE6.md`
- `docs/acceptance/phase6_b_final/`（10 个文件）
- `docs/acceptance/phase5_final/`、`docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md`（历史引用）

### 2.4 目录与文件系统检查

- `reports/` 目录：只有 `__init__.py`、`html_exporter.py`、4 个 HTML 模板和 `__pycache__`；
  **没有** `pdf_exporter.py` 或 PDF 模板。
- `storage/reports/`：`.gitkeep` 与两个 HTML 报告；**没有** PDF 报告文件。
- `storage/acceptance/authorization.pdf`：授权附件，不是报告生成物。
- 字体资源：递归查找 `*.ttf`、`*.otf`、`*.woff`、`*.woff2`，结果为空。
- 依赖文件：根目录只有 `requirements.txt`；根目录**没有** `pyproject.toml`；
  没有 `*.lock` 文件。

### 2.5 只读命令证据

```text
ROOT_PYPROJECT=False
LOCK_FILES:
requirements.txt
PDF_FILES:
D:\挖漏洞\SRC-Research-Assistant\storage\acceptance\authorization.pdf
FONT_FILES:
(empty)
REPORT_FILES:
.gitkeep
project_1_project_summary_c296b0982419.html
project_2_project_summary_a312f270d9a9.html
```

依赖探测：

```text
WARNING: Package(s) not found: pillow, pymupdf, pypdf, pypdfium2, reportlab
```

代码搜索：

```text
(?i)reportlab|pillow|pymupdf|pypdf|pdfium|weasyprint|pdfkit|qtpdf|pdf_exporter|render_pdf|generate_pdf
→ No matches found
```

---

## 3. PDF 残留完整清单

### 3.1 ACTIVE_IMPLEMENTATION

**无。**

没有 PDF exporter、PDF renderer、PDF writer、PDF MIME 常量、PDF 文件命名逻辑或
PDF GUI 调用。`reports/html_exporter.py` 唯一公开写入口是 HTML：

- `reports/html_exporter.py:327-389` `write_html_report()`；
- `reports/html_exporter.py:405-411` `_validate_request()`；
- `reports/html_exporter.py:382` 固定 `report_format=ReportFormat.HTML`。

`_validate_request()` 对非 HTML 请求直接拒绝：

```python
if request.report_format is not ReportFormat.HTML:
    raise ValidationError("本阶段仅支持 HTML 报告")
```

### 3.2 ACTIVE_PRODUCT_PLAN

这些不是运行中的功能，但仍是**当前文档中的未来 PDF 计划**，必须改成
`PDF = CANCELLED / OUT OF SCOPE`。

| ID | 文件/位置 | 内容 | 建议 |
|---|---|---|---|
| P-01 | `README.md:166` | “本阶段明确未实现”列有 `HTML / PDF / JSON 报告` | UPDATE：改为 HTML 已实现；PDF 已取消；JSON 未获授权 |
| P-02 | `README.md:333` | “下一阶段建议”第 1 条仍是“实现 HTML/PDF/JSON 报告” | UPDATE：删除 PDF；不要写成 deferred |
| P-03 | `reports/__init__.py:1` | 模块 docstring 仍写 `HTML/PDF/JSON planned for a later phase` | UPDATE：改为 HTML-only；PDF/JSON 不在范围 |
| P-04 | `docs/PHASE6_C2A_SECURITY_DEBT.md:673` | “评估 PDF/JSON 导出是否沿用同一策略（C2B 之后）” | UPDATE：PDF 已取消；JSON 只有单独授权才评估 |

> P-03 是生产代码文件中的**一行 docstring**，不改变运行行为；它仍会误导后续开发者，
> 因此属于当前产品计划文字，而不是历史验收记录。

### 3.3 UNUSED_PREPARATION

这些是实现前预留的枚举/接口/Schema 值，当前没有任何实际 PDF 写入路径。

| ID | 文件/位置 | 事实 | 建议 |
|---|---|---|---|
| P-05 | `core/models/report.py:55-58` | `ReportFormat.PDF = "pdf"` 仍存在 | **KEEP（休眠兼容）**；当前无导出器、无 GUI 暴露；若未来强制 API 关闭，另行评估删除 |
| P-06 | `core/models/report.py:72-74` | `ReportFormat.options()` 会把 PDF 也列入选项 | **KEEP 但不用于 GUI**；当前 GUI 使用 `ReportType.options()`，未使用此方法 |
| P-07 | `services/report_service.py:104-108` | `get_snapshot_for_request()` 只校验格式是合法枚举，PDF 也可得到只读快照 | **KEEP（不构成 PDF 功能）**；没有写文件 |
| P-08 | `services/report_service.py:322-330` | `artifact_stub()` 会原样带回 `report_format`，但 `path=None`、`sha256=None`，不写文件 | **KEEP（元数据占位）**；不得被当作导出成功 |
| P-09 | `database/schema.py:98` | `reports.report_format CHECK(... 'pdf' ...)` 允许 PDF 值 | **KEEP（休眠兼容）**；当前代码没有 `INSERT INTO reports`，不需要为关闭 PDF 改 Schema |

### 3.4 HISTORICAL_RECORD（保留，不修改）

以下内容记录的是历史阶段事实、当时的限制或当时的建议。它们**不是**当前产品路线；
不得为了“清理 PDF”而改写已完成的阶段报告或归档。

| ID | 文件/位置 | 性质 | 处理 |
|---|---|---|---|
| H-01 | `docs/PHASE6_B_REPORT.md:8,83,507,519,554` | 阶段 B 历史设计：枚举、未实现、等待 ReportLab/字体 | KEEP；历史事实，当前决策已 supersede |
| H-02 | `docs/PROJECT_HISTORY_PHASE6.md:28,61,76,115-163,216,535,824,911,923,1060-1061,1084,1185` | Phase 6 历史重建，含 PDF 可行性和限制 | KEEP |
| H-03 | `docs/acceptance/phase6_b_final/PHASE6_B_FINAL_SUMMARY.md:50,203,209`、`PHASE6_B_ARCHITECTURE.md:44,202` | Phase 6B 封存记录，说明无 exporter/GUI | KEEP；属于已封闭阶段证据 |
| H-04 | `docs/PHASE5_ARCHITECTURE.md:11`、`docs/acceptance/phase5_final/PHASE5_ARCHITECTURE.md:11` | 第五阶段边界“不含 HTML/PDF/JSON 报告” | KEEP |
| H-05 | `docs/TEST_REPORT.md:148` | 第二阶段测试报告“未实现 HTML/PDF/JSON 报告” | KEEP |
| H-06 | `docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md:240` | 第四阶段历史建议“再做 HTML/PDF/JSON 报告” | KEEP；历史建议不等于当前计划 |
| H-07 | `docs/PHASE6_C1_HTML_INVESTIGATION.md:382,596` | C1 历史调查：PDF 证据图不支持；建议 C2 只做 HTML | KEEP；与当前 PDF 关闭一致 |
| H-08 | `docs/PHASE6_C2B_STEP1_GUI_INVESTIGATION.md:21,247,302,438,479,544,568,630` | C2B Step 1 历史调查；其中 `:438` 曾建议设置页写“PDF/JSON 尚未实现” | KEEP；历史建议已被当前产品决策 supersede，不修改阶段报告 |
| H-09 | `docs/PHASE6_C2B_STEP2_IMPLEMENTATION.md:4,103,229,251`、`docs/PHASE6_C2B_STEP3_ACCEPTANCE.md:30,155,186` | C2B Step 2/3 边界“不包含 PDF/JSON” | KEEP；这是范围声明，不是未来计划 |
| H-10 | `docs/PHASE6_C2A_R1_FIX_1.md:450,487`、`docs/PHASE6_C2A_SECURITY_DEBT.md:673` 以外的 C2A/R1 安全报告 | “未执行 PDF/JSON”历史边界 | KEEP；不要修改历史安全证据 |

### 3.5 NO_ACTION

这些出现 `pdf` 字样，但不是报告 PDF 功能或未来入口。

| ID | 文件/位置 | 原因 |
|---|---|---|
| N-01 | `ui/report_page.py:318-327` | `_request_for()` 固定 `ReportFormat.HTML`；页面没有 PDF 选项 |
| N-02 | `reports/html_exporter.py:405-411` | 非 HTML 主动拒绝；这是安全保护，不是 PDF 实现 |
| N-03 | `tests/test_report_html.py:352-358` | 用 `ReportFormat.PDF` 做**负向测试**，证明 HTML exporter 拒绝 PDF；保留 |
| N-04 | `ui/project_page.py:301` | 授权文件选择器允许 `*.pdf`；这是授权附件，不是报告导出 |
| N-05 | `storage/acceptance/authorization.pdf` | 授权附件，不是报告生成物；不得删除 |
| N-06 | `tests/test_report_service.py:55,321`、`tests/test_ui.py:71`、`tests/test_ui_dialogs.py:31`、`tests/test_scope_validator.py:144`、`tests/test_project_service.py:98`、`tests/test_authorization_service.py:117`、`tests/conftest.py:125` | `.pdf` 仅作为授权文件路径，不涉及报告 |
| N-07 | `tools/capture_ui.py:86,95`、`tools/run_acceptance.py:114` | 演示/验收授权附件路径，不是报告 |
| N-08 | `docs/PHASE6_C2A_SECURITY_DEBT.md:673` 之外的 C2A/C2B 安全边界文字 | “未进入 PDF/JSON”属于范围声明，无需处理 |

> **无遗漏说明：** 本轮对所有 `.py` 和 `.md` 的 `(?i)pdf` 命中做了分组：
> 已实现功能、未使用准备、历史记录、无动作四类；授权附件路径不按报告 PDF 处理。

---

## 4. 分类统计

| 分类 | 数量/结论 |
|---|---|
| ACTIVE_IMPLEMENTATION | **0** |
| ACTIVE_PRODUCT_PLAN | 4 处（README 2 处、`reports/__init__.py` 1 处、安全债务文档 1 处） |
| UNUSED_PREPARATION | 5 处（枚举、options、服务接收、artifact stub、Schema CHECK） |
| HISTORICAL_RECORD | 10 组历史文档/归档（不逐行修改） |
| NO_ACTION | 授权附件、测试路径、边界声明等 |

---

## 5. 当前是否存在实际 PDF 功能？

**否。**

- 没有 `reports/pdf_exporter.py`；
- 没有 `generate_pdf()` / `render_pdf()`；
- 没有 PDF MIME 常量；
- 没有 PDF 文件命名、写入或原子发布逻辑；
- 没有 PDF 模板；
- 没有 PDF GUI 调用；
- `storage/reports/` 只有 HTML 报告，没有 `.pdf` 报告；
- 唯一 `.pdf` 文件是 `storage/acceptance/authorization.pdf`（授权附件）。

`ReportFormat.PDF` 只是一个枚举值；`ReportService.get_snapshot_for_request()` 可以接受
这个枚举并返回只读快照，`artifact_stub()` 可以生成 `path=None` 的元数据占位，但
**没有文件写入**，不构成 PDF 功能。`html_exporter` 对 PDF 明确拒绝。

---

## 6. 当前是否存在 PDF 专用依赖？

**否。**

- `requirements.txt` 只有 PySide6-Essentials、PyYAML、Jinja2、bandit、pip-audit、
  semgrep、pytest、pytest-qt；没有 ReportLab、Pillow、PyMuPDF、pypdf、pypdfium2、
  WeasyPrint、pdfkit。
- 根目录没有 `pyproject.toml`，没有锁文件。
- 当前虚拟环境 `pip show` 结果：

```text
WARNING: Package(s) not found: pillow, pymupdf, pypdf, pypdfium2, reportlab
```

- 代码搜索没有上述库或 PDF 导出函数的导入。

---

## 7. 当前是否存在 PDF GUI？

**否。**

- `ui/report_page.py` 没有“报告格式”下拉框；没有 PDF 按钮、菜单、提示或占位入口；
- 导出按钮文本是“导出 HTML”，只调用 `write_html_report()`；
- `_request_for()` 固定 `ReportFormat.HTML`；
- `ui/project_page.py:301` 的 `*.pdf` 是授权文件选择器，不是报告导出；
- `ui/settings_page.py:84-86` 仍有“报告导出 未开发”的旧状态文字，但**没有 PDF 字样**，
  也不构成 PDF GUI 入口；它属于另一个“报告状态文案过时”问题，不在本轮 PDF 清理范围。

因此：**没有活跃 PDF GUI 入口。**

---

## 8. 当前路线文档问题

### 8.1 明确的活跃 PDF 未来计划

`README.md` 仍然把 PDF 写在“未实现”和“下一阶段建议”中：

- `README.md:166`：`HTML / PDF / JSON 报告；`
- `README.md:333`：`实现 HTML/PDF/JSON 报告，并复用第五阶段漏洞/证据关联。`

这两处是**当前产品路线**，不是历史报告；与 `PDF = CANCELLED / OUT OF SCOPE` 冲突，
必须更新。README 同时有过时的报告状态：

- `README.md:5` 仍说“不包含报告生成”；
- `README.md:43` 仍把报告中心列为未开发占位；
- `README.md:292` 仍说 `reports/` 未启用。

这些虽然不是 PDF 专属，但在同一次文档清理中应避免继续误导。

### 8.2 当前安全债务文档

`docs/PHASE6_C2A_SECURITY_DEBT.md:673` 仍建议评估 PDF/JSON 导出。PDF 已取消，
该句应改为“PDF 已取消；JSON 仅在单独授权后评估”。

### 8.3 历史阶段文档

`docs/PHASE6_B_REPORT.md`、`docs/PROJECT_HISTORY_PHASE6.md`、Phase 5/6B 归档中的
“PDF 被字体/ReportLab 阻止”是历史事实；它们不构成当前产品计划，**不修改**。

### 8.4 未发现独立的 ROADMAP/TODO

项目根目录和 `docs/` 未发现独立的 `ROADMAP.md` 或 `TODO.md`；当前路线主要落在
`README.md`。因此 PDF 路线清理应以 README 为主，不能靠修改历史阶段报告来代替。

---

## 9. 历史记录处理原则

1. **历史事实不篡改。** Phase 5、Phase 6B 的验收/封存记录、`docs/PROJECT_HISTORY_PHASE6.md`
   以及 C1/C2A/C2B 的阶段报告保持原样。
2. **历史事实 ≠ 当前计划。** 历史报告说“PDF 等待字体/ReportLab”只说明当时状态，
   不表示今天仍在等待；当前决策是 CANCELLED。
3. **不为了让目录“干净”而删除历史证据。**
4. **不修改已封闭阶段的验收结论、测试数字、文件哈希或归档清单。**
5. 如需提示读者，可在当前文档中写明“历史报告中的 PDF 计划已被本决策取消”，
   而不是回写历史报告。

因此：**不需要修改任何已关闭阶段的历史验收报告。**

---

## 10. 推荐的最小清理范围

### 10.1 建议执行（仅文档/注释，不改运行行为）

1. **`README.md`**
   - `:5`：把“不包含报告生成”改为“已包含 HTML 报告；PDF 已取消，JSON 未授权”；
   - `:43`：把报告中心从“未开发占位”改为“已实现 HTML 报告中心”；
   - `:166`：把 `HTML / PDF / JSON 报告` 改为“HTML 报告（已实现）；PDF 已取消；JSON 未授权”；
   - `:292`：把 `reports/` 注释改为“HTML 报告边界；PDF 不在范围”；
   - `:333`：删除“HTML/PDF/JSON”中的 PDF 和 JSON，明确 HTML 已完成、PDF CANCELLED。
2. **`reports/__init__.py:1`**
   - 改为类似：`"""HTML-only report boundary; PDF and JSON are out of scope."""`
3. **`docs/PHASE6_C2A_SECURITY_DEBT.md:673`**
   - 改为“PDF 已取消；JSON 仅在单独授权后评估”，避免未来工作暗示。

### 10.2 不建议执行

- 不修改 `ReportFormat` 的 PDF 枚举；
- 不修改 `reports` 表的 `CHECK(... 'pdf' ...)`；
- 不新增 schema v6；
- 不修改 `tests/test_report_html.py` 的 PDF 负向测试；
- 不修改 C2A/R1 导出器、模板、ReportService、ReportRepository；
- 不修改任何历史阶段报告/验收归档；
- 不安装 ReportLab/Pillow/PDF 字体；
- 不删除 `storage/acceptance/authorization.pdf`（授权附件，不是报告）。

### 10.3 为什么保留枚举和 Schema

当前 PDF 没有实际导出路径；删除枚举或 Schema 值不会提高安全性，反而会引入
测试改动、API 兼容性问题和潜在 schema v6 迁移。最小、安全的关闭方式是：

- 应用层保持“HTML only” guard；
- GUI 不暴露 PDF；
- 文档明确 CANCELLED；
- 枚举/Schema 作为休眠兼容值保留，并由本审计记录其性质。

如未来产品要求“连枚举和 Schema 值也移除”，那应作为单独的 API/Schema 清理，
不能被描述为本次 PDF 功能关闭的必要条件。

---

## 11. 不建议修改的内容

- `docs/PHASE6_B_REPORT.md`、`docs/PROJECT_HISTORY_PHASE6.md`、Phase 5/6B 归档；
- `docs/PHASE6_C2B_STEP1_GUI_INVESTIGATION.md:438` 等历史建议文字；
- 任何历史验收报告、测试报告、文件清单、SHA-256；
- `reports/html_exporter.py` 的 HTML-only guard；
- `tests/test_report_html.py:352-358` 的 PDF 负向测试；
- `database/schema.py` 的 `reports.report_format` CHECK；
- `ui/project_page.py` 的授权附件 `*.pdf` 过滤器；
- `storage/acceptance/authorization.pdf`。

---

## 12. 是否建议进入 Phase 6P-2？

**建议进入，但仅限文档/注释清理。**

```text
PHASE_6P_2_RECOMMENDATION = YES_DOC_ONLY
CODE_CHANGE_REQUIRED = NO
SCHEMA_CHANGE_REQUIRED = NO
DEPENDENCY_CHANGE_REQUIRED = NO
TEST_CHANGE_REQUIRED = NO
```

理由：当前没有实际 PDF 功能、没有 PDF 依赖、没有 PDF GUI；唯一必须处理的是
README、`reports/__init__.py` docstring 和安全债务文档中的“PDF future”措辞。
完成后即可把 PDF 状态正式记录为 CANCELLED，而不需要改代码或数据库。

---

## 13. 本轮实际修改文件清单

```text
A  docs/PHASE6_PDF_CLOSURE_AUDIT.md
```

没有其他文件被修改。

最终声明：

```text
Production code modified: NO
Tests modified: NO
Database modified: NO
Schema modified: NO
```

本轮到此停止，等待人工审核；不启动 SRC 提交辅助、JSON 实施或任何 PDF 功能。
