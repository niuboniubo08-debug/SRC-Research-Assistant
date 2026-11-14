# Phase 6-R0-B3 数据库、测试、文档与归档只读核查

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 调查时间：2026-11-13（Asia/Shanghai）
- 调查性质：只读；未修改代码、测试、文档、配置、数据库、Schema、Manifest 或归档
- 分支：`main`
- HEAD：`bffb5ac82bbebe7fef5992f87ff90494c9776ace`
- 提交数：8
- Git 工作区：staged 0；`M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`；5 个未跟踪报告（D1B-1、D1B-3、R0-A、R0-B1、R0-B2）；与 `origin/main` 为 ahead 5 / behind 0
- 本次唯一新增：`docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md`
- 数据库连接：只使用 `mode=ro` 或 `mode=ro&immutable=1`；未执行写 SQL、迁移、VACUUM、备份或恢复

## 1. 数据库状态

### 1.1 当前主数据库

`storage/src_research.db`：

| 项目 | 实际值 |
|---|---|
| 文件大小 | 147,456 bytes |
| SHA-256 | `ed3156560fcfe14c88715245cda8a3a919f3ce24d108ebcec9bf81e1536e15f8` |
| `PRAGMA user_version` | `5` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | `0` 行 |
| 业务表 | 11 |
| 显式索引 | 18 |
| `reports` | 0 |
| `projects` / `authorizations` / `scope_assets` | 0 / 0 / 0 |
| `scan_tasks` / `findings` / `evidence` | 0 / 0 / 0 |
| `finding_status_history` | 0 |
| `scan_logs` | 6 |
| `app_settings` | 0 |

主数据库当前是**空业务库**，只保留 6 条项目生命周期审计日志。它与 Phase 6B 记录的 `f03cfb81...` 不同；差异原因已在 R0-A/Git-1 中定位为 2026-11-09 的两次测试项目创建/删除及其 6 条 `scan_logs`，没有 schema 变化或完整性异常。该原因的高可信部分来自日志、HTML 报告和数据库时间线，仍不是逐条操作者证明。

**分类**：当前状态 `CURRENTLY_CONFIRMED`；历史漂移原因 `HISTORICAL_ONLY`；操作者身份 `UNKNOWN`。

### 1.2 Phase 5 验收数据库

`storage/phase5_acceptance/acceptance.db`：

| 项目 | 实际值 |
|---|---|
| 文件大小 | 352,256 bytes |
| SHA-256 | `03de49509b43428eb303f7dc38e1ff749cc58d1b3f186070c63706bba4ceb4c8` |
| Schema | `5` |
| `integrity_check` | `ok` |
| `foreign_key_check` | `0` |
| 业务表 / 索引 | 11 / 18 |
| `projects` / `authorizations` / `scope_assets` | 3 / 0 / 3 |
| `scan_tasks` | 4 |
| `findings` | 41 |
| `evidence` | 3 |
| `finding_status_history` | 2 |
| `scan_logs` | 59 |
| `reports` | 0 |

该库包含 Phase 3/4/5 的历史验收数据；`reports` 为 0，说明 HTML 报告能力没有把报告记录写入该验收库。`PHASE5_FINAL` 归档中的同名副本 SHA 为 `4f120652...`，与当前 live 验收库 `03de...` 不同；两者都是 v5、integrity ok、FK 0。归档副本是历史时点，live 库可能已在后续验收/状态操作中变化，不能据 SHA 差异认定损坏。

### 1.3 其他数据库

只读扫描到 20 个 `.db` 文件，均能打开且 `integrity_check=ok`、`foreign_key_check=0`。除主库和 phase5 验收库外：

