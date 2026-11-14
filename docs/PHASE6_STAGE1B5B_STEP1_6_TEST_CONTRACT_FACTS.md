# Phase 6 Stage 1B-5B — Step 1.6 当前 Scanner 测试契约事实

## 1. 调查范围与证据优先级

本步骤只只读核对：

```text
tests/test_pip_audit_scanner.py
```

为理解调用对象，允许只读参考：

```text
scanners/pip_audit_scanner.py
```

证据优先级：

```text
TEST_FILE = PRIMARY_EVIDENCE
SCANNER_SOURCE = SUPPORTING_EVIDENCE
```

本步骤不修改测试、不新增测试、不运行 pytest，也不根据源码行为代替测试断言。

## 2. 当前测试范围

### CONFIRMED

当前测试文件共 **12 个 `test_` 函数**，覆盖以下类别：

| 类别 | 当前测试 |
|---|---|
| Scanner 构造 | `make_scanner()` 间接构造；无独立构造测试 |
| 命令执行/调用 | `_scan_with_dependencies()` monkeypatch `run_command`；执行失败/超时/取消测试 |
| `parse_output()` | 正常解析、空结果、坏 JSON |
| 正常依赖记录 | 多 dependency fixture、空 vulns dependency |
| vulnerability/Finding 解析 | Finding 字段、规则 ID、严重度、修复建议、metadata |
| warning | `skip_reason` warning、异常/不可用原因 |
| 去重 | 重复 PYSEC ID 测试 |
| metadata | 完整/无漏洞/部分跳过/全部跳过 metadata 断言 |
| 异常/边界 | 坏 JSON、工具不可用、执行失败、超时、取消 |

这不是“当前测试全部通过”的声明；本步骤未运行 pytest。

## 3. `audited_dependencies` 测试契约

### CONFIRMED

当前测试**直接断言** `audited` 或 `ScanOutput.metadata["audited_dependencies"]`。

### 3.1 `parse_output()` 直接返回值

`tests/test_pip_audit_scanner.py:71-94`：

```python
findings, warnings, audited = scanner.parse_output(payload, target, "2.10.1")
assert audited == 2
```

fixture 输入位于 `:22-61`：

```text
dependencies:
1. requests / 2.19.0 / 3 个 vuln（其中 2 个重复 ID）
2. safe-package / 1.0.0 / vulns []
3. skipped-package / 0.1 / vulns [] / skip_reason "failed to resolve"
```

该测试直接断言：

```text
audited == 2
```

它直接证明测试契约期望：`requests` 和 `safe-package` 计入 2，`skipped-package` 不计入。

`tests/test_pip_audit_scanner.py:210-217`：

```python
findings, warnings, audited = scanner.parse_output(
    '{"dependencies": []}', tmp_path / "requirements.txt", "2.10.1"
)
assert audited == 0
```

该测试直接断言空依赖列表时 `audited == 0`。

### 3.2 `ScanOutput.metadata` 直接断言

| 测试 | 位置 | 输入摘要 | `audited_dependencies` 断言 |
|---|---|---:|---:|
| `test_pip_audit_scan_metadata_complete_without_vulnerabilities` | `:123-134` | 1 个无漏洞 dependency | `== 1` |
| `test_pip_audit_scan_metadata_complete_with_vulnerabilities` | `:137-154` | 1 个有漏洞 dependency | `== 1` |
| `test_pip_audit_scan_metadata_partial_skip` | `:157-180` | 2 正常 + 1 skip | `== 2` |
| `test_pip_audit_scan_metadata_all_skipped` | `:183-207` | 2 个 skip | `== 0` |

这些断言直接位于 `ScanOutput.metadata["audited_dependencies"]` 上。

### 3.3 当前测试契约与当前源码的静态冲突

当前源码 `parse_output()` 返回 `len(dependencies)` 且 `scan()` metadata 只写入 `audited_dependencies`，没有 `skipped_dependencies` / `total_dependencies`。

因此上述完整/部分跳过/全部跳过测试同时断言的两个 metadata 键，在当前源码中不存在：

