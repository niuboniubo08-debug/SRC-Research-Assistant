# Phase 6-R0-A：项目历史资料与阶段状态盘点

> 本报告是**历史资料调查**，不是当前代码验收。报告中出现的“通过”“已实现”“已修复”等词，除非明确标为 `CURRENTLY_CONFIRMED`，均只表示**历史报告记录**；当前代码行为由 R0-B 代码核查确认。

## 0. 调查标识与结论摘要

| 项目 | 值 |
|---|---|
| 调查时间 | `2026-11-13T12:41:31+08:00`（Asia/Shanghai） |
| 项目路径 | `D:\挖漏洞\SRC-Research-Assistant` |
| 分支 | `main` |
| 调查开始时 HEAD | `bffb5ac82bbebe7fef5992f87ff90494c9776ace` |
| 调查开始时工作区 | staged 0；unstaged 1（`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`）；untracked 2（`docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`、`docs/PHASE6_D1B_3_JSON_DECISION.md`） |
| 与 origin/main | ahead 5，behind 0 |
| 调查性质 | READ_ONLY，未运行测试，未修改代码/测试/数据库/Schema/已有文档 |
| 唯一新增文件 | `docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md` |
| 总体结论 | `PHASE6_R0_A_STATUS=COMPLETED`；历史资料**部分完整**；发现 8 组需要记录的冲突/陈旧记录；R0-B 可据此建立代码核查索引 |

### 0.1 最重要的五个事实

1. **Phase 1 没有独立的源码、数据库或测试快照**。它是在 Phase 2 交付过程中补齐并被合并验收的基础框架；不能把“Phase 1 通过”理解为存在独立保留下来的 Phase 1 代码库。证据：`docs/acceptance/ACCEPTANCE_REPORT.md:14,20-150,327-341`；`docs/PHASE2_CHANGES.md:3-9`；`docs/PROJECT_HISTORY_STEP1.md:12-16,222-244,617-623`。
2. **Phase 3 是“部分通过”**：Bandit、任务、Finding、UI 均通过；Semgrep 1.183.0 已安装但当前 Windows 会话启动即失败，退出码 2，错误为 `CertOpenSystemStore returned NULL`。没有真实 Semgrep 结果，也没有 Linux/WSL 补验。证据：`docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md:7,46-63,96-103,200-219`。
3. **Phase 4 通过，但有明确的数据质量限制**：pip-audit JSON 不提供 CVSS/severity 和精确 affected range，应用保守使用 `medium` 并标记 `severity_source=conservative-default`；pyproject 只支持 PEP 621 `[project].dependencies`。证据：`docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md:7,80-109,205-210`。
4. **Phase 5 通过，Phase 5 归档核心文件哈希匹配，但整个工作区 Manifest 不能精确复现**：`code_quality.json` 的当前哈希与旧 Manifest 不同（P6B-EX-001），`storage/_rebuild_manifest.py` 已缺失（P6B-EX-002）。证据：`docs/acceptance/phase5_final/PHASE5_FINAL_SUMMARY.md:7,57,120-129`；`docs/acceptance/phase6_b_final/PHASE6_B_EXCEPTION_REGISTER.md:29-152`。
5. **Phase 6 的 PDF 已取消，JSON 已延期且未获批；HTML 报告中心已实现并验收，但仍有 symlink/TOCTOU 等已记录限制**。证据：`docs/PHASE6_P2B_FINAL_ACCEPTANCE.md:90-123,187-203`；`docs/PHASE6_D1B_3_JSON_DECISION.md:6-18,109-171,266-282`；`docs/PHASE6_C2B_STEP3_ACCEPTANCE.md:176-186`；`docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:13,21-27,675-687`。

---

## 1. 调查范围、方法与限制

### 1.1 范围

- `docs/` 及其 `docs/acceptance/`、`docs/screenshots/` 下的阶段报告、验收记录、测试报告、架构说明、Manifest、数据库信息、决策记录。
- Phase 1–6 的历史资料；不以历史报告直接宣布当前代码状态。
- Git 工作区状态只读记录；不暂存、不提交、不清理。

### 1.2 方法

1. 先记录 Git 状态与 `docs/` 文件元数据：79 个 `.md`、10 个 `.json`、4 个 `.txt`、12 个 `.png`、2 个 `.db`（另有 WAL/SHM）。
2. 读取每个阶段的主报告、验收/测试/架构/清单/决策报告的正文；目录和文件名只用于索引，不作为内容结论。
3. 对每个发现标注证据类型：
   - `HISTORICAL_CONFIRMED`：历史报告明确记录；
   - `CURRENTLY_CONFIRMED`：本次只读可确认的文件/内容事实；
   - `REQUIRES_CODE_AUDIT`：必须检查当前代码；
   - `CONFLICT`：不同报告或报告与当前文件冲突；
   - `UNKNOWN`：资料不足或无法确认。
4. 对 Manifest 只做只读比对；没有修复、补写或删除。

### 1.3 限制

- 没有运行 pytest，没有重新执行任何历史验收；历史测试数字只作历史证据。
- 没有读取或修改业务数据库；数据库状态只引用历史报告。
- 没有检查当前代码是否仍与历史报告一致；相关项统一标记 `REQUIRES_CODE_AUDIT`。
- Phase 1 没有独立快照，Phase 6F/6G 没有报告；这些是资料缺口，不是“功能已通过”的证明。

---

## 2. Phase 1–6 历史报告文件索引

### 2.1 文档总量

| 类别 | 数量 | 说明 |
|---|---:|---|
| Markdown | 79 | 阶段报告、验收、架构、Git 过程记录、历史重建 |
| JSON | 10 | 阶段验收、入口/UI 验收、Phase 5 最终验收、code_quality |
| TXT | 4 | Phase 5/6B Manifest、项目树、Phase 6B 测试输出 |
| PNG | 12 | 验收截图；包含 UI、扫描、依赖、证据、漏洞页面 |
| SQLite | 2 | `docs/acceptance` 下的历史验收数据库副本 |
| 其他 | 4 | 2 个 `.db-wal`、2 个 `.db-shm`（不是独立数据库备份） |

### 2.2 关键报告索引

