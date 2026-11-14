# Phase 6 Stage 1B-5B — Step 2.2 RC-01 最小代码实施

## 1. 实施目标与范围

依据 Step 2.1 与 Step 2.1-R1 已审核设计，只修复 `PipAuditScanner` 的依赖统计字段：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

实际修改生产文件：

```text
scanners/pip_audit_scanner.py
```

新增实施报告：

```text
docs/PHASE6_STAGE1B5B_STEP2_2_IMPLEMENTATION.md
```

未修改：

```text
tests/test_pip_audit_scanner.py
Service / Repository / GUI / 数据库 / Schema
JSON 功能或 JSON 文件
```

## 2. 实际修改内容

### 2.1 `scan()` 改为调用私有统计方法

`scanners/pip_audit_scanner.py:194-198`：

```python
findings, warnings, audited, skipped, total = (
    self._parse_with_statistics(
        result.stdout, target_path, availability.version
    )
)
```

`scan()` 不再调用三值公共包装层，而是一次取得五个值。

### 2.2 `ScanOutput.metadata`

`scanners/pip_audit_scanner.py:207-209`：

```python
"audited_dependencies": audited,
"skipped_dependencies": skipped,
"total_dependencies": total,
```

原有 metadata 键保持不变：

```text
returncode
duration_seconds
vulnerability_service
```

### 2.3 公共 `parse_output()` 保留三值契约

`scanners/pip_audit_scanner.py:214-220`：

```python
def parse_output(
    self, payload_text: str, target: Path, version: str
) -> tuple[list[Finding], list[str], int]:
    findings, warnings, audited, _skipped, _total = (
        self._parse_with_statistics(payload_text, target, version)
    )
    return findings, warnings, audited
```

- 仍然是普通实例方法；
- 仍然没有装饰器；
- 签名未改变；
- 返回仍为三个值。

### 2.4 新增私有 `_parse_with_statistics()`

`scanners/pip_audit_scanner.py:222-330`：

```python
def _parse_with_statistics(
    self, payload_text: str, target: Path, version: str
) -> tuple[list[Finding], list[str], int, int, int]:
```

原 `parse_output()` 的完整解析逻辑移入该方法，只新增统计计数和五值返回。

### 2.5 统计实现

`scanners/pip_audit_scanner.py:235-250`：

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
    skip_reason = str(dependency.get("skip_reason") or "").strip()
    if skip_reason:
        skipped += 1
        warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
    else:
        audited += 1
```

规则与批准设计一致：

```text
total   = payload["dependencies"] 中的全部元素（包括非 dict）
skipped = dict 且 bool(skip_reason) 为真
audited = dict 且 bool(skip_reason) 为假
非 dict 只计入 total
```

五值返回：

`scanners/pip_audit_scanner.py:330`：

```python
return findings, warnings, audited, skipped, total
```

## 3. 公共接口证据

```text
METHOD = PipAuditScanner.parse_output
DECORATOR = NONE
KIND = INSTANCE_METHOD
SIGNATURE = (self, payload_text: str, target: Path, version: str)
RETURN = tuple[list[Finding], list[str], int]
```

公共方法最后只返回：

```python
return findings, warnings, audited
```

现有测试调用仍为三值解包，未修改：

```text
tests/test_pip_audit_scanner.py:77
tests/test_pip_audit_scanner.py:212
```

异常路径调用也保持兼容：

```text
tests/test_pip_audit_scanner.py:223
tests/test_pip_audit_scanner.py:225
```

## 4. 私有接口证据

```text
METHOD = PipAuditScanner._parse_with_statistics
DECORATOR = NONE
KIND = INSTANCE_METHOD
SIGNATURE = (self, payload_text: str, target: Path, version: str)
RETURN = tuple[list[Finding], list[str], int, int, int]
```

返回顺序固定：

```text
1. findings : list[Finding]
2. warnings : list[str]
3. audited  : int
4. skipped  : int
5. total    : int
```

`scan()` 是唯一生产调用者，按五值解包；公共 `parse_output()` 是兼容包装层，只取前三值。

## 5. 既有行为未改变

### 5.1 Finding 创建

`Finding(...)` 构造仍在原位置执行：

```text
scanners/pip_audit_scanner.py:313-329
```

没有新增或删除 Finding 条件。

### 5.2 vulnerability 解析

`vulns` 读取、`vuln_id`、aliases、fix_versions、description、severity 和 recommendation 逻辑保持原样。

### 5.3 dedupe

`seen` 集合、`dedupe_key = (name.lower(), vuln_id)` 和重复跳过逻辑保持不变：

```text
scanners/pip_audit_scanner.py:265-268
```

### 5.4 warning

原有：

```python
warnings.append(f"{name or '未知依赖'} 未完成审计：{skip_reason}")
```

仍在 `skip_reason` 为真时执行；本次只在其旁边增加 `skipped += 1`。

### 5.5 `skip_reason` 后的 Finding 控制流

`skip_reason` 为真时**没有新增 `continue`**，也没有新增 `return`。代码仍继续执行：

```text
vulns = dependency.get("vulns")
if not isinstance(vulns, list):
    continue
for vuln in vulns:
    ...
    findings.append(...)
```

因此现有“skip_reason 后仍可能解析 vulns/Finding”的控制流保持不变。

### 5.6 异常处理

JSON 解码、缺 dependencies、非 dict、非 list vulns、非 dict vuln、空字段等现有分支均保持原样。

## 6. 实际修改文件与 SHA-256

### 6.1 修改前

| 文件 | Bytes | SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 12,660 | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

### 6.2 修改后

| 文件 | Bytes | SHA-256 |
|---|---:|---|
| `scanners/pip_audit_scanner.py` | 13,307 | `AC032FE36B0E262928BC61E065D570E39B7B3644D255A4D3478A67AC5CCAF43A` |
| `tests/test_pip_audit_scanner.py` | 10,952 | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

```text
SCANNER_FILE_CHANGED = YES
SCANNER_TEST_FILE_CHANGED = NO
```

生产修改仅此一个文件。

### 6.3 测试文件状态说明

`tests/test_pip_audit_scanner.py` 在 Git 工作区中仍显示 `M`，这是此前 Stage 1B 测试契约工作留下的既有修改；本步骤未编辑它，SHA-256 与 Step 1.1 基线完全一致。

## 7. 静态检查与未执行项目

已执行：

```text
Python AST parse: AST_OK=1
```

仅做语法解析，不属于运行时测试。

未执行：

```text
python -m pytest ...    NO
pip-audit               NO
GUI                     NO
数据库 / Schema 操作      NO
Git add / commit / push  NO
```

## 8. 禁止事项核对

```text
PRODUCTION_CODE_MODIFIED = YES (only scanners/pip_audit_scanner.py)
TEST_CODE_MODIFIED = NO
SERVICE_MODIFIED = NO
REPOSITORY_MODIFIED = NO
GUI_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
DTO_ADDED = NO
JSON_FEATURE_DEVELOPMENT = NO
JSON_CODE_CLEANUP = NO
JSON_FILE_DELETION = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GIT_MUTATION = NO
```

## 9. 当前状态

本次实施只完成生产代码修改和静态语法检查。运行时行为尚未由本步骤验证，不能将静态解析描述成 pytest 或 pip-audit 通过。

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后停止，等待人工审核；不自行进入测试运行或下一阶段。
