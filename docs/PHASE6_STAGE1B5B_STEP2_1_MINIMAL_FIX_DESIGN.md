# Phase 6 Stage 1B-5B — Step 2.1 RC-01 最小修复边界设计

## 1. 设计目标

本步骤只设计 RC-01 的最小修复边界，回答：

> 为使当前 Scanner 实现满足已经存在的统计测试契约，最小需要改变什么？哪些内容绝对不能改变？

本步骤 **只设计，不实施**：

```text
DESIGN_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
AUTO_FIX = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
```

设计只针对当前 `tests/test_pip_audit_scanner.py` 已存在的统计测试契约，不扩展到 Service、GUI、数据库或 JSON 功能。

## 2. 已确认事实

### 2.1 当前运行时失败

Step 1.8 已确认：

```text
12 collected
7 passed
5 failed
0 skipped
1.22s
exit code = 1
```

五个失败的全部证据见 Step 1.8。与统计字段直接相关的失败模式为：

```text
AssertionError: assert 3 == 2     # audited_dependencies
KeyError: 'skipped_dependencies'
AssertionError: assert 3 == 2     # partial skip
AssertionError: assert 2 == 0     # all skipped
```

### 2.2 当前静态实现

当前文件：

```text
scanners/pip_audit_scanner.py
```

当前存在：

```text
metadata["audited_dependencies"]
```

当前静态实现未确认存在：

```text
metadata["skipped_dependencies"]
metadata["total_dependencies"]
```

当前 `ScanOutput` 类型已经提供 `metadata`，不需要新增 DTO：

```text
scanners/base.py:66-70
```

### 2.3 当前测试契约

当前测试文件：

```text
tests/test_pip_audit_scanner.py
```

直接断言三个统计字段：

```text
audited_dependencies
skipped_dependencies
total_dependencies
```

当前统计场景：

```text
complete without vulnerabilities
complete with vulnerabilities
partial skip
all skipped
```

Step 1.9 已确认：四个统计测试的断言顺序均为：

```text
audited_dependencies -> skipped_dependencies -> total_dependencies
```

并且 `total_dependencies` 在 Step 1.8 中均因更早失败而未执行：

```text
TOTAL_ASSERTION_NOT_REACHED_IN_STEP_1_8 = CONFIRMED
```

### 2.4 当前解析调用点

```text
PipAuditScanner.parse_output()  :210
PipAuditScanner.scan()          :126
parse_output() 调用点           :194-196
dependency 循环                 :224
metadata 写入                   :205
```

当前 `parse_output()` 被测试以三值形式直接调用：

```text
findings, warnings, audited = PipAuditScanner.parse_output(...)
```

因此设计必须保持该默认调用形态，不得为了增加两个统计字段而强制现有测试改成五值解包。

## 3. 修复边界

本次修复只允许触及 **统计计算与 metadata 传递**：

```text
计算 total / skipped / audited
传递到 scan()
写入 ScanOutput.metadata
```

不得触及：

```text
Finding 创建
vulnerability 解析
dedupe
skip_reason 现有 warning
skip_reason 之后的 Finding 控制流
pip-audit 命令
subprocess 安全设置
Service
Repository
GUI
数据库 / Schema
JSON 功能 / JSON 文件
```

默认修改范围：

```text
scanners/pip_audit_scanner.py
```

默认不修改：

```text
tests/test_pip_audit_scanner.py = NO_CHANGE
```

当前没有已确认的必要原因要求修改测试。测试失败是当前 Scanner 统计实现不足，不是测试契约错误。

## 4. 三个统计字段的设计

### 4.1 `total_dependencies`

**统计对象**：`payload["dependencies"]` 列表中的每一个元素。

**计数规则**：

```text
total_dependencies = len(payload["dependencies"])
```

包括：

- 正常 dependency 对象；
- 带 `skip_reason` 的 dependency 对象；
- 非 dict 元素；
- 字段不完整或无法形成 Finding 的对象。

**输出位置**：

```text
ScanOutput.metadata["total_dependencies"]
```

**Finding 影响**：无直接关系。该字段只统计输入对象数量。

### 4.2 `skipped_dependencies`

**统计条件**：

```text
isinstance(dependency, dict)
and bool(dependency.get("skip_reason"))
```

即：当前已存在 warning 分支使用的同一个真值判断。

