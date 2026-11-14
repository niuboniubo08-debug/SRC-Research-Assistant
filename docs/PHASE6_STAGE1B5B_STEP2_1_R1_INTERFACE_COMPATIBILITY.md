# Phase 6 Stage 1B-5B — Step 2.1-R1 parse_output 接口兼容性设计修订

## 1. 调查目标

本步骤只修订 Step 2.1 中 `parse_output()` 的接口设计矛盾，确认当前真实方法形态、全部调用者、兼容方案和最终完整签名。

本步骤不实施代码修改：

```text
READ_ONLY = YES
DESIGN_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
```

## 2. 当前方法装饰器

`PipAuditScanner.parse_output()` 位于：

```text
scanners/pip_audit_scanner.py:210
```

当前方法**没有任何装饰器**：

```text
NOT_A_STATICMETHOD
NOT_A_CLASSMETHOD
ORDINARY_INSTANCE_METHOD
```

因此它必须通过实例调用：

```text
self.parse_output(...)
scanner.parse_output(...)
```

不能写成：

```text
PipAuditScanner.parse_output(...)
```

后者会把第一个参数当作 `self`，不是合法的类级调用方式。Step 2.1 报告中的 `PipAuditScanner.parse_output(...)` 是接口描述错误。

## 3. 当前方法签名

当前真实签名：

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int]:
```

三个位置参数：

```text
self         : PipAuditScanner
payload_text : str
target       : Path
version      : str
```

没有 `include_statistics` 参数，没有 `*args` / `**kwargs`，没有重载。

## 4. 当前返回类型与返回结构

当前返回：

```python
tuple[list[Finding], list[str], int]
```

实际解包形式：

```python
findings, warnings, audited = ...
```

第三个返回值当前为：

```python
len(dependencies)
```

`scan()` 在 `scanners/pip_audit_scanner.py:194-196` 使用第三个值，并在 `:205` 写入：

```text
ScanOutput.metadata["audited_dependencies"]
```

当前不返回 skipped/total。

## 5. 全项目调用者清单

### 5.1 PitAuditScanner 生产调用者

| 位置 | 调用方式 | 使用方式 |
|---|---|---|
| `scanners/pip_audit_scanner.py:194-196` | `self.parse_output(result.stdout, target_path, availability.version)` | 三值解包：`findings, warnings, audited` |

没有其他生产代码调用 `PipAuditScanner.parse_output()`。

### 5.2 测试调用者

| 位置 | 调用方式 | 使用方式 |
|---|---|---|
| `tests/test_pip_audit_scanner.py:77` | `scanner.parse_output(payload, target, "2.10.1")` | 三值解包 |
| `tests/test_pip_audit_scanner.py:212-214` | `scanner.parse_output(...)` | 三值解包 |
| `tests/test_pip_audit_scanner.py:223` | 异常路径调用 | 返回值忽略，期望 `ScannerParseError` |
| `tests/test_pip_audit_scanner.py:225` | 异常路径调用 | 返回值忽略，期望 `ScannerParseError` |

四处的对象都是 `PipAuditScanner` 实例，全部通过 `scanner.parse_output(...)` 调用。

### 5.3 其他 Scanner 的同名方法

项目中另有：

```text
scanners/bandit_scanner.py:184   BanditScanner.parse_output(...)
scanners/semgrep_scanner.py:193  SemgrepScanner.parse_output(...)
```

它们是不同类的方法，返回各自的两值结构。它们不调用、也不依赖 `PipAuditScanner.parse_output()`，本修订不涉及它们。

### 5.4 文档提及

历史调查文档中存在 `parse_output()` 的描述和示例；这些不是运行时代码调用者。Step 2.1 的 `PipAuditScanner.parse_output(...)` 示例是文档错误，不表示当前源码存在类级调用。

## 6. 调用者兼容性分析

### 6.1 生产调用者

`scan()` 当前使用三值：

```python
findings, warnings, audited = self.parse_output(...)
```

如果保持公开三值，`scan()` 只改为调用新的内部统计方法，即可不改变外部行为。

### 6.2 测试调用者

两处直接解包三值：

```python
findings, warnings, audited = scanner.parse_output(...)
```

两处异常测试忽略返回值。

因此任何“公共 `parse_output` 强制返回五值”的方案都会破坏现有测试，违反：

```text
tests/test_pip_audit_scanner.py = NO_CHANGE
```

### 6.3 类级调用

当前方法不是 `@staticmethod`，因此以下写法不能作为兼容方案：

```python
PipAuditScanner.parse_output(payload, target, version)
```

正确写法只能是：

```python
scanner.parse_output(payload, target, version)
```

或类内部：

```python
self.parse_output(payload, target, version)
```

## 7. 至少两种接口设计比较

### 方案 A：公共 `parse_output()` 增加 `include_statistics`

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
    *,
    include_statistics: bool = False,
) -> (
    tuple[list[Finding], list[str], int]
    | tuple[list[Finding], list[str], int, int, int]
):
    ...
```

