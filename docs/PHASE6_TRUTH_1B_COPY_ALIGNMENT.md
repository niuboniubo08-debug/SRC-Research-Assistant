# Phase 6-TRUTH-1B 最小范围产品文案真实性修正

## 1. 修改目的

根据已审核的 Phase 6-TRUTH-1A 结论，只修正 `README.md` 与 `ui/settings_page.py` 中与实际已实现 HTML 报告中心不一致的当前产品文案：

- HTML 报告中心已实现；
- PDF 报告导出已取消；
- JSON 报告导出未实施且未获批；
- 不进入 JSON、PDF、报告历史或任何新功能开发。

本轮不修改版本号、业务代码、报告 exporter、模板、Service、Repository、数据库或 Schema。

## 2. 实际修改文件

### 实施文件

```text
README.md
ui/settings_page.py
```

### 新增报告

```text
docs/PHASE6_TRUTH_1B_COPY_ALIGNMENT.md
```

未修改其他生产代码、测试、数据库、Schema、报告 exporter、模板、历史验收文档或 Git 暂存区。

## 3. 每处修改说明

### README.md:3

将当前版本概述从“只完成第一至第五阶段”修正为同时反映第六阶段已实现的 HTML 报告中心。

修改前：

```text
面向合法授权软件安全研究的 Windows 桌面工作台。当前版本 `0.5.0` 完成**第一阶段基础框架、第二阶段项目管理/授权控制、第三阶段本地 Python 源代码审计、第四阶段 Python 依赖漏洞审计、第五阶段漏洞管理与证据中心**。
```

修改后：

```text
面向合法授权软件安全研究的 Windows 桌面工作台。当前版本 `0.5.0` 完成**第一阶段基础框架、第二阶段项目管理/授权控制、第三阶段本地 Python 源代码审计、第四阶段 Python 依赖漏洞审计、第五阶段漏洞管理与证据中心**，并已加入**第六阶段 HTML 报告中心（本地导出）**。
```

版本号 `0.5.0` 未修改。

### README.md:18

将“当前交付不包含第六阶段”修正为准确区分 HTML、PDF、JSON 状态。

修改前：

```text
当前交付包含第一至第五阶段，不包含第六阶段。
```

修改后：

```text
当前交付包含第一至第五阶段，以及第六阶段已实现的 HTML 报告中心（本地导出）；PDF 报告导出已取消，JSON 报告导出未实施且未获批准。
```

### README.md:43

将报告中心从“未开发占位页”修正为 HTML 报告中心已实现；安全配置检查仍是唯一未开发占位页。

修改前：

```text
源代码审计、依赖漏洞检查、漏洞管理、证据中心已实现；其余 2 个未进入本阶段的功能页（安全配置检查、报告中心）显示明确“未开发”占位状态和计划功能，不伪造结果。
```

修改后：

```text
源代码审计、依赖漏洞检查、漏洞管理、证据中心、报告中心（HTML 报告）已实现；安全配置检查仍显示明确“未开发”占位状态和计划功能，不伪造结果。
```

### ui/settings_page.py:84-86

只调整 `_information_card("本阶段说明", ...)` 的文案行，不修改页面结构、布局或业务行为。

修改前：

```python
("完成", "项目 / 授权 / 资产 / 源码审计 / 依赖审计 / 漏洞与证据管理"),
("未开发", "远程配置检查 / 报告导出"),
```

修改后：

```python
("完成", "项目 / 授权 / 资产 / 源码审计 / 依赖审计 / 漏洞与证据管理 / HTML 报告中心"),
("报告能力", "HTML 报告中心已实现；PDF 已取消；JSON 未实施且未批准"),
("未开发", "远程配置检查"),
```

## 4. 未修改的明确范围

以下内容保持不变：

