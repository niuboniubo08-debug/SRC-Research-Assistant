# Phase 6 Stage 1B-5B — Step 2.3 RC-01 定向运行时测试报告

## 1. 测试范围

本次只执行指定的 pip-audit Scanner 测试文件：

```text
tests/test_pip_audit_scanner.py
```

目的是验证 Step 2.2 已实施的统计字段修复，以及 Step 2.2-R1 对原始 `bool(skip_reason)` 语义的修正。

未运行全项目测试，未运行真实 `pip-audit`，未启动 GUI，未修改数据库或 Schema。

## 2. 执行环境

```text
Python:      3.14.4
pytest:      9.2.0
工作目录:    D:\挖漏洞\SRC-Research-Assistant
Python:      D:\挖漏洞\.venv\Scripts\python.exe
TEMP/TMP:    D:\挖漏洞\pytest_c1r_tmp
TMPDIR:      D:\挖漏洞\pytest_c1r_tmp
QT_QPA_PLATFORM: offscreen
```

测试使用项目已有的独立 pytest 临时目录，未修改项目源码或测试文件。

## 3. 完整测试命令

```powershell
D:\挖漏洞\.venv\Scripts\python.exe -m pytest tests/test_pip_audit_scanner.py -q
```

该命令等价于用户指定的：

```text
python -m pytest tests/test_pip_audit_scanner.py -q
```

## 4. 真实执行结果

```text
........................................................ [100%]
12 passed in 0.76s
PYTEST_EXIT_CODE=0
```

### 4.1 数量统计

| 指标 | 数量 |
|---|---:|
| 测试文件 | 1 |
| 执行到的测试 | 12 |
| passed | 12 |
| failed | 0 |
| skipped | 0 |
| errors | 0 |

说明：`-q` 输出没有单独打印 `collected N items` 行，但本次结果为 `12 passed`，因此实际执行并通过的是 12 项测试。

### 4.2 耗时

```text
0.76s
```

### 4.3 退出码

```text
0
```

### 4.4 失败测试

```text
NONE
```

没有失败测试，因此没有失败名称或错误堆栈需要列举。

## 5. Scanner 与测试文件哈希

### 5.1 测试前

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 13,391 | `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

### 5.2 测试后

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 13,391 | `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

```text
SCANNER_HASH_UNCHANGED_DURING_TEST = YES
TEST_FILE_HASH_UNCHANGED_DURING_TEST = YES
```

测试执行期间没有修改 Scanner、测试文件或其他生产代码。

## 6. 执行边界

```text
REAL_PIP_AUDIT_EXECUTED = NO
GUI_EXECUTED = NO
DATABASE_OPENED = NO
SCHEMA_MODIFIED = NO
SERVICE_MODIFIED = NO
REPOSITORY_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
GIT_MUTATION = NO
FULL_TEST_SUITE_EXECUTED = NO
```

本步骤只产生：

```text
docs/PHASE6_STAGE1B5B_STEP2_3_TEST_REPORT.md
```

## 7. 结果性质

本次结果来自真实 pytest 执行，不是静态推断，也不是模拟结果。

```text
TEST_EXECUTION = REAL
RESULT_SOURCE = PYTEST_OUTPUT
PYTEST_EXIT_CODE = 0
```

静态源码复核（Step 2.2-R2）的结论为通过；本次运行时结果进一步确认当前 Scanner 测试文件在目标统计场景下全部通过。但本次没有执行 Service 测试、UI 测试或全项目回归，因此不能据此宣布 RC-01 的端到端行为已完成验收。

## 8. 结论

```text
STEP_2_3_STATUS = PASS
TARGETED_TEST_FILE = tests/test_pip_audit_scanner.py
TEST_FILES_EXECUTED = 1
TESTS_PASSED = 12
TESTS_FAILED = 0
TESTS_SKIPPED = 0
ERRORS = 0
EXIT_CODE = 0
DURATION_SECONDS = 0.76
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
REAL_PIP_AUDIT_EXECUTED = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本报告完成后停止，不自动修复、不扩大测试范围、不进入下一步。
