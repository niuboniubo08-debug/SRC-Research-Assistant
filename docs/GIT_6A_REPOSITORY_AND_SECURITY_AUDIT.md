# Git-6A 本地仓库完整性与提交内容安全调查

## 0. 结论摘要

| 检查项 | 结果 |
|---|---|
| 当前分支 | `main` |
| 当前 HEAD | `5595ef9da71d8a2da7afa886415f24e94b3f9482` |
| Commit 数量 | `1` |
| `git fsck --full` | 退出码 `0`，无错误/悬空对象输出 |
| 已提交文件数 | `223` |
| 已提交总大小 | `4,314,665` 字节 |
| 与 Git-5 对比 | 文件数一致 |
| 配置文件秘密检查 | `PASS` |
| 文档/日志秘密检查 | `PASS`（4 个模式命中均为误报） |
| 二进制内容审查 | `NOT_PERFORMED` |
| 本地秘密扫描工具 | `NOT_AVAILABLE` |
| 工作区 | 仅有预期未跟踪报告 |
| Remote | 未配置 |
| Push | 未执行 |
| Git-6B 准备度 | `CONDITIONAL_GO` |

## 1. 当前 HEAD、分支与 Commit 数量

```text
HEAD = 5595ef9da71d8a2da7afa886415f24e94b3f9482
BRANCH = main
COMMIT_COUNT = 1
```

`git log --oneline --decorate --all` 只有一条记录：

```text
5595ef9 (HEAD -> main) chore: establish initial project baseline
```

与 Git-5 报告记录的 commit hash `5595ef9da71d8a2da7afa886415f24e94b3f9482` 一致。

## 2. Git 对象完整性

执行：

```text
git fsck --full
```

| 指标 | 结果 |
|---|---:|
| 退出码 | `0` |
| stdout/stderr 行数 | `0` |
| 完整性错误 | 0 |
| 悬空对象报告 | 0 |

```text
LOCAL_GIT_INTEGRITY = PASS
```

## 3. 已提交文件范围

```text
TREE_FILES = 223
TREE_BYTES = 4,314,665
COMMIT_FILE_COUNT_MATCH = YES
```

Git-5 记录首次提交为 223 个文件；当前 `git ls-tree -r --name-only HEAD` 仍为 223 个文件，数量一致。`git diff --name-only HEAD` 为空，未提交工作区与 HEAD 无 tracked 差异。

### 3.1 按目录

| 目录 | 文件数 |
|---|---:|
| 根目录 | 6 |
| `app/` | 4 |
| `core/` | 14 |
| `database/` | 3 |
| `docs/` | 83 |
| `reports/` | 6 |
| `repositories/` | 4 |
| `scanners/` | 7 |
| `security/` | 3 |
| `services/` | 10 |
| `storage/` | 26 |
| `tests/` | 26 |
| `tools/` | 14 |
| `ui/` | 17 |
| **合计** | **223** |

### 3.2 按扩展名

| 扩展名 | 文件数 |
|---|---:|
| `.py` | 108 |
| `.md` | 58 |
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
| **合计** | **223** |

二进制/附件文件共 15 个：14 个 PNG + 1 个 PDF。没有已提交的 `.db`、`.db-wal`、`.db-shm`、ZIP 或缓存文件。

## 4. 配置文件安全复核

已检查 5 个已提交配置：

- `config.yaml`
- `storage/acceptance/config.yaml`
- `storage/phase3_acceptance/config.yaml`
- `storage/phase4_acceptance/config.yaml`
- `storage/phase5_acceptance/config.yaml`

检查内容包括：

- 字段名中的 `password`、`token`、`secret`、`api_key`、`private_key`、`credential` 等；
- 字符串值中的 AWS/GitHub/OpenAI/Google/Slack token 形态；
- 私钥 PEM 标记；
- Bearer token；
- URL 内嵌用户名/密码；
- JWT 形态；
- 高敏感键名对应非空值。

结果：

