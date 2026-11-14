# Phase 6 Stage 1B-5B — Step 1.3 当前 audited_dependencies 生成事实

## 1. 调查范围

本步骤只调查：

```text
scanners/pip_audit_scanner.py
```

只回答当前 `audited_dependencies` 如何生成、返回和传递。

本步骤只记录当前事实，不设计新的统计方案，不修改代码，不调查 Service、`skipped_dependencies`、`total_dependencies` 或 Finding 生命周期。

## 2. `audited` 初始化位置

### CONFIRMED

当前 `parse_output()` 中**不存在名为 `audited` 的局部变量**，也没有 `audited = 0`、`audited += 1` 或类似初始化/递增语句。

真实函数签名：

```python
def parse_output(
    self, payload_text: str, target: Path, version: str
) -> tuple[list[Finding], list[str], int]:
```

位置：

```text
scanners/pip_audit_scanner.py:210-212
```

函数内部已有的计数器/集合只有：

```python
findings: list[Finding] = []
warnings: list[str] = []
seen: set[tuple[str, str]] = set()
```

位置：

```text
scanners/pip_audit_scanner.py:220-222
```

`audited` 首次以名称出现是在 `scan()` 接收返回值处：

```python
findings, warnings, audited = self.parse_output(
    result.stdout, target_path, availability.version
)
```

位置：

```text
scanners/pip_audit_scanner.py:194-196
```

因此：

```text
INITIALIZATION_VARIABLE = NONE
INITIAL_VALUE = NOT_APPLICABLE
CURRENT_TYPE_AT_RETURN = int
CURRENT_TYPE_AT_SCAN_LOCAL = int
```

## 3. 当前递增条件

### CONFIRMED

当前代码中没有 `audited` 的递增条件，也没有任何分支执行 `audited += ...`。

`parse_output()` 的返回值是直接表达式：

```python
return findings, warnings, len(dependencies)
```

位置：

```text
scanners/pip_audit_scanner.py:311
```

因此当前事实是：

```text
AUDITED_INCREMENT_STATEMENT = NONE
AUDITED_INCREMENT_BRANCH = NONE
AUDITED_VALUE_EXPRESSION = len(dependencies)
```

也就是说，返回的第三个值由 `dependencies` 列表长度直接决定，不是由循环中的成功处理次数累计。

## 4. 与依赖循环的关系

### CONFIRMED

依赖循环位于：

```text
scanners/pip_audit_scanner.py:224
```

```python
for dependency in dependencies:
```

`audited` 在该循环中没有被初始化、递增或赋值。循环内只处理：

- 非 dict 记录：`continue`；
- `name`、`version`、`skip_reason` 字段读取；
- `vulns` 列表检查与内层 `vuln` 循环；
- `findings` 追加、`warnings` 追加、`seen` 去重集合更新。

循环结束后直接执行：

```python
return findings, warnings, len(dependencies)
```

所以当前关系是：

```text
AUDITED_UPDATED_IN_DEPENDENCY_LOOP = NO
AUDITED_DERIVED_FROM_LOOP_ITERATIONS = NO
AUDITED_DERIVED_FROM_LEN_DEPENDENCIES = YES
```

本步骤只记录该事实，不判断不同记录路径未来应如何统计。

## 5. 当前不会增加 `audited` 的已确认路径

### CONFIRMED

由于不存在递增语句，下面这些当前循环路径都不会“增加 audited”：

1. 非 dict 的 `dependency`：

   ```python
   if not isinstance(dependency, dict):
       continue
   ```

2. `vulns` 不是 list 的 `dependency`：

   ```python
   vulns = dependency.get("vulns")
   if not isinstance(vulns, list):
       continue
   ```

3. `vulns` 为空列表的 `dependency`（内层循环不执行）。

4. `vulns` 中非 dict 的 `vuln`：

   ```python
   if not isinstance(vuln, dict):
       continue
   ```

5. 重复 `dedupe_key` 被跳过的 `vuln`：

   ```python
   if dedupe_key in seen:
       continue
   ```

