# 第五阶段最终测试报告

## 1. 测试环境

| 项目 | 值 |
|---|---|
| 项目 | `D:\挖漏洞\SRC-Research-Assistant` |
| 版本 | `0.5.0` |
| Python | 3.14.4 |
| PySide6 | 6.12.0 |
| SQLite | 3.50.4 |
| 数据库 Schema | v5 |
| Qt 平台 | offscreen |
| 收尾时间 | 2026-11-05（Asia/Shanghai） |

## 2. 开发前基线

第五阶段正式开发前的实际基线：

```text
105 passed in 24.89s
```

基线测试全部通过；本次收尾没有新增业务功能、没有修改数据库 Schema、没有删除测试。

## 3. 定向功能回归

执行命令：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest `
  tests/test_vulnerability_service.py `
  tests/test_evidence_service.py `
  tests/test_ui_phase5.py `
  tests/test_phase5_migration.py `
  -q -p no:cacheprovider
```

实际结果：

```text
21 passed, 1 skipped in 11.27s
```

覆盖：

- 三种扫描器 Finding 统一展示（测试夹具）；
- 漏洞状态修改和历史；
- 漏洞详情；
- 筛选/搜索；
- 证据多关联；
- 证据文件复制；
- SHA-256；
- 证据详情；
- Finding/Evidence 关联；
- 跨项目隔离；
- 授权项目路径检查；
- 证据删除后 Finding 保留；
- v4→v5 迁移和失败回滚。

## 4. 完整测试

严格使用指定命令：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
```

实际结果：

```text
.......................................s................................ [ 56%]
.......................................................                  [100%]
126 passed, 1 skipped in 36.25s
```

| 指标 | 数量 |
|---|---:|
| 收集 | **127** |
| Passed | **126** |
| Failed | **0** |
| Skipped | **1** |

Skipped 不计入 Passed。

跳过项：

```text
tests/test_evidence_service.py::test_symlink_to_outside_is_rejected
当前 Windows 会话无法创建文件符号链接：
WinError 1314 客户端没有所需的特权
```

这是 Windows 当前会话的权限限制，不是测试被删除、不是放宽检查，也没有把跳过项报告为通过。

## 5. 测试文件分布

| 测试文件 | 收集数 |
|---|---:|
| `test_authorization_service.py` | 8 |
| `test_bandit_scanner.py` | 7 |
| `test_database.py` | 5 |
| `test_dependency_audit_service.py` | 15 |
| `test_evidence_service.py` | 11 |
| `test_finding_models.py` | 3 |
| `test_local_path_audit.py` | 7 |
| `test_phase5_migration.py` | 2 |
| `test_pip_audit_scanner.py` | 8 |
| `test_process_runner.py` | 3 |
| `test_project_service.py` | 7 |
| `test_scan_service.py` | 13 |
| `test_scope_validator.py` | 16 |
| `test_semgrep_scanner.py` | 6 |
| `test_ui.py` | 2 |
| `test_ui_dependency_audit.py` | 1 |
| `test_ui_dialogs.py` | 3 |
| `test_ui_phase5.py` | 3 |
| `test_ui_source_audit.py` | 1 |
| `test_vulnerability_service.py` | 6 |
| **合计** | **127** |

## 6. 功能覆盖说明

### 真实执行

- 本地授权项目真实 Bandit 扫描（第五阶段验收数据）：
  - 3 条源码 Finding；
  - 任务状态 completed。
- 第四阶段真实 pip-audit 验收数据迁移到 v5：
  - 19 条依赖 Finding。
- 真实本地 PNG 证据复制和 SHA-256 校验：
  - `d049b0c128fee9f2195887c65b3b1b7acb896f9252142a8561841c0e784e8d64`。
- 真实 v4→v5 数据库迁移。
- 真实 Qt offscreen 页面加载、筛选、状态保存、跨页跳转、删除确认测试。

### 测试夹具/模拟

- 三种扫描器统一列表中的 Semgrep Finding 来自临时数据库夹具，不是真实 Semgrep 运行。
- 文件符号链接实际创建被拒绝；`Path.is_symlink` 分支由单元 monkeypatch 覆盖。
- 多数 UI 测试使用临时 SQLite 数据库和测试夹具。

### 未验证

- Semgrep 真实运行；
- 当前 Windows 环境真实文件符号链接创建；
- 报告导出、远程配置检查（本阶段未开发）。

## 7. 失败分析

本次完整测试和定向测试均为 **0 failed**。

未通过删除测试、跳过测试或降低断言的方式制造通过结果。

## 8. 结论

第五阶段测试收尾结果：

**126 passed / 0 failed / 1 skipped**

通过应用功能和 UI 回归；唯一跳过项为 Windows 当前会话无法创建文件符号链接，已如实记录。
