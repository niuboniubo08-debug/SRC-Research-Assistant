# Git-4 首次真实暂存与暂存区最终审计

## 0. 结论摘要

| 项目 | 结果 |
|---|---|
| Git 仓库 | 已初始化，分支 `main` |
| 首次真实暂存 | 已执行一次 `git add .`，退出码 `0` |
| Index 快照 | 222 个文件，4,306,375 字节 |
| 禁止项 | 0 |
| 重要文件缺失 | 0 |
| 敏感凭据字段 | 0 个命中 |
| 大于 5 MiB 的文件 | 0 |
| 真实 commit | 未创建 |
| remote | 未配置 |
| 最终结论 | `PASS`；`FIRST_BASELINE_COMMIT_READINESS = GO` |

本报告只记录本次 Git-4 的暂存审计。报告文件本身是在首次 `git add .` 之后生成的，因此它不在本次 Index 快照中，当前保持未暂存状态；没有再次执行 `git add .`。

## 1. 暂存前状态

| 检查项 | 实际结果 |
|---|---|
| 当前分支 | `main` |
| `git status --short` | 19 条未跟踪目录/文件 |
| `git diff --cached --name-only` | 空 |
| `HEAD` | 不存在（`git rev-parse --verify HEAD` 退出码 `128`） |
| commit 数量 | 0 |
| `git remote -v` | 空 |
| `PRE_STAGING_INDEX_STATUS` | `EMPTY` |
| `PRE_STAGING_COMMIT_COUNT` | `0` |
| `REMOTE_CONFIGURED` | `NO` |

暂存前状态符合 Git-4 的前置条件，未在已有暂存内容上继续添加。

## 2. 真实暂存结果

在项目根目录执行且仅执行一次：

```text
git add .
```

| 指标 | 结果 |
|---|---:|
| 退出码 | `0` |
| ACL 警告 | `0` |
| 权限错误 | `0` |
| LF/CRLF 规范化警告 | `179` |
| 暂存后 Index 文件数 | `222` |

`git add .` 的 179 条输出均为 LF 将被替换为 CRLF 的换行规范化警告，不是 ACL、权限或文件读取失败。没有出现 `unable to access`、`Permission denied` 或 ACL 相关警告。

```text
REAL_STAGING_STATUS = PASS
```

## 3. 暂存区统计

### 3.1 总量

| 指标 | 结果 |
|---|---:|
| 暂存文件数量 | `222` |
| 暂存总大小 | `4,306,375` 字节 |
| `git diff --cached --name-status` 条数 | `222` |
| 非 `A` 状态 | `0` |

所有 222 条 Index 记录均为新增（`A`），没有修改或删除记录。

### 3.2 分类统计

| 分类 | 文件数 |
|---|---:|
| `SOURCE_CODE` | 86 |
| `TESTS` | 26 |
| `DOCUMENTATION` | 41 |
| `ACCEPTANCE_ARTIFACTS` | 46 |
| `CONFIGURATION` | 7 |
| `EVIDENCE` | 1 |
| `PROJECT_METADATA` | 4 |
| `BINARY_ATTACHMENT` | 2 |
| `OTHER` | 9 |
| **合计** | **222** |

`OTHER` 的 9 个文件为历史验收目录中的 fixture、日志和 `pyproject.toml`：

- `storage/phase3_acceptance/logs/app.log`
- `storage/phase3_acceptance/logs/audit.jsonl`
- `storage/phase4_acceptance/logs/app.log`
- `storage/phase4_acceptance/logs/audit.jsonl`
- `storage/phase4_acceptance/pyproject_project/pyproject.toml`
- `storage/phase4_acceptance/requirements_project/requirements.txt`
- `storage/phase4_acceptance/safe_project/requirements.txt`
- `storage/phase5_acceptance/logs/app.log`
- `storage/phase5_acceptance/logs/audit.jsonl`

这些是历史验收材料，不是新生成的运行日志；它们符合 Git-3B 的人工 REVIEW 决策。

### 3.3 按目录

| 目录 | 文件数 |
|---|---:|
| 根目录 | 6 |
| `app/` | 4 |
| `core/` | 14 |
| `database/` | 3 |
| `docs/` | 82 |
| `reports/` | 6 |
| `repositories/` | 4 |
| `scanners/` | 7 |
| `security/` | 3 |
| `services/` | 10 |
| `storage/` | 26 |
| `tests/` | 26 |
| `tools/` | 14 |
| `ui/` | 17 |
| **合计** | **222** |

### 3.4 按文件类型

| 扩展名 | 文件数 |
|---|---:|
| `.py` | 108 |
| `.md` | 57 |
| `.png` | 14 |
| `.json` | 10 |
| `.txt` | 7 |
| `.yaml` | 5 |
| `.html` | 4 |
| `.jsonl` | 4 |
| `.log` | 4 |
| `.gitkeep` | 4 |
| `.pdf` | 1 |
| `.ini` | 1 |
| `.toml` | 1 |
| `.yml` | 1 |
| `.gitignore` | 1 |
| **合计** | **222** |

## 4. 禁止项检查

扫描 Index 路径，未发现以下任何内容：