| 阶段 | 关键文件 | 大小/性质 | 读取结论 |
|---|---|---|---:|
| Phase 1–2 | `docs/acceptance/ACCEPTANCE_REPORT.md` | 13,352 B；合并验收 | Phase 1/2 均通过；40 pytest；31/31 业务验收 |
| Phase 1–2 | `docs/PHASE2_CHANGES.md` | 7,961 B；交付说明 | 明确开始时无 Phase 1 项目；Phase 2 功能与 v2 迁移 |
| Phase 1–2 | `docs/PROJECT_HISTORY_STEP1.md` | 36,723 B；历史重建 | Phase 1 `reconstructed_with_gaps`；Phase 2 `confirmed` |
| Phase 3 | `docs/acceptance/PHASE3_ACCEPTANCE_REPORT.md` | 10,354 B；验收 | **部分通过**；Semgrep 不可用是唯一主因 |
| Phase 3 | `docs/acceptance/PHASE3_TEST_REPORT.md` | 6,875 B；测试 | 81 passed / 0 failed / 0 skipped；16.74s |
| Phase 3 | `docs/PHASE3_ARCHITECTURE.md` | 4,659 B；架构 | 本地路径校验、Bandit/Semgrep 统一接口 |
| Phase 4 | `docs/acceptance/PHASE4_ACCEPTANCE_REPORT.md` | 9,028 B；验收 | **通过**；pip-audit 2.10.1；105 tests |
| Phase 4 | `docs/acceptance/PHASE4_TEST_REPORT.md` | 5,651 B；测试 | 24 项新增；105 passed |
| Phase 4 | `docs/PHASE4_ARCHITECTURE.md` | 5,527 B；架构 | 依赖发现、pip-audit、Finding 映射 |
| Phase 5 | `docs/acceptance/phase5_final/PHASE5_FINAL_SUMMARY.md` | 5,131 B；收尾 | **收尾完成**；126 passed/1 skipped；41 findings/3 evidence |
| Phase 5 | `docs/acceptance/phase5_final/PHASE5_ACCEPTANCE_REPORT.md` | 11,506 B；验收 | **通过**；38.61s 记录与最终 36.25s 有历史差异 |
| Phase 5 | `docs/acceptance/phase5_final/PHASE5_TEST_REPORT.md` | 4,281 B；测试 | 最终测试报告 |
| Phase 5 | `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` | 28,016 B；清单 | 253 条记录、200 个唯一路径；两个哈希/缺失例外 |
| Phase 6B | `docs/acceptance/phase6_b_final/PHASE6_B_FINAL_SUMMARY.md` | 7,594 B；封存总结 | `sealed_with_recorded_exception`；但归档数量段落后于实际 |
| Phase 6B | `docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt` | 3,066 B；清单 | **当前有效：14 条目、10 个归档文件** |
| Phase 6B | `docs/acceptance/phase6_b_final/PHASE6_B_EXCEPTION_REGISTER.md` | 5,160 B；例外 | P6B-EX-001/002 的正式记录 |
| Phase 6B | `docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json` | 7,171 B；JSON | 归档段为旧值（9/11），与当前 Manifest 冲突 |
| Phase 6C-1 | `docs/PHASE6_C1_HTML_INVESTIGATION.md` | 27,914 B；调查 | 设计可行；Jinja2/autoescape/无远程资源 |
| Phase 6C-1R | `docs/PHASE6_C1_R_TEST_ENV_REPORT.md` | 13,033 B；环境 | pytest ACL 根因与专用临时目录恢复；144/1 |
| Phase 6C-2A | `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md` | 28,591 B；安全收尾 | `PASS_WITH_LIMITATIONS`；SEC-02/TOCTOU 等 UNKNOWN |
| Phase 6C-2A | `docs/PHASE6_C2A_SECURITY_DEBT.md` | 33,775 B；债务 | 0 high/0 critical；多项已记录债务 |
| Phase 6C-2B | `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md` | 10,501 B；验收 | HTML GUI PASS_WITH_LIMITATIONS；203/7 |
| Phase 6C-2B | `docs/PHASE6_C2B_STEP2_REVIEW.md` | 16,809 B；补充审查 | 曾发现快照新鲜度 FAIL；后续修复 |
| Phase 6P | `docs/PHASE6_PDF_CLOSURE_AUDIT.md` | 18,475 B；审计 | PDF 未实现；取消决策；仅文档残留 |
| Phase 6P | `docs/PHASE6_P2B_FINAL_ACCEPTANCE.md` | 5,464 B；验收 | PDF 取消、JSON 未批准；P2B 完成 |
| Phase 6D-1 | `docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md` | 22,733 B；架构调查 | JSON 可接入 `reports/` 适配层；未实现 |
| Phase 6D-1 | `docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md` | 15,033 B；需求 | `INSUFFICIENT_EVIDENCE` |
| Phase 6D-1 | `docs/PHASE6_D1B_3_JSON_DECISION.md` | 7,522 B；决策 | `JSON_REPORT_STATUS=DEFERRED`；未批准 |
| 6 历史重建 | `docs/PROJECT_HISTORY_PHASE6.md` | 47,905 B；历史重建 | 记录 Phase 6A–C2 状态；明确 C2 未开始的历史边界 |

### 2.3 明确缺失或不可用

| 目标 | 状态 | 说明 |
|---|---|---|
| Phase 1 独立源码快照 | `MISSING` | `backups/` 无 Phase 1 归档；`PROJECT_HISTORY_STEP1.md:227` |
| Phase 1 独立 pytest 记录 | `MISSING` | 只有合并验收的 40 项；`PROJECT_HISTORY_STEP1.md:230,322-340` |
| Phase 1 独立版本号/时间线 | `MISSING/UNKNOWN` | 无独立快照；只能从 Phase 2 0.2.0 反推 |
| `PHASE1_*` 专用报告 | `MISSING` | 未找到；合并报告与历史重建替代 |
| Phase 6F 实施/验收材料 | `MISSING` | `docs/` 无 `PHASE6_F*` 文件；全文检索无 Phase 6F 命中 |
| Phase 6G 实施/验收材料 | `MISSING` | 同上 |
| Phase 6D/E 详细计划 | `UNKNOWN` | `PROJECT_HISTORY_PHASE6.md:1040` 明确“现有材料只声明未开始” |

