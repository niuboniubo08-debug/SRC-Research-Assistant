# Phase 6 Stage 1B-5B — Step 2.2-R2 RC-01 源码实施复核

## 1. 复核范围

本步骤为只读源码复核，目标是确认 Step 2.2 与 Step 2.2-R1 的实际代码符合已批准设计。

复核文件：

```text
scanners/pip_audit_scanner.py
tests/test_pip_audit_scanner.py
```

并静态检索全项目对 `PipAuditScanner.parse_output()` 和 `_parse_with_statistics()` 的调用。

本次未修改任何文件；本报告为唯一新增文件。

## 2. 当前文件与基线

| 文件 | Step 1.1 基线 | 当前 | 结论 |
|---|---|---|---|
| `scanners/pip_audit_scanner.py` | 12,660 B · `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` | 13,391 B · `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` | 预期变更（Step 2.2 + R1） |
| `tests/test_pip_audit_scanner.py` | 10,952 B · `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` | 10,952 B · `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` | 未变 |

Scanner 的字节数从 12,660 增至 13,391，来源是 Step 2.2 新增统计辅助方法以及 R1 的原始 bool 判断修订，不是测试文件变化。

## 3. 公共 `parse_output()` 签名与返回

位置：`scanners/pip_audit_scanner.py:214-220`

```python
    def parse_output(
        self, payload_text: str, target: Path, version: str
    ) -> tuple[list[Finding], list[str], int]:
        findings, warnings, audited, _skipped, _total = (
            self._parse_with_statistics(payload_text, target, version)
        )
        return findings, warnings, audited
```

静态确认：

```text
PUBLIC_SIGNATURE = (self, payload_text: str, target: Path, version: str)
PUBLIC_RETURN_ARITY = 3
PUBLIC_RETURN_TYPES = list[Finding], list[str], int
PUBLIC_API_COMPATIBLE = YES
```

公共方法只委托一次私有方法，没有复制解析逻辑；`_skipped`、`_total` 被显式丢弃，不泄露到旧接口。

## 4. 私有 `_parse_with_statistics()` 五值返回

位置：`scanners/pip_audit_scanner.py:222-332`

```python
    def _parse_with_statistics(
        self, payload_text: str, target: Path, version: str
    ) -> tuple[list[Finding], list[str], int, int, int]:
```

最终返回：

```python
        return findings, warnings, audited, skipped, total
```

静态确认：

```text
PRIVATE_SIGNATURE = (self, payload_text: str, target: Path, version: str)
PRIVATE_RETURN_ARITY = 5
PRIVATE_RETURN_TYPES = list[Finding], list[str], int, int, int
```

除异常路径外，函数末尾存在完整五值返回；没有发现提前返回少值或返回 `None` 的路径。

## 5. `scan()` 调用与 metadata 写入

位置：`scanners/pip_audit_scanner.py:194-212`

```python
        findings, warnings, audited, skipped, total = (
            self._parse_with_statistics(
                result.stdout, target_path, availability.version
            )
        )
        if result.output_truncated:
            warnings.append("pip-audit 输出超过捕获上限，结果可能不完整。")
        return ScanOutput(
            findings=tuple(findings),
            warnings=tuple(warnings),
            metadata={
                "returncode": result.returncode,
                "duration_seconds": round(result.duration_seconds, 3),
                "audited_dependencies": audited,
                "skipped_dependencies": skipped,
                "total_dependencies": total,
                "vulnerability_service": self.vulnerability_service,
            },
        )
```

静态确认：

```text
SCAN_CALLS_PRIVATE_METHOD = YES
FIVE_VALUE_UNPACK = YES
AUDITED_METADATA_WRITTEN = YES
SKIPPED_METADATA_WRITTEN = YES
TOTAL_METADATA_WRITTEN = YES
```

`scan()` 没有调用公共三值方法，因此不会在正式扫描路径丢失统计字段。

## 6. 统计计算

位置：`scanners/pip_audit_scanner.py:235-252`

```python
        audited = 0
        skipped = 0
        total = 0
        dependencies = payload.get("dependencies", [])
        for dependency in dependencies:
            total += 1
            if not isinstance(dependency, dict):
                continue
            name = str(dependency.get("name") or "").strip()
            current_version = str(dependency.get("version") or "").strip()
            skip_reason_raw = dependency.get("skip_reason")
            skip_reason = str(skip_reason_raw or "").strip()
            if bool(skip_reason_raw):
                skipped += 1
            else:
                audited += 1
```

### 6.1 `total`

```text
TOTAL_COUNTS_ALL_DEPENDENCIES = YES
TOTAL_COUNTS_NON_DICT = YES
```

`total += 1` 位于 `isinstance(dependency, dict)` 检查之前，因此所有 `dependencies` 元素都计入，包括空对象、非对象、跳过对象和非法对象。

### 6.2 `skipped` / `audited`

```python
            skip_reason_raw = dependency.get("skip_reason")
            ...
            if bool(skip_reason_raw):
                skipped += 1
            else:
                audited += 1
```

```text
STATS_USE_RAW_BOOL = YES
STATS_USE_DISPLAY_STRING = NO
RAW_BOOL_EXPRESSION = bool(skip_reason_raw)
```

统计不再使用 `str(...).strip()` 结果。原始 `0`、`[]`、`{}`、`False` 均按 false 进入 `audited`；原始非空字符串、非空容器等按 true 进入 `skipped`。

### 6.3 非 dict

```python
            if not isinstance(dependency, dict):
                continue
```

```text
NON_DICT_COUNTS_ONLY_TOTAL = YES
NON_DICT_COUNTS_SKIPPED = NO
NON_DICT_COUNTS_AUDITED = NO
```

## 7. warning 与统计判断分离

