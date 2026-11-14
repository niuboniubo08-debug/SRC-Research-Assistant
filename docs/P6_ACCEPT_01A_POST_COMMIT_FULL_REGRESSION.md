# P6-ACCEPT-01A — 当前 Git HEAD 提交后的完整 pytest 回归

## 1. Execution Scope

本步骤验证的是：

```text
CURRENT_HEAD_OVERALL_PROJECT_REGRESSION
```

不是：

```text
RC01_ONLY_COMMIT_REGRESSION
```

用户已人工完成提交，并声明提交时工作区中的 changes 已全部进入当前 HEAD。本步骤只记录并验证：

- 当前 HEAD；
- 当前 HEAD commit 的实际文件范围；
- 当前 HEAD 对应项目的完整 pytest 回归；
- 测试前后的工作树和关键文件完整性。

本步骤不判断 RC-01 是否在业务上最终关闭，也不宣布 Phase 6 完成。

## 2. Git Identity

```text
HEAD_COMMIT = b90d234b1c0755f8f62106eabd7ef4f55e27ac4b
HEAD_ONELINE = b90d234 fix: resolve RC-01 false success vulnerability and finalize TDD tests
BRANCH = main
PRE_TEST_GIT_STATUS = clean (no staged, unstaged or untracked entries)
```

`git status --short` 在测试前没有输出。

### HEAD commit 文件范围

`git show --stat --oneline HEAD`：

```text
b90d234 fix: resolve RC-01 false success vulnerability and finalize TDD tests
 docs/PHASE6_CURRENT_STATUS_AFTER_RC01.md           | 460 +++++++++++++
 docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md        |  92 ++-
 docs/PHASE6_STAGE1B5B_RC01_CROSS_LAYER_DECISION.md | 287 ++++++++
 ...PHASE6_STAGE1B5B_RC01_CROSS_LAYER_TEST_SCOPE.md | 239 ++++++++
 ...SE6_STAGE1B5B_RC01_FINAL_ACCEPTANCE_EVIDENCE.md | 342 ++++++++++
 ...STAGE1B5B_STEP2_1_R1_INTERFACE_COMPATIBILITY.md | 564 ++++++++++++++++
 docs/PHASE6_STAGE1B5B_STEP2_2_IMPLEMENTATION.md    | 317 +++++++++
 docs/PHASE6_STAGE1B5B_STEP2_2_R1_CORRECTION.md     | 288 +++++++++
 docs/PHASE6_STAGE1B5B_STEP2_2_R2_SOURCE_REVIEW.md  | 331 ++++++++++
 docs/PHASE6_STAGE1B5B_STEP2_3_TEST_REPORT.md       | 159 +++++
 ...PHASE6_STAGE1B5B_STEP3_SERVICE_INVESTIGATION.md | 453 +++++++++++++
 docs/PHASE6_STAGE1B5B_STEP4_SERVICE_FIX_DESIGN.md  | 729 +++++++++++++
 scanners/pip_audit_scanner.py                      |  29 +-
 services/dependency_audit_service.py               |  86 ++-
 tests/test_dependency_audit_service.py             | 507 +++++++++++++-
 tests/test_pip_audit_scanner.py                    | 115 +++-
 tests/test_ui_dependency_audit.py                  |  79 ++-
 17 files changed, 5058 insertions(+), 19 deletions(-)
```

事实：

- 当前 HEAD 是一个综合提交，不是 RC-01 专属提交；
- 它同时包含 RC-01 生产/测试修复、Stage 1B 报告，以及此前状态复核报告；
- 测试前工作区干净；
- 没有未提交修改或未跟踪文件参与本步骤验证。

## 3. Pre-Test File Integrity