> 说明：`MISSING` 只表示**没有找到报告/快照**，不表示功能一定未实现或一定已实现；需要 R0-B 代码核查。

---

## 3. 各阶段已完成工作

### 3.1 Phase 1：基础框架

`HISTORICAL_CONFIRMED`

- 项目目录、入口、配置、日志、存储骨架；
- 10 页 PySide6 主窗口、导航、页面切换、正常关闭；
- SQLite v1，7 张基础表：`projects`、`authorizations`、`scan_tasks`、`findings`、`evidence`、`reports`、`scan_logs`；
- 实际生产入口 + offscreen Qt 验收；原生窗口截图受自动化会话限制。
- 证据：`ACCEPTANCE_REPORT.md:14,20-150,327-341`；`PROJECT_HISTORY_STEP1.md:222-309`。

### 3.2 Phase 2：项目管理、授权与范围控制

`HISTORICAL_CONFIRMED`

- 项目 CRUD、搜索、筛选、排序、当前项目；
- 授权创建/确认/过期/撤销/历史/有效性；
- ScopeAsset：domain/IP/local_folder/local_project；精确匹配、无通配符；
- ScopeValidator 默认拒绝、fail-closed、跨项目隔离、审计；
- v2 新增 `scope_assets`、`authorization_history`、`app_settings`，共 10 表；
- 31/31 业务验收；最终 pytest 40 passed。
- 证据：`ACCEPTANCE_REPORT.md:152-251,343-359`；`PHASE2_CHANGES.md:11-80`；`PROJECT_HISTORY_STEP1.md:355-490`。

### 3.3 Phase 3：本地 Python 源代码审计

`HISTORICAL_CONFIRMED` / `PARTIAL`

- Bandit 1.9.4 真实集成；本地路径 `ScopeValidator` 复用；`shell=False`、超时、取消、输出上限；
- Semgrep 接口、项目内本地规则、JSON 解析、统一 Finding；
- 扫描任务、Finding、项目隔离、敏感值脱敏、UI；
- 81 passed / 0 failed / 0 skipped（16.74s）；
- **Semgrep 实际不可用**，任务失败且不伪造结果；阶段结论“部分通过”。
- 证据：`PHASE3_ACCEPTANCE_REPORT.md:7,46-63,96-103,200-219`；`PHASE3_TEST_REPORT.md:16,42-50,57,142-146`。

### 3.4 Phase 4：Python 依赖漏洞审计

`HISTORICAL_CONFIRMED`

- 发现 `requirements.txt` / `pyproject.toml`；pip-audit 2.10.1；项目自有 cache/TMP；
- JSON 解析、按依赖+漏洞编号去重、Finding 映射、ScanTask、SQLite；
- requirements 与 PEP 621 pyproject 各 5 依赖 / 19 唯一漏洞；
- 105 passed；
- 限制：severity 缺省 medium、无 CVSS、无精确 affected range、pyproject 范围有限。
- 证据：`PHASE4_ACCEPTANCE_REPORT.md:7,29-51,80-109,205-210`；`PHASE4_TEST_REPORT.md:129-134`（测试总数）。

### 3.5 Phase 5：漏洞管理与证据中心

`HISTORICAL_CONFIRMED`

- 统一 Bandit/Semgrep/pip-audit Finding；
- 六种状态、状态历史、人工备注、项目隔离；
- 证据文本/文件、受管复制、UUID、SHA-256、路径/链接/50 MB 检查；
- v5：11 表、18 索引；验收库 41 findings / 3 evidence / 2 history / 0 FK；
- 126 passed / 1 skipped（最终收尾记录 36.25s；较早验收记录 38.61s）。
- 证据：`PHASE5_FINAL_SUMMARY.md:23-60,73-129,158-171`；`PHASE5_ACCEPTANCE_REPORT.md:7,207-225,245-311`。

### 3.6 Phase 6：报告中心与后续决策

`HISTORICAL_CONFIRMED`（除个别冲突）

| 子阶段 | 已完成工作 | 状态 |
|---|---|---|
| 6A | 报告中心可行性与架构调查；无独立产物 | `UNKNOWN/MISSING`（无独立报告） |
| 6B | ReportSnapshot/Repository/Service；只读、项目隔离；18 新增测试 | `sealed_with_recorded_exception` |
| 6C-1 | HTML 环境与安全架构调查；Jinja2/autoescape/无远程资源/原子写入设计 | `completed`（设计） |
| 6C-1R | pytest ACL 根因与专用临时目录恢复 | `completed` |
| 6C-2A | HTML exporter + 4 模板；安全审查与最小修复；R1 叶节点 symlink 修复 | `CLOSED_WITH_RECORDED_LIMITATIONS` |
| 6C-2B | ReportPage GUI、ReportService 注入、预览、单写者、覆盖确认 | `PASS_WITH_LIMITATIONS` |
| 6P-1/2A | PDF 关闭审计/残留调查 | `completed`；PDF=`CANCELLED` |
| 6P-2B | README、reports init、Security Debt、结构注释文档修订 | `P2B_FINAL_ACCEPTANCE=PASS` |
| 6D-1A | Report 数据流与 JSON 接入点调查 | `PASS`；无 JSON 实现 |
| 6D-1B | JSON 业务需求核查与最终决策 | `DEFERRED`；未批准 |
| 6F/6G | 未找到实施或验收材料 | `MISSING` |

---

## 4. 各阶段历史遗留问题与债务