- `storage/phase3_acceptance/acceptance.db`：v3，10 表，12 findings、4 tasks、27 logs。
- `storage/phase4_acceptance/acceptance.db`：v4，10 表，38 findings、3 tasks、33 logs。
- `storage/acceptance/acceptance.db`：v2，10 表，2 projects、4 authorizations、7 scope assets、7 history、33 logs。
- `docs/acceptance/phase5_final/db/*`：v5，41 findings / 3 evidence 的历史副本；integrity ok。
- `storage/backups/*.db`：v2/v3/v4/v5 迁移前或最终副本；除早期 4 KB 空文件外均 integrity ok。
- 4 个 4 KB、schema 0、0 表的 `src_research_v1_*.db` / `acceptance_v1_*.db` / `acceptance_v2_*.db` 文件不是可用历史数据副本；它们只能证明“曾生成文件”，不能作为恢复依据。

**分类**：`CURRENTLY_CONFIRMED`（本次只读打开）；4 KB 空文件的历史用途 `UNKNOWN`。

## 2. Schema 状态

### 2.1 版本与表结构

当前主库 `user_version=5`，与 Phase 5 最终报告和 Phase 6 报告一致。11 张业务表：

`app_settings`、`authorization_history`、`authorizations`、`evidence`、`finding_status_history`、`findings`、`projects`、`reports`、`scan_logs`、`scan_tasks`、`scope_assets`。

`findings` 包含 v4/v5 字段：`metadata_json`、`manual_notes`、`status_changed_at`、`last_seen_at` 等；`evidence` 包含 v5 的 `evidence_type`、`title`、`source`；`finding_status_history` 存在。没有 v6 schema，没有新增 PDF/JSON 专用表。

### 2.2 `reports` 表

实际列：

```text
report_id, project_id, report_format, file_path, generated_at, created_at
```

`report_format` CHECK 仍允许 `html`、`pdf`、`json`，但：

- 当前 `reports` 行数为 0；
- 没有 `report_type` 列；
- 没有报告历史表或报告版本表；
- HTML 导出不写 `reports` 表（本报告只读检查，未触发导出）；
- PDF/JSON 没有创建新表、新列或迁移。

因此 **HTML 报告已实现，但报告历史未实现；PDF/JSON 的 enum/CHECK 仍为休眠兼容元数据**。没有发现 PDF/JSON 对 Schema 的意外改变。

**分类**：`CURRENTLY_CONFIRMED`。

## 3. 测试体系与历史结果

### 3.1 当前测试结构

`tests/` 下 23 个 `test_*.py`，共 189 个 `test_` 函数；另有 `conftest.py`、`phase5_helpers.py`、`__init__.py`。

测试函数数量较多的文件：

| 文件 | 测试函数 |
|---|---:|
| `tests/test_report_html.py` | 28 |
| `tests/test_report_service.py` | 18 |
| `tests/test_scope_validator.py` | 16 |
| `tests/test_ui_report.py` | 16 |
| `tests/test_dependency_audit_service.py` | 15 |
| `tests/test_scan_service.py` | 13 |
| `tests/test_evidence_service.py` | 11 |
| `tests/test_pip_audit_scanner.py` | 8 |
| `tests/test_authorization_service.py` | 8 |
| `tests/test_bandit_scanner.py` | 7 |
| `tests/test_project_service.py` | 7 |
| `tests/test_semgrep_scanner.py` | 6 |
| `tests/test_vulnerability_service.py` | 6 |
| 其他数据库/模型/UI/进程测试 | 其余 |

189 个函数不等于 pytest 收集数：参数化会增加实例。历史 Phase 6 收集到 210 个实例，与“189 个函数 + 参数化”不矛盾。该计数本身是**静态函数计数**，不是本次 pytest 结果。

### 3.2 历史测试记录

| 阶段/报告 | 记录结果 | 性质 |
|---|---|---|
| Phase 1/2 | 40 passed | `HISTORICAL_ONLY` |
| Phase 3 | 81 passed | `HISTORICAL_ONLY` |
| Phase 4 | 105 passed | `HISTORICAL_ONLY` |
| Phase 5 | 127 collected / 126 passed / 1 skipped | `HISTORICAL_ONLY` |
| Phase 6B | 145 collected / 144 passed / 1 skipped | `HISTORICAL_ONLY` |
| Phase 6C-2B Step 3 | 210 collected / 203 passed / 7 skipped / 49.92s | `HISTORICAL_ONLY` |
| Phase 6P-2B final | 210 collected / 203 passed / 7 skipped / 51.92s | `HISTORICAL_ONLY` |

