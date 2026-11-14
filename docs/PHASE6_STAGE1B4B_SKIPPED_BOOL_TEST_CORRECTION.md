# Phase 6 Stage 1B-4B — skipped-bool 测试输入修正

## 1. 修改范围

本次任务只修改：

```text
tests/test_dependency_audit_service.py
```

修改对象是 `test_invalid_dependency_statistics_fail_closed` 参数化列表中的 `skipped-bool` 参数。

未修改：

- 生产代码；
- 其他测试用例；
- 测试函数签名、测试体和断言；
- `tests/test_pip_audit_scanner.py`；
- `tests/test_ui_dependency_audit.py`；
- 数据库、Schema、README、Manifest、历史归档和其他文档。

## 2. 修改前后精确内容

### 修改前

```python
        pytest.param(
            {
                "audited_dependencies": 0,
                "skipped_dependencies": True,
                "total_dependencies": 1,
            },
            id="skipped-bool",
        ),
```

### 修改后

```python
        pytest.param(
            {
                "audited_dependencies": 1,
                "skipped_dependencies": True,
                "total_dependencies": 2,
            },
            id="skipped-bool",
        ),
```

### 逐行 diff

```diff
         pytest.param(
             {
-                "audited_dependencies": 0,
+                "audited_dependencies": 1,
                 "skipped_dependencies": True,
-                "total_dependencies": 1,
+                "total_dependencies": 2,
             },
             id="skipped-bool",
         ),
```

`id="skipped-bool"` 保持不变。

## 3. 修改理由

原输入：

```text
audited_dependencies=0
skipped_dependencies=True
total_dependencies=1
```

旧 Service 在 `audited_dependencies == 0` 时本来就会失败，因此这个用例无法独立证明 `skipped_dependencies=True` 被严格类型校验拒绝。

新输入：

```text
audited_dependencies=1
skipped_dependencies=True
total_dependencies=2
```

`audited_dependencies` 是有效正数，`total_dependencies` 与非 skipped 数量表面一致；如果代码没有检查 `skipped_dependencies` 的 bool 类型，就可能通过旧逻辑。因此该用例现在针对 `skipped_dependencies=True` 的严格类型校验。

## 4. 其他参数化用例保持完整

修改后参数 ID 顺序：

```text
audited-none
audited-string
audited-negative
total-zero
skipped-negative
audited-bool
skipped-bool
total-bool
```

共 8 个参数，原有 8 个 ID 全部保留。

其他 7 个参数的内容未修改：

```text
audited-none      audited=None,   skipped=0,  total=1
audited-string    audited="2",    skipped=0,  total=2
audited-negative  audited=-1,     skipped=2,  total=1
total-zero        audited=1,      skipped=0,  total=0
skipped-negative  audited=2,      skipped=-1, total=2
audited-bool      audited=True,   skipped=0,  total=1
total-bool        audited=1,      skipped=0,  total=True
```

`test_invalid_dependency_statistics_fail_closed` 的函数体、参数签名和三条断言均未修改：

```python
assert outcome.task.status is ScanTaskStatus.FAILED
assert outcome.success is False
assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")
```

## 5. 文件校验

### 修改前

```text
tests/test_dependency_audit_service.py
BYTES=21,410
LINES=569
SHA-256=278E89B800FC1C6EBB43005AF163226F18E93EA2F6698E108DB25AC2C10211C4
```

### 修改后

```text
tests/test_dependency_audit_service.py
BYTES=21,410
LINES=569
SHA-256=BF95CC48EBC0D2D86504B9A3588091B5145E01470BD8641FC4D1FC7C94352389
```

字节数和行数不变，因为只替换了两个数字字符；内容哈希已变化。

### 静态语法检查

```text
AST_OK=1
```

说明：只执行了 Python `ast.parse` 静态解析，没有运行 pytest，也没有导入或执行业务逻辑。

## 6. 其他测试文件

本次任务未修改：

```text
tests/test_pip_audit_scanner.py
tests/test_ui_dependency_audit.py
```

它们仍保持 Stage 1B-3B/R1 后的工作区状态，Git 中继续显示为 `M`，但本次没有写入这两个文件。

## 7. Git 状态

执行：

```text
git status --short --untracked-files=all
```

实际输出：

```text
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
 M tests/test_dependency_audit_service.py
 M tests/test_pip_audit_scanner.py
 M tests/test_ui_dependency_audit.py
?? docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md
?? docs/PHASE6_D1B_3_JSON_DECISION.md
?? docs/PHASE6_R0_A_HISTORICAL_INVENTORY.md
?? docs/PHASE6_R0_B1_REPORT_CENTER_CODE_AUDIT.md
?? docs/PHASE6_R0_B2_SCANNER_FINDING_EVIDENCE_AUDIT.md
?? docs/PHASE6_R0_B3_DATABASE_TESTS_DOCS_AUDIT.md
?? docs/PHASE6_R0_C_ENGINEERING_DEBT_AND_ROADMAP.md
?? docs/PHASE6_STAGE1A_PIP_AUDIT_TRUTH_INVESTIGATION.md
?? docs/PHASE6_STAGE1B1_RC01_SEMANTICS_AND_TEST_CONTRACT_DESIGN.md
?? docs/PHASE6_STAGE1B2A_RC01_TEST_SCOPE_INVESTIGATION.md
?? docs/PHASE6_STAGE1B2B_RC01_DATA_INTERFACE_DESIGN.md
?? docs/PHASE6_STAGE1B2C_RC01_STATISTICS_CONTRACT.md
?? docs/PHASE6_STAGE1B3A_RC01_TEST_IMPLEMENTATION_PLAN.md
?? docs/PHASE6_STAGE1B3B_RC01_TEST_IMPLEMENTATION.md
?? docs/PHASE6_STAGE1B4A_RC01_TARGETED_TEST_EXECUTION.md
```

暂存区：

```text
git diff --cached --name-only
```

输出为空，未暂存任何文件。

保护文件：

```text
M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
```

仍保持原有未暂存状态，本次未处理。

所有既有未跟踪报告均保留，未删除、覆盖或移动。

## 8. 执行边界确认

```text
PRODUCTION_CODE_MODIFIED = NO
OTHER_TEST_FILES_MODIFIED = NO
TEST_FUNCTION_MODIFIED = NO
TEST_ASSERTIONS_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
DOCS_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GUI_TEST_RUN = NO
GIT_ADD_COMMIT_PUSH = NO
GIT_RESET_RESTORE_CLEAN = NO
```

本次没有运行任何测试，没有运行 pip-audit，没有启动 GUI，没有修改数据库或 Schema，没有执行 Git 变更。

## 9. 当前状态

```text
STAGE1B4B_STATUS = COMPLETED
SKIPPED_BOOL_INPUT_CORRECTED = YES
SKIPPED_BOOL_ID_RETAINED = YES
OTHER_PARAMETERS_UNCHANGED = YES
ONLY_TEST_INPUT_CHANGED = YES
```

等待人工审核，不进入下一阶段。