| ID | 阶段 | 问题 | 证据 | 历史状态 | R0-B 处理建议 |
|---|---|---|---|---|---|
| P3-01 | Phase 3 | Semgrep 1.183.0 在当前 Windows 会话启动失败；无真实 Semgrep 运行 | `PHASE3_ACCEPTANCE_REPORT.md:7,49-63,96-103,200-219` | `HISTORICAL_CONFIRMED`；阶段部分通过 | 检查 `scanners/semgrep_scanner.py`、规则、测试；确认是否仅环境问题 |
| P3-02 | Phase 3 | 路径存在/目录/权限/`..` 有测试；**没有 Phase 3 独立 symlink 测试记录** | `PHASE3_TEST_REPORT.md:68,79-109,142-146` | `MISSING/UNKNOWN`（该阶段） | 检查路径/链接测试是否在 Phase 3 实际存在；不要与 Phase 5 链接限制混为一谈 |
| P4-01 | Phase 4 | pip-audit 无 CVSS/severity；应用保守 `medium` | `PHASE4_ACCEPTANCE_REPORT.md:205-208` | `HISTORICAL_CONFIRMED` | 检查 `pip_audit_scanner` 的 severity 映射和 metadata |
| P4-02 | Phase 4 | 无精确 affected version range | `PHASE4_ACCEPTANCE_REPORT.md:207-208` | `HISTORICAL_CONFIRMED` | 检查 Finding metadata 是否只保存当前命中版本 |
| P4-03 | Phase 4 | pyproject 仅支持 PEP 621 `[project].dependencies` | `PHASE4_ACCEPTANCE_REPORT.md:210` | `HISTORICAL_CONFIRMED` | 检查转换器/依赖发现器边界 |
| P5-01 | Phase 5 | 真实文件 symlink 创建被 Windows `WinError 1314` 拒绝；`is_symlink` 分支为单元模拟 | `PHASE5_ACCEPTANCE_REPORT.md:7,247-255,299-311`；`PHASE5_FINAL_SUMMARY.md:83-90,122-123` | `HISTORICAL_CONFIRMED` | 检查 evidence 路径检查；在可用环境补动态链接测试 |
| P5-02 | Phase 5 | 工作区 Manifest 不能精确复现：`code_quality.json` 哈希变化；`_rebuild_manifest.py` 缺失 | `PHASE5_FILE_MANIFEST.txt:66,103,171,276`；`PHASE6_B_EXCEPTION_REGISTER.md:36-152` | `CONFLICT/UNKNOWN`；已记录 P6B-EX-001/002 | 不修复历史；核对当前 Manifest/文件 |
| P6B-01 | Phase 6B | `PHASE6_B_ACCEPTANCE.json` 归档字段为旧值：9 files / 11 entries / 不覆盖 seal docs | `PHASE6_B_ACCEPTANCE.json:18-31` | `CONFLICT`（当前实际 10/14） | 对照当前 Manifest；不修改历史 JSON |
| P6B-02 | Phase 6B | `PHASE6_B_FINAL_SUMMARY.md` 仍写归档 9 files、Manifest 未更新 | `PHASE6_B_FINAL_SUMMARY.md:183-191` | `CONFLICT`（当前实际 10 files、14 entries） | 以当前 `PHASE6_B_FILE_MANIFEST.txt:37-39` 与实际文件为准 |
| P6B-03 | Phase 6B | `code_quality.json` 由 Phase B 质量检查重新生成；旧哈希 `5993...`，当前 `f0d0...` | `PHASE6_B_EXCEPTION_REGISTER.md:46-86` | `EXPLAINED_RECORDED` | 不要求回滚；R0-B 只读核对产品计数 59 |
| P6B-04 | Phase 6B | `storage/_rebuild_manifest.py` 历史存在但当前缺失 | `PHASE6_B_EXCEPTION_REGISTER.md:93-136` | `ACCEPTED_UNRESOLVED` | 不要伪造文件；记录为历史缺口 |
| C2A-01 | Phase 6C-2A | SEC-02 root/leaf symlink 动态验证受 `WinError 1314` 限制；父级 reparse/TOCTOU UNKNOWN | `PHASE6_C2A_SECURITY_FINAL_REVIEW.md:13,21-27,362-479,557-566` | `CLOSED_WITH_RECORDED_LIMITATIONS` | 检查 `reports/html_exporter.py`、测试；不要宣称无条件安全 |
| C2A-02 | Phase 6C-2A | SEC-03 CSP 未修复；SEC-06 语义脱敏未做；SEC-04 统计标签残余 | `PHASE6_C2A_SECURITY_FINAL_REVIEW.md:557-566` | `RECORDED_LIMITATION` | 作为债务，不阻塞当前 HTML 关闭；R0-B 记录 |
| P6P-01 | Phase 6P | PDF 已取消，但 `ReportFormat.PDF`/schema CHECK 作为兼容元数据保留；无 exporter/UI/依赖 | `PHASE6_P2A_PDF_RESIDUE_INVESTIGATION.md:7-19,155-221,344-352`；`PHASE6_P2B_FINAL_ACCEPTANCE.md:90-123` | `CANCELLED / DORMANT_COMPATIBILITY` | 不重新开发；核查是否仍有活动 GUI/导出路径 |
| P6D-01 | Phase 6D-1 | JSON 业务需求不足；JSON 未实现、未批准、延期 | `PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`（结论段）；`PHASE6_D1B_3_JSON_DECISION.md:6-18,109-171,266-282` | `DEFERRED / NOT_APPROVED` | 不得因“技术上可做”而开发；R0-B 只检查无 JSON 实现残留 |
| P6D-02 | Phase 6D-1 | D1A 提出的 JSON 接入点是未来 `reports/` 适配层，不是已批准契约 | `PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md:369-432,614-642,687-710` | `HISTORICAL_CONFIRMED` | 记录为设计建议，不作为当前需求 |
| DOC-01 | Phase 6 | `README.md:5` 仍写“不包含……报告生成能力”，与同文件 HTML 已实现表述冲突 | `README.md:5,18,43,162` | `CONFLICT`（当前文件） | R0-B 记录；不修改 README |
| DOC-02 | Phase 6 | `README.md:34` 仍写 `126 passed / 1 skipped`，与后期 203/7 等测试记录不一致 | `README.md:34`；`PHASE6_P2B_6A_FULL_TEST.md:90-104` | `CONFLICT/STALE` | 检查是否为历史陈述；不修改 |
| DOC-03 | Phase 6 | Phase 6F/6G 没有报告、验收或实现材料 | 全目录无 `PHASE6_F*`/`PHASE6_G*`；检索无命中；`PROJECT_HISTORY_PHASE6.md:1040` 只说明 D/E/F 计划未知 | `MISSING/UNKNOWN` | R0-B 查代码/目录；不得补写历史 |
| DOC-04 | Phase 6B | 归档数量旧记录与当前 Manifest/实际文件冲突 | 见 §8/§9 | `CONFLICT` | 以实际文件 + 当前 Manifest 为准 |

