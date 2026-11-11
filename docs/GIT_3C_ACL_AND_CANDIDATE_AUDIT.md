# Git-3C ACL 受限临时目录与首次提交候选审计

- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 任务性质：只读调查；不修复 ACL、不修改 `.gitignore`、不暂存、不提交。
- 前置状态：Git-3B 已初始化 `main` 分支；无提交、无 remote、无真实暂存。

## 0. 结论摘要

| 项目 | 结果 |
|---|---|
| `ACL_INVESTIGATION_STATUS` | **PASS_WITH_LIMITATIONS** |
| `ACL_PATHS_AFFECT_FIRST_COMMIT` | **UNKNOWN** |
| `UNEXPECTED_CANDIDATE_FILES` | **NO** |
| `IMPORTANT_FILES_MISSING` | **UNKNOWN** |
| `REAL_STAGING_PERFORMED` | **NO** |
| `COMMIT_CREATED` | **NO** |
| `FIRST_COMMIT_READINESS` | **CONDITIONAL_GO** |

4 个路径均已定位为项目内目录，均为 ACL 受限的临时目录；当前 Git 无法枚举其内容，且它们均**未被当前 `.gitignore` 覆盖**。没有证据表明它们包含业务文件，但由于无法列举内容，不能声明完全无遗漏。当前 dry-run 的 220 个候选中未发现禁止项。

## 1. 4 个实际 ACL 受限路径

以下是 Git-3B 的 `git add -n .` 实际警告，以及本次重新检查结果。

| # | 绝对路径 | 相对路径 | 类型 | 创建/修改时间 | 警告来源 | 当前访问状态 | `.gitignore` 覆盖 |
|---|---|---|---|---|---|---|---|
| 1 | `D:\挖漏洞\SRC-Research-Assistant\storage\tmpv2ziyrtj` | `storage/tmpv2ziyrtj` | DIRECTORY | 2026-11-05 20:43:51 / 同 | `git add -n .` | 元数据可读；`Get-ChildItem` 被拒绝；子项 UNKNOWN | **NOT_IGNORED** |
| 2 | `D:\挖漏洞\SRC-Research-Assistant\storage\_c1_pytest_tmp\pytest-of-lenovo` | `storage/_c1_pytest_tmp/pytest-of-lenovo` | DIRECTORY | 2026-11-05 20:24:13 / 同 | `git add -n .` | 元数据可读；`Get-ChildItem` 被拒绝；子项 UNKNOWN | **NOT_IGNORED** |
| 3 | `D:\挖漏洞\SRC-Research-Assistant\storage\_c1_pytest_tmp\tmp5kedbboy` | `storage/_c1_pytest_tmp/tmp5kedbboy` | DIRECTORY | 2026-11-05 20:24:13 / 同 | `git add -n .` | 元数据可读；`Get-ChildItem` 被拒绝；子项 UNKNOWN | **NOT_IGNORED** |
| 4 | `D:\挖漏洞\SRC-Research-Assistant\tmpcde5t8kh` | `tmpcde5t8kh` | DIRECTORY | 2026-11-05 20:43:51 / 同 | `git add -n .` 与 `git status --short` | 元数据可读；`Get-ChildItem` 被拒绝；子项 UNKNOWN | **NOT_IGNORED** |

四个路径均在项目根目录内部；没有项目根之外的重解析路径。

### ACL/访问控制事实

- 四个目录的 Owner 均为 `LAPTOP-D1CQ3MQK\lenovo`。
- `icacls` 显示每个目录只有 3 类显式 ACE：
  - `NT AUTHORITY\SYSTEM:(OI)(CI)(F)`
  - `BUILTIN\Administrators:(OI)(CI)(F)`
  - `OWNER RIGHTS:(OI)(CI)(F)`
- 每个目录都有 `Mandatory Label\Low Mandatory Level:(I)(OI)(CI)(NW)`。
- 当前 DSH 低完整性测试进程没有可用的读取/列举访问权；`Get-Item` 能读取目录元数据，但 `Get-ChildItem` 无法枚举子项。
- `storage/_c1_pytest_tmp` 父目录本身有 11 条 ACE，但两个子目录各自只有上述 3 类 ACE。
- 本任务未修改任何 ACL、所有权或目录内容。

### `.gitignore` 覆盖

使用 `git check-ignore -v` 检查：

```text
NOT_IGNORED|storage/tmpv2ziyrtj
NOT_IGNORED|storage/_c1_pytest_tmp
NOT_IGNORED|storage/_c1_pytest_tmp/pytest-of-lenovo
NOT_IGNORED|storage/_c1_pytest_tmp/tmp5kedbboy
NOT_IGNORED|tmpcde5t8kh
```

当前最终 `.gitignore` 没有针对 `storage/tmp*`、`storage/_c1_pytest_tmp` 或根 `tmp*` 的规则；`/pytest-of-*/` 只匹配项目根目录下的该前缀，不匹配 `storage/_c1_pytest_tmp/pytest-of-lenovo`。因此四个受限路径全部**未被正确覆盖**。

## 2. 路径性质判断

