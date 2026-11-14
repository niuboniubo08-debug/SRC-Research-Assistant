# Phase 6 Stage 1B-5B — Step 1.9 统计字段测试契约的断言顺序与可达性

## 1. 调查目标

本步骤只读调查当前：

```text
tests/test_pip_audit_scanner.py
```

中三个统计字段：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

的直接断言位置、执行顺序、失败后的可达性，以及 Step 1.8 中 `total_dependencies` 没有作为独立失败点出现的原因。

本步骤不修改测试或代码，不重新运行 pytest。

## 2. 证据来源与优先级

```text
PRIMARY_CONTRACT_EVIDENCE = tests/test_pip_audit_scanner.py
RUNTIME_EVIDENCE = docs/PHASE6_STAGE1B5B_STEP1_8_SCANNER_RUNTIME_BASELINE.md
```

本步骤已重新核对当前测试文件的实际断言顺序；不引用旧报告摘要代替源码。

## 3. 相关测试完整清单

当前直接断言 `audited_dependencies`、`skipped_dependencies` 或 `total_dependencies` 的测试为：

1. `test_pip_audit_scan_metadata_complete_without_vulnerabilities`
2. `test_pip_audit_scan_metadata_complete_with_vulnerabilities`
3. `test_pip_audit_scan_metadata_partial_skip`
4. `test_pip_audit_scan_metadata_all_skipped`

另外，`test_pip_audit_json_parsing_dedupes_and_maps_metadata` 与 `test_pip_audit_empty_result` 直接断言 `parse_output()` 返回的 `audited`，但不涉及 `ScanOutput.metadata` 的 `skipped_dependencies` / `total_dependencies`。

## 4. 每个测试的统计断言顺序

### 4.1 `test_pip_audit_scan_metadata_complete_without_vulnerabilities`

位置：`tests/test_pip_audit_scanner.py:123-134`

输入：1 个 dependency，无 `skip_reason`。

实际断言顺序：

```text
ASSERTION_ORDER:
1. output.findings == ()
2. output.metadata["audited_dependencies"] == 1     # :132
3. output.metadata["skipped_dependencies"] == 0     # :133
4. output.metadata["total_dependencies"] == 1       # :134
```

统计字段期望：

```text
audited_dependencies = 1
skipped_dependencies = 0
total_dependencies = 1
```

### 4.2 `test_pip_audit_scan_metadata_complete_with_vulnerabilities`

位置：`tests/test_pip_audit_scanner.py:137-154`

输入：1 个 dependency，无 `skip_reason`。

实际断言顺序：

```text
ASSERTION_ORDER:
1. len(output.findings) == 1
2. output.metadata["audited_dependencies"] == 1     # :152
3. output.metadata["skipped_dependencies"] == 0     # :153
4. output.metadata["total_dependencies"] == 1       # :154
```

统计字段期望：

```text
audited_dependencies = 1
skipped_dependencies = 0
total_dependencies = 1
```

### 4.3 `test_pip_audit_scan_metadata_partial_skip`

位置：`tests/test_pip_audit_scanner.py:157-180`

输入：3 个 dependency，其中 1 个含 `skip_reason`。

实际断言顺序：

```text
ASSERTION_ORDER:
1. len(output.findings) == 1
2. output.metadata["audited_dependencies"] == 2     # :177
3. output.metadata["skipped_dependencies"] == 1     # :178
4. output.metadata["total_dependencies"] == 3       # :179
5. warning 包含 "failed to resolve"                 # :180
```

统计字段期望：

```text
audited_dependencies = 2
skipped_dependencies = 1
total_dependencies = 3
```

### 4.4 `test_pip_audit_scan_metadata_all_skipped`

位置：`tests/test_pip_audit_scanner.py:183-207`

输入：2 个 dependency，均含 `skip_reason`。

实际断言顺序：

```text
ASSERTION_ORDER:
1. output.findings == ()
2. output.metadata["audited_dependencies"] == 0     # :203
3. output.metadata["skipped_dependencies"] == 2     # :204
4. output.metadata["total_dependencies"] == 2       # :205
5. warnings 包含两个 skip_reason 文本              # :206-207
```

统计字段期望：

```text
audited_dependencies = 0
skipped_dependencies = 2
total_dependencies = 2
```

## 5. Step 1.8 失败可达性分析

Step 1.8 实际结果：

```text
5 failed, 7 passed in 1.22s
exit code = 1
```

与统计字段相关的五个失败：

| 测试 | 首个失败位置 | 实际异常 |
|---|---|---|
| `test_pip_audit_json_parsing_dedupes_and_maps_metadata` | `:78` | `AssertionError: assert 3 == 2`（`audited`） |
| `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | `:133` | `KeyError: 'skipped_dependencies'` |
| `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | `:153` | `KeyError: 'skipped_dependencies'` |
| `test_pip_audit_scan_metadata_partial_skip` | `:177` | `AssertionError: assert 3 == 2`（`audited_dependencies`） |
| `test_pip_audit_scan_metadata_all_skipped` | `:203` | `AssertionError: assert 2 == 0`（`audited_dependencies`） |

Python/pytest 当前执行语义下，断言失败或异常会终止当前测试函数；同一函数中位于其后的语句不会执行。

因此：

