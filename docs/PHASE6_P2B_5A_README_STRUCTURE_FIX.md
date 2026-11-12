# Phase 6P-2B-5A：README.md 项目结构注释残留修复

- 日期：2026-11-12（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 本轮仅修改：`README.md` 的 `reports/` 结构注释
- 本报告为新增文件；未暂存、未提交

```text
P2B_5A_STATUS = PASS
README_STRUCTURE_FIX = PASS
README_STRUCTURE_CONFLICT = RESOLVED
P2B_5B_READINESS = GO
```

---

## 1. 修改前问题

P2B-5 发现 `README.md:293`：

```text
├── reports/                # 后续报告边界（未启用）
```

该表述与以下事实冲突：

- `README.md:162` 明确“HTML 报告已实现（Phase 6C-2B）”；
- `reports/__init__.py` 明确 `HTML report export is implemented`；
- `reports/html_exporter.py` 已存在；
- `reports/templates/` 已存在；
- Phase 6C-2B 已实际接入 GUI。

因此该行是当前项目结构中的失效注释，不是历史事实，也不是 PDF 兼容元数据说明。

---

## 2. 实际最小修改

```text
OLD_TEXT:
├── reports/                # 后续报告边界（未启用）

NEW_TEXT:
├── reports/                # HTML 报告导出
```

只修改了这一行，保留原有目录树缩进、前缀和列对齐，没有重写项目结构章节。

---

## 3. 修改后逻辑

```text
REPORTS_DIRECTORY_STATUS = ACTIVE_FOR_HTML_EXPORT
HTML_REPORT = IMPLEMENTED
```

该目录现在明确用于已实现的 HTML 报告导出。

同时确认：

```text
PDF_REPORT_EXPORT = NOT_IMPLIED_AS_IMPLEMENTED
JSON_REPORT_EXPORT = NOT_IMPLIED_AS_IMPLEMENTED
```

- 新注释没有声称 PDF 导出已实现；
- 新注释没有声称 JSON 导出已实现；
- PDF 仍为 cancelled / out of scope；
- JSON 仍为 not implemented / not approved。

README 中不存在以下残留表述指向 `reports/`：

```text
未启用
未来功能
后续报告边界
```

---

## 4. Diff 审计

### `git diff --check`

```text
DIFF_CHECK = PASS
EXIT_CODE = 0
```

没有 whitespace error。Git 的 LF/CRLF 提示属于 Windows 工作副本换行提示，不影响退出码。

### 本步骤目标 Diff

```diff
@@ -289,7 +290,7 @@
 ├── repositories/           # 第五阶段漏洞与证据 SQL Repository
 ├── ui/                     # 主窗口、主题、10 个页面
 ├── scanners/               # 统一接口、Bandit、Semgrep、pip-audit、本地规则
-├── reports/                # 后续报告边界（未启用）
+├── reports/                # HTML 报告导出
 ├── storage/                # 主库、第三/四/五阶段验收库、证据、日志
 ├── tests/                  # pytest 测试
 ├── tools/                  # 验收、截图、扫描、备份工具
```

### 范围确认

```text
TARGET_MODIFIED_BY_THIS_STEP = README.md (one structure comment)
PRE_EXISTING_MODIFICATIONS = PRESERVED
OUT_OF_SCOPE_MODIFICATIONS_BY_THIS_STEP = NONE
```

前置修改保持：

- `README.md` 的 P2B-2 报告能力状态与历史澄清；
- `reports/__init__.py` 的 P2B-3 docstring；
- `docs/PHASE6_C2A_SECURITY_DEBT.md` 的 P2B-4 PDF/JSON 表述；
- P2B-1 至 P2B-5 的未跟踪报告。

修改后 README：

```text
大小      20,151 字节
SHA-256   3013F104E1E826F73ADB0261874664777CCB1B0F421DA36A736F8CE0C024961F
```

`reports/__init__.py` 和 `docs/PHASE6_C2A_SECURITY_DEBT.md` 未修改，哈希与 P2B-5 审计时一致。

当前工作区：

```text
 M README.md
 M docs/PHASE6_C2A_SECURITY_DEBT.md
 M reports/__init__.py
?? docs/PHASE6_P2B_1_PREMODIFICATION_VERIFICATION.md
?? docs/PHASE6_P2B_2_README_UPDATE.md
?? docs/PHASE6_P2B_3_REPORTS_INIT_UPDATE.md
?? docs/PHASE6_P2B_4_SECURITY_DEBT_UPDATE.md
?? docs/PHASE6_P2B_5_CONSISTENCY_AUDIT.md
?? docs/PHASE6_P2B_5A_README_STRUCTURE_FIX.md
```

暂存区为空，没有 commit。

---

## 5. 最终状态

```text
P2B_5A_STATUS = PASS
README_STRUCTURE_CONFLICT = RESOLVED
P2B_5B_READINESS = GO
```

本步骤已停止。未重新执行完整 P2B-5，未运行完整 pytest，未执行 `git add`、`git commit` 或 `git push`，未进入最终验收或 Phase 6D。
