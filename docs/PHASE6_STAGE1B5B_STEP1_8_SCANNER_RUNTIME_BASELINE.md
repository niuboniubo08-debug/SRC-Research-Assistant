# Phase 6 Stage 1B-5B — Step 1.8 Scanner 测试运行时基线

## 1. 执行目标

本步骤只运行当前已有的 Scanner 测试，获取真实 Python/pytest 运行时结果，用于确认 Step 1.7 的静态契约对照在当前环境中的实际结果。

本步骤不修改代码或测试，不自动修复失败，不扩大到全项目测试。

## 2. 执行前 SHA-256 基线确认

Step 1.1 基线：

| 文件 | 期望 SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

执行前实际值：

```text
scanners/pip_audit_scanner.py
  BYTES = 12660
  SHA256 = F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA

tests/test_pip_audit_scanner.py
  BYTES = 10952
  SHA256 = B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A
```

```text
PRE_RUN_SCANNER_FILE_CHANGED = NO
PRE_RUN_SCANNER_TEST_FILE_CHANGED = NO
```

## 3. 实际执行的唯一 pytest 命令

```text
python -m pytest tests/test_pip_audit_scanner.py -q
```

实际使用项目虚拟环境 Python：

```text
D:\挖漏洞\.venv\Scripts\python.exe
```

未运行：

```text
pytest
pytest tests/
全项目测试
```

## 4. pytest 原始结果摘要

```text
FFFFF.......
```

```text
5 failed, 7 passed in 1.22s
PYTEST_EXIT_CODE = 1
```

## 5. 通过/失败/跳过数量

```text
PYTEST_COLLECTED = 12
PYTEST_PASSED = 7
PYTEST_FAILED = 5
PYTEST_SKIPPED = 0
PYTEST_RUNTIME = 1.22s
PYTEST_EXIT_CODE = 1
```

## 6. 每个失败测试的真实运行时证据

### 6.1 `test_pip_audit_json_parsing_dedupes_and_maps_metadata`

真实位置：

```text
tests/test_pip_audit_scanner.py:78
```

真实异常：

```text
AssertionError: assert 3 == 2
```

实际断言：

```python
findings, warnings, audited = scanner.parse_output(payload, target, "2.10.1")
assert audited == 2
```

pytest 显示的实际值：

```text
assert 3 == 2
```

### 6.2 `test_pip_audit_scan_metadata_complete_without_vulnerabilities`

真实位置：

```text
tests/test_pip_audit_scanner.py:133
```

真实异常：

```text
KeyError: 'skipped_dependencies'
```

实际断言：

```python
assert output.metadata["audited_dependencies"] == 1
assert output.metadata["skipped_dependencies"] == 0
```

pytest 显示的实际缺失键：

```text
KeyError: 'skipped_dependencies'
```

### 6.3 `test_pip_audit_scan_metadata_complete_with_vulnerabilities`

真实位置：

```text
tests/test_pip_audit_scanner.py:153
```

真实异常：

```text
KeyError: 'skipped_dependencies'
```

实际断言：

```python
assert output.metadata["audited_dependencies"] == 1
assert output.metadata["skipped_dependencies"] == 0
```

pytest 显示的实际缺失键：

```text
KeyError: 'skipped_dependencies'
```

### 6.4 `test_pip_audit_scan_metadata_partial_skip`

真实位置：

```text
tests/test_pip_audit_scanner.py:177
```

真实异常：

```text
AssertionError: assert 3 == 2
```

实际断言：

```python
assert len(output.findings) == 1
assert output.metadata["audited_dependencies"] == 2
```

pytest 显示的实际值：

```text
assert 3 == 2
```

### 6.5 `test_pip_audit_scan_metadata_all_skipped`

真实位置：

```text
tests/test_pip_audit_scanner.py:203
```

真实异常：

```text
AssertionError: assert 2 == 0
```

实际断言：

```python
assert output.findings == ()
assert output.metadata["audited_dependencies"] == 0
```

pytest 显示的实际值：

```text
assert 2 == 0
```

## 7. Step 1.7 静态事实

仅引用 Step 1.7 已确认的静态对照结论：

```text
STATIC_COMPARISON_STATUS = MISMATCH_CONFIRMED

audited_dependencies:
  STATIC_MISMATCH_CONFIRMED

skipped_dependencies:
  TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT

total_dependencies:
  TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT
```

这些是静态事实，不是本步骤的运行时结论。

## 8. Step 1.8 运行时事实

仅依据本次 pytest 输出：

```text
PYTEST_RUNTIME_RESULT = EXECUTED
PYTEST_EXIT_CODE = 1
PYTEST_COLLECTED = 12
PYTEST_PASSED = 7
PYTEST_FAILED = 5
PYTEST_SKIPPED = 0
```

五个失败测试的真实类型：

```text
1 个 AssertionError（audited 3 != 2）
2 个 KeyError（缺少 skipped_dependencies）
1 个 AssertionError（partial skip audited 3 != 2）
1 个 AssertionError（all skipped audited 2 != 0）
```

本步骤不把静态差异自动写成失败原因；以上只是本次 pytest 的实际输出事实。

## 9. 静态事实与运行时事实的分离

### A. Step 1.7 静态事实

```text
STATIC_COMPARISON_STATUS = MISMATCH_CONFIRMED
```

### B. Step 1.8 运行时事实

```text
PYTEST_RUNTIME_RESULT = EXECUTED
5 failed, 7 passed in 1.22s
exit code = 1
```

本步骤没有写：

```text
STATIC_MISMATCH = therefore pytest failure
```

运行时事实只由本次 pytest 输出决定。

## 10. 运行后 SHA-256 对比

运行后实际值：

```text
scanners/pip_audit_scanner.py
  BYTES = 12660
  SHA256 = F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA

tests/test_pip_audit_scanner.py
  BYTES = 10952
  SHA256 = B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A
```

```text
POST_RUN_SCANNER_FILE_CHANGED = NO
POST_RUN_SCANNER_TEST_FILE_CHANGED = NO
```

运行前后 Scanner 与测试文件哈希一致。

## 11. 禁止事项遵守情况

```text
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
AUTO_FIX = NO
PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NEW_TESTS_ADDED = NO
TESTS_DELETED = NO
FULL_SUITE_RUN = NO
```

本步骤只执行了一次指定的 Scanner 测试命令，并在 pytest 结束后进行只读 SHA-256 复核。

## 12. AUTO_FIX

```text
AUTO_FIX = NO
```

未因失败修改 Scanner、测试或其他代码；未重新运行修复后的测试。

## 13. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤完成后立即停止，不设计修复方案，不进入生产代码修改。

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_8_SCANNER_RUNTIME_BASELINE.md
```