所有已知 skip 都是 Windows 文件符号链接创建 `WinError 1314`。历史日志中 Phase 5 时长有 38.61s / 36.25s 两个值，Phase 6B 有 38.44s / 41.51s 两个值；这是不同运行/不同报告的时长差异，不是 pass/fail 冲突。

**当前环境测试结果：UNKNOWN。** 本任务明确不运行 pytest，因此不能把上表写成“当前全绿”。

### 3.3 测试体系缺口

1. `pip-audit` 全部依赖带 `skip_reason` 的测试缺失；现有测试把 skipped 依赖计入 `audited`，固定了 R0-B2 的 B2-01 行为。
2. Evidence 根目录/`project_<id>` junction 没有测试；现有 junction 测试只覆盖源文件路径。
3. Bandit 项目路径包含 `env` 组件没有回归测试。
4. Semgrep 当前 Windows 真实运行没有测试；历史测试只验证不可用/解析路径。
5. `run_command` 的子进程树取消/超时没有测试。
6. 没有 README/Manifest/归档元数据一致性测试。
7. 没有“全部项目”视图下 Evidence/Vulnerability 写操作的 UI 级项目 ID 校验测试。

**分类**：测试文件存在 `CURRENTLY_CONFIRMED`；历史通过 `HISTORICAL_ONLY`；当前结果 `UNKNOWN`；缺口 `CURRENTLY_CONFIRMED`（静态阅读）。

## 4. README 和产品文档真实性

### 4.1 准确的内容

- `README.md:3` 已说明 Phase 6 HTML 报告中心（本地导出）。
- `README.md:18` 明确 HTML 已实现、PDF 已取消、JSON 未实施/未批准。
- `README.md:43` 说明源代码审计、依赖审计、漏洞管理、证据中心、HTML 报告已实现，安全配置检查未开发。
- `README.md:162` 的 PDF/JSON/HTML 状态与当前实现一致。
- `README.md:170` 对 Semgrep 当前 Windows 不可用状态的描述准确。
- `ui/settings_page.py:84-86` 已完成项包含 HTML 报告中心，报告能力说明 PDF/JSON 状态正确。
- 安装/启动命令仍指向项目根目录和虚拟环境；与实际目录一致。

### 4.2 已确认的文档冲突

**B3-DOC-01：README 总述仍说“不包含报告生成能力”**

- `README.md:5`：
  “...不包含远程漏洞扫描、网站扫描、漏洞利用、密码爆破、自动攻击、证据上传或报告生成能力。”
- 同一文件 `README.md:3`、`:18`、`:43`、`:162` 已说明 HTML 报告中心已实现。
- 这是当前产品文案冲突，不是代码冲突。
- **分类**：`CURRENTLY_CONFIRMED`。

**B3-DOC-02：README 测试数字过期**

- `README.md:34` 和 `:216` 写“126 passed / 1 skipped”。
- 这是 Phase 5 的数字；Phase 6C-2B/P2B 历史记录为 210 collected / 203 passed / 7 skipped。
- 当前未运行 pytest，因此正确写法应是“历史值”或留待重新运行后更新，不能继续把 126/1 当作当前值。
- **分类**：`CURRENTLY_CONFIRMED`（文本过期）；当前实际数字 `UNKNOWN`。

**B3-DOC-03：`requirements.txt` 注释乱码**

- `requirements.txt:10` 的 CA-store 注释出现 `"������"` 乱码，原本应是“不可用”。
- 只影响依赖文件注释的可读性，不影响 pip 解析 `semgrep>=1.100,<2`。
- **分类**：`CURRENTLY_CONFIRMED`。

**B3-DOC-04：Phase 6B 归档内部元数据过期**

