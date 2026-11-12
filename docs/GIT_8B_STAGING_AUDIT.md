# Git-8B：Phase 6P-2B 精确暂存与 Staged Diff 复核

- 日期：2026-11-12（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 步骤性质：精确暂存与暂存区复核
- 本步骤未修改任何项目文件
- 未执行 commit / push

```text
PROJECT_FILES_MODIFIED_BY_THIS_STEP = NONE
GIT_ADD = EXECUTED (EXPLICIT_FILE_LIST)
GIT_COMMIT = NOT_EXECUTED
GIT_PUSH = NOT_EXECUTED

STAGED_FILE_COUNT = 13
STAGED_SCOPE = APPROVED
STAGED_DIFF_CHECK = FAIL
GIT_8B_STATUS = BLOCKED
COMMIT_SCOPE = APPROVED
GIT_8C_READINESS = BLOCKED
```

---

## 1. 暂存前状态

`git status --short`：

```text
 M README.md
 M docs/PHASE6_C2A_SECURITY_DEBT.md
 M reports/__init__.py
?? docs/GIT_8A_PRECOMMIT_AUDIT.md
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
?? docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
?? docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
?? docs/PHASE6_P2B_5B_REAUDIT.md
?? docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
?? docs/PHASE6_P2B_6A_FULL_TEST.md
?? docs/PHASE6_P2B_FINAL_ACCEPTANCE.md
```

```text
PRE_STAGE_STAGED_FILES = 0
PRE_STAGE_DIFF_CHECK = PASS (exit 0)
```

暂存前状态与 Git-8A 审计一致，没有新增未预期项目修改。

---

## 2. 实际暂存命令

使用显式文件列表：

```text
git add -- README.md reports/__init__.py docs/PHASE6_C2A_SECURITY_DEBT.md \
  docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md \
  docs/PHASE6_P2B_2_README_UPDATE.md \
  docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md \
  docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md \
  docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md \
  docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md \
  docs/PHASE6_P2B_5B_REAUDIT.md \
  docs/PHASE6_P2B_6A_FULL_TEST.md \
  docs/PHASE6_P2B_FINAL_ACCEPTANCE.md \
  docs/GIT_8A_PRECOMMIT_AUDIT.md
```

```text
STAGING_MODE = EXPLICIT_FILE_LIST
git add . = NOT_USED
ADD_EXIT_CODE = 0
```

---

## 3. 暂存区结果

`git diff --cached --name-status`：

```text
M	README.md
A	docs/GIT_8A_PRECOMMIT_AUDIT.md
M	docs/PHASE6_C2A_SECURITY_DEBT.md
A	docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
A	docs/PHASE6_P2B_2_README_UPDATE.md
A	docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
A	docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
A	docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
A	docs/PHASE6_P2B_5B_REAUDIT.md
A	docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
A	docs/PHASE6_P2B_6A_FULL_TEST.md
A	docs/PHASE6_P2B_FINAL_ACCEPTANCE.md
M	reports/__init__.py
```

```text
STAGED_FILE_COUNT = 13
UNSTAGED_FILE_COUNT = 0
UNEXPECTED_STAGED_FILES = NONE
```

`git diff --cached --stat`：

```text
13 files changed, 2218 insertions(+), 10 deletions(-)
```

---

## 4. Staged Diff 复核

### 4.1 `README.md`

`git diff --cached -- README.md` 只包含已验收的 P2B 修改：

- 报告能力状态：HTML implemented / PDF cancelled / JSON not approved；
- 移除“HTML/PDF/JSON 报告”未实现项；
- `reports/` 结构注释改为 HTML 报告导出；
- 下一阶段建议移除过时的报告待办；
- Phase 5 历史边界保留并增加当前能力澄清。

没有新增业务代码、配置或数据库修改。

### 4.2 `reports/__init__.py`

只有 docstring 修改：

```python
"""Report export package.

HTML report export is implemented.
PDF report export is cancelled and out of scope.
JSON report export is not implemented and has not been approved.
"""
```

没有 import、函数、类、常量或导出实现。

### 4.3 `docs/PHASE6_C2A_SECURITY_DEBT.md`

只有第 673 行的 PDF/JSON 决策文字修改，没有其他条目变化。

```text
STAGED_SCOPE = APPROVED
UNEXPECTED_STAGED_FILES = NONE
```

---

## 5. Staged Diff Check 结果

执行：

```text
git diff --cached --check
```

退出码：

```text
STAGED_DIFF_CHECK_EXIT = 2
STAGED_DIFF_CHECK = FAIL
```

实际告警为 11 处 Markdown 行尾双空格，分布在 3 个报告文件中：

```text
docs/GIT_8A_PRECOMMIT_AUDIT.md:63,64
docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md:21,110,117,118,206,207,253,254
docs/PHASE6_P2B_2_README_UPDATE.md:142
```

这些行尾空格是 Markdown 硬换行写法，不是代码、JSON、配置或数据库修改；但按 `git diff --cached --check` 的标准，它们仍是 trailing whitespace，因此本步骤不能把 staged diff 质量判定为 PASS。

由于本步骤明确禁止修改任何报告和项目文件，未修复这些行尾空格，也未执行 `git restore`、`git reset` 或重新暂存来掩盖问题。

---

## 6. 报告文件集合复核

暂存区的 10 个报告文件均属于 P2B 证据：

```text
P2B_IMPLEMENTATION_EVIDENCE:
- docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
- docs/PHASE6_P2B_2_README_UPDATE.md
- docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
- docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md

P2B_AUDIT_ACCEPTANCE_EVIDENCE:
- docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
- docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
- docs/PHASE6_P2B_5B_REAUDIT.md
- docs/PHASE6_P2B_6A_FULL_TEST.md
- docs/PHASE6_P2B_FINAL_ACCEPTANCE.md

PRE_COMMIT_EVIDENCE:
- docs/GIT_8A_PRECOMMIT_AUDIT.md
```

未暂存：

```text
OTHER_PHASE_FILES = NONE
DATABASE_FILES = NONE
CACHE_FILES = NONE
TEMP_FILES = NONE
CONFIG_FILES = NONE
GIT_METADATA = NONE
```

---

## 7. Git-8B 报告边界

```text
GIT_8B_REPORT = NOT_STAGED
GIT_8B_REPORT_PATH = docs/GIT_8B_STAGING_AUDIT.md
```

本报告是 Git-8B 新增文件，未加入暂存区；当前 Index 仍严格保持 13 个文件。

---

## 8. 最终状态

```text
GIT_8B_STATUS = BLOCKED
COMMIT_SCOPE = APPROVED
GIT_8C_READINESS = BLOCKED

STAGED_FILE_COUNT = 13
UNEXPECTED_STAGED_FILES = NONE
STAGED_DIFF_CHECK = FAIL
STAGED_DIFF_CHECK_EXIT = 2
GIT_8B_REPORT = NOT_STAGED
GIT_COMMIT = NOT_EXECUTED
GIT_PUSH = NOT_EXECUTED
```

暂存范围正确，但 staged diff 的 11 处 Markdown trailing whitespace 需要人工决定：接受为 Markdown 硬换行，或在后续步骤中统一清理报告格式。本步骤不修复、不 commit、不 push。
