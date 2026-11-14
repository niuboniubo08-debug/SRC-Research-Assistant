# Phase 6 Stage 1B-5B — Step 1.5 当前 Finding 解析控制流边界

## 1. 调查范围

本步骤只调查：

```text
scanners/pip_audit_scanner.py
```

中 `PipAuditScanner.parse_output()` 内，从 `dependency` 进入 `vulns`、`vuln`，到 `Finding(...)` 与 `findings.append(...)` 的当前控制流。

本步骤只记录当前事实，不设计新的 Finding 行为、不修改去重策略、不修改统计字段、不调查 Service。

## 2. `vulns` 进入 Finding 处理的条件

### CONFIRMED

`vulns` 从当前 `dependency` 读取：

```text
scanners/pip_audit_scanner.py:232
```

```python
vulns = dependency.get("vulns")
```

随后进行结构检查：

```text
scanners/pip_audit_scanner.py:233-234
```

```python
if not isinstance(vulns, list):
    continue
```

当前 dependency 能进入内层 `for vuln in vulns` 的条件：

```text
1. dependency 是 dict（否则 :225-226 continue）；
2. vulns 是 list（否则 :233-234 continue）；
3. vulns 非空（空 list 可进入循环头，但没有内层迭代）。
```

当前不会进入内层 Finding 处理的情况：

```text
- dependency 不是 dict；
- vulns 不是 list；
- vulns 是空 list（无 vuln 迭代）。
```

### CURRENT_CONTROL_FLOW_FACT

```text
VULNS_SOURCE = dependency.get("vulns")
VULNS_LIST_REQUIRED = YES
NON_LIST_VULNS_CONTINUE = YES
EMPTY_VULNS_HAS_FINDING_ITERATION = NO
```

本步骤不判断 `skip_reason` 是否应阻止进入此处；该内容不属于当前控制流事实。

## 3. 内层 `vuln` 处理事实

### CONFIRMED

内层循环位于：

```text
scanners/pip_audit_scanner.py:235
```

```python
for vuln in vulns:
```

当前单次循环处理对象：

```text
vuln
```

结构检查：

```text
scanners/pip_audit_scanner.py:236-237
```

```python
if not isinstance(vuln, dict):
    continue
```

非 dict 的 `vuln` 当前直接跳过当前内层迭代。

当前内层循环读取/使用的真实字段：

```text
vuln.get("id")
vuln.get("aliases")
vuln.get("fix_versions")
vuln.get("description")
vuln.get("severity")
vuln.get("cvss")
vuln.get("cvss_score")
vuln.get("affected_versions")
```

此外使用外层当前依赖的：

```text
name
current_version
```

### CURRENT_CONTROL_FLOW_FACT

```text
INNER_LOOP_OBJECT = vuln
NON_DICT_VULN_CONTINUE = YES
FINDING_FIELDS_SOURCE = vuln + 当前 dependency 的 name/current_version
```

## 4. Finding 构造前的真实条件与字段处理

### CONFIRMED

在 `Finding(...)` 之前，当前代码实际执行以下处理。

#### 4.1 `vuln_id` 规范化

```text
scanners/pip_audit_scanner.py:238
```

```python
vuln_id = str(vuln.get("id") or "").strip()
```

这不是过滤条件；空值后续可被 aliases 或 `"UNKNOWN"` 替代。

#### 4.2 aliases 规范化

```text
scanners/pip_audit_scanner.py:239-243
```

```python
aliases = [
    str(alias).strip()
    for alias in vuln.get("aliases", [])
    if str(alias).strip()
] if isinstance(vuln.get("aliases"), list) else []
```

#### 4.3 `vuln_id` 缺失时的替代

```text
scanners/pip_audit_scanner.py:244-245
```

```python
if not vuln_id:
    vuln_id = aliases[0] if aliases else "UNKNOWN"
```

这是字段规范化/回退，不是针对当前记录的整体过滤条件。

#### 4.4 去重检查

见第 5 节。

#### 4.5 fix_versions 规范化

```text
scanners/pip_audit_scanner.py:250-254
```

空值不阻止后续 Finding 构造。

#### 4.6 description 读取与回退

```text
scanners/pip_audit_scanner.py:255, 276-281
```

