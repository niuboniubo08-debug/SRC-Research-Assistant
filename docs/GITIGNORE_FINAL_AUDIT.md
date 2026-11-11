# SRC Research Assistant — Git-3A `.gitignore` 最终审计

## 0. 结论摘要

| 结论项 | 值 |
|---|---|
| `GITIGNORE_DESIGN_STATUS` | **CONDITIONAL_GO** |
| `GIT_INIT_READINESS` | **CONDITIONAL_GO** |

本阶段只做了只读扫描和规则设计；**没有创建或修改 `.gitignore`，没有初始化 Git，没有暂存或提交任何文件**。

当前 `.gitignore` 能忽略 125 个文件，但漏掉了 `pytest-of-lenovo` 的 **2,415 个文件 / 104,478,924 字节**，并且 `storage/*.db` 只覆盖 `storage/` 根目录，漏掉多个验收数据库及 sidecar。推荐草案改为更明确的规则后，默认可忽略 **2,579 个文件 / 115,608,114 字节**，保留 **220 个默认候选文件 / 4,264,771 字节** 供人工审查后暂存。

条件是先完成本报告第 8 节列出的 REVIEW 决策，并在 Git-3B 中实际创建 `.gitignore`、执行 `git check-ignore` 和 `git add -n` 验证。

## 1. 当前 `.gitignore` 状态

### 1.1 文件状态

- `D:\挖漏洞\SRC-Research-Assistant\.gitignore` 存在，不是空文件。
- 大小：221 字节。
- 行数：18 行，18 条有效规则；无空规则。
- 当前没有 `.git` 目录；未初始化 Git。

### 1.2 当前规则及实际匹配