6. `skip_reason` 非空的 `dependency`：当前代码只追加 warning，然后继续处理 `vulns`；该路径同样没有 `audited` 递增。

必须强调：上述“不增加”是**因为没有递增变量**，不是因为代码显式判断这些路径不计入。当前返回值始终是：

```text
len(dependencies)
```

本步骤不分析 `skip_reason` 的业务语义，也不设计未来的 skipped/total 归类。

## 6. `parse_output()` 返回路径

### CONFIRMED

`parse_output()` 的返回类型：

```python
tuple[list[Finding], list[str], int]
```

实际 return 语句：

```python
return findings, warnings, len(dependencies)
```

位置：

```text
scanners/pip_audit_scanner.py:311
```

返回的三个值依次为：

```text
1. findings: list[Finding]
2. warnings: list[str]
3. audited: int（值为 len(dependencies)）
```

## 7. `scan()` 接收与 metadata 传递路径

### CONFIRMED

`scan()` 接收返回值：

```python
findings, warnings, audited = self.parse_output(
    result.stdout, target_path, availability.version
)
```

位置：

```text
scanners/pip_audit_scanner.py:194-196
```

`scan()` 将 `audited` 写入 `ScanOutput.metadata`：

```python
return ScanOutput(
    findings=tuple(findings),
    warnings=tuple(warnings),
    metadata={
        "returncode": result.returncode,
        "duration_seconds": round(result.duration_seconds, 3),
        "audited_dependencies": audited,
        "vulnerability_service": self.vulnerability_service,
    },
)
```

位置：

```text
scanners/pip_audit_scanner.py:199-208
```

当前真实传递路径：

```text
parse_output()
  |
  +-- return findings, warnings, len(dependencies)
        |
        +-- scan() 局部变量 audited
              |
              +-- ScanOutput.metadata["audited_dependencies"]
```

真实字段名：

```text
audited_dependencies
```

真实承载对象：

```text
ScanOutput.metadata
```

## 8. CONFIRMED

```text
CONFIRMED: parse_output() 没有名为 audited 的局部计数变量。
CONFIRMED: parse_output() 没有 audited 的初始化语句。
CONFIRMED: parse_output() 没有 audited 的递增语句。
CONFIRMED: parse_output() 在 :311 返回 len(dependencies) 作为第三个值。
CONFIRMED: 依赖循环在 :224；循环内不更新 audited。
CONFIRMED: 非 dict、vulns 非 list、空 vulns、非 dict vuln、重复 vuln、skip_reason 非空路径均不执行 audited 递增。
CONFIRMED: scan() 在 :194-196 接收第三个返回值并命名为 audited。
CONFIRMED: scan() 在 :205 将其写入 ScanOutput.metadata["audited_dependencies"]。
CONFIRMED: 该字段当前类型为 int。
```

## 9. UNKNOWN

```text
UNKNOWN: 未运行真实 pip-audit，未观察真实 stdout 中 dependencies 的实际内容。
UNKNOWN: 未验证真实输出是否存在本步骤未列出的 dependency/vuln 形态。
```

这些属于运行时验证范围，不在 Step 1.3 展开。

## 10. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.3 结束时只读复核：

```text
scanners/pip_audit_scanner.py
  BYTES = 12660
  SHA256 = F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA

tests/test_pip_audit_scanner.py
  BYTES = 10952
  SHA256 = B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A
```

结果：

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
SKIPPED_DEPENDENCIES_INVESTIGATED = NO
TOTAL_DEPENDENCIES_INVESTIGATED = NO
SKIP_REASON_SEMANTICS_ANALYZED = NO
SERVICE_INVESTIGATED = NO
FINDING_LIFECYCLE_MODIFIED = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_3_AUDITED_DEPENDENCIES_FACTS.md
```

未修改 Scanner、测试、数据库或 Schema；未执行 Git 写操作。

## 12. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不进入 Step 1.4，不设计修复方案。
