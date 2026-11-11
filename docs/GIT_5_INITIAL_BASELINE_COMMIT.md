# Git-5 首次基线提交与提交后验证

## 0. 结论摘要

| 项目 | 结果 |
|---|---|
| 提交前分支 | `main` |
| 提交前 commit 数 | `0` |
| 提交前 Index | `222` 个文件 |
| Git-4 报告精确暂存 | 成功 |
| 最终 Index | `223` 个文件，4,314,665 字节 |
| 禁止项 | `0` |
| 重要文件缺失 | `0` |
| Git identity | 已配置，具备提交条件 |
| 首次 commit | 已创建 |
| Commit hash | `5595ef9da71d8a2da7afa886415f24e94b3f9482` |
| Commit 文件数 | `223` |
| Remote | 未配置 |
| Push | 未执行 |
| 最终结论 | `PASS` |

Git initial baseline：**COMPLETED**。

## 1. 提交前状态

只读检查结果：

| 检查项 | 实际结果 |
|---|---|
| 当前分支 | `main` |
| `git status --short` | 223 条：222 条已暂存 `A` + 1 条未跟踪 Git-4 报告 |
| `git diff --cached --name-only` | 222 个文件 |
| `HEAD` | 不存在（退出码 `128`） |
| commit 数 | 0 |
| `git remote -v` | 空 |
| 非预期工作区变更 | 0 |
| 唯一的未跟踪文件 | `docs/GIT_4_STAGING_AUDIT.md` |

```text
PRE_COMMIT_WORKTREE_CLEAN = YES (仅保留预期的 Git-4 报告)
PRE_STAGING_COMMIT_COUNT = 0
REMOTE_CONFIGURED = NO
```

## 2. Git-4 报告精确暂存

仅执行：

```text
git add docs/GIT_4_STAGING_AUDIT.md
```

| 指标 | 结果 |
|---|---:|
| 退出码 | `0` |
| 错误 | 0 |
| 权限错误 | 0 |
| LF/CRLF 规范化警告 | 1 |

```text
GIT_4_REPORT_STAGED = YES
```

没有执行 `git add .` 或 `git add -A`。

## 3. 最终 Index 审计

| 指标 | Git-4 快照 | Git-5 最终 Index | 差异 |
|---|---:|---:|---:|
| 文件数 | 222 | 223 | +1 |
| 总大小 | 4,306,375 字节 | 4,314,665 字节 | +8,290 字节 |

差异完全来自：

- `docs/GIT_4_STAGING_AUDIT.md`：8,290 字节。

全部 223 条 Index 状态均为 `A`，无修改/删除记录。

### 3.1 禁止项

最终 Index 中不存在：

- `pytest-of-lenovo/`、`__pycache__/`、`.pytest_cache/`
- `*.pyc` / `*.pyo`
- `*.db` / `*.db-wal` / `*.db-shm`
- `/backups/`、`/storage/backups/`
- `storage/logs/*.log`、`storage/logs/*.jsonl`
- `/storage/reports/*.html`
- `.env`、`.env.*`
- `storage/tmpv2ziyrtj/`、`storage/_c1_pytest_tmp/`、`tmpcde5t8kh/`

历史验收目录中的 `.log`/`.jsonl`（`storage/phase3_acceptance`、`storage/phase4_acceptance`、`storage/phase5_acceptance`、`storage/acceptance`）按 Git-3B 人工决策保留，不属于 `storage/logs/` 运行时日志。

```text
FINAL_INDEX_PROHIBITED_FILES = NO
FINAL_INDEX_FORBIDDEN_COUNT = 0
```

### 3.2 重要文件

以下文件均在最终 Index 中：

- `.gitignore`
- `app/application.py`
- `tests/test_ui_report.py`
- `README.md`、`requirements.txt`、`pytest.ini`
- 根 `config.yaml`、`storage/acceptance/config.yaml`
- Git-3B/3C/3D 报告
- `docs/GIT_4_STAGING_AUDIT.md`
- 历史验收 Markdown/JSON/TXT 和 Phase 6B 归档
- `storage/acceptance/authorization.pdf`
- `storage/evidence/.gitkeep`
- HTML 报告模板

