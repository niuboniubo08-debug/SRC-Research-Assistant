# Phase 6 Stage 1B-5B — Step 1.7 当前测试契约与 Scanner 源码静态对照

## 1. 调查范围

本步骤只读对照两个当前文件：

```text
tests/test_pip_audit_scanner.py
scanners/pip_audit_scanner.py
```

只对照三个统计字段：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

不运行 pytest，不修改源码或测试，不设计修复方案。

## 2. 证据方法

测试侧只使用 `tests/test_pip_audit_scanner.py` 中的直接断言；源码侧只使用 `scanners/pip_audit_scanner.py` 中的当前实现。

证据标记：

```text
测试侧：DIRECTLY_ASSERTED / NOT_DIRECTLY_ASSERTED / UNKNOWN
源码侧：IMPLEMENTED / NOT_PRESENT / UNKNOWN
对照侧：MATCH_CONFIRMED / STATIC_MISMATCH_CONFIRMED /
        TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT /
        TEST_CONTRACT_NOT_DIRECTLY_CONFIRMED / UNKNOWN
```

## 3. 三字段逐项测试契约

### 3.1 `audited_dependencies`

#### DIRECTLY_ASSERTED

`parse_output()` 直接返回值：

| 测试 | 位置 | 输入 | 期望 |
|---|---|---:|---:|
| `test_pip_audit_json_parsing_dedupes_and_maps_metadata` | `tests/test_pip_audit_scanner.py:78` | 2 正常 + 1 skip | `audited == 2` |
| `test_pip_audit_empty_result` | `:217` | 0 dependency | `audited == 0` |

`ScanOutput.metadata["audited_dependencies"]`：

| 测试 | 位置 | 输入 | 期望 |
|---|---|---:|---:|
| `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | `:132` | 1 正常 | `1` |
| `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | `:152` | 1 正常 | `1` |
| `test_pip_audit_scan_metadata_partial_skip` | `:177` | 2 正常 + 1 skip | `2` |
| `test_pip_audit_scan_metadata_all_skipped` | `:203` | 2 skip | `0` |

主 fixture 的 skip 记录位于 `:52-57`：

```python
{
    "name": "skipped-package",
    "version": "0.1",
    "vulns": [],
    "skip_reason": "failed to resolve",
}
```

直接断言事实：

```text
MAIN_FIXTURE_DEPENDENCY_COUNT = 3
MAIN_FIXTURE_EXPECTED_AUDITED = 2
PARTIAL_SKIP_EXPECTED_AUDITED = 2
ALL_SKIPPED_EXPECTED_AUDITED = 0
```

### 3.2 `skipped_dependencies`

#### DIRECTLY_ASSERTED

| 测试 | 位置 | 期望 `metadata["skipped_dependencies"]` |
|---|---|---:|
| complete without vulnerabilities | `:133` | `0` |
| complete with vulnerabilities | `:153` | `0` |
| partial skip | `:178` | `1` |
| all skipped | `:204` | `2` |

### 3.3 `total_dependencies`

#### DIRECTLY_ASSERTED

| 测试 | 位置 | 输入 dependency 数量 | 期望 `metadata["total_dependencies"]` |
|---|---|---:|---:|
| complete without vulnerabilities | `:134` | 1 | `1` |
| complete with vulnerabilities | `:154` | 1 | `1` |
| partial skip | `:179` | 3 | `3` |
| all skipped | `:205` | 2 | `2` |

## 4. 三字段逐项 Scanner 静态实现

### 4.1 `audited_dependencies`

#### IMPLEMENTED

`parse_output()` 的返回类型：

```text
scanners/pip_audit_scanner.py:212
tuple[list[Finding], list[str], int]
```

真实 return：

```text
scanners/pip_audit_scanner.py:311
return findings, warnings, len(dependencies)
```

`scan()` 接收：

```text
scanners/pip_audit_scanner.py:194-196
findings, warnings, audited = self.parse_output(...)
```

写入 metadata：

```text
scanners/pip_audit_scanner.py:205
"audited_dependencies": audited,
```

当前值来源：

```text
audited_dependencies = len(dependencies)
```

当前 metadata 键：

```text
"returncode"
"duration_seconds"
"audited_dependencies"
"vulnerability_service"
```

### 4.2 `skipped_dependencies`

#### NOT_PRESENT

当前 `scanners/pip_audit_scanner.py` 中不存在：

```text
skipped_dependencies 局部变量
skipped_dependencies 返回值
metadata["skipped_dependencies"] 键
```

### 4.3 `total_dependencies`

#### NOT_PRESENT

当前 `scanners/pip_audit_scanner.py` 中不存在：

```text
total_dependencies 局部变量
total_dependencies 返回值
metadata["total_dependencies"] 键
```

当前源码只有：

```python
len(dependencies)
```

作为 `parse_output()` 的第三个返回值，并在 `scan()` 中写入 `audited_dependencies`；该表达式没有被写入 `total_dependencies` metadata 字段。

## 5. 当前事实对照矩阵

| 字段 | 当前测试直接断言 | 当前 Scanner 静态实现 | 静态结论 |
|---|---|---|---|
| `audited_dependencies` | 主 fixture 期望 `2`；空输入 `0`；metadata 期望 `1/1/2/0` | 存在；值来自 `len(dependencies)`；metadata 键存在 | `STATIC_MISMATCH_CONFIRMED` |
| `skipped_dependencies` | metadata 期望 `0/0/1/2` | `NOT_PRESENT` | `TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT` |
| `total_dependencies` | metadata 期望 `1/1/3/2` | `NOT_PRESENT`；只有 `len(dependencies)` 作为 `audited` 返回值，没有对应 metadata 键 | `TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT` |

