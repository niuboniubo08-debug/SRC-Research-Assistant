# Phase 6 Stage 1B-5B — Step 2.2-R1 RC-01 统计判断规则修订

## 1. 修订目标

修正 `scanners/pip_audit_scanner.py` 中 `skip_reason` 的统计判断，使统计使用原始值：

```python
bool(dependency.get("skip_reason"))
```

而不是使用：

```python
str(dependency.get("skip_reason") or "").strip()
```

的真实性结果。

本次只修改：

```text
scanners/pip_audit_scanner.py
```

新增报告：

```text
docs/PHASE6_STAGE1B5B_STEP2_2_R1_CORRECTION.md
```

不修改测试、公共三值接口、私有五值接口、Finding、vulnerability、dedupe、warning 触发或 `skip_reason` 后的控制流。

## 2. 修订前后代码

### 2.1 修订前

```python
name = str(dependency.get("name") or "").strip()
current_version = str(dependency.get("version") or "").strip()
skip_reason = str(dependency.get("skip_reason") or "").strip()
if skip_reason:
    skipped += 1
    warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
else:
    audited += 1
```

问题：统计判断使用了字符串化、去空白后的 `skip_reason`，不是原始 JSON 值的真值。

### 2.2 修订后

```python
name = str(dependency.get("name") or "").strip()
current_version = str(dependency.get("version") or "").strip()
skip_reason_raw = dependency.get("skip_reason")
skip_reason = str(skip_reason_raw or "").strip()
if bool(skip_reason_raw):
    skipped += 1
else:
    audited += 1
if skip_reason:
    warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

位置：`scanners/pip_audit_scanner.py:243-252`。

## 3. 修订后的完整统计判断代码

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
    if skip_reason:
        warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

说明：

```text
total       += 1 对所有 dependencies 元素执行
skipped     += 1 仅在 bool(skip_reason_raw) 为真时执行
audited     += 1 仅在 bool(skip_reason_raw) 为假时执行
非 dict     只计入 total
```

## 4. 原始 bool 规则的输入语义

统计判断严格使用原始值：

| `skip_reason` 原始值 | `bool(raw)` | 统计归属 | warning 文本/触发 |
|---|---:|---|---|
| `None` | false | audited | 无文本，不触发 |
| `""` | false | audited | 无文本，不触发 |
| `"   "` | true | skipped | 文本为空，不触发 |
| `0` | false | audited | 文本 `"0"`，触发 |
| `0.0` | false | audited | 文本 `"0.0"`，触发 |
| `False` | false | audited | 文本 `"False"`，触发 |
| `[]` | false | audited | 文本 `"[]"`，触发 |
| `{}` | false | audited | 文本 `"{}"`，触发 |
| `"0"` | true | skipped | 文本 `"0"`，触发 |
| 非空非零字符串 | true | skipped | 文本按原规则触发 |

关键点：

- 空字符串是 false -> audited；
- 纯空白字符串原始值非空，所以是 true -> skipped，但其显示文本去掉空白后为空，因此 warning 不触发；
- 数字 `0` 原始值为 false -> audited；
- 空列表 `[]` 原始值为 false -> audited；
- `"0"` 字符串原始值为 true -> skipped；
- 显示文本与统计归属不再共用同一个真假判断。

## 5. warning 文本处理与统计判断分离

统计：

```python
if bool(skip_reason_raw):
    skipped += 1
else:
    audited += 1
```

warning：

```python
skip_reason = str(skip_reason_raw or "").strip()
if skip_reason:
    warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

两者使用不同值：

```text
STATISTICS_VALUE = skip_reason_raw
WARNING_DISPLAY_VALUE = str(skip_reason_raw or "").strip()
```

warning 的条件、文本格式和 append 位置保持原有行为；本次只把统计判断从显示字符串改为原始值。

## 6. 接口与既有行为未改变

### 6.1 公共接口

```text
PipAuditScanner.parse_output
位置：scanners/pip_audit_scanner.py:214
签名：(self, payload_text: str, target: Path, version: str)
返回：tuple[list[Finding], list[str], int]
```

公共方法仍只返回：

```python
return findings, warnings, audited
```

### 6.2 私有接口

```text
PipAuditScanner._parse_with_statistics
位置：scanners/pip_audit_scanner.py:222
签名：(self, payload_text: str, target: Path, version: str)
返回：tuple[list[Finding], list[str], int, int, int]
```

五值返回仍为：

```python
return findings, warnings, audited, skipped, total
```

### 6.3 `scan()` 与 metadata

`scan()` 仍调用：

```python
self._parse_with_statistics(
    result.stdout, target_path, availability.version
)
```

metadata 仍包含：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

### 6.4 Finding、vulnerability、dedupe 与控制流

`skip_reason` 分支之后没有新增 `continue` 或 `return`，代码仍继续：

```text
vulns = dependency.get("vulns")     # :253
if not isinstance(vulns, list):
    continue
for vuln in vulns:
    ...
    dedupe_key = (name.lower(), vuln_id)  # :267
    if dedupe_key in seen:                # :268
        continue
    seen.add(dedupe_key)                  # :270
    ...
    findings.append(                      # :315
        Finding(...)
    )
```

具体确认：

```text
Finding 创建逻辑             NO_CHANGE
vulnerability 解析           NO_CHANGE
dedupe                       NO_CHANGE
warning 文本与触发            NO_CHANGE
skip_reason 后控制流          NO_CHANGE
异常处理                     NO_CHANGE
```

## 7. SHA-256 与文件修改

| 文件 | 修订前 | 修订后 |
|---|---|---|
| `scanners/pip_audit_scanner.py` | 13,307 bytes / `AC032FE36B0E262928BC61E065D570E39B7B3644D255A4D3478A67AC5CCAF43A` | **13,391 bytes** / `5568220FFBB2485D92E42177C4A9320DBAF9F45AF107AE4FC938C4C29074879D` |
| `tests/test_pip_audit_scanner.py` | 10,952 bytes / `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` | **10,952 bytes / 未变** / `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

```text
SCANNER_FILE_CHANGED = YES
SCANNER_TEST_FILE_CHANGED = NO
```

测试文件本步骤未编辑；其 SHA-256 与 Step 1.1 基线一致。工作区中既有的 `M` 状态不是本步骤产生的。

## 8. 验证与禁止事项

已执行：

```text
Python AST parse: AST_OK=1
```

仅做语法解析，不等同于运行时测试。

未执行：

```text
pytest                  NO
pip-audit               NO
GUI                     NO
数据库 / Schema 操作      NO
Git add / commit / push  NO
```

```text
PRODUCTION_CODE_MODIFIED = YES (only scanners/pip_audit_scanner.py)
TEST_CODE_MODIFIED = NO
SERVICE_MODIFIED = NO
GUI_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
JSON_FEATURE_DEVELOPMENT = NO
JSON_CODE_CLEANUP = NO
JSON_FILE_DELETION = NO
GIT_MUTATION = NO
STAGED_COUNT = 0
```

## 9. 停止条件

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不运行 pytest 或 pip-audit，不进入下一阶段。