- `docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json` 的 `archive.file_count=9`、`manifest_entries=11`、`manifest_covers_seal_documents=false`。
- 当前实际 archive 文件数 10；Manifest 条目 14，且覆盖 seal 文档；Manifest 自 SHA `d898d4e...`。
- `PHASE6_B_FINAL_SUMMARY.md` 也保留“9 files”的历史表述。
- **分类**：`CURRENTLY_CONFIRMED`（当前文件与内部记录冲突）；历史时点 `HISTORICAL_ONLY`。

**B3-DOC-05：Phase 5 归档数量表述与当前目录不一致**

- `PHASE6_B_FINAL_SUMMARY.md` / seal 文档写 `docs/acceptance/phase5_final/` 包含 10 files。
- 当前该目录实际 16 个文件：10 个普通文档/图片 + 2 个 `.db` + 2 个 `.db-shm` + 2 个 `.db-wal`，其中包含 Manifest 自身；以 `Get-ChildItem -Recurse -File` 计。
- “10 files”可能是当时核心文件口径，不是当前完整目录口径；文档没有说明口径。
- **分类**：`CURRENTLY_CONFIRMED`（计数口径冲突）；是否为错误取决于“core archive”定义，`UNKNOWN`。

## 5. Manifest 与归档完整性

### 5.1 Phase 6B Manifest

`docs/acceptance/phase6_b_final/PHASE6_B_FILE_MANIFEST.txt`：

- 3,066 bytes；Manifest 自 SHA-256 `d898d4e091fc72f2885cb6db2ca99ba856552d06172ee99af2e57c6729463c6f`。
- 14 个条目，覆盖 5 个 Stage B 交付物 + 9 个 archive 记录（不含 Manifest）。
- 14/14 路径存在，大小和 SHA-256 全部匹配；0 缺失、0 mismatch、0 重复。
- 当前 archive 目录 10 个文件；Manifest 覆盖正确。
- Manifest 头部 `Project:` 行有中文路径乱码（`D:\...` 显示为替换字符），不影响按 ASCII 相对路径校验，但影响可读性/可移植性。

**结论**：Phase 6B Manifest 的**条目校验通过**；仅内部 acceptance JSON 的旧计数（9/11）与当前 10/14 冲突。

### 5.2 Phase 5 Manifest

`docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt`：

- 28,016 bytes；253 条条目，200 个唯一路径，53 条重复条目。
- 190 个唯一路径大小/哈希匹配。
- 1 个缺失：`storage/_rebuild_manifest.py`。
- 9 个 mismatch：
  1. `app/bootstrap.py`：实际 5,161 / `9d3e789f...`；Manifest 4,763 / `7365d906...`
  2. `ui/main_window.py`：实际 13,264 / `0f673ecc...`；Manifest 13,124 / `ee1f51cd...`
  3. `ui/settings_page.py`：实际 4,682 / `dc36095a...`；Manifest 4,564 / `377ebca2...`
  4. `README.md`：实际 20,307 / `de4066c1...`；Manifest 19,877 / `42984348...`
  5. `docs/acceptance/code_quality.json`：实际 9,144 / `f0d0fca2...`；Manifest 9,144 / `5993473a...`
  6. `.gitignore`：实际 496 / `312e1168...`；Manifest 221 / `9a9f928f...`
  7. `reports/__init__.py`：实际 180 / `1a0d3d47...`；Manifest 75 / `f45e8003...`
  8. `storage/src_research.db`：实际 147,456 / `ed315656...`；Manifest 147,456 / `f03cfb81...`
  9. `ui/report_page.py`：实际 18,090 / `884b6e8e...`；Manifest 691 / `995b342f...`
- 部分 mismatch 文件同时出现在“new/modified”两段，导致 53 条重复条目；这是 Manifest 结构质量缺陷，不是磁盘上有 53 个重复文件。
- Manifest 头部 `Project:` 路径同样有中文乱码。
- 该 Manifest 是 Phase 5 时点快照；上述 mismatch 多数由 Phase 6 的后续修改造成，不能为了“修复 Manifest”而回滚文件。
- 缺失的 `storage/_rebuild_manifest.py` 已在 Phase 6B 中记录为 P6B-EX-002；本次未恢复、未重建。