```text
CURRENT_TEST_CONTRACT_FOR_AUDITED_DEPENDENCIES = DIRECTLY_ASSERTED
CURRENT_CODE_HAS_SKIPPED_METADATA = NO
CURRENT_CODE_HAS_TOTAL_METADATA = NO
TEST_CONTRACT_VS_CURRENT_CODE = STATIC_CONFLICT
```

本步骤未运行测试，因此不声称这些断言运行时一定失败；这是测试断言与当前源码字段的静态对照事实。

## 4. `skip_reason` 测试契约

### CONFIRMED

fixture 在 `tests/test_pip_audit_scanner.py:52-57` 包含：

```python
{
    "name": "skipped-package",
    "version": "0.1",
    "vulns": [],
    "skip_reason": "failed to resolve",
}
```

另有直接测试输入：

- `:168-174`：partial skip 输入；
- `:188-200`：两个 all-skipped 输入，`skip_reason` 分别为 `"failed to resolve"`、`"index unavailable"`。

### 4.1 直接断言的 warning

`tests/test_pip_audit_scanner.py:92`：

```python
assert "failed to resolve" in " ".join(warnings)
```

partial skip 测试 `:180`：

```python
assert "failed to resolve" in " ".join(output.warnings)
```

all skipped 测试 `:206-207`：

```python
assert "failed to resolve" in " ".join(output.warnings)
assert "index unavailable" in " ".join(output.warnings)
```

### 4.2 skip 记录与 Finding 路径

当前 fixture 中 `skipped-package` 的 `vulns` 是空 list。

因此当前测试：

```text
DIRECTLY_ASSERTED: skip_reason 存在时会出现在 warning 文本中。
NOT_DIRECTLY_ASSERTED: skip_reason 非空且 vulns 非空时是否仍进入 Finding 路径。
NOT_DIRECTLY_ASSERTED: skip_reason 非空时是否应阻止 Finding。
```

没有测试用“非空 skip_reason + 非空 vulns”直接验证 Finding 控制流。

## 5. `skipped_dependencies` 当前测试事实

### CONFIRMED

测试直接断言 `ScanOutput.metadata["skipped_dependencies"]`：

| 测试 | 位置 | 断言值 |
|---|---|---:|
| complete without vulnerabilities | `:133` | `0` |
| complete with vulnerabilities | `:153` | `0` |
| partial skip | `:178` | `1` |
| all skipped | `:204` | `2` |

测试也直接断言 `total_dependencies`：

| 测试 | 位置 | 断言值 |
|---|---|---:|
| complete without vulnerabilities | `:134` | `1` |
| complete with vulnerabilities | `:154` | `1` |
| partial skip | `:179` | `3` |
| all skipped | `:205` | `2` |

当前测试没有定义独立的 `skipped_dependencies` 统计模型；它只是直接期待上述 metadata 键和值。

当前源码没有这两个 metadata 键；这是静态冲突，不是对测试通过/失败的运行结论。

## 6. Finding 控制流测试覆盖矩阵

### CONFIRMED

| 控制流/行为 | 覆盖状态 | 直接证据 |
|---|---|---|
| `vulns` 非 list | `NOT_DIRECTLY_TESTED` | 无该输入测试 |
| 非 dict dependency | `NOT_DIRECTLY_TESTED` | fixture/helper 均为 dict |
| 非 dict vuln | `NOT_DIRECTLY_TESTED` | 无该输入测试 |
| 去重 | `DIRECTLY_TESTED` | `:31-49` 重复 ID；`:79` `len(findings) == 2` |
| Finding 创建 | `DIRECTLY_TESTED` | `:79-94`、`:151`、`:176`、`:202` |
| `findings.append(...)` 最终结果 | `DIRECTLY_TESTED` | 通过 `findings` / `output.findings` 长度与内容断言 |
| 空 vulns 不产生 Finding | `DIRECTLY_TESTED` | `:51` safe package；`:131` 空 findings；`:202` all skipped 空 findings |
| skip_reason + 非空 vulns 仍进入 Finding | `NOT_DIRECTLY_TESTED` | 无此组合 |
| Finding 构造后的额外过滤 | `NOT_DIRECTLY_TESTED` | 无断言该中间路径 |