| 路径 | 判断 | 证据强度 | 依据 |
|---|---|---|---|
| `storage/_c1_pytest_tmp/pytest-of-lenovo` | `PYTEST_TEMP` | **CONFIRMED** | 父目录名为 `_c1_pytest_tmp`；子目录名精确为 `pytest-of-lenovo`；时间与 Phase 6C-1 测试调查时段一致；Phase 6C-1 报告记录了 `storage/_c1_pytest_tmp` 和 `pytest-of-lenovo` 的临时目录问题。 |
| `storage/_c1_pytest_tmp/tmp5kedbboy` | `PYTEST_TEMP` | **INFERENCE** | 位于同一 `_c1_pytest_tmp` 测试临时父目录；随机 `tmp` 名称符合 pytest/临时目录结构；内容无法枚举，不能确认。 |
| `storage/tmpv2ziyrtj` | `RUNTIME_TEMP` | **INFERENCE** | 位于 `storage`，名称以 `tmp` 开头；创建时间 20:43:51 与 Phase 6C-1/6C-R 临时目录活动时间重合；没有 pytest 专用路径证据。 |
| `tmpcde5t8kh` | `RUNTIME_TEMP` | **INFERENCE** | 项目根下随机 `tmp` 目录；Git-2A 审计曾把它列为空临时目录；本次因 ACL 无法枚举；没有证据表明是业务目录。 |

没有将任何路径标记为 `PROJECT_CONTENT` 或 `SYSTEM_ARTIFACT`：它们都位于项目目录，但名称、父目录和时间均指向测试/运行时临时目录；内容状态为 UNKNOWN。

## 3. ACL 风险判断

- **是否影响当前 Git 首次提交候选项**：当前 Git 无法枚举这些目录，所以它们不会进入 `git add -n .` 候选；当前 220 个候选不受其内容直接影响。`ACL_PATHS_AFFECT_FIRST_COMMIT = UNKNOWN`，因为无法排除受限目录中存在重要文件的可能性。
- **是否可能导致重要文件遗漏**：不能完全排除。没有观察到 `.py`、文档或验收材料路径；但四个目录均不可列举，`IMPORTANT_FILES_MISSING = UNKNOWN`。
- **是否需要未来人工处理**：需要。当前 `.gitignore` 未覆盖这些路径；若未来 ACL 被修复或目录被重建，其中内容可能进入 Git 候选。建议在人工审核时决定是否在下一阶段明确排除；本次**不修改** `.gitignore`，也不修改 ACL。
- 四个目录均属于临时目录类别，不应当作为首次提交的业务内容；当前候选审计未发现禁止项。

## 4. Dry-run 复核结果

执行：`git add -n .`（只读 dry-run，未真实暂存）。

- 退出码：`0`
- `add '...'` 候选：**220**
- 原始输出：224 行（220 个候选 + 4 个 ACL 警告）
- 候选总大小：**4,289,753 字节**
- `git diff --cached --name-only`：0 行
- `HEAD`：不存在
- 4 个 ACL 警告与 Git-3B 一致

当前候选分类：

| 分类 | 文件数 | 字节数 |
|---|---:|---:|
| `SOURCE_CODE` | 83 | 672,866 |
| `TESTS` | 26 | 197,746 |
| `DOCUMENTATION` | 35 | 673,928 |
| `ACCEPTANCE_ARTIFACTS` | 53 | 1,723,735 |
| `CONFIGURATION` | 10 | 3,028 |
| `EVIDENCE` | 7 | 997,972 |
| `PROJECT_METADATA` | 6 | 20,478 |
| `OTHER` | 0 | 0 |
| **合计** | **220** | **4,289,753** |

禁止项统计（全部为 0）：

- `pytest-of-lenovo/`：0
- `__pycache__/`：0
- `.pytest_cache/`：0
- `*.pyc`：0
- `*.db` / `*.db-wal` / `*.db-shm`：0
- `/backups/` / `/storage/backups/`：0
- `storage/logs/*.log` / `*.jsonl`：0
- `/storage/reports/*.html`：0
- `.env`：0

### 应进入候选的重要文件确认

- Python 源码与测试：83 个源码文件、26 个测试文件进入候选。
- `README.md`、`requirements.txt`、`pytest.ini`、根 `config.yaml`：进入候选。
- `docs/` 阶段报告与验收 Markdown/JSON/TXT：进入候选。
- 4 个 storage 验收 `config.yaml`：进入候选。
- 4 个历史验收 `audit.jsonl`：进入候选；根 `storage/logs/audit.jsonl` 被忽略。
- `storage/acceptance/authorization.pdf`：进入候选，未被忽略。
- 14 个 PNG：进入候选，包括验收截图和 Evidence。
- 4 个 `.gitkeep`：进入候选。
- 7 个验收小夹具：进入候选。
- `reports/html_exporter.py`、4 个模板、`reports/__init__.py`：进入候选。

没有发现被 `.gitignore` 错误排除的重要文件；但四个 ACL 受限目录的内容仍是 UNKNOWN。

## 5. 首次提交候选最终结论

```text
ACL_INVESTIGATION_STATUS = PASS_WITH_LIMITATIONS
ACL_PATHS_AFFECT_FIRST_COMMIT = UNKNOWN
UNEXPECTED_CANDIDATE_FILES = NO
IMPORTANT_FILES_MISSING = UNKNOWN
REAL_STAGING_PERFORMED = NO
COMMIT_CREATED = NO
FIRST_COMMIT_READINESS = CONDITIONAL_GO
```

本次未执行真实 `git add`、`git commit`、`git remote add` 或 `git push`；未修改 `.gitignore`、ACL、目录或项目文件。实际修改文件仅为本报告。

## 6. 本报告生成后的复核

- 本报告生成后再次执行 `git add -n .`：候选 **221**（原 220 + 本报告 1），仍只有 4 条 ACL 警告。
- 本报告属于 `DOCUMENTATION` 候选，不是禁止项。
- `git diff --cached` 仍为 0，`HEAD` 仍不存在。