```python
description = str(vuln.get("description") or "").strip()
...
if not description:
    description = f"pip-audit 在 {name} {current_version} 中检测到 {vuln_id}。"
```

这是文本回退，不是过滤条件。

#### 4.7 severity 读取与回退

```text
scanners/pip_audit_scanner.py:256-265
```

```python
severity_value = (
    vuln.get("severity")
    or vuln.get("cvss")
    or vuln.get("cvss_score")
)
severity_source = "advisory"
severity = map_pip_audit_severity(severity_value)
if severity_value is None:
    severity = Severity.MEDIUM
    severity_source = "conservative-default"
```

这是字段映射与默认值，不是过滤条件。

#### 4.8 affected_versions 读取与回退

```text
scanners/pip_audit_scanner.py:267-270
```

缺失时使用当前审计版本的说明文本，不阻止 Finding 构造。

#### 4.9 recommendation 文本生成

```text
scanners/pip_audit_scanner.py:271-275
```

根据 `fix_versions` 是否为空生成不同建议文本，不阻止 Finding 构造。

#### 4.10 metadata 构造

```text
scanners/pip_audit_scanner.py:282-293
```

在当前路径中直接构造 metadata，不构成额外过滤。

### CURRENT_CONTROL_FLOW_FACT

在 `Finding(...)` 之前，存在的硬性停止点只有：

```text
- dependency 不是 dict；
- vulns 不是 list；
- vuln 不是 dict；
- dedupe_key 已存在于 seen。
```

不存在基于以下字段的过滤分支：

```text
name 为空
version 为空
vuln_id 为空
aliases 为空
fix_versions 为空
description 为空
severity 为空
affected_versions 为空
```

这些字段为空时会走当前代码的规范化/回退路径，而不是被显式跳过。

## 5. 当前去重边界

### CONFIRMED

去重键构造：

```text
scanners/pip_audit_scanner.py:246
```

```python
dedupe_key = (name.lower(), vuln_id)
```

使用字段：

```text
name       -> 外层 dependency 的 name
vuln_id    -> 当前 vuln 的 id，或 aliases[0]，或 "UNKNOWN"
```

检查位置：

```text
scanners/pip_audit_scanner.py:247-249
```

```python
if dedupe_key in seen:
    continue
seen.add(dedupe_key)
```

重复时的控制流：

```text
当前 vuln 直接 continue；
不构造 Finding；
不 append。
```

通过去重检查的路径：

```text
dedupe_key 不在 seen
  -> seen.add(dedupe_key)
  -> 继续执行当前 vuln 的 Finding 构造
```

`seen` 初始化于 `:222`：

```python
seen: set[tuple[str, str]] = set()
```

它是本次 `parse_output()` 调用范围内的集合，不是跨调用持久状态。

### CURRENT_CONTROL_FLOW_FACT

```text
DEDUPE_KEY = (name.lower(), vuln_id)
DEDUPE_CHECK = if dedupe_key in seen
DUPLICATE_ACTION = continue
SEEN_SCOPE = 当前 parse_output() 调用
```

本步骤不评价去重策略是否正确，也不设计新的去重规则。

## 6. `Finding(...)` 构造路径

### CONFIRMED

真实构造位置：

```text
scanners/pip_audit_scanner.py:294-310
```

当前代码将 `Finding(...)` 直接作为 `findings.append(...)` 的参数：

```python
findings.append(
    Finding(
        title=f"{name} {current_version} · {vuln_id}",
        category="依赖漏洞",
        severity=severity,
        confidence=Confidence.HIGH,
        description=description,
        file_path=str(target),
        line_number=0,
        rule_id=vuln_id,
        recommendation=recommendation,
        scanner_name=self.name,
        scanner_version=version,
        detected_at=self._clock(),
        metadata=metadata,
    )
)
```

在 `Finding(...)` 调用之前，没有额外的 `if` 条件包住该构造；进入此处的前提是：

```text
通过第 4 节的字段处理
且通过第 5 节的去重检查
```

## 7. `findings.append(...)` 追加路径

### CONFIRMED

真实追加位置：

```text
scanners/pip_audit_scanner.py:294-310
```

`findings.append(...)` 与 `Finding(...)` 是同一个表达式：

```python
findings.append(Finding(...))
```