```text
CONFIG_FILES_CHECKED = 5
CONFIG_FIELDS_PER_FILE = 17
CONFIG_SECRET_AUDIT = PASS
SENSITIVE_KEY_HITS = 0
VALUE_PATTERN_HITS = 0
```

配置值未在终端或本报告中输出。普通本地路径、端口和非秘密运行参数未判定为凭据。

## 5. 历史文档和日志安全复核

扫描 208 个已提交文本文件，覆盖 `.py`、`.md`、`.json`、`.jsonl`、`.txt`、`.log`、`.yaml`、`.yml`、`.ini`、`.toml`、`.html`、`.gitignore`、`.gitkeep`。

检测项包括 token/密码/私钥/Bearer/URL 凭据、邮箱和手机号模式。

结果：

```text
TEXT_SCAN_FILES = 208
TEXT_HIT_FILES = 4
ACTUAL_CREDENTIAL_FINDINGS = 0
DOCUMENT_SECRET_AUDIT = PASS
```

4 个模式命中均已人工复核为误报：

| 文件 | 模式类别 | 结论 |
|---|---|---|
| `docs/acceptance/phase5_final/PHASE5_FILE_MANIFEST.txt` | 手机号模式 2 处 | SHA/哈希文本片段误匹配 |
| `security/scope_rules.py` | password 赋值模式 1 处 | 代码条件 `parsed.username or parsed.password` |
| `tests/test_bandit_scanner.py` | token/secret 赋值模式 1 处 | 测试变量名 `secret = findings[1]` |
| `tests/test_evidence_service.py` | token/secret 赋值模式 1 处 | 测试路径 `secret.txt` |

没有发现真实凭据；报告中未记录命中的原始值。

## 6. PDF / PNG / Evidence 检查

### 6.1 PDF

```text
PDF_PATH = storage/acceptance/authorization.pdf
PDF_SIZE = 44 bytes
PDF_SHA256 = dc3486e22e7bd9752b18e24222dca04cf49f291a5e298df2389530e3044fb012
PDF_HEADER = LOCAL AC (not %PDF)
PDF_METADATA_FIELDS = none
PDF_TEXT_OPERATORS = none
```

该文件不是有效的 PDF 文档，而是 44 字节本地占位附件；没有 PDF 作者、标题、主题、关键词、Creator、Producer 元数据，也没有文本操作符。没有发现个人身份信息或认证信息。

### 6.2 PNG

已解析 14 个已提交 PNG：

- 全部为 `1440x900`、8-bit、RGB；
- 全部无 PNG `tEXt`/`iTXt`/`zTXt` 文本块；
- 全部无 EXIF；
- 文件大小范围 14,701–269,443 字节。

PNG 的实际视觉内容未进行 OCR/图像内容审查；仅完成了格式、尺寸和元数据检查。

```text
PNG_METADATA_REVIEW = PERFORMED
PNG_VISUAL_CONTENT_REVIEW = NOT_PERFORMED
BINARY_CONTENT_REVIEW = NOT_PERFORMED
```

### 6.3 Evidence 路径

`storage/evidence/` 下已提交的只有 `.gitkeep`；实际 Evidence 截图为历史验收目录中的 PNG。没有在 `storage/evidence/` 下发现新的已提交二进制证据。

## 7. 本地秘密扫描工具

只检查环境，不安装依赖、不联网：

| 工具 | 状态 |
|---|---|
| `gitleaks` | `NOT_INSTALLED` |
| `detect-secrets` | `NOT_INSTALLED` |
| `trufflehog` | `NOT_INSTALLED` |
| `secretlint` | `NOT_INSTALLED` |
| `git-secrets` | `NOT_INSTALLED` |

```text
SECRET_SCANNER_STATUS = NOT_AVAILABLE
```

本报告的配置/文本扫描是本地正则补充检查，不冒充 Gitleaks/detect-secrets 的扫描结论。

## 8. 当前工作区状态

### A. Git-6A 开始前

