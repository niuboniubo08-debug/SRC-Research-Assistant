# 第五阶段测试报告：漏洞管理与证据中心

## 1. 执行信息

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-11-05（Asia/Shanghai） |
| 项目 | `D:\挖漏洞\SRC-Research-Assistant` |
| Python | 3.14.4 |
| PySide6 | 6.12.0 |
| SQLite | 3.50.4 |
| schema | v5 |
| 测试命令 | `python -m pytest -q -p no:cacheprovider` |
| **最终结果** | **126 passed / 0 failed / 1 skipped** |
| 收集数 | 127 |
| 耗时 | 38.61 s |
| 真实远程目标 | 0 个 |

## 2. 开发前基线

```text
105 passed in 24.89s
```

基线状态：

- schema v4；
- 已有统一 `Finding`、`ScanTask`、项目隔离和本地路径校验；
- `evidence` 表存在但只有旧字段；
- `findings.status` CHECK 不允许 `reviewing`；
- 漏洞管理、证据中心仍是占位页；
- 没有 Repository 层。

## 3. 测试结果

```text
.......................................s................................ [ 56%]
.......................................................                  [100%]
126 passed, 1 skipped in 38.61s
```

| 测试文件 | 收集数 | 主要覆盖 |
|---|---:|---|
| `test_vulnerability_service.py` | 6 | 三扫描器统一读取、筛选、状态历史、备注、详情、项目隔离 |
| `test_evidence_service.py` | 11 | 多证据、文件复制/哈希、同名文件、路径越界、目录联接、符号链接分支、项目校验、删除后 Finding 保留 |
| `test_phase5_migration.py` | 2 | v4→v5 数据保留、v5 部分失败回滚、备份恢复 |
| `test_ui_phase5.py` | 3 | 漏洞/证据页面加载、筛选、状态保存、跨页跳转、删除、证据对话框 |
| `test_database.py` | 5 | v5 表/字段、v2→v5 迁移、外键 |
| 既有回归文件 | 100 | 项目/授权/范围/扫描器/依赖/既有 UI |
| **合计** | **127** | **126 passed + 1 skipped** |

## 4. 需求覆盖

| 要求 | 结果 |
|---|---|
| 三种扫描器 Finding 统一展示 | PASS（单元/UI 夹具） |
| 原始扫描器字段不错误混合 | PASS（保留 scanner/rule/metadata/file） |
| 六种处理状态 | PASS |
| 状态持久化 | PASS |
| 状态变更时间 | PASS（`status_changed_at`） |
| 状态变更历史 | PASS（`finding_status_history`，2 条真实验收变更） |
| 人工备注 | PASS |
| 项目隔离 | PASS（跨项目 read/write 抛 NotFound） |
| 详情完整性 | PASS |
| 多证据关联一个 Finding | PASS |
| 证据关联项目校验 | PASS |
| 文件路径越界拒绝 | PASS（实际 `..` 路径） |
| 实际目录联接越界拒绝 | PASS（Windows junction） |
| 文件符号链接拒绝 | **1 skipped**（当前会话无 `SeCreateSymbolicLinkPrivilege`，`WinError 1314`） |
| `is_symlink` 显式分支 | PASS（单元模拟） |
| SHA-256 | PASS（实际本地截图，哈希一致） |
| 证据删除后 Finding 保留 | PASS |
| 数据库迁移与备份 | PASS |
| UI 页面加载 | PASS |
| 搜索和筛选 | PASS（风险/扫描器/状态/关键词） |
| 既有功能回归 | PASS |

## 5. 真实、模拟与单元测试的区分

### 真实执行

- 真实 Bandit 1.9.4 在本地授权测试项目执行，新增 3 条源码 Finding；
- 第四阶段真实 pip-audit 验收库迁移到 v5，保留 19 条 pip-audit Finding（本项目）；
- 真实本地 PNG 截图通过 EvidenceService 复制到 `storage/evidence/project_1/`；
- 真实 SHA-256：
  `d049b0c128fee9f2195887c65b3b1b7acb896f9252142a8561841c0e784e8d64`；
- 实际 v4→v5 迁移和主库迁移；
- 实际 Qt offscreen 页面加载、筛选、状态保存、跨页跳转和删除。

### 测试夹具/模拟

- `test_vulnerability_service.py` 用临时数据库插入 Bandit/Semgrep/pip-audit 三条确定性 Finding，用于验证统一读取；不是真实扫描。
- `test_ui_phase5.py` 使用同一组临时夹具加载页面，用于验证 UI；不是真实扫描。
- 文件符号链接实际创建失败；仅有 `is_symlink` 分支的单元模拟。
- 目录联接（junction）是实际 Windows reparse-point 测试。

### 未声称真实执行

- Semgrep 实际运行：当前 Windows 会话仍不可用，没有伪造 Semgrep 结果。
- 远程扫描、报告生成：本阶段不在范围，未执行。

## 6. 验收中发现并修复的问题

1. v4 `findings.status` CHECK 不含 `reviewing`；采用事务内重建表并保留全部行。
2. v5 重建期间 `evidence.finding_id` 外键指向 findings；迁移使用 `foreign_keys=OFF` + 单一事务，失败回滚。
3. 证据页面列表线程的 `finished` 信号使用页面当前 worker，旧线程完成后误删新线程，触发 `QThread: Destroyed while thread is still running`；改为绑定具体 worker 实例。
4. 关闭页面时 pending refresh 的 QTimer 可能在 shutdown 后启动新线程；增加 `_shutting_down` 和 timer 停止。
5. 证据对话框固定 Finding 时没有 populate finding combo；修复。
6. 初始列宽造成工具/状态/哈希截断；调整固定列和伸缩列。
7. 文件符号链接创建被系统权限拒绝，记录 skip，未伪造成功。

最终失败：0。

## 7. 代码质量

最终 `tools/code_quality_check.py`：

```text
EMPTY_FUNCTIONS=0
PASS_STATEMENTS=19 (14 ExceptHandler + 5 exception classes, OUTSIDE=0)
TODO=0
UI_SCANNER_IMPORTS=0
UI_SQL_STATEMENTS=0
SUSPICIOUS_CONFIRMED_ALLOW=0
```

（最终数字以 `docs/acceptance/code_quality.json` 为准。）

## 8. 限制

- 文件符号链接实际创建受当前 Windows 权限限制；目录联接和路径越界实际验证，符号链接分支为模拟单元测试。
- Semgrep 真实运行仍待 Linux/WSL 验证。
- 未实现 Finding 跨扫描去重；首次/最近发现按每条 Finding 的行时间展示。
- UI 列表上限 1000 条；更大量数据需要分页，但查询在线程中执行，不阻塞 UI。
- Evidence 文件必须在项目授权根目录内，项目外截图需用户先复制进项目。