**计数规则**：每个满足条件的 dependency 计数一次。

**输出位置**：

```text
ScanOutput.metadata["skipped_dependencies"]
```

**Finding 影响**：

```text
STATISTICS_CHANGE = YES
FINDING_CONTROL_FLOW_CHANGE = NO
```

`skip_reason` 只影响统计计数，不新增 `continue`，不改变当前 warning，不改变 `vulns` 读取，不改变 Finding 创建，不改变 dedupe。

这一点必须明确：统计上计为 skipped，不自动等于“该 dependency 不产生 Finding”。当前 Finding 控制流保持不变。

### 4.3 `audited_dependencies`

**统计条件**：

```text
isinstance(dependency, dict)
and not bool(dependency.get("skip_reason"))
```

**计数规则**：

- 正常 dict dependency：计入；
- 带真值 `skip_reason` 的 dict：不计入（计入 skipped）；
- 非 dict 元素：不计入 audited，也不计入 skipped；
- 当前不增加额外的 name/version/vulns 有效性门槛。

**输出位置**：

```text
ScanOutput.metadata["audited_dependencies"]
```

**Finding 影响**：

```text
VULNERABILITY_PARSING_CHANGE = NO
FINDING_CREATION_CHANGE = NO
DEDUPE_CHANGE = NO
```

该字段只替换当前 `len(dependencies)` 的错误计数，不改变 vulnerability/Finding 解析。

### 4.4 当前测试场景核对

| 场景 | 输入 dependency 数 | skip_reason 数 | total | skipped | audited |
|---|---:|---:|---:|---:|---:|
| complete without vulnerabilities | 1 | 0 | 1 | 0 | 1 |
| complete with vulnerabilities | 1 | 0 | 1 | 0 | 1 |
| partial skip | 3 | 1 | 3 | 1 | 2 |
| all skipped | 2 | 2 | 2 | 2 | 0 |

上述值逐项对应现有测试断言，不需要修改测试。

## 5. 数据流设计

当前数据流必须保持原有 Finding 路径，只在同一次 dependency 遍历中增加计数：

```text
pip-audit JSON
  └─ payload["dependencies"]
       ↓
parse_output(payload, include_statistics=True)
  ├─ 现有 Finding 解析 / dedupe / warning 逻辑
  ├─ total += 1
  ├─ skip_reason 为真 -> skipped += 1
  └─ 非 skip 的 dict -> audited += 1
       ↓
(findings, warnings, audited, skipped, total)
       ↓
scan()
       ↓
ScanOutput.metadata:
  audited_dependencies = audited
  skipped_dependencies = skipped
  total_dependencies = total
```

### 5.1 计算位置

在 `parse_output()` 的现有 dependency 循环中计算：

- `total`：每个元素进入循环时计数；
- `skipped`：命中真值 `skip_reason` 时计数；
- `audited`：非 skip 的 dict dependency 计数。

不得为统计新增第二次 dependency 遍历；不得新增 Service/DB 结构。

### 5.2 返回与传递

`parse_output()` 必须兼容现有测试的三值调用，同时向 `scan()` 提供五值：

```text
parse_output(stdout)                          -> (findings, warnings, audited)
parse_output(stdout, include_statistics=True) -> (findings, warnings, audited, skipped, total)
```

设计采用 **可选关键字参数**：

```python
def parse_output(
    self,
    stdout: str,
    *,
    include_statistics: bool = False,
) -> ...:
```

`scan()` 改为：

```python
findings, warnings, audited, skipped, total = self.parse_output(
    stdout,
    include_statistics=True,
)
```

现有测试继续使用默认调用：

```python
findings, warnings, audited = PipAuditScanner.parse_output(...)
```

因此默认三值契约不破坏，测试文件无需修改。

### 5.3 写入 metadata

`scan()` 现有 metadata 写入点 `:205` 只增加两个键：

```python
"audited_dependencies": audited,
"skipped_dependencies": skipped,
"total_dependencies": total,
```

保留现有：

```text
returncode
duration_seconds
vulnerability_service
```

不改变 `ScanOutput` 类型，不改变 Service。

## 6. 最小修改范围

### 6.1 允许修改

```text
scanners/pip_audit_scanner.py
```

预计只改：