---

## 5. 历史测试结果

> 所有数字均来自历史报告；本次没有运行 pytest，不能把它们当作当前测试结果。

| 阶段/里程碑 | 收集 | 通过 | 失败 | 跳过 | 耗时 | 证据 |
|---|---:|---:|---:|---:|---:|---|
| Phase 1 | 未独立记录 | `UNKNOWN` | — | — | — | 无独立 Phase 1 测试；`PROJECT_HISTORY_STEP1.md:230,322-340` |
| Phase 1–2 合并最终 | 40 | 40 | 0 | 0 | 6.14s | `TEST_REPORT.md:15-18`；`PROJECT_HISTORY_STEP1.md:464-482` |
| Phase 2 初始快照 | 37 | 37 | 0 | 0 | 5.65s | 历史重建；后由新增 3 个对话框测试解释 37→40 |
| Phase 3 | 81 | 81 | 0 | 0 | 16.74s | `PHASE3_TEST_REPORT.md:16,57` |
| Phase 4 | 105 | 105 | 0 | 0 | 历史记录（报告未统一显示耗时） | `PHASE4_ACCEPTANCE_REPORT.md:129-134` |
| Phase 5 验收记录 | 127 | 126 | 0 | 1 | 38.61s | `PHASE5_ACCEPTANCE_REPORT.md:210-225` |
| Phase 5 最终收尾 | 127 | 126 | 0 | 1 | 36.25s | `PHASE5_FINAL_SUMMARY.md:73-81` |
| Phase 6B 封存重跑 | 145 | 144 | 0 | 1 | 41.51s | `PHASE6_B_ACCEPTANCE.json:71-87` |
| Phase 6C-2A 首轮修复 | — | 181 | 0 | 1 | — | 历史记录；`PHASE6_C2A_SECURITY_FINAL_REVIEW.md:585-591` |
| Phase 6C-2A SEC-02 后 | — | 184 | 0 | 2 | — | `PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md`；`PHASE6_C2A_SECURITY_FINAL_REVIEW.md:591-598` |
| Phase 6C-2B Step 3 | 210 | 203 | 0 | 7 | 49.92s | `PHASE6_C2B_STEP3_ACCEPTANCE.md:114,172-186` |
| Phase 6P-2B 最终回归 | 210 | 203 | 0 | 7 | 51.92s | `PHASE6_P2B_6A_FULL_TEST.md:90-104`；`PHASE6_P2B_FINAL_ACCEPTANCE.md:152-164` |
| 当前 R0-A | 未运行 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | — | 本任务明确不运行测试 |

### 5.1 历史 skip 说明

Phase 5 至 Phase 6 的 skip 主要是 Windows 非特权会话无法创建文件 symlink：`WinError 1314`。历史报告没有把 skip 写成通过；R0-B 不得把该限制改写成 PASS。证据：`PHASE5_FINAL_SUMMARY.md:83-90`；`PHASE6_C2B_STEP3_ACCEPTANCE.md:75,120-126`；`PHASE6_C2A_SECURITY_FINAL_REVIEW.md:598`。

---

## 6. 历史数据库与 Schema 状态

| 阶段 | Schema | 表/索引/数据 | 证据 | 标签 |
|---|---|---|---|---:|
| Phase 1 | v1 | 7 张基础表；无有效独立 v1 数据库快照 | `PROJECT_HISTORY_STEP1.md:28-30,264-309` | `HISTORICAL_CONFIRMED`；数据库 `UNKNOWN` |
| Phase 2 | v2 | 10 张表；0 外键违规；验收库 2 projects/4 auth/7 assets/7 history/33 logs | `ACCEPTANCE_REPORT.md:96-106,180-189`；`PROJECT_HISTORY_STEP1.md:443-462` | `HISTORICAL_CONFIRMED` |
| Phase 3 | v3 | 10 张业务表；验收库 2 projects/4 tasks/12 findings/27 logs/0 FK | `PHASE3_ACCEPTANCE_REPORT.md:6,85`；`PROJECT_HISTORY_STEP2.md`（Phase 3 DB 段） | `HISTORICAL_CONFIRMED` |
| Phase 4 | v4 | 10 张表；验收库 3 projects/3 tasks/38 findings/33 logs/0 FK；38 Finding 均带 `metadata_json` | `PHASE4_ACCEPTANCE_REPORT.md`；`PROJECT_HISTORY_STEP2.md`（Phase 4 DB 段） | `HISTORICAL_CONFIRMED` |
| Phase 5 | v5 | 11 表、18 索引；验收库 41 findings/3 evidence/2 history；主库/验收库 integrity ok、0 FK | `PHASE5_FINAL_SUMMARY.md:44-60,120-129,158-171`；`PHASE6_B_ACCEPTANCE.json:96-129` | `HISTORICAL_CONFIRMED` |
| Phase 6B | v5 | 未改 Schema；`reports` 表 0 行；主库/验收库 unchanged | `PHASE6_B_ACCEPTANCE.json:96-129`；`PHASE6_B_FINAL_SUMMARY.md:83-94` | `HISTORICAL_CONFIRMED`（历史哈希） |
| Phase 6C-2B | v5 | 仍无 Schema 修改；报告导出不写 `reports` 表 | `PHASE6_C2B_STEP3_ACCEPTANCE.md:149-159` | `HISTORICAL_CONFIRMED` |
| 当前 R0-A | `UNKNOWN` | 未打开数据库；不声称当前 schema/行数 | 本任务限制 | `REQUIRES_DB_AUDIT` |

### 6.1 补充：主数据库哈希变化

`docs/GIT_DATABASE_HASH_INVESTIGATION.md` 记录了主库从 `F03CFB81...` 变为 `ED315656...` 的只读调查：数据层变化是 6 条 `scan_logs` 项目生命周期日志和 `sqlite_sequence`/索引/页布局变化，不是 schema 损坏；原因高置信度为 C2B 手工 GUI 项目/报告验证使用了生产库，但操作者/会话 `UNKNOWN`。该报告是 Phase 6 后续资料，不属于原始 Phase 5 验收，不能据此倒推 Phase 5 当前状态。

