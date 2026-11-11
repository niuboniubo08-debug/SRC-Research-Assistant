# Git 仓库建立前只读盘点报告

> 项目：`D:\挖漏洞\SRC-Research-Assistant`  
> 调查开始时间：`2026-11-10 10:21:29 +08:00`（Asia/Shanghai）  
> 文件盘点时间：`2026-11-10 10:25:16 +08:00`  
> 报告生成时间：`2026-11-10 10:26:00 +08:00`（约值）  
> 调查性质：**只读**。未执行 `git init`、`git add`、`git commit`、`git reset`、`git clean`、`git checkout`，未创建或修改 `.gitignore`，未打开数据库执行写入。

## 0. 结论摘要

| 项目 | 结果 |
|---|---|
| 项目根目录 | `D:\挖漏洞\SRC-Research-Assistant` |
| 文件总数（报告生成前） | **353** |
| 目录总数 | **77** |
| 总大小 | **14,931,883 bytes**（约 14.24 MiB） |
| 已有 `.git` | **不存在** |
| 已有 `.gitignore` | **存在**，221 bytes，18 行；本任务未修改 |
| 已有 Git 提交/远程 | **无**（没有 `.git`，因此无本地历史或远程配置） |
| 大文件 | 最大为 `backups/src-research-assistant_phase5_final.zip`，2,313,348 bytes；没有单个文件超过 3 MiB |
| 主要二进制 | 20 个 SQLite `.db`、9 个 `.db-shm`、5 个 ZIP、14 个 PNG、92 个 `.pyc` |
| 敏感度重点 | `config.yaml` 的机器相关路径、`storage/acceptance/authorization.pdf`、Evidence/验收截图、SQLite 数据库、验收日志 |
| Git 建议 | **源码、测试、模板、产品文档、验收文本/Manifest 可跟踪；数据库、Evidence、验收运行产物、缓存和现有备份走独立备份，不直接进入 Git** |
| 是否可直接初始化 Git | **不可以直接初始化**；需先完成 `.gitignore` 补全、数据库/证据/敏感材料决策和外部备份 |

**重要边界：** `storage/acceptance/authorization.pdf` 是授权附件，不是 PDF 报告功能产物。PDF 报告已取消，本报告不把 PDF 重新列为未来开发计划。

## 1. 调查时间和项目路径

- 调查开始：`2026-11-10 10:21:29 +08:00`
- 项目路径：`D:\挖漏洞\SRC-Research-Assistant`
- 当前版本：`0.5.0`
- 当前数据库 Schema：主数据库 `user_version=5`；Phase 5 验收数据库 `user_version=5`；旧 `storage/acceptance/acceptance.db` 为 `user_version=2` 的遗留数据库。
- Python：`3.14.4`；PySide6：`6.12.0`；pytest：`9.2.0`；pytest-qt：`4.5.0`（环境信息来自已有项目环境，本轮未运行测试）。
- 本轮没有连接网络，没有上传任何文件，没有打开 GUI。

**实际检查方法：**

- 使用 `Get-ChildItem -Recurse -File -Force` 统计文件数、目录数、大小和修改时间；
- 使用 `Get-FileHash -Algorithm SHA256` 对关键二进制/HTML/PDF 计算哈希；
- 使用 `sqlite3` 的 `file:...?mode=ro&immutable=1` 只读连接检查主数据库、Phase 5 验收数据库和旧验收数据库的 `user_version` 与 `PRAGMA integrity_check`；
- 只读取配置键名，不打印配置值；未读取 `.env`（不存在）；
- 未运行 pytest、未打开 GUI、未执行任何 Git 命令。

## 2. 当前版本管理状态

| 检查项 | 结果 | 证据强度 |
|---|---|---|
| `.git` 目录 | **不存在** | 实际检查 |
| `.gitignore` | **存在**，221 bytes，18 行 | 实际检查并读取内容 |
| `.gitattributes` | 不存在 | 实际检查 |
| `.gitmodules` | 不存在 | 实际检查 |
| `.github/` | 不存在 | 实际检查 |
| `.svn/`、`.hg/` | 不存在 | 实际检查 |
| 本地提交历史 | 不存在（没有 `.git`） | 推断，基于 `.git` 不存在 |
| 远程仓库 | 未配置/不可验证（没有 `.git`） | 推断；未连接远程 |
| Git 用户身份、`core.autocrlf`、全局 `core.excludesFile` | 未检查 | **UNKNOWN** |
| 文件系统重解析点（symlink/junction） | 项目树内未发现 | 实际检查 `ReparsePoint` 属性；结果 `NONE` |

### 2.1 已有 `.gitignore` 内容

现有文件内容如下（仅记录，未修改）：

