# Git-6B 本地仓库最终验收与二进制人工审查

## 0. 验收范围

本验收仅针对本地 Git 仓库健康状态。

不包含：

- GitHub Remote 验收；
- Push 验收；
- 云端备份验收；
- 历史内容重写或清理。

## 1. 最终状态

```text
GIT_6B_STATUS = PASS_WITH_LIMITATIONS
LOCAL_GIT_INTEGRITY = PASS
INITIAL_BASELINE_COMMIT = PRESERVED
PNG_VISUAL_CONTENT_REVIEW = PASS
BINARY_SENSITIVE_CONTENT = NO
INDEPENDENT_SECRET_SCANNER = NOT_AVAILABLE
REMOTE_CONFIGURED = NO
PUSH_PERFORMED = NO
LOCAL_REPOSITORY_FINAL_READINESS = GO
```

`PASS_WITH_LIMITATIONS` 的唯一遗留限制是独立 Secret Scanner 不可用；该限制不能被写成 `PASS`。

## 2. Git 基线完整性

```text
HEAD = 5595ef9da71d8a2da7afa886415f24e94b3f9482
BRANCH = main
COMMIT_COUNT = 1
COMMITTED_FILE_COUNT = 223
REMOTE_COUNT = 0
```

| 检查 | 结果 |
|---|---|
| HEAD 与 Git-5 | 一致 |
| Commit 数量 | 1 |
| 已提交文件数 | 223 |
| `git fsck --full` | 退出码 0，无错误/悬空对象输出 |
| `git diff --cached` | 空 |
| `git remote -v` | 空 |

首次基线 Commit：

```text
commit 5595ef9da71d8a2da7afa886415f24e94b3f9482
chore: establish initial project baseline
```

## 3. 已提交 PNG 清单

当前 HEAD 中共有 14 个 PNG。逐项列出路径、大小和 SHA-256。

| # | PNG 路径 | 字节 | SHA-256 |
|---:|---|---:|---|
| 1 | `docs/acceptance/entrypoint_runtime.png` | 14,701 | `C9E03FCF2CDAB02C1DCC0CBD4D4EAD88EDBF10CB1384EC123B586F5C41DFF584` |
| 2 | `docs/acceptance/phase3_source_audit.png` | 189,951 | `5E093032392A4978BCDBF2DA5BCFF8E69137D9C7B22F09FDE35F838158D19ABD` |
| 3 | `docs/acceptance/phase4_dependency_audit.png` | 240,530 | `D049B0C128FEE9F2195887C65B3B1B7ACB896F9252142A8561841C0E784E8D64` |
| 4 | `docs/acceptance/phase5_evidence_center.png` | 169,531 | `A529EC942B55F4D766F9E42A9BF0795D298DA6CCEFE8595246E37B57AF1569C8` |
| 5 | `docs/acceptance/phase5_final/phase5_evidence_center.png` | 169,531 | `A529EC942B55F4D766F9E42A9BF0795D298DA6CCEFE8595246E37B57AF1569C8` |
| 6 | `docs/acceptance/phase5_final/phase5_vulnerability_management.png` | 269,443 | `F67B1F64C9E570BF38BAB5C3D243EB94398371BFDB49CDD9E20A3E1A7A15CE3C` |
| 7 | `docs/acceptance/phase5_vulnerability_management.png` | 269,443 | `F67B1F64C9E570BF38BAB5C3D243EB94398371BFDB49CDD9E20A3E1A7A15CE3C` |
| 8 | `docs/acceptance/ui_runtime.png` | 98,181 | `6031E67EC34EF2BEDFCD31C515491925CE2FDE25F96DB2610DC61E515A7EF362` |
| 9 | `docs/screenshots/phase2_authorization_management.png` | 138,191 | `1C61EA849B687AAB4D44CABB5E8275A3F0AB3E9D39AA0B1CE211FA3424E79C4A` |
| 10 | `docs/screenshots/phase2_dashboard.png` | 132,773 | `A95204626F5AB9D7F3561768810982AEBD69039690E091ACC1CEF0380F5E753F` |
| 11 | `docs/screenshots/phase2_project_management.png` | 120,534 | `96B054A916F01263BF4BBD90941F4B46365347A0B6B4A8D2257D369504722B98` |
| 12 | `docs/screenshots/phase2_scope_assets.png` | 125,370 | `CAA1A0F61B65F67E621F70D049818554058D710F30E8A419883EF86FC6BC43B1` |
| 13 | `storage/phase4_acceptance/requirements_project/phase5_evidence_screenshot.png` | 240,530 | `D049B0C128FEE9F2195887C65B3B1B7ACB896F9252142A8561841C0E784E8D64` |
| 14 | `storage/phase5_acceptance/evidence/project_1/1062362eb51642dead2aaeffbdd3bacb_phase5_evidence_screenshot.png` | 240,530 | `D049B0C128FEE9F2195887C65B3B1B7ACB896F9252142A8561841C0E784E8D64` |