1. `parse_output()` 签名增加可选 `include_statistics`；
2. 现有 dependency 循环增加三个计数器；
3. `parse_output()` 默认三值返回保持不变；
4. `scan()` 使用带统计的五值调用；
5. `ScanOutput.metadata` 增加 `skipped_dependencies`、`total_dependencies`。

### 6.2 不修改

```text
tests/test_pip_audit_scanner.py = NO_CHANGE
```

不通过修改测试断言、删除测试、放宽断言或新增 fixtures 来绕过实现问题。

## 7. 明确禁止修改项

```text
DO_NOT_CHANGE:
- Finding 创建逻辑
- vulnerability 解析逻辑
- dedupe 逻辑
- skip_reason 现有 warning 行为
- skip_reason 之后现有 Finding 控制流
- pip-audit 命令执行方式
- subprocess 安全设置
- Service 层
- Repository 层
- GUI
- 数据库
- Schema
- JSON 功能
- 任何既有 JSON 文件或代码
```

强化声明：

```text
NO_JSON_FEATURE_DEVELOPMENT
NO_JSON_CODE_CLEANUP
NO_JSON_FILE_DELETION
```

## 8. 修改影响分析

| 区域 | 是否改变 | 原因 |
|---|---|---|
| dependency 遍历 | YES（仅增加计数） | 在现有循环中累计 total/skipped/audited；不新增遍历，不改变 continue |
| audited 统计 | YES | 从 `len(dependencies)` 改为“非 skip 的 dict 计数” |
| skipped 统计 | YES | 按真值 `skip_reason` 新增计数 |
| total 统计 | YES | 统计全部输入元素 |
| Finding 创建 | NO | 现有 append 与控制流不动 |
| warning | NO | 现有 skip_reason warning 文本和触发不变 |
| dedupe | NO | 现有 key 与逻辑不动 |
| metadata | YES | 增加两个键，保留原有键 |

任何会改变 Finding、warning 或 dedupe 的方案：

```text
OUT_OF_SCOPE
```

不得纳入本次修复。

## 9. 统计关系的证据边界

Step 1.9 已确认四个当前测试场景的数值均满足：

```text
audited_dependencies + skipped_dependencies == total_dependencies
```

但当前测试没有写成统一等式断言。因此报告严格区分：

```text
OBSERVED_CURRENT_TEST_CASE_RELATIONSHIP = YES
EXPLICIT_UNIVERSAL_TEST_CONTRACT = NO
UNIFIED_RELATIONSHIP_NOT_DIRECTLY_ASSERTED = YES
```

本设计只保证四个现有统计场景，不把该观察扩大为未经证实的全局业务规则。

同时明确非测试边界：

```text
非 dict 元素：
  total += 1
  skipped 不增加
  audited 不增加
因此可能出现 audited + skipped < total。
```

该行为不在当前测试契约内，标记为边界事实，不设计新的 invalid 字段，也不擅自改变 Finding 行为。

## 10. 后续验证计划（不执行）

### V1

```text
python -m pytest tests/test_pip_audit_scanner.py -q
```

预期：

```text
12 collected
12 passed
0 failed
0 skipped
```

依据当前测试契约，所有当前 Scanner 测试应通过。

### V2

分别验证：

```text
total_dependencies
skipped_dependencies
audited_dependencies
```

三个键存在，且四个统计场景的值符合第 4.4 节。

### V3

确认：

- Finding 相关既有测试仍通过；
- warning 相关既有测试仍通过；
- `parse_output()` 默认三值调用仍可工作；
- 没有新增 JSON 功能或 JSON 清理。

本步骤不执行 V1/V2/V3。

## 11. 不执行实施的确认

```text
DESIGN_ONLY = YES
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
AUTO_FIX = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
TEST_DESIGN_CHANGE = NO
SERVICE_CHANGE = NO
GUI_CHANGE = NO
JSON_FEATURE_DEVELOPMENT = NO
JSON_CLEANUP = NO
```

本步骤只新增本设计报告：

```text
docs/PHASE6_STAGE1B5B_STEP2_1_MINIMAL_FIX_DESIGN.md
```

没有修改任何 `.py` 文件、测试、数据库或 Schema。

## 12. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 2.1 结束时只读复核：

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

## 13. 停止条件

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本设计报告后立即停止。不得进入 `CODE_IMPLEMENTATION`，不得运行 pytest，不得修改 Scanner 或测试。