**结论**：Phase 5 工作区 Manifest **不能精确复现当前工作区**；这符合 Phase 6B 的 `historical_workspace_manifest_exact_match=false` 记录。Phase 5 归档核心文件仍可单独核对，但“Manifest 全量通过”不成立。

### 5.3 归档文件覆盖

- Phase 5 归档实际 16 个文件；Manifest 未列出自身、2 个 `.db-shm`、2 个 `.db-wal`（5 个未列）。数据库主文件已列。Manifest 对“所有文件”的声明与实际目录覆盖不完全一致。
- Phase 6B 归档实际 10 个文件；Manifest 覆盖 9 个 archive 记录（不含自身）+ 5 个外部 Stage B 文件；覆盖关系正确。

**分类**：`CURRENTLY_CONFIRMED`（路径/哈希计数）；历史时点差异 `HISTORICAL_ONLY`；缺失脚本原因 `UNKNOWN`。

## 6. 备份状态

### 6.1 项目内 ZIP 备份

`backups/` 下 5 个 ZIP：

| 文件 | 大小 | 条目数 | ZIP CRC | 含主库 |
|---|---:|---:|---|---|
| `src-research-assistant_acceptance_final.zip` | 738,979 | 92 | pass | yes |
| `src-research-assistant_phase2_20261104T145255Z.zip` | 598,157 | 72 | pass | yes |
| `src-research-assistant_phase3_final.zip` | 996,834 | 120 | pass | yes |
| `src-research-assistant_phase4_final.zip` | 1,305,451 | 139 | pass | yes |
| `src-research-assistant_phase5_final.zip` | 2,313,348 | 166 | pass | yes |

5/5 ZIP 可只读打开，`testzip()` 无坏条目。ZIP 中的数据库是否存在不等于已做恢复演练；本次没有解压或恢复。

### 6.2 E 盘本地备份

`E:\SRC-Research-Assistant_Backups\backup_20261110_110447`：

- 实际 247 个文件 / 12,952,436 bytes；Manifest 记录 246 个数据文件（226 normal + 20 DB）+ Manifest 自身，数量/总字节与 Manifest 一致。
- Manifest：70,281 bytes；`normal_count_match=true`、`normal_size_match=true`、`normal_hash_match=true`、`database_count_match=true`、`database_integrity_all_ok=true`、`database_foreign_keys_all_zero=true`、`source_project_unchanged=true`。
- `databases` 20 个；`normal_files` 226 个。
- 主库副本 `storage/src_research.db` 147,456 bytes；以 `mode=ro&immutable=1` 打开成功，schema 5、integrity ok、FK 0、11 表。
- **可读性限制**：普通 `mode=ro` 打开该 E 盘副本返回 `sqlite3.OperationalError: unable to open database file`；改用 `immutable=1` 后成功。原因可能是 E 盘/DSH 沙箱对 sidecar 或目录的访问限制，未作进一步权限修改；不能据此宣称所有恢复工具都能直接打开。
- **物理独立性**：Manifest 明确写 “local backup on the same physical SSD as the source; not a physical-independent backup”。当前 `Get-Partition` 查询被系统拒绝（Access denied），因此本次不能重新验证 D/E 是否同一物理盘；该事实依赖 Git-2A 的历史检查，分类为 `HISTORICAL_ONLY`。
- 本次没有创建、覆盖、删除或恢复 E 盘备份。

### 6.3 备份结论

- 项目内 5 个 ZIP：存在、可读、CRC 通过。
- E 盘本地备份：Manifest 计数/哈希验证通过；主库副本可 immutable 只读检查；不是物理独立备份。
- 没有做完整恢复演练；`RESTORE_VALIDATION` 只能引用历史 Git-2B 的隔离恢复结果，不能把“文件存在”当成“已恢复”。