`PNG_COMMITTED_COUNT = 14`。

重复内容组：

- `#4` 与 `#5` 完全相同；
- `#6` 与 `#7` 完全相同；
- `#3`、`#13`、`#14` 完全相同。

因此 14 个路径对应 10 个唯一图像内容。所有重复路径均按相同 SHA-256 映射到同一审查结论。

## 4. PNG 人工视觉审查

审查方式：

- 在本地逐张查看；
- 不使用联网服务；
- 不上传图片；
- 不安装 OCR 或新依赖；
- 不修改、压缩、转换或覆盖图片。

审查覆盖 A 凭据类、B 个人身份信息、C 不适合公开共享的信息。

| PNG 路径 | 审查结果 | 风险类别 |
|---|---|---|
| `docs/acceptance/entrypoint_runtime.png` | PASS | 无；字体未渲染，未发现可读凭据/PII |
| `docs/acceptance/phase3_source_audit.png` | PASS | 本地测试路径、漏洞编号；无凭据/PII |
| `docs/acceptance/phase4_dependency_audit.png` | PASS | 依赖名/版本/漏洞编号；无凭据/PII |
| `docs/acceptance/phase5_evidence_center.png` | PASS | 本地验收路径、证据元数据；无凭据/PII |
| `docs/acceptance/phase5_final/phase5_evidence_center.png` | PASS | 与 #4 相同 |
| `docs/acceptance/phase5_final/phase5_vulnerability_management.png` | PASS | 漏洞列表、本地项目名；无凭据/PII |
| `docs/acceptance/phase5_vulnerability_management.png` | PASS | 与 #6 相同 |
| `docs/acceptance/ui_runtime.png` | PASS | 空项目管理界面；无凭据/PII |
| `docs/screenshots/phase2_authorization_management.png` | PASS | 占位项目名、`C:/demo/...` 测试路径；无凭据/PII |
| `docs/screenshots/phase2_dashboard.png` | PASS | 占位项目名、统计数字；无凭据/PII |
| `docs/screenshots/phase2_project_management.png` | PASS | 占位项目名、本地测试路径；无凭据/PII |
| `docs/screenshots/phase2_scope_assets.png` | PASS | 示例域名、文档保留 IP、测试路径；无凭据/PII |
| `storage/phase4_acceptance/requirements_project/phase5_evidence_screenshot.png` | PASS | 与 #3 相同 |
| `storage/phase5_acceptance/evidence/project_1/...png` | PASS | 与 #3 相同 |

```text
PNG_VISUAL_CONTENT_REVIEW = PASS
BINARY_SENSITIVE_CONTENT = NO
```

说明：

- 截图中可见的 `客户 A`、`客户 B`、`内部 Python SDK 审查`、`XSS测试项目`、`安全项目B` 均为测试/占位项目名；
- 可见的 `portal.example.com`、`203.0.113.20` 是示例域名/文档保留地址；
- 可见的本地路径和历史验收路径属于项目内部测试路径，不是凭据或个人身份信息；
- `entrypoint_runtime.png` 的字体未渲染，图内文字显示为方块，未发现可读凭据或 PII；该图的文字内容无法从像素可靠恢复；
- 未发现 Password、Token、API Key、Secret、Access Key、Private Key、Session/Cookie、真实姓名、手机号、个人邮箱、身份证号或家庭住址。

## 5. 授权附件状态

```text
AUTHORIZATION_ATTACHMENT_STATUS = PLACEHOLDER
```

| 指标 | 值 |
|---|---|
| 路径 | `storage/acceptance/authorization.pdf` |
| 大小 | 44 字节 |
| SHA-256 | `DC3486E22E7BD9752B18E24222DCA04CF49F291A5E298DF2389530E3044FB012` |
| 文件头 | `LOCAL AC`（不是 `%PDF`） |
| PDF 元数据 | 无 |
| PDF 文本操作符 | 无 |