| 规则 | 实际匹配文件数 | 实际大小 | 主要匹配 |
|---|---:|---:|---|
| `.venv/` | 0 | 0 | 无；项目 venv 在 `D:\挖漏洞\.venv`，不在仓库内 |
| `.tmp/` | 0 | 0 | 无 |
| `.screenshot-demo/` | 0 | 0 | 无 |
| `debug.log` | 0 | 0 | 无 |
| `__pycache__/` | 92 | 1,826,838 | 各包下的 `.pyc` |
| `*.py[cod]` | 92 | 1,826,838 | 同上；当前没有 `.pyo`，与上条重叠 |
| `.pytest_cache/` | 5 | 17,803 | `.pytest_cache` 下缓存文件 |
| `storage/*.db` | 1 | 147,456 | 仅 `storage\src_research.db` |
| `storage/*.db-*` | 2 | 32,768 | 仅 `storage\src_research.db-shm` / `.db-wal` |
| `storage/logs/*.log` | 1 | 0 | 仅 `storage\logs\app.log` |
| `storage/logs/*.jsonl` | 1 | 1,732 | 仅 `storage\logs\audit.jsonl` |
| `storage/backups/` | 18 | 1,077,248 | 仅 `storage\backups\` 下的 DB/sidecar |
| `storage/cache/` | 0 | 0 | 无 |
| `storage/tmp/` | 0 | 0 | 无 |
| `backups/` | 5 | 5,952,769 | 根目录 5 个历史 ZIP |
| `build/` | 0 | 0 | 无 |
| `dist/` | 0 | 0 | 无 |
| `*.spec` | 0 | 0 | 无 |

规则并集实际忽略：**125 个文件 / 9,056,614 字节**。

### 1.3 当前规则的主要缺口

1. **`pytest-of-lenovo` 完全未忽略**：2,415 个文件 / 104,478,924 字节，是当前最大风险。
2. **数据库规则只覆盖 `storage/` 根**：`storage/*.db` 只匹配 1 个文件；`storage/backups/` 另由单独规则覆盖 6 个数据库和 12 个 sidecar，除此之外仍有 **11 个 storage 数据库 / 22 个 sidecar** 未覆盖（主要是 `storage/acceptance` 和 `storage/phase*_acceptance` 下的验收/备份文件）。
3. **`docs/acceptance` 的 2 个历史数据库未忽略**：499,712 字节；是否进入 Git 属于 REVIEW，不应由宽泛规则自动决定。
4. **验收 logs 未忽略**：`storage/acceptance/logs`、`storage/phase3/4/5_acceptance/logs` 共 8 个文件 / 57,136 字节；这些是历史审计材料，不能简单按“包含 log”误排除。
5. **生成报表 HTML 未忽略**：`storage/reports/*.html` 2 个 / 19,082 字节；属于历史/生成产物的 REVIEW 项。
6. **配置和授权附件未忽略或分类**：根 `config.yaml`、4 个 storage 配置、`storage/acceptance/authorization.pdf` 需要 REVIEW，不能套用宽泛 `*.pdf` 或 `storage/` 规则。

## 2. 实际扫描口径

- 扫描时间：2026-11-11（本任务）。
- 项目：`D:\挖漏洞\SRC-Research-Assistant`。
- 总文件：**2,799 个**。
- 总大小：**119,872,885 字节**。
- 总目录：1,595 个（含缓存目录）。
- 扫描方式：递归读取路径、大小、类型；**未读取配置文件、日志、授权 PDF、证据图片、HTML 报告的内容**；未打开数据库，未执行 Git 命令。
- 当前无 `.git`；扫描未创建文件。
- 本报告本身在扫描完成后新增，因此不计入上述 2,799；当前实际文件数为 2,800，默认候选由 220 变为 221（仅多出本报告）。

### 2.1 顶层分布

| 顶层 | 文件数 | 字节数 | 说明 |
|---|---:|---:|---|
| `<root>` | 6 | 21,262 | 根文件 |
| `pytest-of-lenovo` | 2,415 | 104,478,924 | pytest 临时目录，IGNORE |
| `storage` | 84 | 3,326,510 | 含运行时/验收数据库、日志、报告 |
| `docs` | 84 | 3,378,300 | 文档、验收数据库、截图 |
| `backups` | 5 | 5,952,769 | 历史 ZIP，IGNORE/REVIEW |
| `.pytest_cache` | 5 | 17,803 | 缓存，IGNORE |
| `tests` | 55 | 1,124,028 | 含 26 个测试源码，其余为缓存 |
| `ui` | 34 | 652,000 | 含缓存 |
| `core` | 28 | 123,043 | 含缓存 |
| `services` | 20 | 301,142 | 含缓存 |
| `tools` | 14 | 84,714 | 工具脚本 |
| `reports` | 8 | 87,154 | 模板和模块 |
| `app` | 8 | 35,020 | 含缓存 |
| `scanners` | 13 | 110,824 | 含缓存 |
| 其他源码目录 | — | — | `security`、`database`、`repositories` 等 |

## 3. TRACK / IGNORE / REVIEW 清单

### 3.1 TRACK（建议进入版本控制）

| 类别 | 实际内容 | 默认文件数 | 说明 |
|---|---|---:|---|
| 根元数据 | `.gitignore`、`README.md`、`main.py`、`pytest.ini`、`requirements.txt` | 5 | 均为项目入口/依赖/规则文件 |
| Python 源码 | `app/`、`core/`、`database/`、`repositories/`、`scanners/`、`security/`、`services/`、`tools/`、`ui/` 下的 `.py` | 68 | 排除 `__pycache__` |
| 测试源码 | `tests/` 下 26 个 `.py` | 26 | 排除 `__pycache__` |
| 报告模块/模板 | `reports/__init__.py`、`reports/html_exporter.py`、4 个 HTML 模板 | 6 | 不含 `__pycache__` |
| 文档 | `docs/` 下 54 个 `.md`、10 个 `.json`、4 个 `.txt` 等 | 54+ | 历史验收 Markdown/JSON/TXT；不含数据库和截图 |
| `.gitkeep` | `storage/evidence`、`storage/logs`、`storage/projects`、`storage/reports` 下的 4 个占位文件 | 4 | 保留空目录 |
| 验收数据/夹具（REVIEW 后） | `storage/acceptance/local_project/app.py`、phase3 两个示例 `.py`、phase4 的 `requirements.txt`/`pyproject.toml`/示例源码 | 7 | 小体量、可复现验收；当前归入 REVIEW，不建议未经确认直接暂存 |

说明：`docs/` 不能整体排除。历史验收报告、Manifest、架构文档和 JSON 应保留；`docs/acceptance` 中的截图和数据库属于 REVIEW，不能因为目录名是 `docs` 就整体忽略，也不能因为“生成”就整体删除。

### 3.2 IGNORE（建议明确忽略）

| 类别 | 规则/路径 | 匹配文件数 | 字节数 | 备注 |
|---|---|---:|---:|---|
| pytest 临时 | `/pytest-of-*/` | 2,415 | 104,478,924 | 含测试数据库、夹具和日志；当前未忽略 |
| Python 缓存 | `__pycache__/`、`*.py[cod]` | 92 | 1,826,838 | 两者重叠；无可执行语义 |
| pytest 缓存 | `.pytest_cache/` | 5 | 17,803 | 可再生 |
| SQLite 主文件 | `*.db` | 1,772 | 106,606,592 | 1,752 个在 pytest 临时；仓库外 20 个（运行时/备份/历史验收） |
| SQLite WAL | `*.db-wal` | 20 | 0 | 与 SHM 成对，均不应版本化 |
| SQLite SHM | `*.db-shm` | 20 | 655,360 | 传输/缓存文件，不是数据库 |
| 运行时日志 | `/storage/logs/*.log`、`/storage/logs/*.jsonl` | 2 | 1,732 | 仅 `storage/logs` 根；不扩展到验收 logs |
| 根备份 ZIP | `/backups/` | 5 | 5,952,769 | 二进制历史备份；E 盘已有正式备份 |
| storage 根备份 | `/storage/backups/` | 18 | 1,077,248 | 备份数据库/sidecar；主要由 `*.db*` 覆盖，显式保留意图 |
| 环境文件 | `.env`、`.env.*` | 0 | 0 | 当前没有；作为未来敏感配置防线 |
| 环境模板例外 | `!.env.example`、`!.env.template` | 0 | 0 | 当前不存在；保留模板可跟踪的语义 |

**不采用**：`storage/`、`docs/`、`*.pdf`、`*.zip`、`*.json`、`*.md` 这类宽泛规则。它们会误伤历史验收材料、授权附件、报告和文档。

### 3.3 REVIEW（必须人工决定，不能自动套规则）

| 路径/类别 | 文件数 | 字节数 | 风险/原因 | 建议动作 |
|---|---:|---:|---|---|
| `config.yaml`（根） | 1 | 508 | 可能包含本机路径或本地配置 | 决定 track 或显式 ignore；不要直接输出内容 |
| `storage/acceptance/config.yaml` 等 4 个配置 | 4 | 1,836 | 验收环境配置，可能含路径 | 逐个决定；建议 REVIEW |
| `storage/acceptance/authorization.pdf` | 1 | 44 | 授权附件，不是 PDF 报告功能 | 不应被 `*.pdf` 自动忽略；决定是否入库 |
| `storage/logs/audit.jsonl` + 4 个验收 `logs/*.jsonl`、`app.log` | 10 | 58,868 | 审计日志可能含项目/路径/主体信息 | 运行时 `storage/logs` 可忽略；验收 logs 逐项 REVIEW |
| `storage/reports/*.html` | 2 | 19,082 | 生成报告，可能含 Finding/项目名称 | 是可再生产物还是历史证据；决定 track/ignore |
| `storage/phase4_acceptance/requirements_project/phase5_evidence_screenshot.png` | 1 | 240,530 | 证据截图，可能含用户数据 | REVIEW；不要自动忽略 |
| `storage/phase5_acceptance/evidence/project_1/..._phase5_evidence_screenshot.png` | 1 | 240,530 | 证据副本，可能含用户数据 | REVIEW |
| `docs/acceptance/*.png` 及 `docs/screenshots/*.png` | 8 | 1,421,311 | 验收截图，可能含项目/路径/用户数据 | REVIEW 后决定是否入库；不要因 PNG 自动排除 |
| `docs/acceptance/phase5_final/db/*.db` | 2 | 499,712 | 历史验收数据库；不是模板 | 默认被 `*.db` 忽略；如要保留历史，需明确批准后 `git add -f` |
| `storage/acceptance/*.db`、`storage/phase3/4/5_acceptance/*.db` | 4 | 876,544 | 历史验收数据库；不是运行主库 | 默认被 `*.db` 忽略；如要入库需逐库决定 |
| `backups/*.zip` | 5 | 5,952,769 | 大型历史备份，可能含敏感配置/证据 | 建议 IGNORE；如要历史留存需说明 |
| `storage/acceptance/local_project/app.py` 等验收小夹具 | 7 | 约 601 | 验收样例，非生产源码 | 逐项 REVIEW；可 TRACK 以复现验收 |
| `.gitkeep` | 4 | 219 | 空目录占位 | TRACK，不应被忽略 |

**REVIEW 的数量不是“必须忽略”的意思**：它表示没有足够依据自动决定。当前默认草案不主动排除这些路径，因而它们会出现在 `git add -n` 结果中；必须在 Git-3B 前逐项决定，不能先 `git add .`。

## 4. 推荐 `.gitignore` 完整草案

只写入本报告，**没有创建或修改实际 `.gitignore`**：

```gitignore
# Python / pytest generated files
__pycache__/
*.py[cod]
.pytest_cache/
/pytest-of-*/

