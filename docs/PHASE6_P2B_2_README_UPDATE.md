# Phase 6P-2B-2：README.md 最小文档修订

- 日期：2026-11-12（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 本轮仅修改：`README.md`
- 本报告为新增文件；未暂存、未提交

```text
README_UPDATE_STATUS = PASS
README_LOGIC_CONSISTENCY = PASS
OUT_OF_SCOPE_MODIFICATIONS = NONE
DIFF_CHECK = PASS
```

---

## 1. 修改前问题

`README.md` 有两处与当前报告能力状态不一致：

1. “本阶段明确未实现”把 `HTML / PDF / JSON 报告` 一起列为未实现；
2. “下一阶段建议”仍要求实现 `HTML/PDF/JSON 报告`。

此外，第 339 行“第五阶段在此停止，不进入报告模块”是 Phase 5 的历史边界，但单独阅读会让当前读者误以为项目现在仍没有报告模块。

实际状态是：

```text
HTML_REPORT = IMPLEMENTED
PDF_REPORT_EXPORT = CANCELLED
JSON_REPORT_EXPORT = NOT_APPROVED
```

`ReportFormat.PDF` 的兼容元数据仍然存在，但没有任何 PDF 导出器、GUI 入口或依赖；这不代表 PDF 导出可用。

---

## 2. 修改后逻辑

### 2.1 “本阶段明确未实现”

修订为：

- 从“以下功能只显示占位页”列表中删除 `HTML / PDF / JSON 报告`；
- 增加一段独立的报告能力状态说明：
  - HTML 报告已实现（Phase 6C-2B）；
  - PDF 报告导出已正式取消，不属于当前项目范围；
  - `ReportFormat.PDF` 兼容元数据仍保留，但不代表导出可用；
  - JSON 报告导出尚未实施，也未获得实施批准；
- 保留远程检测、外部漏洞导入、Windows EXE 等其他未实现项。

### 2.2 “下一阶段建议”

- 删除“实现 HTML/PDF/JSON 报告”这一已过时条目；
- 不把 HTML 或 PDF 写成未来待办；
- 不把 JSON 写成已批准的开发任务；
- 其他仍有效的建议保留，并顺序重排为 1-4。

### 2.3 三个实际状态

```text
HTML_REPORT = IMPLEMENTED
PDF_REPORT_EXPORT = CANCELLED
JSON_REPORT_EXPORT = NOT_APPROVED
```

没有写成“系统支持 PDF 导出”，也没有写成“所有 PDF 枚举和兼容层已经删除”。

---

## 3. Phase 5 历史表述的处理

原文：

```text
第五阶段在此停止，不进入报告模块；等待用户审查第五阶段验收结果。
```

修订后：

```text
第五阶段在此停止，不进入报告模块；这是 Phase 5 当时的历史状态。Phase 6 后续已实现 HTML 报告能力（PDF 导出已取消，JSON 未实施/未批准）。等待用户审查第五阶段验收结果。
```

处理原则：

- 保留“Phase 5 当时未进入报告模块”的历史事实；
- 增加最小澄清，说明当前已经有 HTML 报告能力；
- 没有删除 Phase 5 历史，也没有全面重写章节。

---

## 4. 实际 Diff 摘要

```text
README.md
```

变更范围：

1. “本阶段明确未实现”：
   - 删除 `HTML / PDF / JSON 报告` 列表项；
   - 新增报告能力状态段。
2. “下一阶段建议”：
   - 删除报告功能待办；
   - 其余建议保留并重排编号。
3. “第五阶段在此停止”：
   - 保留历史事实；
   - 增加当前 HTML 报告状态澄清。

修改前 SHA-256：

```text
4298434848DC9DFD0572B5E009C1862CA5C275028E086292901C08F87504BF69
```

修改后 SHA-256：

```text
52894867AD6AD2B5B33F5956168003C7D4E6A8B9954F1DC0EF69BD7A6022BC35
```

修改后大小：20,167 字节。

---

## 5. `git diff --check` 结果

执行：

```text
git diff --check
```

结果：

```text
DIFF_CHECK_EXIT = 0
DIFF_CHECK = PASS
```

没有 whitespace error。
Git 同时提示 README 工作副本存在 LF/CRLF 规范化提示；这是 Windows 换行提示，不是空白错误，也没有导致 `git diff --check` 失败。

---

## 6. 修改范围确认

```text
MODIFIED_TARGET = README.md ONLY
OUT_OF_SCOPE_MODIFICATIONS = NONE
```

本步骤仅修改：

```text
README.md
```

并新增：

```text
docs/PHASE6_P2B_2_README_UPDATE.md
```

没有修改：

- `reports/__init__.py`
- `docs/PHASE6_C2A_SECURITY_DEBT.md`
- Python 业务代码
- 测试
- 数据库或 Schema
- 配置
- Git remote
- Git 历史

没有执行 `git add`、`git commit` 或 `git push`；没有运行 pytest；没有进入最终验收或 Phase 6D。

当前 Git 状态预期为：

```text
 M README.md
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
```

暂存区为空，未创建 commit。