该文件仍是首次 Commit 中的本地占位附件，未重新生成、未替换、未修复，也未修改。

## 6. 独立 Secret Scanner 限制

重新检查：

| 工具 | 状态 |
|---|---|
| `gitleaks` | 未安装 |
| `detect-secrets` | 未安装 |
| `trufflehog` | 未安装 |
| `secretlint` | 未安装 |
| `git-secrets` | 未安装 |

```text
INDEPENDENT_SECRET_SCANNER = NOT_AVAILABLE
```

保留 Git-6A 的本地补充检查结论：

```text
LOCAL_CONFIG_VALUE_AUDIT = PASS
LOCAL_TEXT_PATTERN_AUDIT = PASS
```

没有将 `NOT_AVAILABLE` 写成 `PASS`。

## 7. 工作区状态

### A. Git-6B 开始前

```text
PRE_GIT_6B_WORKTREE_STATUS = EXPECTED_UNTRACKED_ONLY
UNTRACKED:
  docs/GIT_5_INITIAL_BASELINE_COMMIT.md
  docs/GIT_6A_REPOSITORY_AND_SECURITY_AUDIT.md
TRACKED_MODIFICATIONS = 0
STAGED_FILES = 0
```

### B. Git-6B 报告生成后

```text
POST_REPORT_WORKTREE_STATUS = EXPECTED_UNTRACKED_ONLY
UNTRACKED:
  docs/GIT_5_INITIAL_BASELINE_COMMIT.md
  docs/GIT_6A_REPOSITORY_AND_SECURITY_AUDIT.md
  docs/GIT_6B_LOCAL_REPOSITORY_FINAL_ACCEPTANCE.md
TRACKED_MODIFICATIONS = 0
STAGED_FILES = 0
```

本阶段没有执行 `git add`、`git commit`、`git reset`、`git rebase`、`git filter-repo`、remote 配置或 push。

## 8. 未发现的问题

- 本地 Git 对象完整性正常；
- 首次基线 Commit 仍为 `5595ef9...`；
- Commit 数量仍为 1；
- 已提交文件数仍为 223；
- 14 个 PNG 均完成实际视觉查看，未发现凭据或 PII；
- 授权附件仍是已知占位文件；
- 无 remote、无 push；
- 未发生 tracked 修改或 index 写入。

## 9. 无法确认/保留的限制

- 独立 Secret Scanner 不可用，无法提供 Gitleaks/detect-secrets 级别规则扫描；
- 本地正则/字段审计不能等同于完整 DLP；
- `entrypoint_runtime.png` 字体未渲染，无法从该图可靠恢复文字；
- 历史截图中的本地测试路径属于内部路径信息，不是凭据/PII，但如需公开仓库仍应由人工决定是否接受；
- `authorization.pdf` 不是有效 PDF，只能按占位附件处理。

## 10. 最终验收结论

```text
GIT_6B_STATUS = PASS_WITH_LIMITATIONS
LOCAL_GIT_INTEGRITY = PASS
INITIAL_BASELINE_COMMIT = PRESERVED
PNG_VISUAL_CONTENT_REVIEW = PASS
BINARY_SENSITIVE_CONTENT = NO
INDEPENDENT_SECRET_SCANNER = NOT_AVAILABLE
REMOTE_CONFIGURED = NO
PUSH_PERFORMED = NO
LOCAL_REPOSITORY_FINAL_READINESS = GO
```

放行依据：

- 本地 Git 完整性通过；
- 首次基线 Commit 保留；
- PNG 视觉审查通过且未发现敏感内容；
- 无 remote、无 push。

保留限制：

- 独立 Secret Scanner 不可用；
- 本地补充检查不能替代独立扫描器；
- PNG 中的本地测试路径属于内部路径信息，是否进入公开历史需人工决定。

## 11. 本轮实际修改文件

本轮只新增：

- `docs/GIT_6B_LOCAL_REPOSITORY_FINAL_ACCEPTANCE.md`

未修改源码、测试、数据库、Schema、`.gitignore`、PNG/PDF、Git 历史、E 盘备份或 Phase 6 文档。

## 12. 阶段边界

```text
Git-6B = COMPLETED
GitHub Remote = NOT_CONFIGURED
Push = NOT_PERFORMED
Phase 6P-2 = NOT_STARTED
Phase 6D = NOT_STARTED
PDF report feature = CANCELLED
```

不得擅自进入 GitHub Remote、Push、Phase 6P-2 或 Phase 6D；等待人工审核决定下一步。