```gitignore
.venv/
.tmp/
.screenshot-demo/
debug.log
__pycache__/
*.py[cod]
.pytest_cache/
storage/*.db
storage/*.db-*
storage/logs/*.log
storage/logs/*.jsonl
storage/backups/
storage/cache/
storage/tmp/
backups/
build/
dist/
*.spec
```

**已覆盖：** 根级 `.venv`、Python 缓存、pytest 缓存、`storage/` 直接层级的 `.db`/`.db-*`、`storage/logs` 直接层日志、`storage/backups/`、`backups/`、构建产物。

**未覆盖或覆盖不完整：**

- `pytest-of-lenovo/`、`tmpcde5t8kh/`、`storage/_c1_pytest_tmp/`、`storage/tmpv2ziyrtj/` 等测试临时目录；
- `storage/phase3_acceptance/`、`storage/phase4_acceptance/`、`storage/phase5_acceptance/`、`storage/acceptance/` 下的嵌套数据库、日志、配置和证据；
- `storage/evidence/` 和 `storage/reports/` 的生成物；
- `docs/acceptance/phase5_final/db/` 下的数据库副本；
- `.env`、PEM/KEY/PFX/P12 等潛在密钥文件没有明确规则；
- 现有 `storage/*.db` 不是递归模式，不能覆盖嵌套数据库。

> 结论：`.gitignore` 已经存在，但不足以安全地直接初始化 Git。由于本任务禁止修改，本报告只给出建议，不实际修改文件。

## 3. 项目文件分类统计

### 3.1 按目录统计（互不重叠）

| 目录/位置 | 文件数 | 大小（bytes） | 主要内容 |
|---|---:|---:|---|
| `app/` | 8 | 35,020 | 应用初始化、启动、配置 |
| `core/` | 28 | 123,043 | 模型、错误、时间工具 |
| `database/` | 6 | 53,261 | 连接、Schema、迁移 |
| `reports/` | 8 | 87,154 | HTML exporter、模板、`__pycache__` |
| `repositories/` | 8 | 64,900 | 漏洞、证据、报告 Repository |
| `scanners/` | 13 | 110,824 | Bandit、Semgrep、pip-audit、规则 |
| `security/` | 6 | 61,231 | ScopeValidator、Scope 规则 |
| `services/` | 20 | 301,142 | 业务服务 |
| `ui/` | 34 | 652,000 | PySide6 页面 |
| `tools/` | 14 | 84,714 | 验收、截图、检查工具 |
| `tests/` | 55 | 1,124,028 | 测试模块 + `__pycache__` |
| `docs/` | 76 | 3,228,937 | 产品文档、验收材料、截图 |
| `storage/` | 66 | 3,031,598 | 数据库、验收数据、Evidence、日志、生成 HTML |
| `backups/` | 5 | 5,952,769 | 历史 ZIP 快照 |
| 根目录文件 | 6 | 21,262 | `.gitignore`、`config.yaml`、`main.py`、`pytest.ini`、`README.md`、`requirements.txt` |
| **合计** | **353** | **14,931,883** | — |

### 3.2 按扩展名统计

| 扩展名 | 文件数 | 大小（bytes） | 说明 |
|---|---:|---:|---|
| `.py` | 108 | 850,137 | 78 个应用/工具源码、26 个测试模块、4 个验收样例源码 |
| `.pyc` | 92 | 1,826,838 | Python 缓存，可忽略 |
| `.md` | 49 | 704,686 | README 1 + `docs/` 48 |
| `.db` | 20 | 2,674,688 | SQLite 数据库及备份 |
| `.png` | 14 | 2,419,239 | 验收截图、Evidence、Phase 2 截图 |
| `.json` | 10 | 63,741 | 验收 JSON |
| `.db-shm` | 9 | 294,912 | SQLite 共享内存文件 |
| `.db-wal` | 9 | 0 | SQLite WAL 文件（当前为空） |
| `.txt` | 7 | 42,992 | Manifest、测试输出 |
| `.html` | 6 | 36,482 | 4 个模板 + 2 个生成报告 |
| `.jsonl` | 5 | 58,868 | 审计日志 |
| `.log` | 5 | 0 | 空日志文件 |
| `.yaml` | 5 | 2,344 | 根配置 + 4 个验收配置 |
| `.yml` | 1 | 3,515 | Semgrep 规则 |
| `.zip` | 5 | 5,952,769 | 历史快照 |
| `.pdf` | 1 | 44 | `storage/acceptance/authorization.pdf`（授权附件，不是报告） |
| `.toml` | 1 | 130 | 验收用 pyproject 样例 |
| `.gitkeep` | 4 | 219 | 占位文件 |
| `.gitignore` | 1 | 221 | 现有忽略规则 |
| `.ini` | 1 | 58 | pytest 配置 |
| **合计** | **353** | **14,931,883** | — |

