# Phase 6P-2B-4：PHASE6_C2A_SECURITY_DEBT.md PDF 残留最小修订

- 日期：2026-11-12（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 本轮仅修改：`docs/PHASE6_C2A_SECURITY_DEBT.md`
- 本报告为新增文件；未暂存、未提交

```text
SECURITY_DEBT_UPDATE_STATUS = PASS
PDF_DOCUMENTATION_RESIDUE = RESOLVED
JSON_DECISION_SPACE = PRESERVED
P2B_5_READINESS = GO
```

---

## 1. 修改前确认

### Git 状态

修改前：

```text
 M README.md
 M reports/__init__.py
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
```

- `git diff -- docs/PHASE6_C2A_SECURITY_DEBT.md` 为空；
- `git diff --cached -- docs/PHASE6_C2A_SECURITY_DEBT.md` 为空；
- 修改前 SHA-256：`E66EE52DB36D951001365A77E818A8167AD33EF28EEE86618121442A51858626`
- 修改前大小：33,689 字节

### 实际相关文本

文件第 10.5 节“尚缺少的验证/决策”最后一项原文：

```text
6. 评估 PDF/JSON 导出是否沿用同一策略（C2B 之后）。
```

上下文：

- 该列表讨论报告导出中的语义脱敏策略；
- 前 5 项分别是原始证据文本、敏感类型、脱敏优先级、可复现性和用户确认；
- 第 6 项把 PDF 和 JSON 一起列为未来评估事项；
- 这已经不符合当前事实：PDF 导出已取消，JSON 是独立且未获批准的决策。

---

## 2. 修改内容

仅替换第 1 行列表项，修改为：

```text
6. PDF 导出已取消，不再作为后续评估项；JSON 报告导出是独立决策且尚未获批，不与 SubmissionDraft JSON persistence 混同。
```

修改原则：

- 删除“PDF 仍需在 C2B 之后评估”的失效表述；
- 明确 PDF 导出已取消，且不再作为后续评估项；
- 保留 JSON 报告导出的独立决策状态；
- 不把 JSON 写成已批准任务；
- 明确 `JSON_REPORT_EXPORT` 与 `SubmissionDraft JSON persistence` 不是同一事项；
- 不修改第 10 节其他安全债务内容；
- 不删除无关的隐私、XSS、路径或并发结论。

---

## 3. 修改后逻辑

```text
PDF_EXPORT = CANCELLED / OUT_OF_SCOPE
PDF_AS_FUTURE_EVALUATION = NO

JSON_REPORT_EXPORT = NOT_APPROVED / SEPARATE_DECISION
```

文件中的新表述不再要求未来评估 PDF 导出；JSON 仍保留为独立、未批准的决策空间。

---

## 4. 逻辑边界确认

```text
JSON_REPORT_EXPORT
≠
SubmissionDraft JSON persistence
```

- `JSON_REPORT_EXPORT`：报告导出格式之一，当前未实施、未获批准；
- `SubmissionDraft JSON persistence`：提交草稿的 JSON 持久化问题，属于不同数据路径；
- 本次修订没有把两者合并，也没有因为 PDF 取消而自动批准 JSON 导出。

相邻安全债务：

```text
RELATED_DEBT_ITEMS_MODIFIED = NO
UNRELATED_SECURITY_CONCLUSIONS_MODIFIED = NO
```

本次仅修改第 10.5 节的第 6 项，第 10 节其他条目保持原样。

---

## 5. Diff 审计

### `git diff --check`

```text
DIFF_CHECK = PASS
EXIT_CODE = 0
```

没有 whitespace error。Git 的 LF/CRLF 提示是 Windows 工作副本换行提示，不影响退出码。

### 实际 Diff

```diff
@@ -670,7 +670,7 @@
 3. 定义“安全证据完整性”和“隐私脱敏”的优先级；
 4. 验证遮盖后报告仍可用于复现；
 5. 验证用户确认/审计记录；
-6. 评估 PDF/JSON 导出是否沿用同一策略（C2B 之后）。
+6. PDF 导出已取消，不再作为后续评估项；JSON 报告导出是独立决策且尚未获批，不与 SubmissionDraft JSON persistence 混同。
```

### 范围确认

```text
TARGET_MODIFIED = docs/PHASE6_C2A_SECURITY_DEBT.md
README.md = PRE_EXISTING_P2B_2_MODIFICATION
reports/__init__.py = PRE_EXISTING_P2B_3_MODIFICATION
OUT_OF_SCOPE_MODIFICATIONS = NONE
```

修改后目标文件：

- 大小：33,775 字节
- SHA-256：`DF069E504A72DA6788495D359C3213347A55D2544EC9F0D1CFA7531EFAA92765`

README 保持 P2B-2 修改：

```text
README.md SHA-256 = 52894867AD6AD2B5B33F5956168003C7D4E6A8B9954F1DC0EF69BD7A6022BC35
```

`reports/__init__.py` 保持 P2B-3 修改：

```text
reports/__init__.py SHA-256 = 1A0D3D47FFEE9EE3406EE9EC28EF57EF69FB852463F4DB6EF06E3EE0EFF9B7EB
```

未覆盖、恢复、修改、暂存或删除 README、`reports/__init__.py` 或前置报告。

当前工作区状态：

```text
 M README.md
 M docs/PHASE6_C2A_SECURITY_DEBT.md
 M reports/__init__.py
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
?? docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
```

暂存区为空，没有创建 commit。

---

## 6. 最终状态

```text
SECURITY_DEBT_UPDATE_STATUS = PASS
PDF_DOCUMENTATION_RESIDUE = RESOLVED
JSON_DECISION_SPACE = PRESERVED
P2B_5_READINESS = GO
```

本步骤已停止。未运行完整 pytest，未执行 `git add`、`git commit` 或 `git push`，未进入最终验收或 Phase 6D。