位置：`scanners/pip_audit_scanner.py:245-252`

```python
            skip_reason_raw = dependency.get("skip_reason")
            skip_reason = str(skip_reason_raw or "").strip()
            if bool(skip_reason_raw):
                skipped += 1
            else:
                audited += 1
            if skip_reason:
                warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

静态确认：

```text
WARNING_DISPLAY_SEPARATE_FROM_STATS = YES
STATS_VALUE = skip_reason_raw
WARNING_VALUE = skip_reason  # string(raw or "").strip()
WARNING_TRIGGER = bool(skip_reason)
```

warning 文本仍使用原有显示字符串，统计判断只使用原始值。空字符串、`None`、数字 `0`、空列表等会按原始 bool 进入 `audited`；若显示字符串非空，原有 warning 仍会被追加，显示行为未改为由统计结果驱动。

## 8. Finding、vulnerability、dedupe 与后续控制流

`skip_reason` 之后没有新增 `continue`、`return` 或 `if` 拦截：

```python
            vulns = dependency.get("vulns")             # :253
            if not isinstance(vulns, list):              # :254
                continue
            for vuln in vulns:                           # :256
                ...
                dedupe_key = (name.lower(), vuln_id)     # :267
                if dedupe_key in seen:                   # :268
                    continue
                seen.add(dedupe_key)                     # :270
                ...
                findings.append(                         # :315
                    Finding(...)                         # :316-330
                )
```

静态确认：

```text
SKIP_REASON_DOES_NOT_SKIP_VULN_PROCESSING = YES
FINDING_CREATION_UNCHANGED = YES
VULNERABILITY_PARSING_UNCHANGED = YES
DEDUPE_KEY_UNCHANGED = YES
WARNING_TEXT_UNCHANGED = YES
POST_SKIP_CONTROL_FLOW_UNCHANGED = YES
```

这是必要的：`skip_reason` 表示该依赖审计未完成，但 Finding 解析仍按原逻辑执行；新逻辑只修正统计归属与 warning 的统计耦合。

## 9. 重复解析与返回路径检查

### 9.1 重复解析

```text
PUBLIC_WRAPPER_PARSES_ONCE = YES
SCAN_PARSES_ONCE = YES
DUPLICATE_JSON_PARSE = NO
```

- 公共 `parse_output()` 只调用一次 `_parse_with_statistics()`；
- `scan()` 只调用一次私有方法；
- 私有方法内部只执行一次 `json.loads()`；
- 没有发现两个入口各自独立复制解析循环。

### 9.2 五值解包与遗漏返回

```text
FIVE_VALUE_UNPACK_SITES = 1
FIVE_VALUE_UNPACK_LOCATION = scanners/pip_audit_scanner.py:194
FIVE_VALUE_RETURN_LOCATION = scanners/pip_audit_scanner.py:332
MISSING_RETURN_PATH = NO
```

全项目检索 `_parse_with_statistics` 只有：

```text
scanners/pip_audit_scanner.py:195  (scan)
scanners/pip_audit_scanner.py:218  (public wrapper)
```

没有其他调用者，也没有任何位置把五值返回解包成三值或相反。

## 10. 全项目 `parse_output()` 调用兼容性

`PipAuditScanner.parse_output()` 的实际调用者：

| 文件:行 | 调用形式 | 兼容性 |
|---|---|---|
| `tests/test_pip_audit_scanner.py:77` | `findings, warnings, audited = scanner.parse_output(...)` | PASS |
| `tests/test_pip_audit_scanner.py:212` | 三值解包 | PASS |
| `tests/test_pip_audit_scanner.py:223` | 直接调用并期待异常 | PASS |
| `tests/test_pip_audit_scanner.py:225` | 直接调用并期待异常 | PASS |

全项目还检索到 `services/dependency_audit_service.py:325` 使用 `output.metadata["audited_dependencies"]`，并读取 `skipped_dependencies`/`total_dependencies` 的设计目标；本步骤只验证 Scanner 输出字段存在，不评价 Service 后续逻辑。

其他 `parse_output` 定义和调用属于 `BanditScanner`/`SemgrepScanner`，不是 `PipAuditScanner` 的方法，未被本次修改影响。

```text
ALL_PIP_AUDIT_PUBLIC_CALLERS_COMPATIBLE = YES
ALL_PIP_AUDIT_PRIVATE_CALLERS_COMPATIBLE = YES
OTHER_SCANNER_PARSE_OUTPUT_AFFECTED = NO
```

## 11. 运行时验证边界

本次只做静态源码复核：

```text
STATIC_REVIEW = YES
PYTEST_EXECUTED = NO
PIP_AUDIT_EXECUTED = NO
GUI_EXECUTED = NO
DATABASE_OPENED = NO
```

没有运行 `pytest`、`pip-audit`、GUI，也没有执行真实依赖审计。因此本报告不声称运行时行为已经通过，只确认源码结构、返回路径和静态调用关系符合设计。

## 12. 复核结论

```text
STEP_2_2_R2_STATUS = PASS
STATIC_REVIEW_ONLY = YES
PUBLIC_API_COMPATIBILITY = PASS
PRIVATE_FIVE_VALUE_RETURN = PASS
SCAN_METADATA_WRITING = PASS
RAW_BOOL_STATISTICS = PASS
NON_DICT_TOTAL_ONLY = PASS
WARNING_STATS_SEPARATION = PASS
FINDING_DEDUPE_CONTROL_FLOW = PASS
DUPLICATE_PARSING = NO
FIVE_VALUE_UNPACK_ERROR = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
PYTEST_EXECUTED = NO
PIP_AUDIT_EXECUTED = NO
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

未发现需要在本步骤修复的源码缺陷；运行时验证仍待后续获准执行。
