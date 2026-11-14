# Phase 6 Stage 1B-5B — Step 1.4 当前跳过依赖处理事实

## 1. 调查范围

本步骤只调查：

```text
scanners/pip_audit_scanner.py
```

只记录当前代码如何处理依赖记录中的 `skip_reason`，以及相关 warning 和后续控制流。

本步骤不定义 `skipped_dependencies`、不计算统计值、不设计新的 metadata、不修改代码或测试，也不调查 Service 或 Finding 生命周期。

## 2. `skip_reason` 读取位置

### CONFIRMED

真实读取语句位于：

```text
scanners/pip_audit_scanner.py:229
```

```python
skip_reason = str(dependency.get("skip_reason") or "").strip()
```

事实：

```text
真实函数 = PipAuditScanner.parse_output()
读取对象 = dependency
真实字段名 = "skip_reason"
读取方式 = dependency.get("skip_reason")
后处理 = str(... or "").strip()
当前局部变量 = skip_reason
```

该读取发生在依赖记录循环 `:224` 内部。

## 3. 当前条件判断事实

### CONFIRMED

紧随读取后的条件判断位于：

```text
scanners/pip_audit_scanner.py:230
```

```python
if skip_reason:
```

当前真实逻辑是：

1. 先用 `str(... or "").strip()` 得到字符串 `skip_reason`；
2. 直接使用该字符串的真值性作为条件；
3. 条件满足时执行 `:231` 的 warning 追加；
4. 条件不满足时跳过 `:231`，继续执行 `:232` 之后的当前依赖处理。

当前代码**没有**使用：

```python
isinstance(skip_reason, str) and skip_reason.strip() != ""
```

也没有定义“有效 skip_reason”的新规则。本步骤不设计该规则。

### CURRENT_CONTROL_FLOW_FACT

```text
CONDITION = if skip_reason:
TRUE_BRANCH = warnings.append(...)
FALSE_BRANCH = 跳过 warning 追加，继续后续处理
```

### FUTURE_STATISTICAL_INTERPRETATION

本步骤不对“什么算 skipped dependency”作判断，也不将上述条件映射为任何统计字段。

## 4. 当前 warning 生成路径

### CONFIRMED

条件满足后执行：

```text
scanners/pip_audit_scanner.py:231
```

```python
warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

事实：

```text
warning 生成 = YES
warning 集合 = warnings
warning 类型 = list[str]
warning 文本包含 skip_reason = YES
warning 文本包含 name = YES（name 为空时使用“未知依赖”）
```

`warnings` 初始化于：

```text
scanners/pip_audit_scanner.py:221
```

```python
warnings: list[str] = []
```

`warnings` 最终通过 `parse_output()` 的第二个返回值传出：

```text
scanners/pip_audit_scanner.py:311
```

```python
return findings, warnings, len(dependencies)
```

本步骤不修改 warning 文案，也不定义新的 warning 规则。

## 5. `skip_reason` 后的实际控制流

### CONFIRMED

当前代码在 `skip_reason` 非空、warning 追加后：

- **没有** `continue`；
- **没有** `return`；
- **没有** 跳过当前 `dependency` 的后续处理；
- 仍然继续执行 `:232`：

```python
vulns = dependency.get("vulns")
```

- 如果 `vulns` 是 list，仍然进入 `:235` 的内层 `for vuln in vulns`；
- 因而当前代码仍可能进入 Finding 构造与 `findings.append(...)` 路径。

真实控制流：

```text
skip_reason = str(dependency.get("skip_reason") or "").strip()
        |
        +-- if skip_reason:
        |       warnings.append(...)
        |
        +-- vulns = dependency.get("vulns")
                |
                +-- if not isinstance(vulns, list): continue
                |
                +-- for vuln in vulns:
                        ...
                        findings.append(Finding(...))
```

### CURRENT_CONTROL_FLOW_FACT

```text
SKIP_REASON_CONTINUE = NO
SKIP_REASON_RETURN = NO
SKIP_REASON_SKIPS_DEPENDENCY = NO
SKIP_REASON_STILL_READS_VULNS = YES
SKIP_REASON_MAY_REACH_FINDING_PATH = YES
```

### FUTURE_STATISTICAL_INTERPRETATION

本步骤不判断：

- 该路径未来是否应阻止 Finding；
- 该路径未来是否应算 skipped；
- 该路径是否应影响统计字段。

## 6. 当前其他既有 `continue` / 跳过路径

### CONFIRMED

当前依赖处理过程中共有以下既有 `continue`：

1. 非 dict 的 `dependency`：

```text
scanners/pip_audit_scanner.py:225-226
```

```python
if not isinstance(dependency, dict):
    continue