- `pytest-of-lenovo/`
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc` / `*.pyo`
- `*.db` / `*.db-wal` / `*.db-shm`
- `/backups/` 或 `/storage/backups/`
- `storage/logs/*.log` 或 `storage/logs/*.jsonl`
- `storage/reports/*.html`
- `.env` / `.env.*`
- `storage/tmpv2ziyrtj/`
- `storage/_c1_pytest_tmp/`
- `tmpcde5t8kh/`

结果：

```text
STAGED_PROHIBITED_FILES = NO
FORBIDDEN_PATH_COUNT = 0
```

没有执行 `git reset`，也没有修改 `.gitignore` 来处理暂存结果。

## 5. 重要文件存在性检查

以下代表文件均在 Index 中：

- `app/application.py`
- `tests/test_ui_report.py`
- `README.md`
- `requirements.txt`
- `pytest.ini`
- `.gitignore`
- 根 `config.yaml`
- `storage/acceptance/config.yaml`
- Git-3 系列报告（3B/3C/3D）
- `docs/acceptance/ACCEPTANCE_REPORT.md` 及 Phase 3/4/5 验收报告
- `docs/acceptance/phase5_final/PHASE5_ACCEPTANCE.json`
- `storage/acceptance/authorization.pdf`
- `storage/evidence/.gitkeep`
- `reports/templates/base.html`

结果：

```text
IMPORTANT_STAGED_FILES_MISSING = NO
MISSING_IMPORTANT_FILE_COUNT = 0
```

## 6. 配置与敏感信息检查

已检查 5 个已暂存的配置文件：

- `config.yaml`
- `storage/acceptance/config.yaml`
- `storage/phase3_acceptance/config.yaml`
- `storage/phase4_acceptance/config.yaml`
- `storage/phase5_acceptance/config.yaml`

检查方式为读取字段名，仅匹配 `password`、`passwd`、`token`、`secret`、`credential`、`api_key`、`private_key` 等敏感键名；未输出任何配置值。

结果：

```text
CONFIG_FILES_CHECKED = 5
SENSITIVE_KEY_HITS = 0
ENV_EXAMPLE_STAGED = NO
ENV_TEMPLATE_STAGED = NO
SENSITIVE_DATA_RISK = NO
```

限制：本检查不读取 `authorization.pdf`、PNG、Evidence 正文，也不进行内容级 DLP；这些二进制/证据文件仍属于人工 REVIEW 范围。

## 7. 大文件审计

最大文件如下：

| 大小（字节） | 路径 |
|---:|---|
| 269,443 | `docs/acceptance/phase5_final/phase5_vulnerability_management.png` |
| 269,443 | `docs/acceptance/phase5_vulnerability_management.png` |
| 240,530 | `storage/phase4_acceptance/requirements_project/phase5_evidence_screenshot.png` |
| 240,530 | `docs/acceptance/phase4_dependency_audit.png` |
| 240,530 | `storage/phase5_acceptance/evidence/project_1/1062362eb51642dead2aaeffbdd3bacb_phase5_evidence_screenshot.png` |
| 189,951 | `docs/acceptance/phase3_source_audit.png` |
| 169,531 | `docs/acceptance/phase5_final/phase5_evidence_center.png` |
| 169,531 | `docs/acceptance/phase5_evidence_center.png` |
| 138,191 | `docs/screenshots/phase2_authorization_management.png` |
| 132,773 | `docs/screenshots/phase2_dashboard.png` |

| 指标 | 结果 |
|---|---:|
| 最大文件 | `269,443` 字节 |
| 大于 5 MiB 的文件 | `0` |
| `LARGE_FILE_REVIEW_REQUIRED` | `NO` |

最大文件均为历史验收截图/Evidence 截图，不是数据库、日志、备份 ZIP 或构造出的异常大文件。

## 8. Git 工作区与 Index 状态

首次暂存后的 Index 快照：

```text
INDEX_FILES = 222
INDEX_BYTES = 4,306,375
REAL_STAGING_PERFORMED = YES
```

Git-4 报告生成后：

```text
STAGED_FILES = 222
INDEX_SNAPSHOT_UNCHANGED = YES
REPORT_STAGED = NO
```

报告 `docs/GIT_4_STAGING_AUDIT.md` 是工作区中的新文件，保持未暂存；没有再次执行 `git add .`。

当前状态：

| 检查项 | 结果 |
|---|---|
| 当前分支 | `main` |
| 是否存在 commit | 否 |
| `HEAD` | 不存在 |
| remote | 空 |
| 是否存在已暂存文件 | 是，222 个 |
| 是否存在未暂存变更 | 仅 Git-4 报告为新未跟踪文件 |
| `COMMIT_CREATED` | `NO` |
| `REMOTE_CONFIGURED` | `NO` |

`git diff --cached --name-only` 仍返回 222 个文件；`git diff --cached --name-status` 全部为 `A`。

## 9. 最终状态

```text
GIT_4_STAGING_STATUS = PASS
STAGED_PROHIBITED_FILES = NO
IMPORTANT_STAGED_FILES_MISSING = NO
SENSITIVE_DATA_RISK = NO
LARGE_FILE_REVIEW_REQUIRED = NO
REAL_STAGING_PERFORMED = YES
COMMIT_CREATED = NO
REMOTE_CONFIGURED = NO
FIRST_BASELINE_COMMIT_READINESS = GO
```

## 10. 实际修改文件清单

本轮实际新增/修改：

- `docs/GIT_4_STAGING_AUDIT.md`（本报告，未暂存）

Git 操作实际改变了 Index，但未改变工作区业务文件。没有修改：

- 源码；
- 测试；
- 数据库或 Schema；
- `.gitignore`；
- `.git/config` 的 remote 配置；
- E 盘备份；
- Phase 6P-2 或 Phase 6D 文件。

未执行 `git commit`、`git remote add`、`git push`，也未连接 GitHub。后续首次提交审计需人工审核后再进行。