```text
IMPORTANT_FILES_MISSING = NO
SENSITIVE_DATA_RISK = NO
```

`SENSITIVE_DATA_RISK` 沿用 Git-4 的配置字段名检查：5 个 `config.yaml` 无敏感键名命中，未读取 PDF/Evidence 正文。

## 4. Git Identity

提交前读取了 `user.name` 和 `user.email` 的存在性，仅记录状态，不输出实际姓名或邮箱：

```text
GIT_IDENTITY_STATUS = READY
```

## 5. Commit 结果

在最终 Index 审计、禁止项检查和 identity 检查通过后，执行且仅执行一次：

```text
git commit -m "chore: establish initial project baseline"
```

| 项目 | 结果 |
|---|---|
| 退出码 | `0` |
| Commit hash | `5595ef9da71d8a2da7afa886415f24e94b3f9482` |
| Short hash | `5595ef9` |
| 提交时间 | `2026-11-11T11:54:42+08:00` |
| 提交信息 | `chore: establish initial project baseline` |
| 提交文件数 | `223` |
| 插入行数 | `47,162` |
| 初始提交类型 | root commit |
| `COMMIT_CREATED` | `YES` |
| `COMMIT_AMENDED` | `NO` |

## 6. 提交后验证

| 检查项 | 结果 |
|---|---|
| `HEAD` | 存在 |
| commit 数 | 1 |
| `git log --oneline -1` | `5595ef9 chore: establish initial project baseline` |
| Commit tree 文件数 | 223 |
| Commit 内容禁止项 | 0 |
| 重要文件缺失 | 0 |
| `COMMIT_CONTENT_AUDIT` | `PASS` |
| 当前分支 | `main` |
| remote | 空 |
| `REMOTE_CONFIGURED` | `NO` |
| `PUSH_PERFORMED` | `NO` |

`git show --stat --oneline HEAD` 确认首次提交包含 `.gitignore`、源码、测试、文档、Git-3/Git-4 报告、历史验收材料和授权附件，不包含数据库、日志运行时文件、缓存或备份。

```text
HEAD_EXISTS = YES
COMMIT_COUNT = 1
COMMIT_CONTENT_AUDIT = PASS
```

## 7. 工作区状态

### A. 首次 commit 刚创建后

```text
POST_COMMIT_STATUS_BEFORE_REPORT = EMPTY
WORKTREE_CLEAN_AFTER_COMMIT = YES
```

`git status --short` 为 0 行。

### B. Git-5 报告生成后

```text
POST_REPORT_WORKTREE_STATUS = 1 个未跟踪文件
```

唯一未跟踪文件：

```text
?? docs/GIT_5_INITIAL_BASELINE_COMMIT.md
```

Git-5 报告不要求进入首次 commit；没有为了加入报告而创建第二次 commit，也没有执行 `git add`/`git commit` 第二次。

## 8. 最终状态

```text
GIT_5_STATUS = PASS
INITIAL_BASELINE_COMMIT_CREATED = YES
COMMIT_CONTENT_AUDIT = PASS
WORKTREE_CLEAN_AFTER_COMMIT = YES
REMOTE_CONFIGURED = NO
PUSH_PERFORMED = NO
```

Git initial baseline = **COMPLETED**。

## 9. 实际修改文件清单

提交前 Git-4 的 222 个 Index 文件保持不变；Git-5 仅新增：

- `docs/GIT_5_INITIAL_BASELINE_COMMIT.md`（本报告，未暂存）

Commit 本身新增了 Git-4 报告：

- `docs/GIT_4_STAGING_AUDIT.md`

未修改源码、测试、数据库、Schema、`.gitignore` 或 E 盘备份。未配置 remote、未连接 GitHub、未 push。

## 10. 阶段边界

```text
Git initial baseline = COMPLETED (local only)
GitHub remote = NOT CONFIGURED
Push = NOT PERFORMED
Phase 6P-2 = NOT_STARTED
Phase 6D = NOT_STARTED
```

后续 Git-6 仓库最终验收、GitHub remote 配置或 Phase 6P-2 均需人工审核后另行授权。