## 7. Git 当前状态

实际只读结果：

```text
BRANCH=main
HEAD=bffb5ac82bbebe7fef5992f87ff90494c9776ace
COMMIT_COUNT=8
STAGED=0
UNSTAGED=M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
UNTRACKED=
  docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
  docs/PHASE6_D1B_3_JSON_DECISION.md
  docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md
  docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md
  docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md
AHEAD_BEHIND=0 5
```

- `origin/main` 存在；ahead 5 / behind 0。
- `M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md` 是既有修改，本次未修改、未暂存、未恢复。
- 5 个未跟踪报告中，D1B-1、D1B-3、R0-A、R0-B1 为既有；R0-B2 为本轮前一份报告；本报告生成后将成为第 6 个未跟踪文件。
- R0-A 记录 HEAD `bffb5ac...`、staged 0、1 个 M、3 个未跟踪；R0-B1 记录 4 个未跟踪；R0-B2 记录 5 个未跟踪。三者与当前一致，差异只是新报告增加。
- 本次没有 Git 写操作。

**分类**：`CURRENTLY_CONFIRMED`。

## 8. 与 R0-A、R0-B1、R0-B2 的问题关联

### 8.1 R0-A

R0-A 已确认：

- 历史文档完整性 `PARTIAL`；
- Phase 1 独立资料/测试缺失；
- Phase 6F/6G 无材料；
- Phase 5 Manifest 不是当前工作区的精确快照；
- Phase 6B 归档计数内部冲突。

本次 B3 复核了这些结论：Phase 5 Manifest 当前 253 条/200 唯一/53 重复、9 mismatch、1 missing；Phase 6B 当前 10 文件/14 Manifest 条目，与 acceptance JSON 的 9/11 不一致。

### 8.2 R0-B1

R0-B1 的报告中心问题：

- Evidence 根目录/project 目录 reparse；
- 报告输出根父级 reparse；
- TOCTOU；
- 无 CSP；
- `CountView` 无界；
- 清理失败静默。

B3 的数据库检查确认 `reports` 表 0 行、没有报告历史表、没有 PDF/JSON 写入；Schema v5 未因 HTML 报告增加表/列。B3 不重新判断报告导出代码的运行时安全，只记录当前 DB/归档状态。

### 8.3 R0-B2

R0-B2 的高严重度 B2-01（pip-audit 将 skip 依赖计入 audited）仍然成立，且测试文件 `tests/test_pip_audit_scanner.py:53-78` 固定了 `audited == 3` 的旧行为。B3 没有修复，也没有重新运行扫描器。

B2-02（Evidence 根目录/project junction）和 B2-03（Bandit `env` 排除）也仍是当前已知限制，未在 B3 修复。

## 9. 当前已确认问题

| ID | 问题 | 证据 | 分类 | 影响 |
|---|---|---|---|---|
| B3-01 | README 总述仍说“不包含报告生成能力” | `README.md:5` 与 `:3/:18/:43/:162` 冲突 | `CURRENTLY_CONFIRMED` | 产品文案错误 |
| B3-02 | README 测试数字 126/1 过期 | `README.md:34`、`:216` | `CURRENTLY_CONFIRMED` | 用户误判测试状态 |
| B3-03 | Phase 6B acceptance JSON 记录 9 files/11 entries | `PHASE6_B_ACCEPTANCE.json` `archive.file_count/manifest_entries`；实际 10/14 | `CURRENTLY_CONFIRMED` | 归档元数据不可信 |
| B3-04 | Phase 5 Manifest 53 重复、9 mismatch、1 missing | `PHASE5_FILE_MANIFEST.txt` | `CURRENTLY_CONFIRMED` | 历史 Manifest 不能全量复现 |
| B3-05 | Phase 5/6 Manifest 中文项目路径乱码 | 两文件头部 `Project:` 行 | `CURRENTLY_CONFIRMED` | 可读性/可移植性 |
| B3-06 | `requirements.txt:10` 注释乱码 | 实际字节 | `CURRENTLY_CONFIRMED` | 依赖说明不可读 |
| B3-07 | 主库 SHA 从 f03c 变为 ed3156 | 当前 6 条 scan_logs + R0-A/Git-1 时间线 | `CURRENTLY_CONFIRMED` 状态；原因 `HISTORICAL_ONLY` | 非损坏；历史记录不可直接复用 |
| B3-08 | 当前完整测试未运行 | 本任务约束 | `UNKNOWN` | 无法确认当前全绿 |
| B3-09 | Phase 5 归档 16 文件 vs 文档 10 files | `phase5_final` 实际目录 | `CURRENTLY_CONFIRMED` | 计数口径冲突 |
| B3-10 | E 备份普通 mode=ro 打开失败 | 本次 `sqlite3.OperationalError`; immutable 成功 | `REQUIRES_RUNTIME_TEST`/`UNKNOWN` | 备份可读性依赖方式 |
| B3-11 | 继承 B2-01：pip-audit 全部 skip 可假成功 | `scanners/pip_audit_scanner.py:311`; `services/dependency_audit_service.py:325-338` | `CURRENTLY_CONFIRMED`（静态） | 安全结论可靠性 |

