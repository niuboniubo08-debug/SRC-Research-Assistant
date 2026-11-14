# Phase 6 Stage 1B-5B — Step 1.1 调查基线

## 1. Step 1.1 范围

本步骤只建立后续 Scanner 调查所需的三项基线：

1. 当前工作区文件基线；
2. 调查文件范围；
3. 证据来源及优先级。

本步骤不分析 Scanner 业务逻辑、JSON、统计字段、Finding 控制流或 `skip_reason` 行为。

## 2. 调查文件存在性

| 文件 | 是否存在 |
|---|---|
| `scanners/pip_audit_scanner.py` | YES |
| `tests/test_pip_audit_scanner.py` | YES |
| `docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md` | YES |
| `docs/PHASE6_STAGE1B5A_CORRECTION.md` | YES |
| `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` | YES |

五项调查文件全部存在。

## 3. 文件大小

| 文件 | 字节数 |
|---|---:|
| `scanners/pip_audit_scanner.py` | 12,660 |
| `tests/test_pip_audit_scanner.py` | 10,952 |
| `docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md` | 20,583 |
| `docs/PHASE6_STAGE1B5A_CORRECTION.md` | 19,049 |
| `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` | 7,949 |

## 4. SHA-256

| 文件 | SHA-256 |
|---|---|
| `scanners/pip_audit_scanner.py` | `F8A451B192F22ABD5969C3956DB51A300499330D41F63E9DB8561693C6B6D5CA` |
| `tests/test_pip_audit_scanner.py` | `B40EEBC86832F31599437FB73CA41F613F52FB956B64833D1ABEA2C6B175471A` |
| `docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md` | `57246C2B1CF9C45F5DEC571DDC388C864D6167A5168BEC26F11C0EAF00A29C8D` |
| `docs/PHASE6_STAGE1B5A_CORRECTION.md` | `C02E7D226B28D3062DD9DCB5E468BA687098E9599793FF90E0F823C3DEB9A1D9` |
| `docs/PHASE6_STAGE1B5A_CORRECTION_R1.md` | `88902C729FAD1C5E1E60E721C8944AEAF344FC127B535E877E7CAC832898C4EF` |

以上值为本次 Step 1.1 开始时的只读计算结果。

## 5. 证据优先级

后续 Scanner 调查必须按以下顺序使用证据：

### 第一优先级

```text
scanners/pip_audit_scanner.py
```

当前真实生产源码。任何与当前源码冲突的推断不得直接作为当前实现事实。

### 第二优先级

```text
tests/test_pip_audit_scanner.py
```

当前 Scanner 测试。测试可证明项目期望和边界，但不能替代当前生产源码。

### 第三优先级

```text
docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
docs/PHASE6_STAGE1B5A_CORRECTION.md
docs/PHASE6_STAGE1B5A_CORRECTION_R1.md
```

已批准的 RC-01 调查和修正记录。用于理解已批准契约，但不得覆盖当前源码或当前测试事实。

### 冲突处理

如果后续发现三者冲突：

```text
SOURCE_OR_CONTRACT_CONFLICT
```

必须记录冲突并停止，不得自行修改代码、测试或契约。

## 6. Git 基线

### `git status --short --untracked-files=all`

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
?? docs/PHASE6_STAGE1B4B_SKIPPED_BOOL_TEST_CORRECTION.md
?? docs/PHASE6_STAGE1B4C_RC01_SERVICE_PARAMETRIZED_TEST.md
?? docs/PHASE6_STAGE1B5A_CORRECTION.md
?? docs/PHASE6_STAGE1B5A_CORRECTION_R1.md
?? docs/PHASE6_STAGE1B5A_RC01_PRODUCTION_FIX_SCOPE_INVESTIGATION.md
```

### `git diff --cached --name-only`

```text
（空）
```

暂存区为空。

本步骤未暂存、提交、重置、恢复或清理任何文件。

## 7. 边界遵守确认

```text
READ_ONLY = YES
SCANNER_BUSINESS_LOGIC_ANALYZED = NO
JSON_ANALYZED = NO
STATISTICS_FIELDS_ANALYZED = NO
FINDING_CONTROL_FLOW_ANALYZED = NO
SKIP_REASON_ANALYZED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
PYTEST_RUN = NO
PIP_AUDIT_RUN = NO
GUI_RUN = NO
GIT_WRITE = NO
```

本步骤唯一新增文件为：

```text
docs/PHASE6_STAGE1B5B_STEP1_1_INVESTIGATION_BASELINE.md
```

## 8. 下一步

```text
NEXT_STEP = HUMAN_REVIEW_REQUIRED
```

本步骤完成后立即停止，不进入 Step 1.2。