测试前记录：

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 13,391 | `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| `services/dependency_audit_service.py` | 28,981 | `94451DF78D6CE3E85E8E6DA7A7CB1D6F01138C9AF43FECCF2DA3351D3971A4C5` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |
| `tests/test_dependency_audit_service.py` | 31,910 | `1E22EE3A1AC7DF2C982252A2A206FEB6448545E8505EC8AF5E016A77E872FCCF` |
| `tests/test_ui_dependency_audit.py` | 7,855 | `06A24F9F016FCCBA1F7EA770CDBCDAC365523453884F0A9D12009548832A9FD5` |

## 4. Full pytest Execution

### 命令

```text
python -m pytest -q --basetemp=D:\挖漏洞\pytest_c1r_tmp\bt_p6_accept_01a
```

### 临时目录配置

```text
TEMP = D:\挖漏洞\pytest_c1r_tmp
TMP = D:\挖漏洞\pytest_c1r_tmp
TMPDIR = D:\挖漏洞\pytest_c1r_tmp
PYTEST_DEBUG_TEMPROOT = D:\挖漏洞\pytest_c1r_tmp
BASE_TEMP = D:\挖漏洞\pytest_c1r_tmp\bt_p6_accept_01a
```

### 结果

```text
COLLECTED = 260
PASSED = 253
FAILED = 0
SKIPPED = 7
ERRORS = 0
EXIT_CODE = 0
EXECUTION_TIME = 61.84s
```

说明：

- `COLLECTED=260` 是从 pytest 最终汇总 `253 passed + 7 skipped` 推导出的观察总数；
- `pytest -q` 没有单独打印 `collected N items` 行，因此不是逐字报告字段；
- 完整 pytest 只执行一次：
  `FULL_PYTEST_EXECUTION_COUNT = 1`；
- 没有因结果而修改代码、测试、工作树或重跑。

## 5. Failures

```text
NO_FAILED_TESTS
```

`FAILED = 0`，`ERRORS = 0`。

因此没有可分类的失败项。

## 6. Skips

共 7 项，全部为 Windows 文件/目录符号链接创建失败：

```text
[WinError 1314] 客户端没有所需的特权。
```

| 数量 | 测试位置 | 分类 | 依据 |
|---:|---|---|---|
| 1 | `tests/test_evidence_service.py:184` | `KNOWN_HISTORICAL_SKIP` | 既有 Evidence symlink 测试；Windows 权限限制 |
| 1 | `tests/test_report_html.py:577` | `KNOWN_HISTORICAL_SKIP` | 报告输出根目录 symlink 测试；既有 `WinError 1314` |
| 5 | `tests/test_report_html.py:529` | `KNOWN_HISTORICAL_SKIP` | 叶节点 symlink/断链/外部链接测试；既有 `WinError 1314` |

```text
NEW_SKIP = 0
UNKNOWN_SKIP = 0
```

注意：

- 7 项 skip 是真实未执行的 symlink 动态测试；
- 不能因为 `FAILED=0` 就声称所有动态路径测试都执行并通过；
- 这些 skip 不影响 pytest 退出码，但必须保留为环境限制。

## 7. Post-Test Verification

### Git 状态

```text
POST_TEST_GIT_STATUS = clean (no staged, unstaged or untracked entries)
```

测试后 `git status --short` 没有输出。

### 文件完整性

| 文件 | 测试后大小 | 测试后 SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 13,391 | `5568220F...74879D` |
| `services/dependency_audit_service.py` | 28,981 | `94451DF7...71A4C5` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC8...B175471A` |
| `tests/test_dependency_audit_service.py` | 31,910 | `1E22EE3A...E872FCCF` |
| `tests/test_ui_dependency_audit.py` | 7,855 | `06A24F9F...32A9FD5` |

```text
FILE_INTEGRITY_CHANGED = NO
WORKTREE_CHANGED_BY_TEST = NO
```

### 数据库

```text
storage/src_research.db
size = 4,354,048 bytes
sha256 = 70E452A98ABED7F8ED7AC7C90B38647A4A1440F556006A223F49051A4BF81148
```

测试前后数据库文件哈希一致。

## 8. Evidence Boundary

### 历史定向证据

```text
Level A Scanner:
12 passed
source = prior RC-01 Step 7A
not re-executed in this step

Level B Service:
60 passed
source = prior RC-01 Step 7B
not re-executed in this step
```

这些历史定向结果不是本步骤重新执行的结果。

### 本步骤新增证据

```text
CURRENT_GIT_HEAD
+ HEAD_COMMIT_FILE_STAT
+ FULL_PROJECT_PYTEST
```

本步骤只证明：当前 HEAD `b90d234...` 对应的已提交工作区，通过一次完整 pytest 回归。

它不证明：

- 真实 Scanner → 真实 Service 运行时链路；
- 真实 pip-audit 网络执行；
- 真实 GUI 端到端工作流；
- RC-01 已完成最终人工业务验收；
- Phase 6 已最终封存。

## 9. Final Status

```text
P6_ACCEPT_01A_STATUS = EXECUTED
CURRENT_HEAD_SCOPE = OVERALL_COMMITTED_WORKTREE

GIT_WRITE = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
ACL_MODIFIED = NO
SYSTEM_PERMISSION_MODIFIED = NO

FULL_PYTEST_EXECUTED = YES
FULL_PYTEST_EXECUTION_COUNT = 1

FULL_REGRESSION_STATUS = PASSED
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤只新增本报告，未修改生产代码、测试、数据库、Schema、ACL 或 Git 状态。