从 `Finding(...)` 构造到 `findings.append(...)` 之间没有额外条件，也没有中间的保存/删除步骤。

当前代码没有在 append 之后再次检查并删除该 Finding 的逻辑。

### CURRENT_CONTROL_FLOW_FACT

```text
FINDING_CONSTRUCTION = inline in findings.append(...)
APPEND_CONDITION_AFTER_CONSTRUCTION = NONE
FINDING_REMOVAL_AFTER_APPEND = NONE
```

## 8. 当前控制流完整路径

```text
dependency
  |
  +-- if not isinstance(dependency, dict): continue
  |
  +-- vulns = dependency.get("vulns")
  |
  +-- if not isinstance(vulns, list): continue
  |
  +-- for vuln in vulns:
        |
        +-- if not isinstance(vuln, dict): continue
        |
        +-- vuln_id = str(vuln.get("id") or "").strip()
        +-- aliases = ...
        +-- if not vuln_id: vuln_id = aliases[0] if aliases else "UNKNOWN"
        +-- dedupe_key = (name.lower(), vuln_id)
        +-- if dedupe_key in seen: continue
        +-- seen.add(dedupe_key)
        |
        +-- fix_versions = ...
        +-- description = ...
        +-- severity_value = ...
        +-- severity = ...
        +-- alias_text = ...
        +-- affected = ...
        +-- recommendation = ...
        +-- metadata = ...
        |
        +-- findings.append(
              Finding(...)
            )
```

不存在从 `skip_reason` 到本段 Finding 路径的额外 `continue`/`return`；本步骤只记录该事实，不判断未来应如何处理。

## 9. 未进入未来修复或统计语义的内容

### CURRENT_CONTROL_FLOW_FACT

本步骤只确认当前代码“会不会”到达 `Finding(...)` / `findings.append(...)`。

本步骤**没有**：

- 判断 `skip_reason` 未来是否应阻止 Finding；
- 修改 Finding 生成条件；
- 修改 Finding 保存、删除或去重行为；
- 修改去重策略；
- 设计 skipped/audited/total 统计模型；
- 设计新的 metadata；
- 调查 Service。

上述内容属于后续独立步骤。

## 10. CONFIRMED

```text
CONFIRMED: vulns 从 :232 dependency.get("vulns") 读取。
CONFIRMED: 非 list vulns 在 :233-234 continue。
CONFIRMED: 空 vulns list 不产生内层 vuln 迭代。
CONFIRMED: 内层循环在 :235，对象为 vuln。
CONFIRMED: 非 dict vuln 在 :236-237 continue。
CONFIRMED: vuln 字段读取范围包括 id/aliases/fix_versions/description/severity/cvss/cvss_score/affected_versions。
CONFIRMED: vuln_id 为空时使用 aliases[0] 或 "UNKNOWN"。
CONFIRMED: dedupe_key 为 (name.lower(), vuln_id)，构造于 :246。
CONFIRMED: 重复时 :247-248 continue，不构造 Finding。
CONFIRMED: Finding 构造位于 :294-310，直接作为 findings.append 的参数。
CONFIRMED: Finding 构造到 append 之间没有额外条件。
CONFIRMED: append 后没有删除该 Finding 的代码。
CONFIRMED: 不存在基于 name/version/vuln_id/aliases/fix_versions/description/severity/affected_versions 为空的显式过滤分支。
```

## 11. UNKNOWN

```text
UNKNOWN: 未运行真实 pip-audit，未观察真实 vulns/vuln 的实际字段分布。
UNKNOWN: 未验证真实输出中是否存在本步骤未列出的异常记录形态。
UNKNOWN: 未判断当前去重策略在未来业务上是否正确。
```

## 12. SHA-256 基线对比

Step 1.1 基线：

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.5 结束时只读复核：

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
FINDING_BEHAVIOR_MODIFIED = NO
FINDING_FILTER_ADDED = NO
DEDUPE_POLICY_MODIFIED = NO
STATISTICS_MODEL_DESIGNED = NO
SERVICE_INVESTIGATED = NO
JSON_FEATURE_DEVELOPMENT = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_5_FINDING_CONTROL_FLOW_FACTS.md
```

未执行 Git 写操作，未修改 Scanner、测试、数据库或 Schema。

## 14. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

完成本报告后立即停止，不进入 Step 1.6。