---

## 7. 历史安全问题及处理记录

### 7.1 Phase 3–4

| 问题 | 历史处理 | 证据 | 当前判断 |
|---|---|---|---|
| Semgrep Windows CA 初始化失败 | 标记不可用，不伪造 Finding；Semgrep-only 任务 failed | `PHASE3_ACCEPTANCE_REPORT.md:7,96-103,200-219` | 需 R0-B 检查当前环境/代码 |
| 本地路径逃逸、非法路径、权限 | `ScopeValidator` + 7 路径测试；`shell=False` | `PHASE3_TEST_REPORT.md:68,79-109` | 需代码核查 |
| pip-audit 数据质量 | 保守 medium，标记 `severity_source=conservative-default`，不伪造 CVSS/范围 | `PHASE4_ACCEPTANCE_REPORT.md:205-210` | 需代码/metadata 核查 |
| pip-audit cache 路径 | 项目自有 cache/TMP | `PHASE4_ACCEPTANCE_REPORT.md:34-43` | 需代码核查 |

### 7.2 Phase 5

| 问题 | 历史处理 | 证据 |
|---|---|---|
| 证据路径/链接安全 | 绝对路径、项目根、`check_local_path`、遍历、junction、50 MB；symlink 动态跳过 | `PHASE5_ACCEPTANCE_REPORT.md:245-311`；`PHASE5_FINAL_SUMMARY.md:120-129` |
| 证据敏感内容 | 人工确认；不自动上传/执行 | `README.md` 证据安全说明；`PHASE5_FINAL_SUMMARY.md:34-42` |
| Manifest 精确性 | 记录 P6B-EX-001/002，不修改 Phase 5 历史 | `PHASE6_B_EXCEPTION_REGISTER.md:29-152` |

### 7.3 Phase 6C-2A HTML 安全

| 项 | 结论 | 说明 |
|---|---|---|
| View Model allowlist | 历史审查通过 | 排除 `Project.local_path/description`、raw Finding/Evidence 路径、task target/error |
| Jinja2 autoescape | 通过 | `autoescape=True` + `StrictUndefined`；无 `|safe`/Markup |
| SEC-01 原子排他发布 | PASS（模拟） | `os.link()`；无 `os.replace` fallback；真实双进程未测 |
| SEC-02 root/leaf 路径 | PASS_WITH_LIMITATIONS | root junction 动态 PASS；root symlink/叶 symlink 动态 UNKNOWN；父级 reparse/TOCTOU UNKNOWN |
| SEC-04 文本卫生 | PASS（指定字段） | title 200、字段 2,000、列表 100；TAB/LF 保留 |
| SEC-05 清理 | PASS | `finally`；KeyboardInterrupt 模拟通过；强杀不保证 |
| SEC-07 文件名 | PASS（校验） | 保留名/非法字符拒绝；设备写入未实测 |
| SEC-03/06 | 未修复/设计边界 | 无 CSP；语义脱敏未做 |

证据：`docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:13,21-27,362-479,557-566,675-687`；`docs/PHASE6_C2A_SECURITY_DEBT.md`（9 项债务；0 critical/high，4 medium/5 low）。

### 7.4 PDF / JSON

- PDF：`CANCELLED / OUT_OF_SCOPE`；无实际 exporter、依赖、UI、测试或 PDF 报告文件；仅保留 `ReportFormat.PDF` 和 schema CHECK 兼容元数据。证据：`PHASE6_P2A_PDF_RESIDUE_INVESTIGATION.md:7-19,155-221,344-352`；`PHASE6_P2B_FINAL_ACCEPTANCE.md:90-123`。
- JSON：`DEFERRED`；`JSON_DEVELOPMENT_APPROVED=NO`；无 exporter/contract/output/GUI/test。证据：`PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`（结论段）；`PHASE6_D1B_3_JSON_DECISION.md:6-18,109-171,266-282`。

---

## 8. 文档与 Manifest 问题

### 8.1 Phase 5 Manifest

- 文件：`docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt`，28,016 B，生成于 `2026-11-05T14:22:49+08:00`。
- 结构：`TOTAL FILES: 200`，但实际有 **253 条路径记录**；53 个路径在清单中重复出现（例如 `docs/acceptance/code_quality.json` 出现 2 次）。`CURRENTLY_CONFIRMED`。
- 两个例外：
  1. `docs/acceptance/code_quality.json`：旧 `9144 / 5993...`，当前 `9144 / f0d0...`；P6B-EX-001 解释为 Phase B 质量检查重生成，`product_file_count 57 -> 59`。
  2. `storage/_rebuild_manifest.py`：旧 `4150 / aed42f...`，当前缺失；P6B-EX-002 被接受为未解决历史差异，未恢复/伪造。
- 结论：Phase 5 **核心归档** 9 个非 Manifest 文件匹配；整个工作区 Manifest **不能精确复现**。`CONFLICT/EXPLAINED`。

### 8.2 Phase 6B Manifest 与归档

- 当前实际：`docs/acceptance/phase6_b_final/` **10 个文件**；当前有效 Manifest：**14 个条目**（5 个 Stage B 交付物 + 9 个归档记录，排除 Manifest 自身）。
- 当前有效证据：`docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt:10,15-39`（`TOTAL MANIFEST ENTRIES=14`、`ARCHIVE FILE COUNT=10`）。
- 旧记录冲突：
  - `PHASE6_B_ACCEPTANCE.json:18-31` 写 `file_count: 9`、`manifest_entries: 11`、`manifest_covers_seal_documents: false`；实际为 10/14/true（`PHASE6_B_FILE_MANIFEST.txt:37-39`）。
  - `PHASE6_B_FINAL_SUMMARY.md:183-191` 写“archive now contains 9 files”“manifest was not updated”；实际 10 files、Manifest 已更新。
  - `PHASE6_B_ACCEPTANCE.json:186` 的 `manifest_note` 也仍说 Manifest 未修改，属于旧快照。