`audited_dependencies` 的差异依据：

```text
主 fixture dependencies 数量 = 3
测试期望 audited = 2
源码 audited_dependencies = len(dependencies) = 3
```

complete 场景中 `1 == 1`；partial/all-skipped 场景中测试期望与 `len(dependencies)` 不一致。因此该字段整体结论为 `STATIC_MISMATCH_CONFIRMED`，不是 `MATCH_CONFIRMED`。

## 6. `audited_dependencies` 专项核对

### 测试端

```text
DIRECTLY_ASSERTED
```

- `:78`：`audited == 2`，fixture 含 1 个 `skip_reason` 依赖；
- `:217`：`audited == 0`；
- `:132`：metadata `1`；
- `:152`：metadata `1`；
- `:177`：metadata `2`（2 正常 + 1 skip）；
- `:203`：metadata `0`（2 个 skip）。

### 源码端

```text
IMPLEMENTED
```

- `parse_output()` 第三个返回值是 `len(dependencies)`；
- `scan()` 将第三个返回值命名为 `audited`；
- metadata 键为 `audited_dependencies`；
- 没有排除 `skip_reason` 记录，也没有单独的计数递增。

### 静态结论

```text
STATIC_MISMATCH_CONFIRMED
```

依据：skip 记录存在时，测试期望排除 skip 的计数，而源码直接返回整个 `dependencies` 列表长度。

## 7. `skipped_dependencies` 专项核对

### 测试端

```text
DIRECTLY_ASSERTED
```

四个 scan 测试直接读取：

```python
output.metadata["skipped_dependencies"]
```

期望值分别为 `0/0/1/2`。

### 源码端

```text
NOT_PRESENT
```

全文没有该变量、返回值或 metadata 键。

### 静态结论

```text
TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT
```

## 8. `total_dependencies` 专项核对

### 测试端

```text
DIRECTLY_ASSERTED
```

四个 scan 测试直接读取：

```python
output.metadata["total_dependencies"]
```

期望值分别为 `1/1/3/2`。

### 源码端

```text
NOT_PRESENT
```

当前源码没有 `total_dependencies` 变量、返回值或 metadata 键。

`len(dependencies)` 只作为 `parse_output()` 的第三个返回值，并被写入 `audited_dependencies`；它没有作为 `total_dependencies` 传入 metadata。

### 静态结论

```text
TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT
```

## 9. 静态差异结论

```text
STATIC_COMPARISON_STATUS = MISMATCH_CONFIRMED

audited_dependencies:
  TEST_CONTRACT = DIRECTLY_ASSERTED
  STATIC_IMPLEMENTATION = IMPLEMENTED
  RESULT = STATIC_MISMATCH_CONFIRMED

skipped_dependencies:
  TEST_CONTRACT = DIRECTLY_ASSERTED
  STATIC_IMPLEMENTATION = NOT_PRESENT
  RESULT = TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT

total_dependencies:
  TEST_CONTRACT = DIRECTLY_ASSERTED
  STATIC_IMPLEMENTATION = NOT_PRESENT
  RESULT = TEST_ASSERTION_PRESENT_IMPLEMENTATION_NOT_PRESENT
```

## 10. pytest 运行结果

```text
PYTEST_RUNTIME_RESULT = NOT_EXECUTED
```

本步骤没有运行 pytest，也没有把静态差异表述为已发生的运行时失败。

## 11. CONFIRMED / UNKNOWN 边界

### CONFIRMED

```text
CONFIRMED: 测试对 audited_dependencies 有 6 处直接断言（2 处 parse_output + 4 处 metadata）。
CONFIRMED: 主 fixture 的 dependencies 数量为 3，其中 1 个含 skip_reason。
CONFIRMED: 测试主 fixture 期望 audited == 2。
CONFIRMED: 源码 parse_output() 第三个返回值为 len(dependencies)。
CONFIRMED: 源码 metadata 写入 audited_dependencies，而不写入 total_dependencies。
CONFIRMED: 测试直接断言 skipped_dependencies 的 0/0/1/2。
CONFIRMED: 测试直接断言 total_dependencies 的 1/1/3/2。
CONFIRMED: 源码没有 skipped_dependencies 或 total_dependencies 变量/返回/metadata 键。
```

### UNKNOWN

```text
UNKNOWN: 未运行 pytest，未观察这些测试在当前源码下的运行时结果。
UNKNOWN: 未运行真实 pip-audit，未观察真实 dependencies 的更多输入形态。
```

## 12. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.7 结束时只读复核：

```text
scanners/pip_audit_scanner.py
  BYTES = 12660
  SHA256 = F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA

tests/test_pip_audit_scanner.py
  BYTES = 10952
  SHA256 = B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A
```

```text
SCANNER_FILE_CHANGED = NO
SCANNER_TEST_FILE_CHANGED = NO
```

## 13. 边界遵守情况

```text
READ_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
FIX_DESIGNED = NO
METADATA_MODIFIED = NO
STATISTICS_FIELDS_ADDED = NO
FINDING_BEHAVIOR_MODIFIED = NO
SERVICE_INVESTIGATED = NO
JSON_FEATURE_DEVELOPMENT = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_7_STATIC_CONTRACT_COMPARISON.md
```

未执行 Git 写操作，未修改 Scanner、测试、数据库或 Schema。

## 14. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不运行 pytest，不设计修复方案，不进入生产代码修改步骤。