### 3.3 源码与测试拆分

| 分类 | 文件数 | 大小（bytes） | 说明 |
|---|---:|---:|---|
| 应用/工具 `.py` | 78 | 651,951 | `app/`、`core/`、`database/`、`reports/`、`repositories/`、`scanners/`、`security/`、`services/`、`ui/`、`tools/`、`main.py` |
| 测试 `.py` | 26 | 197,746 | `tests/*.py` |
| 验收样例 `.py` | 4 | 440 | `storage/.../*.py`，运行产物 |
| `.pyc` 缓存 | 92 | 1,826,838 | 不进入 Git |

源码目录 `.py` 数量拆分：`app` 4、`core` 14、`database` 3、`reports` 2、`repositories` 4、`scanners` 6、`security` 3、`services` 10、`ui` 17、`tools` 14、根 `main.py` 1，合计 **78**。

## 4. 大文件及特殊文件清单

### 4.1 最大的文件

| 大小（bytes） | 文件 | 处置建议 |
|---:|---|---|
| 2,313,348 | `backups/src-research-assistant_phase5_final.zip` | BACKUP_ONLY；现有 `.gitignore` 已忽略 `backups/` |
| 1,305,451 | `backups/src-research-assistant_phase4_final.zip` | BACKUP_ONLY |
| 996,834 | `backups/src-research-assistant_phase3_final.zip` | BACKUP_ONLY |
| 738,979 | `backups/src-research-assistant_acceptance_final.zip` | BACKUP_ONLY |
| 598,157 | `backups/src-research-assistant_phase2_20261104T145255Z.zip` | BACKUP_ONLY |
| 352,256 | `storage/phase5_acceptance/acceptance.db` | BACKUP_ONLY；数据库，不直接跟踪 |
| 352,256 | `storage/backups/phase5_acceptance_final_20261105T061441Z.db` | BACKUP_ONLY；与 docs 副本重复 |
| 352,256 | `docs/acceptance/phase5_final/db/phase5_acceptance_final_20261105T061441Z.db` | BACKUP_ONLY；与 storage 副本重复 |
| 269,443 | `docs/acceptance/phase5_vulnerability_management.png`（及 Phase 5 final 副本） | REVIEW：历史截图，检查是否含本地路径 |
| 245,760 | `storage/phase4_acceptance/acceptance.db` | BACKUP_ONLY |
| 240,530 | `storage/phase5_acceptance/evidence/project_1/*.png`、`storage/phase4_acceptance/requirements_project/phase5_evidence_screenshot.png` | BACKUP_ONLY；Evidence 截图 |
| 189,951 | `docs/acceptance/phase3_source_audit.png` | REVIEW |
| 169,531 | `docs/acceptance/phase5_evidence_center.png`（及副本） | REVIEW |
| 147,456 | `storage/src_research.db` | BACKUP_ONLY；当前主数据库 |
| 138,191 | `docs/screenshots/phase2_authorization_management.png` | REVIEW |
| 132,773 | `docs/screenshots/phase2_dashboard.png` | REVIEW |
| 131,072 | `storage/backups/src_research_v3_20261105T024055Z.db` | BACKUP_ONLY |
| 131,072 | `storage/backups/src_research_v4_20261105T034341Z.db` | BACKUP_ONLY |

**结论：** 没有单个文件超过 3 MiB；最大的 5 个都是历史 ZIP 备份，合计 5,952,769 bytes。当前没有必要为 Git 引入 LFS；如果未来 Evidence/数据库快速增长，再评估 LFS 或外部对象存储。

### 4.2 特殊文件

| 文件/目录 | 大小/数量 | 说明 |
|---|---|---|
| `.gitignore` | 221 bytes | 已存在，未修改 |
| `.gitkeep` | 4 个，219 bytes | `storage/evidence`、`storage/logs`、`storage/projects`、`storage/reports` |
| SQLite | 20 个 `.db`，9 个 `.db-shm`，9 个 `.db-wal` | 数据库与备份；见第 6 节 |
| ZIP | 5 个，5,952,769 bytes | Phase 2–5 历史快照 |
| PNG | 14 个，2,419,239 bytes | 验收截图、Evidence、Phase 2 截图 |
| PDF | 1 个，44 bytes | `storage/acceptance/authorization.pdf`，授权附件，不是 PDF 报告 |
| 生成 HTML | 2 个，19,082 bytes | `storage/reports/project_1_...html`、`project_2_...html` |
| Python 缓存 | 92 个 `.pyc`，1,826,838 bytes | `__pycache__`，可忽略 |
| 测试临时目录 | `.pytest_cache/`、`pytest-of-lenovo/`、`tmpcde5t8kh/`、`storage/_c1_pytest_tmp/`、`storage/tmpv2ziyrtj/` | 目录存在；`.pytest_cache` 在当前沙箱中递归读取被拒绝，内容 UNKNOWN；其他目录未发现文件 |
| 重解析点 | 0 | 未发现 symlink/junction；不排除未来测试创建 |