- 历史解释：`docs/PROJECT_HISTORY_PHASE6.md:449` 已指出旧文档是封存/归档同步前生成，后续同步到 14 条；当前有效事实以当前 Manifest 和实际 10 个文件为准。

### 8.3 `code_quality.json` 当前状态

`CURRENTLY_CONFIRMED`（本次只读）：

```text
path: docs/acceptance/code_quality.json
size: 9144
sha256: F0D0FCA2A1F144D9F44891DF76D4BD581B55F52139687C68EDFCDC748CAF2E59
product_file_count: 59
```

旧 Manifest 记录为 `5993473a...` / `product_file_count 57`。该差异已由 P6B-EX-001 登记，**不应回滚或重写历史**。

### 8.4 README 当前文案

- `README.md:5` 仍写“不包含……报告生成能力”；同文件 `README.md:18,43,162` 明确 HTML 报告已实现、PDF 已取消、JSON 未批准。`CONFLICT`。
- `README.md:34` 仍写 `126 passed / 1 skipped`；后期 Phase 6B/6C-2B/P2B 历史测试为 144/1、203/7 等。该行可能是 Phase 5 历史表的旧值，但当前 README 未标注；`CONFLICT/STALE`。
- TRUTH-1B 已纠正 `README.md:3,18,43` 与 `ui/settings_page.py:84-85`，但**没有修改** `README.md:5,34`。证据：`docs/PHASE6_TRUTH_1B_COPY_ALIGNMENT.md`。

---

## 9. 不同报告之间的结论冲突

| ID | 冲突 | 报告 A | 报告 B/当前事实 | 处理 |
|---|---|---|---|---|
| C-01 | Phase 5 全量测试耗时 | `38.61s`（`PHASE5_ACCEPTANCE_REPORT.md:213`） | `36.25s`（`PHASE5_FINAL_SUMMARY.md:73-81`） | 历史测量差异；不取其一作为当前结果 |
| C-02 | Phase 6B 归档文件数 | 9（`PHASE6_B_ACCEPTANCE.json:20`；`PHASE6_B_FINAL_SUMMARY.md:185`） | **10**（实际目录；`PHASE6_B_FILE_MANIFEST.txt:39`） | `CONFLICT`；当前以 10 为准 |
| C-03 | Phase 6B Manifest 条目数 | 11（`PHASE6_B_ACCEPTANCE.json:22`） | **14**（`PHASE6_B_FILE_MANIFEST.txt:37`） | `CONFLICT`；当前以 14 为准 |
| C-04 | Phase 6B Manifest 是否覆盖 seal docs | `false`（`PHASE6_B_ACCEPTANCE.json:24`） | 当前 Manifest 包含两份 seal 文档（`PHASE6_B_FILE_MANIFEST.txt:31,33`） | `CONFLICT`；旧 JSON 未同步 |
| C-05 | Phase 6B Manifest 是否被更新 | “not updated”（`PHASE6_B_FINAL_SUMMARY.md:188`；`PHASE6_B_ACCEPTANCE.json:186`） | 实际 Manifest 生成于 20:15:34，含 14 条（`PHASE6_B_FILE_MANIFEST.txt:8,37`） | `CONFLICT`；当前 Manifest 已更新 |
| C-06 | Phase 2 测试数量 | 37 passed（初始快照） | 40 passed（最终验收；新增 3 个对话框测试） | 已解释；最终以 40 为历史记录 |
| C-07 | Phase 5 Manifest 哈希 | 旧 `5993...`（Manifest 第 66/103 行） | 当前 `f0d0...`（P6B-EX-001；本次只读确认） | 已解释为生成物差异；工作区不能精确复现 |
| C-08 | README 报告能力 | 第 5 行“不包含报告生成” | 第 18/43/162 行“HTML 已实现” | 当前文案冲突；未修复 |
| C-09 | JSON 状态演进 | D1A：可接入、建议 D1B | D1B-1：证据不足；D1B-3：DEFERRED/未批准 | 不是矛盾，是决策演进；当前为 DEFERRED |
| C-10 | Phase 6F/6G 状态 | 无报告 | 无报告/代码材料；历史重建只提 D/E/F 计划未知 | `MISSING/UNKNOWN`；不能判定完成 |

---

## 10. 当前无法确认的事项

以下事项**不得**从历史报告直接升级为当前事实；R0-B 需要检查代码/测试/数据库/环境：

1. 当前 Semgrep 是否仍因 Windows 证书存储失败；其他环境是否可运行。
2. 当前完整 pytest 的真实通过/失败/skip 数量；历史 203/7 不是本次结果。
3. 当前代码是否仍与 Phase 5/6 报告中的路径、行号、安全修复一致。
4. 当前主数据库/验收数据库的 schema、行数、完整性、哈希；R0-A 未打开数据库。
5. 当前 `reports/html_exporter.py` 的 SEC-02/TOCTOU 边界是否仍如最终审查所述。
6. 当前是否确实没有 JSON/PDF 实现残留；历史报告和 P2A 已给出否定证据，但未在 R0-A 重新全代码扫描。
7. Phase 6F/6G 是否曾经存在外部/未跟踪材料；当前仓库没有报告，`UNKNOWN`。
8. `storage/_rebuild_manifest.py` 缺失原因和用途；已接受为 unresolved，`UNKNOWN`。
9. `README.md:34` 的 126/1 是历史阶段表还是当前测试摘要；需要人工确认文案意图。
10. Phase 6A 的独立产物不存在；其“完成”只能依据后续报告/对话上下文，当前 `MISSING`。

---

## 11. 下一轮 R0-B 代码核查所需的文件和位置

### 11.1 扫描器与依赖

| 核查目标 | 文件/位置 | 需要确认 |
|---|---|---|
| Semgrep 可用性/失败处理 | `scanners/semgrep_scanner.py`、`scanners/rules/python_security.yml`、Semgrep 相关测试 | 是否仍使用本地规则；不可用是否 fail closed；是否有真实运行记录 |
| Bandit 统一接口 | `scanners/bandit_scanner.py`、`scanners/base.py`、`scanners/process_runner.py` | `shell=False`、超时/取消/输出上限、Finding 映射 |
| pip-audit | `scanners/pip_audit_scanner.py`、`services/dependency_audit_service.py`、依赖相关测试 | cache/TMP、JSON 解析、severity/affected range、requirements/pyproject |
| 依赖发现 | `services/dependency_audit_service.py`、`scanners/pip_audit_scanner.py` | 项目根限制、requirements 优先、pyproject PEP 621 边界 |

