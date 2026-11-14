# Phase 6 Stage 1B-5B — Step 1.2 Scanner 主入口与依赖循环

## 1. 调查范围

本步骤只调查：

```text
scanners/pip_audit_scanner.py
```

只回答：

> 当前 Scanner 从哪里开始处理一次扫描，以及依赖记录在哪里逐条处理。

本步骤不分析统计字段、`skip_reason` 语义、Finding 生命周期、Service 最终状态，也不设计或修改任何 JSON 功能。

## 2. 当前 Scanner 类

真实类定义：

```text
PipAuditScanner(scanners/pip_audit_scanner.py:51)
```

继承关系：

```python
class PipAuditScanner(BaseScanner):
```

基础信息：

```text
name = "pip-audit"
display_name = "pip-audit"
supported_languages = ("python-dependencies",)
vulnerability_service = "pypi"
```

该类是 pip-audit 的适配器，不是 Service，也不负责任务状态或数据库写入。

## 3. 主扫描入口

真实主扫描方法：

```text
PipAuditScanner.scan(self, target: str | Path, options: ScanOptions)
  scanners/pip_audit_scanner.py:126
```

入口开始处：

```python
def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
    target_path = Path(target).expanduser().resolve()
    if not target_path.is_file():
        raise ScannerExecutionError("pip-audit 输入依赖文件不存在")
```

主扫描方法负责：

1. 解析并确认目标依赖文件；
2. 检查 Scanner 可用性；
3. 创建缓存/临时目录；
4. 构造 pip-audit 命令；
5. 调用 `run_command(...)`；
6. 将标准输出交给 `parse_output(...)`；
7. 将结果封装为 `ScanOutput`。

这些是控制流程事实，不是统计或业务语义分析。

## 4. pip-audit 结果处理入口

真实结果处理入口：

```text
PipAuditScanner.parse_output(
    self,
    payload_text: str,
    target: Path,
    version: str,
)
  scanners/pip_audit_scanner.py:210
```

`scan()` 在 `:194-196` 调用它：

```python
findings, warnings, audited = self.parse_output(
    result.stdout, target_path, availability.version
)
```

`parse_output()` 首先进行现有输入解析：

```python
payload = json.loads(payload_text)
...
dependencies = payload.get("dependencies", [])
```

这里的 JSON 仅是 pip-audit 的既有外部输出格式，不作为新 JSON 功能开发。

## 5. 依赖记录处理循环

真实循环位置：

```text
scanners/pip_audit_scanner.py:224
```

循环头：

```python
for dependency in dependencies:
```

单次循环处理的当前记录对象：

```text
dependency
```

循环开始处的实际结构：

```python
for dependency in dependencies:
    if not isinstance(dependency, dict):
        continue
    name = str(dependency.get("name") or "").strip()
    current_version = str(dependency.get("version") or "").strip()
    ...
    vulns = dependency.get("vulns")
    if not isinstance(vulns, list):
        continue
    for vuln in vulns:
        ...
```

本步骤只记录该控制结构：

- 最外层逐条处理 `dependencies`；
- 单条记录对象名为 `dependency`；
- 非 dict 记录直接 `continue`；
- 循环内部再读取该记录的字段和 `vulns`；
- `vulns` 为 list 时进入内层 `vuln` 循环。

不展开统计规则、`skip_reason` 语义、Finding 生命周期或 Service 状态。

## 6. 当前真实调用路径

```text
PipAuditScanner.scan()
  |
  +-- is_available()
  |
  +-- run_command(...)
  |     pip-audit -r <dependency-file> --format json ...
  |
  +-- parse_output(result.stdout, target_path, availability.version)
        |
        +-- json.loads(payload_text)
        |
        +-- dependencies = payload.get("dependencies", [])
        |
        +-- for dependency in dependencies:      # :224
              |
              +-- if not isinstance(dependency, dict): continue
              |
              +-- 读取当前 dependency 的字段
              |
              +-- vulns = dependency.get("vulns")
              |
              +-- if not isinstance(vulns, list): continue
              |
              +-- for vuln in vulns:
                    ...
```

主入口是 `scan()`；逐条处理依赖记录的位置是 `parse_output()` 的 `for dependency in dependencies` 循环。

## 7. CONFIRMED

```text
CONFIRMED: 当前 Scanner 类为 PipAuditScanner。
CONFIRMED: 主扫描入口为 PipAuditScanner.scan()，位于 :126。
CONFIRMED: scan() 在 :194-196 调用 parse_output()。
CONFIRMED: parse_output() 位于 :210。
CONFIRMED: 依赖记录处理循环位于 :224。
CONFIRMED: 单次循环对象变量为 dependency。
CONFIRMED: 循环体先处理非 dict 记录，再读取字段和 vulns。
CONFIRMED: vulns 为 list 时存在内层 vuln 循环。
CONFIRMED: 本步骤未修改 Scanner 或其测试。
```

## 8. UNKNOWN

```text
UNKNOWN: 未运行真实 pip-audit，未观察运行时 stdout 的实际内容。
UNKNOWN: 未验证真实输出中 dependency 记录的所有边界形态。
UNKNOWN: 本步骤不分析统计字段、skip_reason 语义或 Finding 生命周期。
```

这些内容属于后续独立步骤，不在 Step 1.2 展开。

## 9. SHA-256 基线对比

Step 1.1 基线：

| 文件 | Step 1.1 SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |

Step 1.2 结束时只读复核：

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

## 10. 边界遵守情况

```text
READ_ONLY = YES
JSON_FEATURE_DEVELOPMENT = NO
JSON_RELATED_FILES_OR_CODE_CLEANUP = NO
SCANNER_BUSINESS_LOGIC_CHANGED = NO
STATISTICS_FIELDS_ANALYZED = NO
SKIP_REASON_SEMANTICS_ANALYZED = NO
FINDING_LIFECYCLE_ANALYZED = NO
SERVICE_INVESTIGATED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
GIT_MUTATION = NO
```

本步骤只新增本报告：

```text
docs/PHASE6_STAGE1B5B_STEP1_2_SCANNER_ENTRY_AND_LOOP.md
```

未执行 Git 写操作，未修改其他报告或未跟踪文件。

## 11. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤完成后立即停止，不进入 Step 1.3。