### 4.3 重复文件观察（用于备份取舍，不建议删除）

| 哈希组 | 重复情况 |
|---|---|
| `4F120652...` | `storage/backups/phase5_acceptance_final_...db` 与 `docs/acceptance/phase5_final/db/phase5_acceptance_final_...db` 相同 |
| `A2423FA7...` | `storage/backups/src_research_phase5_final_...db` 与 `docs/acceptance/phase5_final/db/src_research_phase5_final_...db` 相同 |
| `5C9DEC18...` | 7 个 4 KiB 空/初始数据库副本（多个验收备份目录） |
| `FD25F11A...` | `storage/phase4_acceptance/acceptance.db` 与 `storage/phase5_acceptance/backups/acceptance_v4_...db` 相同 |

这些重复文件可以用于独立备份去重，但**不得删除**；它们可能代表不同阶段的可恢复点。

## 5. 敏感文件风险提示（不暴露敏感值）

### 5.1 扫描结果

- 未发现 `.env`、`.pem`、`.key`、`.pfx`、`.p12` 文件。
- 文件名层面的 `secret`、`token`、`password`、`credential`、`api_key` 搜索未命中真正的凭据文件；命中的 `authorization.py`、`authorization_service.py`、`test_authorization_service.py` 是业务代码/测试代码，不是凭据。
- 根 `config.yaml` 只读取了键名，未打印值。键名包括：`app`、`name`、`version`、`environment`、`theme`、`window_width`、`window_height`、`storage`、`root`、`database`、`path`、`projects`、`reports`、`logs`、`evidence`、`security`、`require_exact_remote_match`、`require_valid_authorization`、`allow_wildcard_scope`、`allow_redirect_following`、`default_remote_access`。**未发现 `password`、`token`、`secret`、`api_key` 等键名。**
- 验收目录下的 `config.yaml` 也呈现相同的配置键结构，未发现显式凭据键名。
- `storage/acceptance/authorization.pdf`：44 bytes，授权附件；**不是 PDF 报告功能产物**；内容未打开，无法确认是否含姓名、邮箱、签名或其他个人信息。
- `storage/**/*.db`：可能包含项目名称、路径、Finding 描述、人工备注、扫描结果、审计记录；未做语义级 PII 扫描。
- `storage/**/evidence/*.png`、`docs/acceptance/*.png`、`docs/screenshots/*.png`：截图可能显示本地路径、项目名、代码片段或用户界面数据；未逐张目视审查。
- `storage/**/logs/*.jsonl`：审计日志可能包含项目路径、操作目标、Finding 摘要；不进入 Git，备份时需限制访问。
- `README.md`、历史阶段报告可能包含本地路径、测试数据、验收环境信息；属于文档风险，不是凭据泄露。

### 5.2 风险等级

| 风险项 | 等级 | 建议 |
|---|---|---|
| 根 `config.yaml` 的机器路径/环境值 | 中低 | REVIEW；考虑未来提供脱敏 `config.example.yaml`，本轮不修改 |
| `storage/acceptance/authorization.pdf` | 中 | REVIEW / BACKUP_ONLY；未确认内容前不跟踪 |
| SQLite 数据库 | 中高 | BACKUP_ONLY；不进入 Git；备份加密/限权 |
| Evidence/验收截图 | 中 | REVIEW/BACKUP_ONLY；确认无敏感信息后才考虑文档化 |
| 验收日志/审计 JSONL | 中 | IGNORE + BACKUP_ONLY；不进入 Git |
| 现有 ZIP 备份 | 中 | BACKUP_ONLY；可能含完整数据库和截图 |
| 无 `.env`/密钥文件 | 低 | 现有情况下未发现凭据文件；未来加入 `.env` 规则 |

> 本报告不打印任何配置值、数据库内容、PDF 内容或截图内容；上述结论是**文件名/键名/元数据级别**的，不是内容级安全审计。

## 6. TRACK / IGNORE / REVIEW / BACKUP_ONLY 分类建议

### 6.1 建议总表