- `README.md:5`：第五阶段历史范围说明，未修改；
- `README.md:34`：`126 passed / 1 skipped` 测试基线过期项，未修改；
- `README.md:160-162` 与 `README.md:339`：已正确描述 HTML/PDF/JSON 状态的章节，未修改；
- `core/models/report.py`
- `repositories/report_repository.py`
- `services/report_service.py`
- `reports/html_exporter.py`
- `reports/templates/*`
- `reports/__init__.py`
- `ui/report_page.py`
- `ui/main_window.py`
- `app/bootstrap.py`
- `database/*`
- `tests/*`
- `docs/acceptance/*`
- 其他 `docs/PHASE6_*.md`
- 任何历史验收报告
- Git 暂存区、提交、远端和分支状态

本轮没有实现 JSON、PDF、报告历史或证据图片功能。

## 5. 最小验证结果

### 文件范围

实际实施修改恰好为：

```text
README.md
ui/settings_page.py
```

新增文件仅为：

```text
docs/PHASE6_TRUTH_1B_COPY_ALIGNMENT.md
```

### README 检查

```text
README_H2_COUNT=11
README_LINE3_UPDATED=YES
README_LINE18_UPDATED=YES
README_LINE43_UPDATED=YES
README_LINE5_UNCHANGED=YES
README_LINE34_UNCHANGED=YES
```

Git diff 仅包含上述 3 处 README 文案变化，没有结构或无关内容变化。

### SettingsPage 检查

```text
SETTINGS_AST=OK
SETTINGS_COMPLETED_HAS_HTML=YES
SETTINGS_REPORT_CAPABILITY_ROW=YES
SETTINGS_UNBUILT_REPORT_REMOVED=YES
SETTINGS_UNBUILT_REMOTE_CONFIG_PRESERVED=YES
SETTINGS_STRUCTURE_CHANGED=NO
SETTINGS_BUSINESS_BEHAVIOR_CHANGED=NO
```

`ui/settings_page.py` 通过 `ast.parse()` 语法检查；修改仅为信息卡中的元组文案行，没有导入、类、布局或事件逻辑变更。

### 文件哈希

```text
README.md before:
  20,151 bytes
  SHA-256 3013F104E1E826F73ADB0261874664777CCB1B0F421DA36A736F8CE0C024961F
README.md after:
  20,307 bytes
  SHA-256 DE4066C16E2E01844935A820052DE2314D8EF3DC8344498DC638CBFAD1CFD449

ui/settings_page.py before:
  4,564 bytes
  SHA-256 377EBCA2910BD7918332571F82B7D5B92B86B67464B192BB3CAD5384CE44D989
ui/settings_page.py after:
  4,682 bytes
  SHA-256 DC36095A348CFDDF43A2D8E35B4B37B7A44A7ECF954B53E5C5321B3376CCD202
```

### Diff 统计

```text
README.md           | 6 +++---
ui/settings_page.py | 5 +++--
2 files changed, 6 insertions(+), 5 deletions(-)
```

### 未运行的验证

本轮没有运行完整或定向 pytest，没有启动 GUI，没有修改或读取业务数据库；这些不属于最小文案验证范围。

## 6. Git 状态

```text
BRANCH=main
HEAD=9ca064e
STAGED_COUNT=0
GIT_ADD=NO
GIT_COMMIT=NO
GIT_PUSH=NO
GIT_RESET=NO
GIT_RESTORE=NO
GIT_CLEAN=NO
GIT_MUTATION=NO
```

当前工作区还包含本轮开始前已存在的其他变更：

```text
 M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
?? docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md
```

这两项不是本任务修改的内容，本轮未触碰。

## 7. 最终 Diff 范围

```text
M README.md
M ui/settings_page.py
?? docs/PHASE6_TRUTH_1B_COPY_ALIGNMENT.md (本轮报告)
```

本轮实施修改文件数为 2，新增报告数为 1；没有暂存、提交、推送或 Git 历史变更。

## 最终状态

```text
PHASE6_TRUTH_1B_STATUS = PASS
UNEXPECTED_FILE_CHANGES = NO
GIT_MUTATION = NO
IMPLEMENTATION_FILES_CHANGED = 2
REPORT_FILES_CREATED = 1
PDF_IMPLEMENTED = NO
JSON_IMPLEMENTED = NO
REPORT_HISTORY_IMPLEMENTED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
TESTS_MODIFIED = NO
HISTORICAL_ACCEPTANCE_MODIFIED = NO
```