```

2. `vulns` 不是 list：

```text
scanners/pip_audit_scanner.py:233-234
```

```python
vulns = dependency.get("vulns")
if not isinstance(vulns, list):
    continue
```

3. `vulns` 列表中非 dict 的 `vuln`：

```text
scanners/pip_audit_scanner.py:236-237
```

```python
if not isinstance(vuln, dict):
    continue
```

4. 重复的 `(name.lower(), vuln_id)`：

```text
scanners/pip_audit_scanner.py:247-248
```

```python
if dedupe_key in seen:
    continue
```

其中第 4 条位于内层 `vuln` 循环，跳过的是当前 `vuln`，不是当前 `dependency`。

### CURRENT_CONTROL_FLOW_FACT

```text
NON_DICT_DEPENDENCY_CONTINUE = YES
VULNS_NOT_LIST_CONTINUE = YES
NON_DICT_VULN_CONTINUE = YES
DUPLICATE_VULN_CONTINUE = YES
SKIP_REASON_CONTINUE = NO
```

这些 `continue` 是否属于“skipped dependency”的统计语义，本步骤不作判断。

## 7. 尚未赋予 skipped 统计语义的内容

### CONFIRMED

当前 `parse_output()` 中没有：

- 名为 `skipped_dependencies` 的局部变量；
- 名为 `skipped_dependencies` 的返回值；
- 写入 `ScanOutput.metadata["skipped_dependencies"]` 的代码；
- 基于 `skip_reason` 的 skipped 计数；
- 对非 dict 依赖、非 list `vulns`、非 dict `vuln` 或重复 `vuln` 的 skipped 统计。

当前只有：

```text
skip_reason 非空 -> warnings.append(...)
```

以及上述既有 `continue` 控制流。

本步骤不把 warning 或 `continue` 路径认定为 skipped dependency；这些语义尚未在当前代码中定义。

## 8. CONFIRMED

```text
CONFIRMED: skip_reason 在 parse_output() :229 读取。
CONFIRMED: 读取对象为当前循环变量 dependency。
CONFIRMED: 字段名为 "skip_reason"。
CONFIRMED: 读取表达式为 str(dependency.get("skip_reason") or "").strip()。
CONFIRMED: 条件为 if skip_reason:（字符串真值性）。
CONFIRMED: 条件满足时 warnings.append(...)，位置 :231。
CONFIRMED: warning 使用 name 和 skip_reason。
CONFIRMED: warning 写入 warnings 列表，并在 :311 随第二个返回值传出。
CONFIRMED: skip_reason 条件后没有 continue 或 return。
CONFIRMED: skip_reason 条件后仍读取 dependency.get("vulns")。
CONFIRMED: vulns 为 list 时仍可能进入 Finding 构造路径。
CONFIRMED: 当前不存在 skipped_dependencies 变量、返回值或 metadata 字段。
CONFIRMED: 当前有 4 个既有 continue 路径（非 dict dependency、vulns 非 list、非 dict vuln、重复 vuln）。
```

## 9. UNKNOWN

```text
UNKNOWN: 未运行真实 pip-audit，未观察真实数据中 skip_reason 的分布和类型。
UNKNOWN: 未验证当前代码对真实输出中所有 dependency/vuln 形态的运行时行为。
UNKNOWN: 未判断现有 continue 路径或 skip_reason warning 在未来统计契约中的归类。
```

## 10. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.4 结束时只读复核：

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

## 11. 边界遵守情况

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
SKIPPED_DEPENDENCIES_DEFINED = NO
SKIPPED_DEPENDENCIES_CALCULATED = NO
TOTAL_DEPENDENCIES_DEFINED = NO
AUDITED_DEPENDENCIES_MODIFIED = NO
STATISTICS_METADATA_DESIGNED = NO
SERVICE_INVESTIGATED = NO
FINDING_BEHAVIOR_MODIFIED = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_4_SKIPPED_HANDLING_FACTS.md
```

未执行 Git 写操作，未修改 Scanner、测试、数据库或 Schema。

## 12. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不进入 Step 1.5，不定义 skipped/total 统计契约。