| 分类 | 对象 | 规模 | 建议 |
|---|---|---:|---|
| **TRACK** | 应用/工具 `.py` | 78 个，651,951 bytes | 跟踪 |
| **TRACK** | 测试 `.py` | 26 个，197,746 bytes | 跟踪；测试是历史资产，不整体排除 |
| **TRACK** | `reports/templates/*.html` | 4 个，17,400 bytes | 跟踪 |
| **TRACK** | README + `docs/**.md` | 49 个，704,686 bytes | 跟踪；历史阶段/架构报告不得整体排除 |
| **TRACK** | `docs/acceptance` 文本/JSON/Manifest | 33 个，244,848 bytes | 跟踪；含验收报告、测试输出、Manifest |
| **TRACK** | `.gitignore`、`pytest.ini`、`requirements.txt` | 3 个，744 bytes | 跟踪；`.gitignore` 本轮不改 |
| **TRACK** | `storage/**/.gitkeep` | 4 个，219 bytes | 跟踪占位文件 |
| **REVIEW** | `docs/acceptance/*.png` | 8 个，1,421,311 bytes | 检查是否含本地路径/敏感信息；通过后可跟踪 |
| **REVIEW** | `docs/screenshots/*.png` | 4 个，516,868 bytes | 同上 |
| **REVIEW** | 根 `config.yaml` | 1 个，508 bytes | 检查是否含机器特定值；无凭据键名 |
| **REVIEW** | `storage/acceptance/authorization.pdf` | 1 个，44 bytes | 授权附件，不是 PDF 报告；确认内容后决定 |
| **REVIEW / BACKUP_ONLY** | `storage/phase*_acceptance/` 下的样例源码、配置、验收输入 | 若干小文件 | 运行/验收产物，不建议进 Git |
| **IGNORE** | `__pycache__/`、`*.pyc` | 92 个，1,826,838 bytes | 忽略 |
| **IGNORE** | `.pytest_cache/`、`pytest-of-lenovo/`、`tmpcde5t8kh/`、`storage/_c1_pytest_tmp/`、`storage/tmpv2ziyrtj/` | 0 个文件（目录存在） | 忽略；不删除 |
| **IGNORE** | `storage/reports/*.html` | 2 个，19,082 bytes | 忽略；可由报告功能重新生成；保留 `.gitkeep` |
| **IGNORE** | `storage/**/logs/*.log`、`*.jsonl` | 5 个日志（0 bytes）+ 5 个 JSONL（58,868 bytes） | 忽略；备份保留 |
| **BACKUP_ONLY + IGNORE** | 所有 SQLite `.db`、`.db-shm`、`.db-wal` | 20 + 9 + 9 个，约 2,969,600 bytes | 不进入 Git；独立备份 |
| **BACKUP_ONLY + IGNORE** | `backups/*.zip` | 5 个，5,952,769 bytes | 不进入 Git；独立备份 |
| **BACKUP_ONLY + IGNORE** | `storage/evidence/**`、验收 Evidence 截图 | 2 个 PNG，481,060 bytes | 不进入 Git；敏感证据独立备份 |
| **BACKUP_ONLY + IGNORE** | `docs/acceptance/phase5_final/db/` | 2 个 DB，499,712 bytes | 历史数据库副本；不进入 Git，保留在备份 |
| **BACKUP_ONLY + IGNORE** | 验收运行配置/审计/数据库目录 | `storage/phase*_acceptance/`、`storage/acceptance/` 中生成内容 | 保留在备份，不进入 Git |

> 分类表不是互斥文件计数表：例如 `docs/acceptance` 同时包含应 TRACK 的文本和应 BACKUP_ONLY 的 DB。第 3 节目录统计是互斥的；本节是建议处置，允许一个路径被拆成多类。

### 6.2 对“历史价值”的明确处理

- **不整体排除** `docs/acceptance/`、`docs/screenshots/`、`docs/*.md` 和 `tests/`。
- `docs/acceptance` 的 Markdown、JSON、TXT、Manifest 全部建议 TRACK；其中的 DB 只做 BACKUP_ONLY；截图做 REVIEW，通过审查后可 TRACK，而不是删除或整体忽略。
- `docs/acceptance/phase5_final/db/` 是历史数据库副本，**不删除、不改写、不伪造**；只建议不进入 Git，独立备份。
- 既有 `backups/*.zip` 是历史快照，**不删除、不重建、不覆盖**；只建议 BACKUP_ONLY。
- `.gitignore` 已存在，本任务不修改；建议内容只写在本报告中。

### 6.3 不建议进入 Git 的具体二进制

- `backups/` 下 5 个 ZIP；
- `storage/` 下 20 个 `.db` 及 9 个 `.db-shm`；
- `docs/acceptance/phase5_final/db/` 下 2 个 DB；
- `storage/evidence/` 和验收 Evidence PNG；
- 92 个 `.pyc`；
- 2 个 `storage/reports/*.html` 生成物；
- `storage/acceptance/authorization.pdf` 在确认内容前不跟踪（它是授权附件，不是 PDF 报告）。

> 这些文件不是“因为体积大就删除”；它们被建议独立备份或忽略，原文件保持不动。