- complete without vulnerabilities：`:133` 的 `skipped_dependencies` KeyError 阻断 `:134`；
- complete with vulnerabilities：`:153` 的 `skipped_dependencies` KeyError 阻断 `:154`；
- partial skip：`:177` 的 `audited_dependencies` AssertionError 阻断 `:178` 和 `:179`；
- all skipped：`:203` 的 `audited_dependencies` AssertionError 阻断 `:204` 和 `:205`。

## 6. `total_dependencies` 未独立失败的确认原因

### CONFIRMED

Step 1.8 中四个包含 `total_dependencies` 断言的测试，均出现了更早的阻断点：

| 测试 | 更早阻断点 | `total_dependencies` 断言状态 |
|---|---|---|
| complete without vulnerabilities | `:133` KeyError | `NOT_REACHED_IN_STEP_1_8` |
| complete with vulnerabilities | `:153` KeyError | `NOT_REACHED_IN_STEP_1_8` |
| partial skip | `:177` AssertionError | `NOT_REACHED_IN_STEP_1_8` |
| all skipped | `:203` AssertionError | `NOT_REACHED_IN_STEP_1_8` |

因此 Step 1.8 的输出中没有出现 `total_dependencies` 的独立失败：

```text
TOTAL_ASSERTION_NOT_REACHED_IN_THIS_RUN = CONFIRMED
```

该结论同时依赖：

1. 当前测试源码中的断言顺序（第 4 节）；
2. Step 1.8 的实际失败输出（第 5 节）。

### 附带的 skipped 断言可达性

- complete 两个测试：`skipped_dependencies` 断言本身已执行并失败（KeyError），但 `total_dependencies` 未执行；
- partial skip / all skipped：`skipped_dependencies` 断言位于更早的 `audited_dependencies` 失败之后，因此也未执行。

## 7. 三字段当前测试契约关系

### CONFIRMED

四个测试直接断言的数值为：

```text
complete without vulnerabilities: 1 / 0 / 1
complete with vulnerabilities:    1 / 0 / 1
partial skip:                     2 / 1 / 3
all skipped:                      0 / 2 / 2
```

这些数值逐项满足：

```text
audited_dependencies + skipped_dependencies == total_dependencies
```

但当前测试没有显式写出该等式断言，也没有单独测试“三字段统一关系”为一条公式。

因此：

```text
DIRECT_VALUE_RELATIONSHIP_OBSERVED = YES
UNIFIED_RELATIONSHIP_NOT_DIRECTLY_ASSERTED = YES
```

本步骤不把该观察升级为新的统计契约设计。

## 8. 可达性矩阵

| 测试 | 第一个失败/阻断点 | 后续 skipped 断言是否可达 | 后续 total 断言是否可达 |
|---|---|---|---|
| complete without vulnerabilities | `:133` KeyError | 是（该断言本身失败） | 否 |
| complete with vulnerabilities | `:153` KeyError | 是（该断言本身失败） | 否 |
| partial skip | `:177` AssertionError | 否 | 否 |
| all skipped | `:203` AssertionError | 否 | 否 |

## 9. CONFIRMED

```text
CONFIRMED: complete without vulnerabilities 的统计断言顺序为 audited :132 -> skipped :133 -> total :134。
CONFIRMED: complete with vulnerabilities 的统计断言顺序为 audited :152 -> skipped :153 -> total :154。
CONFIRMED: partial skip 的统计断言顺序为 audited :177 -> skipped :178 -> total :179。
CONFIRMED: all skipped 的统计断言顺序为 audited :203 -> skipped :204 -> total :205。
CONFIRMED: Step 1.8 中两个 complete 测试在 :133/:153 因 skipped_dependencies KeyError 停止。
CONFIRMED: Step 1.8 中 partial skip/all skipped 测试在 :177/:203 因 audited_dependencies 断言失败停止。
CONFIRMED: 四个 total_dependencies 断言在本次运行中均未执行。
CONFIRMED: 四个场景的数值均满足 audited + skipped == total。
CONFIRMED: 当前测试没有显式以公式形式断言三字段统一关系。
```

## 10. UNKNOWN

```text
UNKNOWN: 如果完整/partial/all-skipped 场景的 skipped/total 断言开始执行，其实际运行时表现不在 Step 1.8 输出中。
UNKNOWN: 未验证其他未列出的测试输入组合。
```

## 11. NOT_REACHED_IN_STEP_1_8

```text
NOT_REACHED_IN_STEP_1_8:
- complete without vulnerabilities: total_dependencies (:134)
- complete with vulnerabilities: total_dependencies (:154)
- partial skip: skipped_dependencies (:178), total_dependencies (:179)
- all skipped: skipped_dependencies (:204), total_dependencies (:205)
```

`total_dependencies` 的四条断言的 `NOT_REACHED_IN_STEP_1_8` 标签依据第 4 节源码顺序与第 5 节实际失败证据。

## 12. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.9 结束时只读复核：

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
TEST_DESIGN_PERFORMED = NO
FIX_DESIGNED = NO
STATISTICS_IMPLEMENTATION_DESIGNED = NO
FINDING_BEHAVIOR_MODIFIED = NO
JSON_FEATURE_DEVELOPMENT = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_9_STATISTICS_CONTRACT_REACHABILITY.md
```

未重新运行 pytest，未修改 Scanner、测试、数据库或 Schema。

## 14. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不设计修复方案，不进入生产修改。
