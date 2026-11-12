# Phase 6P-2B-6A：完整 pytest 回归测试

- 日期：2026-11-12（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 测试性质：完整测试执行
- 本步骤未修改任何项目源码、测试、数据库或 Schema
- 未执行 Git add/commit/push

```text
FULL_TEST_EXECUTION = YES
PROJECT_CODE_MODIFIED_BY_THIS_STEP = NO
P2B_6A_TEST_STATUS = PASS
P2B_6B_READINESS = GO
```

---

## 1. 测试前状态

`git status --short`：

```text
 M README.md
 M docs/PHASE6_C2A_SECURITY_DEBT.md
 M reports/__init__.py
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
?? docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
?? docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
?? docs/PHASE6_P2B_5B_REAUDIT.md
?? docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
```

`git diff --check`：

```text
PRE_TEST_DIFF_CHECK = PASS
EXIT_CODE = 0
```

三个 tracked 修改均为已确认的 P2B 文档修订，不是本步骤产生的改动。

---

## 2. 测试环境

```text
PYTHON_VERSION = Python 3.14.4
PYTEST_VERSION = pytest 9.2.0
```

未安装、升级或卸载任何依赖，未修改项目配置或系统 ACL。

测试进程使用已有的专用临时根目录：

```text
D:\挖漏洞\pytest_c1r_tmp
```

这是当前 Windows 会话已记录的 ACL 受限环境下运行完整 pytest 的必要进程级配置；没有写入项目文件，也不是持久性环境修改。

---

## 3. 测试命令

在项目根目录执行：

```powershell
python -m pytest -q
```

测试进程继承了以下临时目录环境：

```text
TEMP=D:\挖漏洞\pytest_c1r_tmp
TMP=D:\挖漏洞\pytest_c1r_tmp
TMPDIR=D:\挖漏洞\pytest_c1r_tmp
PYTEST_DEBUG_TEMPROOT=D:\挖漏洞\pytest_c1r_tmp
```

未使用缩小的测试范围，未只运行新增测试，未跳过已有测试。

---

## 4. 实际结果

```text
COLLECTED = 210
PASSED = 203
FAILED = 0
SKIPPED = 7
ERRORS = 0
EXIT_CODE = 0
ELAPSED_TIME = 51.92s (pytest)
```

pytest 最后一行：

```text
203 passed, 7 skipped in 51.92s
```

`COLLECTED=210` 是本次实际通过的 203 项加跳过的 7 项之和。

### 跳过项

7 个 skip 全部来自 Windows 符号链接权限限制 `[WinError 1314]`：

1. `tests/test_evidence_service.py:184`；
2. `tests/test_report_html.py:577`（reports 根目录 symlink）；
3. `tests/test_report_html.py:529`（内部文件 symlink，多个参数化用例）；
4. `tests/test_report_html.py:529`（断链 symlink，多个参数化用例）；
5. `tests/test_report_html.py:529`（外部文件 symlink）。

这些是环境限制导致的 skip，不是测试断言通过，也不是被静默忽略。

---

## 5. 与历史基线对比

历史参考值：

```text
Phase 6B historical:
COLLECTED = 145
PASSED = 144
SKIPPED = 1
```

当前结果：

```text
COLLECTED = 210
PASSED = 203
SKIPPED = 7
```

历史值仅作参考，不能替代本次真实执行结果。测试数量增加来自后续 UI、报告导出、快照一致性、安全修复和 Windows 路径测试；不能把 145→210 的变化解释为同一测试集的通过率变化。

---

## 6. 测试后范围检查

`git status --short`：

```text
 M README.md
 M docs/PHASE6_C2A_SECURITY_DEBT.md
 M reports/__init__.py
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
?? docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
?? docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
?? docs/PHASE6_P2B_5B_REAUDIT.md
?? docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
```

`git diff --check`：

```text
POST_TEST_DIFF_CHECK = PASS
EXIT_CODE = 0
```

```text
STAGED = 0
UNEXPECTED_TRACKED_CHANGES = NONE
TEST_GENERATED_UNEXPECTED_CHANGES = NONE
```

三个 tracked 文件哈希未变：

```text
README.md                         3013F104E1E826F73ADB0261874664777CCB1B0F421DA36A736F8CE0C024961F
reports/__init__.py               1A0D3D47FFEE9EE3406EE9EC28EF57EF69FB852463F4DB6EF06E3EE0EFF9B7EB
docs/PHASE6_C2A_SECURITY_DEBT.md  DF069E504A72DA6788495D359C3213347A55D2544EC9F0D1CFA7531EFAA92765
```

测试执行产生了正常的 Python/`pytest` 缓存；普通 `git status` 未出现新的 tracked 修改。额外检查 `git status --short --ignored` 时，`.pytest_cache/` 因既有 ACL 权限返回 `Permission denied`；这是已知环境限制，不是本轮修改，也不是测试断言失败。

---

## 7. 最终状态

```text
P2B_6A_TEST_STATUS = PASS
P2B_6B_READINESS = GO
```

本步骤只执行完整 pytest 和范围记录：

- 未修改 README、`reports/__init__.py`、`SECURITY_DEBT`；
- 未修改生产代码或测试；
- 未修改数据库或 Schema；
- 未执行 `git add`、`git commit` 或 `git push`；
- 未进行最终验收；
- 未进入 Phase 6D。