## 7. `.gitignore` 建议内容（只写入报告，不创建/修改文件）

### 7.1 现有规则（保留）

现有 `.gitignore` 的 18 行规则见第 2.1 节。建议初始化 Git 前保留这些规则，不删除。

### 7.2 建议追加的规则

以下内容**仅作为报告建议**；本任务不执行，不创建 `.gitignore`，不修改现有 `.gitignore`。

```gitignore
# 凭据/本地环境（未来）
.env
.env.*
*.pem
*.key
*.pfx
*.p12

# 测试/运行临时目录
pytest-of-lenovo/
tmpcde5t8kh/
storage/_c1_pytest_tmp/
storage/tmp*/

# SQLite（递归覆盖，避免只忽略 storage 根层）
storage/**/*.db
storage/**/*.db-wal
storage/**/*.db-shm
*.db-journal

# 运行时日志（递归）
storage/**/logs/*.log
storage/**/logs/*.jsonl

# 生成报告与证据
storage/reports/*
!storage/reports/.gitkeep
storage/evidence/**
!storage/evidence/.gitkeep

# 验收运行数据（不是 docs/acceptance 历史文档）
storage/phase*_acceptance/
storage/acceptance/

# 文档目录中的数据库副本
docs/acceptance/**/db/
docs/acceptance/**/*.db
docs/acceptance/**/*.db-wal
docs/acceptance/**/*.db-shm
```

### 7.3 注意事项

- `storage/phase*_acceptance/` 和 `storage/acceptance/` 是运行/验收数据目录；忽略它们不会删除任何历史报告，`docs/acceptance/` 仍保留并建议 TRACK。
- `docs/acceptance/**/db/` 只忽略数据库副本；`docs/acceptance` 下的 Markdown/JSON/TXT/Manifest 不会被忽略。
- `storage/evidence/**` 的 `.gitkeep` 例外用于保留目录；如果决定不跟踪空证据目录，可以删除该例外。
- `config.yaml` 没有自动加入忽略；它是 REVIEW 项。若最终决定只提交脱敏示例，应在初始化前明确新增 `config.example.yaml`，本轮不创建。
- 不建议使用全局 `*.zip` 或 `*.png` 一刀切规则；它们会误伤未来可跟踪的文档资产。
- 现有 `.gitignore` 本身已被纳入建议 TRACK；初始化后应审查其 diff，但本轮不修改。

## 8. 独立备份建议

### 8.1 备份位置

- 首选：**项目目录之外**的独立物理磁盘/网络位置，例如 `E:\SRC-Research-Assistant-Backups\` 或 NAS 的专用备份目录。
- 次选（同机但项目外）：`D:\SRC-Research-Assistant-Backups\`。
- **不要**把正式备份放在项目根目录或 `backups/` 内；现有 `backups/` 只是历史 ZIP，不应作为唯一副本。
- 本任务不创建任何备份目录或文件。

### 8.2 命名规则

建议每次完整备份创建独立目录，避免覆盖：

```text
<backup_root>/
  src-research-assistant_20261110T103000Z/
    workspace/                 # 源码、测试、文档、模板、配置
    databases/                 # SQLite 一致性副本
    evidence/                  # Evidence 文件（如决定备份）
    manifest.sha256            # 相对路径 + 大小 + SHA-256
    metadata.json              # 时间、文件数、总大小、DB user_version/integrity
    src-research-assistant_20261110T103000Z_full.zip
    20261110T103000Z.sha256    # 压缩包自身 SHA-256