# SQLite databases and sidecars (see report: no template DB found;
# historical acceptance DBs need an explicit force-add decision)
*.db
*.db-wal
*.db-shm

# Runtime logs only at storage/logs; acceptance logs remain REVIEW
/storage/logs/*.log
/storage/logs/*.jsonl

# Binary backup artifacts
/backups/
/storage/backups/

# Secret/environment files
.env
.env.*
!.env.example
!.env.template
```

### 4.1 设计取舍

- `*.db` 是全局 SQLite 忽略；当前 **没有数据库模板或示例数据库**，因此不会误伤模板。历史验收数据库默认被忽略；如果人工确认要保留，使用 `git add -f` 明确加入，而不是放宽全局规则。
- `.gitignore` 没有 `*.pdf`；`storage/acceptance/authorization.pdf` 保留可见，交由 REVIEW。
- `.gitignore` 没有 `*.zip`；只忽略明确的 `/backups/`，未来其他 ZIP 仍需人工判断。
- `.gitignore` 没有 `docs/` 或 `storage/` 整体规则；文档、验收 JSON/Markdown、`.gitkeep` 和部分验收夹具仍可跟踪。
- `.gitignore` 没有 `*.json` 或 `*.md`；历史验收 JSON/Markdown 不会被误排除。
- `.gitignore` 没有 `storage/reports/*.html`、`config.yaml`、验收 logs 的规则；这些是 REVIEW 项，待人工决定。
- 旧规则中 `.venv/`、`.tmp/`、`.screenshot-demo/`、`debug.log`、`storage/cache/`、`storage/tmp/`、`build/`、`dist/`、`*.spec` 当前实际匹配均为 0。可从新草案中删除，或作为未来防线保留；本报告建议删除，以保持最小化。

## 5. 规则影响分析

### 5.1 推荐规则的逐条影响

| 规则 | 匹配数 | 典型路径 | 潜在误伤/例外 |
|---|---:|---|---|
| `__pycache__/` | 92 | `app/__pycache__/config.cpython-314.pyc` | 无；缓存可再生 |
| `*.py[cod]` | 92 | 同上 | 与上一条重叠；当前无 `.pyo` |
| `.pytest_cache/` | 5 | `.pytest_cache/v/cache/nodeids` | 无；缓存可再生 |
| `/pytest-of-*/` | 2,415 | `pytest-of-lenovo/pytest-7/...` | 仅根目录的 pytest 临时目录；不会匹配 docs 中的正常文件 |
| `*.db` | 1,772 | `storage/src_research.db`、`docs/acceptance/phase5_final/db/*.db` | 默认忽略 6 个历史验收 DB；需人工 `git add -f` 才能保留 |
| `*.db-wal` | 20 | `storage/src_research.db-wal` | 0 字节也可能存在；不应跟踪 |
| `*.db-shm` | 20 | `storage/src_research.db-shm` | 传输缓存；不应跟踪 |
| `/storage/logs/*.log` | 1 | `storage/logs/app.log` | 仅运行时根；验收 logs 不动 |
| `/storage/logs/*.jsonl` | 1 | `storage/logs/audit.jsonl` | 仅运行时根；验收 audit 仍 REVIEW |
| `/backups/` | 5 | `backups/src-research-assistant_phase5_final.zip` | 历史 ZIP 被忽略；如要入库需例外 |
| `/storage/backups/` | 18 | `storage/backups/*.db` | 备份产物；与 `*.db*` 重叠 |
| `.env` / `.env.*` | 0 | 当前无 | 未来 `.env.example` 由 `!` 规则保留 |
| `!.env.example` / `!.env.template` | 0 | 当前无 | 当前无可匹配文件，规则为未来语义 |

### 5.2 与当前 `.gitignore` 的差异

- 新增 `/pytest-of-*/`：多忽略 **2,415 个文件 / 104,478,924 字节**，解决最大风险。
- 将 `storage/*.db`/`storage/*.db-*` 改为全局 `*.db`/`*.db-wal`/`*.db-shm`：覆盖当前 20 个仓库内数据库和 40 个 sidecar，而不是仅根目录 1+2 个。
- 保留 `/storage/logs/*` 的精确范围，不扩大到验收 logs。
- 保留 `/backups/` 与 `/storage/backups/`；删除 0 匹配的旧规则（如采用最小草案）。
- 当前规则并集 125 个文件 / 9,056,614 字节；推荐草案并集 **2,579 个文件 / 115,608,114 字节**。
- 推荐草案默认保留 **220 个文件 / 4,264,771 字节**；其中包含需 REVIEW 的配置、日志、授权 PDF、报告 HTML 和截图，不能直接用 `git add .`。

## 6. 敏感信息审计

本阶段只报告路径、类别和大小，**未打印任何密钥、Token、密码、配置值、日志内容、证据内容或 PDF 内容**。

| 类别 | 路径 | 处理建议 |
|---|---|---|
| 根配置 | `config.yaml`（508 字节） | REVIEW；可能含本机路径/本地设置 |
| 验收配置 | `storage/acceptance/config.yaml`、`storage/phase3/4/5_acceptance/config.yaml`（4 个，共 1,836 字节） | REVIEW；不要直接入库 |
| 授权附件 | `storage/acceptance/authorization.pdf`（44 字节） | REVIEW；不是 PDF 报告功能，不能按扩展名忽略 |
| 运行/审计日志 | `storage/logs/audit.jsonl`、`storage/logs/app.log`、4 个验收 logs（10 个，共 58,868 字节） | 运行时根可 IGNORE；验收 logs 逐项 REVIEW |
| 证据/截图 | `storage/phase4_acceptance/.../phase5_evidence_screenshot.png`、`storage/phase5_acceptance/evidence/...png`（2 个，共 481,060 字节） | REVIEW；可能含用户数据 |
| 验收截图 | `docs/acceptance/*.png`、`docs/screenshots/*.png`（8 个，共 1,421,311 字节） | REVIEW；可保留历史但需检查是否含敏感信息 |
| 报告产物 | `storage/reports/*.html`（2 个，共 19,082 字节） | REVIEW；可能含 Finding/项目名称 |
| 历史备份 ZIP | `backups/*.zip`（5 个，共 5,952,769 字节） | 建议 IGNORE；如保留需专门说明 |
| 历史数据库 | `docs/acceptance/.../*.db`（2 个，共 499,712 字节）、`storage/*_acceptance/*.db`（4 个，共 876,544 字节） | 默认被 `*.db` 忽略；如入库需人工批准并 `git add -f` |
| `.env` | 当前 0 个 | 未来由 `.gitignore` 规则保护；保留 `.env.example`/`.env.template` |

**UNKNOWN**：上述文件是否包含真实凭据、个人信息或客户数据，未通过读取内容确认；当前只依据路径、名称和大小做风险分类。

## 7. 特别目录审计

### 7.1 `storage/`

- 总文件 84 个 / 3,326,510 字节。
- 18 个 `.db` / 2,174,976 字节，40 个 sidecar / 655,360 字节。
- 运行时主数据库：`storage/src_research.db`，应 IGNORE。
- 验收数据库：`storage/acceptance/acceptance.db`、`storage/phase3/4/5_acceptance/acceptance.db`，默认被 `*.db` 忽略，标记 REVIEW，不能声称已纳入 Git。
- 备份数据库：`storage/backups/` 18 个文件 / 1,077,248 字节，IGNORE。
- 验收 logs：8 个 / 57,136 字节，REVIEW；运行时 `storage/logs` 2 个 / 1,732 字节 IGNORE。
- 报告 HTML 2 个 / 19,082 字节，REVIEW。
- `.gitkeep` 4 个，TRACK。
- 小验收夹具 7 个，REVIEW 后可 TRACK。

### 7.2 `storage/backups/`

- 18 个文件 / 1,077,248 字节，全部为 `.db` 或 sidecar。
- 属于备份产物；推荐 IGNORE，并由 E 盘正式备份承担历史保留职责。
- 如果需要在 Git 中保留特定备份，应逐文件 `git add -f`，不能整体放宽 `storage/`。

### 7.3 `storage/acceptance/`

- 11 个文件 / 212,175 字节。
- 包含 `acceptance.db`、backup、`authorization.pdf`、`config.yaml`、logs 和 `local_project/app.py`。
- 数据库被 `*.db` 忽略；PDF、配置、日志和小夹具进入 REVIEW。
- **不能因为目录名包含 acceptance 就整体排除**；其中 `authorization.pdf` 和验收材料具有历史意义。

### 7.4 `storage/reports/`

- 3 个文件 / 19,136 字节：`.gitkeep` + 2 个 HTML。
- `.gitkeep` TRACK；HTML 是生成报告，REVIEW；当前不加入忽略规则。
- 如确认 HTML 只是可再生产物，可后续加入 `/storage/reports/*.html`；本轮不创建该规则。

### 7.5 `docs/acceptance/`

- 43 个文件 / 2,165,871 字节：19 个 `.md`、10 个 `.json`、4 个 `.txt`、8 个 `.png`、2 个 `.db` 和 sidecar 等。
- Markdown/JSON/TXT 默认 TRACK；PNG REVIEW；2 个 DB 被 `*.db` 忽略，REVIEW。
- 不能整体忽略 `docs/`；历史验收正文、Manifest、JSON 是项目历史的一部分。

### 7.6 `tests/`

- 55 个文件 / 1,124,028 字节，其中 26 个测试 `.py`；其余 29 个为 `__pycache__`/`.pyc`。
- 测试源码 TRACK；缓存 IGNORE。

### 7.7 `reports/`

- 8 个文件 / 87,154 字节。
- `__init__.py`、`html_exporter.py`、4 个模板、2 个 `__pycache__` 文件。
- 源码和模板 TRACK；缓存 IGNORE。
- 模板 HTML 不会被 `/storage/reports/*.html` 规则误伤，因为规则只匹配 storage 下。

### 7.8 `backups/`

- 根目录 5 个 ZIP / 5,952,769 字节。
- 推荐 IGNORE；E 盘正式备份是当前备份依据。
- 由于是大型二进制历史备份，标记 REVIEW：如果团队要求 Git 内保留历史 ZIP，必须单独决定并说明。

## 8. Git-3B 前置条件

### 8.1 是否可以安全执行 `git init`

**可以执行 `git init`，但只能作为空仓库初始化，不能紧接着 `git add .`。**

原因：

- 当前没有 `.git`，`git init` 本身不暂存文件。
- 当前 `.gitignore` 尚未替换为推荐草案；如果立即 `git add .`，会尝试加入 `pytest-of-lenovo` 的 2,415 个文件及未决定的历史数据库/日志/截图。
- 必须先创建推荐 `.gitignore`（Git-3B），并用 `git check-ignore`、`git add -n` 验证，再执行真正的 `git add`。

因此 `GIT_INIT_READINESS = CONDITIONAL_GO`。

### 8.2 初始化后的验证命令

```powershell
git init
git status --short
git check-ignore -v pytest-of-lenovo .pytest_cache storage/src_research.db storage/src_research.db-shm
git check-ignore -v docs/acceptance/phase5_final/db/phase5_acceptance_final_20261105T061441Z.db
git add -n .
git ls-files --others --exclude-standard
```

预期：

- `pytest-of-lenovo` 下 2,415 个文件不进入 `git add -n` 的暂存候选。
- `storage/src_research.db` 和 sidecar 被忽略。
- 6 个历史验收数据库默认被 `*.db` 忽略；如要保留，需单独 `git add -f`。
- `git add -n .` 只显示约 220 个默认候选；需人工检查其中 REVIEW 项。
- `git ls-files --others --exclude-standard` 不应出现 `pytest-of-lenovo`、`__pycache__`、`.pytest_cache`、`storage/src_research.db*`。
- 不执行 `git commit`、不配置 GitHub、不推送。

### 8.3 必须人工决定的 REVIEW 项

1. 根 `config.yaml` 和 4 个 storage `config.yaml`：TRACK 还是 IGNORE；不得直接输出内容。
2. `storage/acceptance/authorization.pdf`：是否作为授权附件入库；不能按 `*.pdf` 自动忽略。
3. 6 个历史验收数据库：`docs/acceptance` 2 个 + `storage` 4 个；默认被 `*.db` 忽略；如要历史留存，批准后 `git add -f`。
4. 10 个验收/运行时 logs 文件：运行时根可 IGNORE；验收 logs 是否作为审计历史入库。
5. 2 个 `storage/reports/*.html`：可再生产物还是历史报告；决定 track/ignore。
6. 8 个 `docs/acceptance`/`docs/screenshots` PNG 与 2 个 storage 证据 PNG：检查敏感信息后决定是否入库。
7. 7 个 storage 验收小夹具：是否保留以复现验收。
8. `backups/` 5 个 ZIP：保持 IGNORE 还是作为历史备份入库；默认建议 IGNORE。

在这些决定完成前，`GITIGNORE_DESIGN_STATUS = CONDITIONAL_GO`。

## 9. 事实、推断与 UNKNOWN

### CONFIRMED（实际扫描确认）

- 当前 `.gitignore` 存在，221 字节，18 条规则。
- 当前无 `.git`。
- 总文件 2,799 / 119,872,885 字节；`pytest-of-lenovo` 2,415 个 / 104,478,924 字节。
- 当前规则并集忽略 125 个文件 / 9,056,614 字节；推荐草案并集 2,579 个 / 115,608,114 字节。
- 当前有 20 个非 pytest 数据库（`storage` 18 + `docs/acceptance` 2）；总 `.db` 1,772 个（含 pytest 临时 1,752 个）。
- 40 个 sidecar：`storage` 36 + `docs/acceptance` 4。
- `storage/acceptance/authorization.pdf` 44 字节；`docs/acceptance` 2 个 DB 共 499,712 字节；`storage` 4 个验收 DB 共 876,544 字节。
- 当前没有 `.env` 文件；没有 DB 模板/示例数据库。
- 未执行任何 Git、测试、数据库打开或内容读取。

### INFERENCE（基于路径/元数据，不读取内容）

- 20 个数据库是运行时、备份或历史验收产物；没有模板语义。
- 配置、授权 PDF、日志、证据/截图、报告 HTML 可能含敏感信息，需 REVIEW。
- 历史验收数据库和截图具有保留价值，但不适合由宽泛规则自动决定。
- `pytest-of-lenovo` 可安全忽略，因为它是 pytest 临时输出目录。

### UNKNOWN（本轮未验证）

- 上述文件是否实际包含凭据、Token、个人信息、客户数据或真实 SRC 目标信息。
- 历史验收数据库是否必须进入 Git，以及团队是否接受 `git add -f`。
- 未来是否会出现数据库模板、`.env.example` 或新的存储产物。
- 实际 `git init` 后 Git 的路径匹配行为；本轮未初始化 Git，也未运行 `git check-ignore`。

## 10. 本轮实际修改文件清单

- 新增：`docs/GITIGNORE_FINAL_AUDIT.md`。
- 修改：无。
- 删除/移动：无。
- `.gitignore`：**未创建、未修改**。
- Git：**未初始化、未暂存、未提交、未连接远程**。
- 数据库/ Schema：未修改，未打开数据库。
- 测试：未运行。
- Phase 6P-2 文件、历史验收报告、历史 Manifest、E 盘备份：未修改。

## 11. 最终结论

- `GITIGNORE_DESIGN_STATUS = CONDITIONAL_GO`
- `GIT_INIT_READINESS = CONDITIONAL_GO`

规则草案已经足够明确，可以解决当前最大的 `pytest-of-lenovo` 和数据库漏忽略问题；但历史数据库、配置、日志、授权附件、报告 HTML 和截图仍需人工 REVIEW。完成这些决定并实际创建 `.gitignore` 后，才建议进入 Git-3B 的 `git init` 与 dry-run 验证。