优点：

- 保留默认三值；
- 只增加一个参数；
- 一次解析即可返回统计。

缺点：

- 公共返回类型变成联合类型；
- 调用者必须依赖布尔参数判断返回形状；
- `scan()` 与测试走不同分支；
- 类型检查和接口理解成本上升；
- 仍改变了公共方法签名。

风险：**中等**。

### 方案 B：公共 `parse_output()` 保持三值，新增私有统计解析方法

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int]:
    findings, warnings, audited, _skipped, _total = (
        self._parse_with_statistics(payload_text, target, version)
    )
    return findings, warnings, audited


def _parse_with_statistics(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int, int, int]:
    ...
```

`scan()` 改为：

```python
findings, warnings, audited, skipped, total = (
    self._parse_with_statistics(
        result.stdout,
        target_path,
        availability.version,
    )
)
```

优点：

- 公共 `parse_output()` 的签名和返回类型完全不变；
- 所有现有测试和异常调用者无需修改；
- 不引入联合返回类型；
- `scan()` 仍只解析一次；
- 统计计数与 Finding 解析在同一内部方法中完成；
- 无需修改 Service、GUI、数据库、Schema。

缺点：

- 新增一个私有方法；
- 内部五值结构需要清晰命名和注释。

风险：**低**。

### 方案 C：公共 `parse_output()` 直接改为五值

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int, int, int]:
    ...
```

缺点：

- 直接破坏 `tests/test_pip_audit_scanner.py:77` 和 `:212` 的三值解包；
- 必须修改测试，违反本轮 `NO_CHANGE`；
- 扩大接口变更范围。

结论：不采用。

### 方案 D：新公共 `parse_output_statistics()`

新增一个公开方法，`parse_output()` 保持原样。

相比方案 B：

- 公开 API 面积更大；
- 仍需避免重复解析；
- 没有额外收益。

结论：不采用。

## 8. 最终推荐接口及完整签名

采用 **方案 B**。

### 8.1 公共接口保持不变

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int]:
    """Parse pip-audit JSON and return findings, warnings, audited count."""
```

这是当前调用者看到的唯一公共解析接口。

### 8.2 新增私有统计解析方法

```python
def _parse_with_statistics(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int, int, int]:
    """Return findings, warnings, audited, skipped, total."""
```

返回值顺序固定：

```text
1. findings : list[Finding]
2. warnings : list[str]
3. audited  : int
4. skipped  : int
5. total    : int
```

### 8.3 生产调用方式

```python
findings, warnings, audited, skipped, total = (
    self._parse_with_statistics(
        result.stdout,
        target_path,
        availability.version,
    )
)
```

### 8.4 公共方法调用方式

```python
findings, warnings, audited = scanner.parse_output(
    payload,
    target,
    version,
)
```

## 9. 三值返回兼容性证明

公共方法保留：

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int]:
```