```

命名格式：`src-research-assistant_<UTC时间戳>Z_full.zip`；同一时间戳的目录、清单和 SHA 文件一一对应，不覆盖历史。

### 8.3 备份内容

建议包含：

- `app/`、`core/`、`database/`、`reports/`、`repositories/`、`scanners/`、`security/`、`services/`、`ui/`、`tools/`、`tests/`；
- `main.py`、`README.md`、`docs/`（含 `docs/acceptance/` 全部历史材料）；
- `config.yaml`（如包含机器路径/敏感信息，备份介质加密并限权）；
- `requirements.txt`、`pytest.ini`、`.gitignore`；
- `backups/` 现有 5 个 ZIP（保留历史快照）；
- SQLite 数据库的一致性副本（见 8.4）；
- `storage/evidence/`、验收截图/日志（如确认需要保留）。

建议排除（可由 `.gitignore` 同步排除，但完整备份应记录排除规则）：

- `.venv/`、`.tmp/`、`__pycache__/`、`*.pyc`；
- `.pytest_cache/`、`pytest-of-lenovo/`、`tmpcde5t8kh/`、`storage/_c1_pytest_tmp/`、`storage/tmpv2ziyrtj/`；
- 可由导出器重新生成的 `storage/reports/*.html`（是否排除应记录，不删除原文件）。

### 8.4 SQLite 数据库备份

不要在应用运行且数据库打开时直接复制 `.db` 文件并假定一致。建议：

1. 正常关闭应用；
2. 对每个 `.db` 使用 SQLite 在线备份 API（Python `sqlite3.Connection.backup()`）写出到 `databases/`；
3. 备份后以 `mode=ro&immutable=1` 执行 `PRAGMA integrity_check` 和 `PRAGMA user_version`，写入 `metadata.json`；
4. 如果必须做原始文件复制，同时保留 `-wal`/`-shm`，并记录应用已关闭；不要让 Git 跟踪这些文件；
5. 保留 `storage/backups/` 和 `docs/acceptance/phase5_final/db/` 的历史数据库副本，不做删除或合并。

当前数据库只读检查结果（实际执行）：

| 数据库 | 大小 | user_version | integrity_check |
|---|---:|---:|---|
| `storage/src_research.db` | 147,456 | 5 | ok |
| `storage/phase5_acceptance/acceptance.db` | 352,256 | 5 | ok |
| `storage/acceptance/acceptance.db`（遗留） | 126,976 | 2 | ok |

### 8.5 完整性记录与验证

每次备份记录：

- 备份时间（UTC 和本地时间）、项目版本、Schema 版本；
- 文件数量、总字节数；
- 每个文件的相对路径、大小、SHA-256；
- 压缩包 SHA-256；
- 数据库 `integrity_check`、`user_version`；
- 现有 ZIP 备份的 SHA-256（如果一并备份）。

验证步骤：

1. 用 `Get-FileHash` 对比备份包和 sidecar SHA；
2. 解压到**项目外**的临时目录，逐文件对比 `manifest.sha256`；
3. 确认文件数、总大小与 `metadata.json` 一致；
4. 对解压后的数据库执行只读 `PRAGMA integrity_check`；
5. 记录验证结果和验证人/时间；验证失败不得覆盖原备份。

### 8.6 保留策略

- 至少保留最近 7 个每日快照、4 个每周快照和 3 个关键阶段快照；
- 历史 `backups/*.zip` 和 Phase 5 final DB 副本保留，不因新备份而删除；
- 备份介质加密（BitLocker 或 7z AES-256），密钥独立保管；
- 定期做一次恢复演练，验证不只是“文件存在”。

## 9. 初始化 Git 前必须解决的问题

1. **先补全 `.gitignore`**：现有规则没有覆盖嵌套 `storage/**/*.db`、`storage/phase*_acceptance/`、`storage/evidence/`、`storage/reports/`、测试临时目录和 `docs/acceptance/**/db/`；本任务按约束未修改。
2. **决定数据库策略**：数据库 20 个、约 2.67 MB，且包含主库、Phase 3/4/5 验收库、历史备份库和重复副本；建议 BACKUP_ONLY，不进入 Git；不要把 `.db-shm`/`.db-wal` 当普通文本提交。
3. **决定 Evidence/截图策略**：14 个 PNG（2.42 MB）中既有文档截图，也有 Evidence 截图；截图可能显示本地路径、项目名或代码片段，必须先 REVIEW，不能盲目提交。
4. **确认 `authorization.pdf` 的性质**：它是 `storage/acceptance/` 下的 44-byte 授权附件，不是 PDF 报告功能产物；未确认内容前不应跟踪，也不应因“PDF”而重新开启 PDF 功能。
5. **确认 `config.yaml` 是否包含机器特定信息**：键名层面未发现 token/password/secret/api_key，但包含 `root`、`path` 等路径键；建议 REVIEW，必要时只提交脱敏示例。
6. **处理已有 `.gitignore` 的来源与意图**：它已存在 18 行，但没有 `.git`；无法确认是历史遗留、备用规则还是尚未启用的配置。初始化前应由人工确认，而不是直接信任。
7. **确认 Git 身份和换行策略**：Git 全局 `user.name`/`user.email`、`core.autocrlf`、全局 excludes 文件未检查，属于 UNKNOWN。
8. **在首次提交前做一次外部备份**：尤其在主数据库、验收数据库、Evidence 和 `backups/` ZIP 尚未独立备份的情况下，不要先 `git init` 再补救。
9. **决定首个提交的范围**：建议第一阶段只提交源码、测试、模板、文档和文本验收材料；数据库/Evidence/备份先排除，待安全审查和完成独立备份后再讨论是否纳入。
10. **不要删除或移动现有 ZIP/DB/验收材料**：它们有历史价值；Git 忽略与独立备份是不同问题。

## 10. UNKNOWN 和无法验证的事项

| 项目 | 状态 | 说明 |
|---|---|---|
| `.pytest_cache/` 内容 | **UNKNOWN** | 目录存在，但当前沙箱递归读取被拒绝（`UnauthorizedAccessException`）；未读取、未修改 |
| `pytest-of-lenovo/`、`tmpcde5t8kh/`、`storage/_c1_pytest_tmp/`、`storage/tmpv2ziyrtj/` 内容 | 目录存在；文件计数为 0（非递归检查） | 空目录/临时目录的完整内容未能完全验证；不应跟踪 |
| 数据库内容中的 PII/敏感业务数据 | **UNKNOWN** | 仅做只读 `integrity_check`/`user_version`；未做内容级 PII 扫描 |
| `authorization.pdf` 内容 | **UNKNOWN** | 只记录 44 bytes 和路径；未打开，不确认是否含个人信息 |
| Evidence/PNG 截图的可见内容 | **UNKNOWN** | 未逐张目视检查；可能含本地路径、项目名、代码片段 |
| Git 全局用户身份、`core.autocrlf`、全局 excludes | **UNKNOWN** | 未读取全局 Git 配置，避免暴露个人信息 |
| 外部备份介质、可用空间、BitLocker 状态 | **UNKNOWN** | 未检查任何备份盘或网络位置 |
| `.gitignore` 的来源/意图 | **UNKNOWN** | 文件已存在且可读，但没有 Git 历史可追溯 |
| 全项目逐文件 SHA-256 清单 | **未生成** | 本轮只对关键 DB/ZIP/HTML/PDF 做了哈希；完整清单应在外部备份阶段生成 |
| 主数据库哈希变化 | **UNKNOWN** | 当前 `storage/src_research.db` SHA-256 为 `ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8`，mtime 为 `2026-11-09 22:51:03`（早于本审计）；早期 Phase 6 记录曾为 `F03CFB81...`。本审计未写数据库，变化原因未调查，不能声称两者完全一致 |
| 测试环境全域可用性 | **不在本轮范围** | 未运行 pytest；完整测试需要专用临时目录/full-access 的处理见 C1-R 报告 |
| 文件系统 ACL/所有权 | 部分 | 只读盘点未修改 ACL；`.pytest_cache` 的拒绝访问说明当前沙箱环境存在限制 |

## 11. 本轮实际修改清单与完成声明

### 11.1 新增文件

- `docs/GIT_REPOSITORY_PREPARATION_AUDIT.md`（本报告）

### 11.2 明确没有执行的操作

- 没有执行 `git init`；
- 没有创建或修改 `.gitignore`；
- 没有执行 Git add/commit/reset/clean/checkout；
- 没有删除、移动、重命名或覆盖任何现有文件；
- 没有修改 Python 代码、测试、数据库或 Schema；
- 没有安装/升级软件包；
- 没有打开数据库执行写入；
- 没有上传项目到远程仓库；
- 没有打印配置值、密码、Token、密钥或数据库内容；
- 没有运行 pytest；
- 没有开始 HTML/PDF/JSON 开发。

### 11.3 完成条件核对

| 完成条件 | 结果 |
|---|---|
| 只新增调查报告 | **满足**；本报告为唯一新增文件 |
| 其他现有文件未修改 | **满足**；仅只读命令和只读数据库连接 |
| 数据库/Schema 未变化 | **本审计未写入**；主库/验收库只读检查 `integrity=ok`；主库既有 mtime 早于审计 |
| 没有初始化 Git | **满足**；`.git` 仍不存在 |
| 没有创建提交 | **满足** |
| 没有连接远程 | **满足** |
| 区分实际检查/推测/UNKNOWN | **满足**；见第 1、2、10 节标注 |

## 12. 最终建议

```text
GIT_PREPARATION_STATUS = READ_ONLY_AUDIT_COMPLETED
INITIALIZE_NOW = NO
TRACK_SOURCE_TESTS_DOCS = YES
TRACK_DATABASES = NO
TRACK_EVIDENCE = NO_BY_DEFAULT
TRACK_BACKUPS = NO
NEED_GITIGNORE_UPDATE = YES
NEED_EXTERNAL_BACKUP_FIRST = YES
AUTHORIZATION_PDF_IS_REPORT_PDF = NO
PDF_REPORT_REOPENED = NO
```

**建议顺序：**

1. 人工审核本报告和 `.gitignore` 建议；
2. 完成一次项目外部的完整备份（含数据库一致性副本、Evidence 和现有 ZIP）；
3. 由人工决定 `config.yaml`、验收截图和 `authorization.pdf` 的最终处置；
4. 在独立步骤中更新 `.gitignore`（本任务不执行）；
5. 再执行 `git init`、首次基线提交和远程配置审查。

本报告到此停止，等待人工审核；**不进入 Git 初始化阶段**。