`findings.append(...)` 本身没有被 monkeypatch 或 spy 直接断言；测试直接断言最终 `findings` / `output.findings` 集合，因此属于最终结果覆盖，不是调用级覆盖。

## 7. 当前 fixture 输入结构事实

### CONFIRMED

主 fixture `payload` 位于 `:22-61`，是一个 JSON 字符串，顶层包含：

```text
dependencies: list
fixes: []
```

`dependencies` 中当前出现的形态：

```text
1. 正常 dependency：name、version、vulns（list，含多个 vuln）
2. 无漏洞 dependency：name、version、vulns []
3. skipped dependency：name、version、vulns []、skip_reason 非空
```

vulnerability 记录中出现的字段：

```text
id
fix_versions
aliases
description
```

`_scan_with_dependencies()` 位于 `:97-120`，将传入的 dependency dict 列表重新包装为：

```json
{"dependencies": [...], "fixes": []}
```

并 monkeypatch：

```text
scanner.is_available
scanner._executable
scanners.pip_audit_scanner.run_command
```

fixture 中没有：

```text
非 dict dependency
vulns 非 list
vuln 非 dict
skip_reason 非空且 vulns 非空
```

## 8. DIRECTLY_ASSERTED

```text
DIRECTLY_ASSERTED:
- parse_output() 的 audited == 2（主 fixture）。
- parse_output() 空 dependencies 的 audited == 0。
- ScanOutput.metadata["audited_dependencies"] == 1/1/2/0（四个 scan 测试）。
- ScanOutput.metadata["skipped_dependencies"] == 0/0/1/2（四个 scan 测试）。
- ScanOutput.metadata["total_dependencies"] == 1/1/3/2（四个 scan 测试）。
- skip_reason 文本出现在 warnings 中（主 fixture、partial、all skipped）。
- 重复 PYSEC ID 被去重，findings 长度为 2。
- Finding 的 title/category/severity/rule_id/recommendation/metadata/scanner 信息。
- 空 dependencies/空 vulns 产生空 findings。
- 坏 JSON 抛出 ScannerParseError。
- 工具不可用/执行失败/超时/取消的异常类型。
- severity 映射的具体结果。
```

## 9. NOT_DIRECTLY_ASSERTED

```text
NOT_DIRECTLY_ASSERTED:
- vulns 非 list 的控制流。
- 非 dict dependency 的控制流。
- 非 dict vuln 的控制流。
- skip_reason 非空且 vulns 非空时是否进入 Finding 路径。
- Finding 构造与 findings.append 之间的调用级行为。
- findings.append 之后是否存在删除/过滤的调用级断言。
- 当前源码是否拥有 skipped_dependencies/total_dependencies metadata 字段（测试期待存在；当前源码静态不存在）。
```

## 10. UNKNOWN

```text
UNKNOWN: 未运行 pytest，未观察上述测试在当前源码下的实际 passed/failed。
UNKNOWN: 未运行真实 pip-audit，未观察真实输出对测试 fixture 的补充边界。
UNKNOWN: 未判断这些测试契约是否与已批准的 RC-01 目标契约完全一致。
```

## 11. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.6 结束时只读复核：

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

## 12. 边界遵守情况

```text
READ_ONLY = YES
TEST_FILE = PRIMARY_EVIDENCE
SCANNER_SOURCE = SUPPORTING_EVIDENCE
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
TEST_DESIGN_PERFORMED = NO
STATISTICS_MODEL_DESIGNED = NO
FINDING_BEHAVIOR_MODIFIED = NO
SERVICE_INVESTIGATED = NO
JSON_FEATURE_DEVELOPMENT = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_6_TEST_CONTRACT_FACTS.md
```

未执行 Git 写操作，未修改测试、Scanner、数据库或 Schema。

## 13. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不进入 Step 1.7，不设计统计模型或生产修改。