并始终返回三元素元组：

```python
return findings, warnings, audited
```

现有四个测试调用点均不需要改变：

```text
tests/test_pip_audit_scanner.py:77   三值解包
tests/test_pip_audit_scanner.py:212  三值解包
tests/test_pip_audit_scanner.py:223  异常路径，忽略返回值
tests/test_pip_audit_scanner.py:225  异常路径，忽略返回值
```

生产调用者 `scan()` 改用私有方法，不依赖公共三值；即使如此，公共三值契约仍完整保留。

因此：

```text
PUBLIC_THREE_VALUE_SIGNATURE_UNCHANGED = YES
PUBLIC_RETURN_ARITY_UNCHANGED = YES
EXISTING_TEST_CALLERS_COMPATIBLE = YES
```

## 10. 五值统计传递方式

五值只在私有方法内部及 `scan()` 中传递：

```text
_parse_with_statistics()
  -> (findings, warnings, audited, skipped, total)
  -> scan()
  -> ScanOutput.metadata
```

`scan()` metadata 写入：

```python
metadata={
    "returncode": result.returncode,
    "duration_seconds": round(result.duration_seconds, 3),
    "audited_dependencies": audited,
    "skipped_dependencies": skipped,
    "total_dependencies": total,
    "vulnerability_service": self.vulnerability_service,
}
```

不新增 DTO，不修改 `ScanOutput` 类型，不修改 Service。

## 11. 类型标注

公共方法：

```python
def parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int]:
```

私有方法：

```python
def _parse_with_statistics(
    self,
    payload_text: str,
    target: Path,
    version: str,
) -> tuple[list[Finding], list[str], int, int, int]:
```

局部变量：

```python
audited: int = 0
skipped: int = 0
total: int = 0
```

不增加 `include_statistics` 参数；不产生联合返回类型。

## 12. 与原 Step 2.1 统计规则的兼容性

本修订不重新设计 Step 2.1 的统计规则，只替换接口方案：

```text
total_dependencies:
  统计 payload["dependencies"] 的全部元素

skipped_dependencies:
  dict 且 bool(dependency.get("skip_reason")) 时为真

audited_dependencies:
  dict 且 bool(dependency.get("skip_reason")) 为假时计数
```

保持不变：

```text
Finding 创建                 NO_CHANGE
vulnerability 解析           NO_CHANGE
dedupe                       NO_CHANGE
warning                      NO_CHANGE
skip_reason 后的 Finding 控制流  NO_CHANGE
Finding 持久化                OUT_OF_SCOPE
```

统计值与四个现有测试场景的对应关系不变：

```text
complete without vulnerabilities: 1 / 0 / 1
complete with vulnerabilities:    1 / 0 / 1
partial skip:                     2 / 1 / 3
all skipped:                      0 / 2 / 2
```

Step 1.9 的证据边界继续保持：

```text
DIRECT_VALUE_RELATIONSHIP_OBSERVED = YES
UNIFIED_RELATIONSHIP_NOT_DIRECTLY_ASSERTED = YES
```

不把四个场景扩展为未经证实的全局公式；非 dict/无效对象的统计缺口仍作为边界事实，不新增 `invalid_dependencies`。

## 13. SHA-256 对照

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 2.1-R1 结束时只读复核：

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

## 14. 禁止事项遵守情况与停止条件

```text
READ_ONLY = YES
DESIGN_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
NO_JSON_FEATURE_DEVELOPMENT = YES
NO_JSON_CODE_CLEANUP = YES
NO_JSON_FILE_DELETION = YES
```

本步骤新增且仅新增：

```text
docs/PHASE6_STAGE1B5B_STEP2_1_R1_INTERFACE_COMPATIBILITY.md
```

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不实施任何代码修改，不运行 pytest。