```text
HEAD_COMMITTED_FILES = 223
UNTRACKED = docs/GIT_5_INITIAL_BASELINE_COMMIT.md
TRACKED_MODIFICATIONS = 0
STAGED_FILES = 0
```

### B. Git-6A 报告生成后

```text
UNTRACKED = docs/GIT_5_INITIAL_BASELINE_COMMIT.md
            docs/GIT_6A_REPOSITORY_AND_SECURITY_AUDIT.md
TRACKED_MODIFICATIONS = 0
STAGED_FILES = 0
```

没有执行 `git add`、`git reset`、`git commit` 或历史修改。Git-5 报告仍是预期未跟踪文件；Git-6A 报告也不进入 Index。

```text
WORKTREE_STATUS = EXPECTED_UNTRACKED_ONLY
REMOTE_CONFIGURED = NO
PUSH_PERFORMED = NO
```

## 9. 未发现的问题

- Git 对象完整性无错误；
- HEAD 与 Git-5 commit hash 一致；
- Commit 文件数 223 与 Git-5 一致；
- 5 个配置文件未发现凭据；
- 208 个文本文件未发现真实凭据；
- 无 DB/WAL/SHM、缓存、运行时日志、备份 ZIP 或 `.env` 被提交；
- 无 tracked 工作区修改；
- 无 remote、无 push；
- 历史验收资料和授权占位附件未发现个人身份信息。

## 10. 无法确认的内容

- 14 个 PNG 的实际视觉/OCR 内容未审查；只能确认格式、尺寸、无文本块和无 EXIF；
- 本机没有 Gitleaks/detect-secrets 等独立秘密扫描器，无法给出其规则级结论；
- `authorization.pdf` 不是有效 PDF，无法进行 PDF 元数据/正文级审查；只能确认其 44 字节占位内容无上述元数据与文本操作符；
- 配置字段名检查不能替代完整内容级 DLP；但本次值模式扫描未发现凭据形态。

这些限制必须在 Git-6B 的放行判断中保留，不能写成 `PASS`。

## 11. Git-6B 条件判断

本地仓库完整、提交哈希与文件数均匹配、配置/文本文档检查通过，这是进入 Git-6B 的基础条件。

但二进制视觉内容未审查，且没有独立秘密扫描器，因此不能给出无条件的 `GO`。

```text
GIT_6B_READINESS = CONDITIONAL_GO
```

条件：

1. 人工确认 14 个 PNG 的视觉内容不含个人/组织敏感信息，或提供本地 OCR/图像审查工具；
2. 接受当前“无独立 secret scanner，仅正则补充扫描”的限制；
3. Git-6B 仍不得配置 remote、不得 push，除非另行授权。

## 12. 最终状态

```text
LOCAL_GIT_INTEGRITY = PASS
COMMIT_HASH_MATCH = YES
COMMIT_FILE_COUNT_MATCH = YES
CONFIG_SECRET_AUDIT = PASS
DOCUMENT_SECRET_AUDIT = PASS
BINARY_CONTENT_REVIEW = NOT_PERFORMED
SECRET_SCANNER_STATUS = NOT_AVAILABLE
WORKTREE_STATUS = EXPECTED_UNTRACKED_ONLY
REMOTE_CONFIGURED = NO
PUSH_PERFORMED = NO
GIT_6B_READINESS = CONDITIONAL_GO
```

## 13. 本轮实际修改文件

本轮只新增：

- `docs/GIT_6A_REPOSITORY_AND_SECURITY_AUDIT.md`

未修改源码、测试、数据库、Schema、`.gitignore`、历史提交、E 盘备份或 Phase 6 文档。

## 14. 阶段边界

```text
Git-6A = COMPLETED
Git-6B = NOT_STARTED
GitHub remote = NOT_CONFIGURED
Push = NOT_PERFORMED
Phase 6P-2 = NOT_STARTED
Phase 6D = NOT_STARTED
PDF report feature = CANCELLED
```

等待人工审核后再决定是否进入 Git-6B。