## 10. 尚需运行验证的问题

1. 运行完整 pytest，确认当前收集数、passed/failed/skipped、时长和退出码；不能只引用历史 210/203/7。
2. 运行 `pip-audit` 的全部 `skip_reason` 场景，验证 B2-01 的实际输出和任务状态。
3. 运行 Semgrep 当前 Windows 可用性探针，确认是否仍为 `CertOpenSystemStore` 失败。
4. 用专用临时目录验证 Evidence 根目录/project 目录 junction，以及报告输出根目录父级 reparse。
5. 用进程树观察取消/超时后是否有子进程残留。
6. 验证 E 盘备份在普通 SQLite 客户端中的可读性，并完成一次隔离恢复演练；本次仅 immutable 只读检查。
7. 验证 Phase 5/6 归档 Manifest 的“core archive”定义，决定是否接受当前计数口径。

## 11. 总体结论

**`OVERALL_DELIVERY_JUDGMENT = NOT_READY`**

- 数据库和 Schema 本身健康：主库与验收库 integrity ok、FK 0、schema v5、11 表/18 索引；`reports=0`；没有 PDF/JSON 表或迁移。
- 备份可用：项目内 5 个 ZIP 无 CRC 错误；E 盘 247 文件/12,952,436 bytes 的 Manifest 计数匹配，主库副本 immutable 只读 integrity ok；但 E 备份不是物理独立备份，普通只读打开方式存在限制。
- 测试体系覆盖面广（23 文件/189 函数），但当前完整测试未运行；历史 210/203/7 不能当作当前结果。
- 文档和归档存在明确冲突：README 报告能力叙述、测试数字、Phase 5 Manifest 重复/缺失/mismatch、Phase 6B acceptance 计数、中文路径乱码。
- 更关键的是继承自 R0-B2 的 B2-01：pip-audit 对全部 `skip_reason` 依赖仍可产生“已审计、未发现漏洞”的假成功；这是扫描结果真实性问题，未修复前不能把当前系统判定为可交付。
- 数据库健康不等于扫描结论可靠；归档/备份存在也不等于已恢复验证。

**建议**：先修复 B2-01 并补测试，再运行完整 pytest；随后单独清理 README/Manifest/Phase 6B acceptance 元数据。本次只读，不实施修复、不进入 R0-C。

## 12. 本次实际变更与声明

- 新增文件：`docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md`。
- 生产代码：未修改。
- 测试代码：未修改。
- README/现有文档：未修改。
- 数据库/Schema：未修改；只读连接。
- Manifest/归档/备份：未修改、未重建、未恢复。
- Git：未执行 add/commit/push/reset/restore/clean。
- pytest/GUI/扫描器：未运行。

**`PHASE6_R0_B3_STATUS = COMPLETED`**