### 11.2 漏洞/证据/数据库

| 核查目标 | 文件/位置 | 需要确认 |
|---|---|---|
| 漏洞状态/历史 | `services/vulnerability_service.py`、`repositories/vulnerability_repository.py`、`ui/vulnerability_page.py` | 六状态、历史、备注、项目隔离 |
| 证据路径/哈希 | `services/evidence_service.py`、`repositories/evidence_repository.py`、`ui/evidence_page.py`、`ui/evidence_dialog.py` | 受管复制、UUID、SHA-256、symlink/junction/遍历/50 MB |
| Schema/迁移 | `database/schema.py`、`database/connection.py`、迁移测试 | v1→v5、备份/回滚、11 表/18 索引、`reports` 0 行 |
| 审计/隔离 | `services/audit_service.py`、`services/scan_service.py`、`security/scope_validator.py` | `project_id` 过滤、fail-closed、`scan_logs` |

### 11.3 报告中心

| 核查目标 | 文件/位置 | 需要确认 |
|---|---|---|
| 数据层 | `repositories/report_repository.py`、`services/report_service.py`、`core/models/report.py` | 只读事务、项目范围、自动转义边界、`ReportSnapshot` 字段 |
| HTML exporter | `reports/html_exporter.py` | SEC-01/02/04/05/07、原子写、文件名、根/叶路径 |
| 模板 | `reports/templates/base.html`、`vulnerability.html`、`evidence.html`、`project_summary.html` | 无脚本/远程资源、autoescape、无 `|safe` |
| GUI | `ui/report_page.py`、`ui/main_window.py`、`app/bootstrap.py` | ReportService 注入、固定 `reports_dir`、单写者、覆盖确认 |
| 测试 | `tests/test_report_service.py`、`tests/test_report_html.py`、`tests/test_ui_report.py` | 18/28/16 测试是否仍在；当前 skip 原因 |
| Phase 6 归档 | `docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt`、`PHASE6_B_ACCEPTANCE.json`、`PHASE6_B_FINAL_SUMMARY.md` | 当前 10/14 与旧 9/11 的差异；不要“修复”历史 |

### 11.4 文档/决策/缺口

| 核查目标 | 文件/位置 | 需要确认 |
|---|---|---|
| PDF 取消 | `docs/PHASE6_PDF_CLOSURE_AUDIT.md`、`docs/PHASE6_P2A_PDF_RESIDUE_INVESTIGATION.md`、`docs/PHASE6_P2B_FINAL_ACCEPTANCE.md`、`core/models/report.py` | 是否有活动 PDF 路径；枚举/schema 仅兼容 |
| JSON 延期 | `docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md`、`docs/PHASE6_D1B_3_JSON_DECISION.md`、`reports/__init__.py` | 无 exporter/consumer/契约 |
| README 文案 | `README.md:5,18,34,43,162`；`ui/settings_page.py:84-85` | 哪些是历史陈述；不修改 |
| Phase 6F/6G | `docs/`、`tests/`、`reports/`、`tools/` | 是否完全没有材料；不要补写 |

---

## 12. 本次实际文件变化清单

| 文件 | 变化 | 说明 |
|---|---|---|
| `docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md` | 新增 | 唯一新增文件；本报告 |
| 生产代码 | 无 | 未修改 |
| 测试代码 | 无 | 未修改 |
| 数据库/Schema | 无 | 未打开/修改 |
| 已有文档/README/Manifest | 无 | 未修改/未修复 |
| Git index/commit | 无 | 未 add/commit/push/reset/clean |

调查开始时的既有工作区变化（不是本任务产生）：

```text
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
?? docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
?? docs/PHASE6_D1B_3_JSON_DECISION.md
```

本报告生成后会新增一个未跟踪文件；不会暂存或清理上述任一文件。

---

## 13. 调查结束时的 Git 工作区状态

调查开始记录：

```text
branch: main
HEAD: bffb5ac82bbebe7fef5992f87ff90494c9776ace
staged: 0
unstaged: 1 (docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md)
untracked: 2 (D1B-1, D1B-3)
ahead/behind origin/main: 5/0
```

本任务只读，未执行任何 Git mutation；报告自身会成为新的未跟踪文件：

```text
expected after report:
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
?? docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
?? docs/PHASE6_D1B_3_JSON_DECISION.md
?? docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md
staged: 0
```

---

## 14. 调查结论

```text
PHASE6_R0_A_STATUS = COMPLETED
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
EXISTING_DOCS_MODIFIED = NO
GIT_MUTATION = NO
TESTS_RUN = NO
HISTORICAL_DOCUMENTATION_COMPLETENESS = PARTIAL
PHASE1_INDEPENDENT_ARCHIVE = MISSING
PHASE6_F_MATERIAL = MISSING
PHASE6_G_MATERIAL = MISSING
CURRENT_CODE_ASSESSMENT = NOT_PERFORMED
R0_B_EVIDENCE_INDEX = READY
```

**结论：** Phase 1–6 的主要阶段报告、验收、测试、架构、Manifest 和决策记录已经定位并读取；Phase 2/3/4/5/6B/C2A/C2B/P2B/D1B 的核心结论有历史报告依据。主要缺口是 Phase 1 独立快照/测试、Phase 6F/6G 材料，以及 Phase 6B 旧 JSON/总结与当前 10 文件、14 条 Manifest 的归档冲突；此外 Phase 5 工作区 Manifest 的两个已知例外仍未消除，README 仍有未修正的当前文案冲突。

上述缺口和冲突均已标为 `MISSING`、`CONFLICT`、`UNKNOWN` 或 `REQUIRES_CODE_AUDIT`，没有从历史报告自动升级为当前代码事实。可进入 R0-B 只读代码核查；本报告不修改任何现有文件，也不进入 R0-B。
