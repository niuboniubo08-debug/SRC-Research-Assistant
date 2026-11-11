# 第五阶段最终收尾总结

- 收尾时间：2026-11-05（Asia/Shanghai）
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 项目版本：`0.5.0`
- 数据库 Schema：**v5**
- 阶段结论：**收尾完成**
- 本阶段不新增业务功能，不进入第六阶段

## 1. 收尾范围

本次仅执行：

1. 项目状态与文件检查；
2. 第五阶段数据库备份和 SQLite 完整性验证；
3. 漏洞管理、证据中心、状态历史、文件哈希、项目隔离和路径检查回归；
4. 完整 pytest；
5. 最终归档目录和五个必需文件；
6. 最终收尾检查。

没有开发报告中心、远程检查、漏洞利用、网络探测、EXE 打包，也没有修改数据库 Schema。

## 2. 第五阶段功能

### 漏洞管理中心

- 汇总 Bandit、Semgrep、pip-audit Finding；
- 项目、风险、工具、状态筛选和关键词搜索；
- 六种处理状态；
- 状态时间、状态历史和人工备注；
- 漏洞详情、依赖/源码信息、原始 metadata、任务和项目；
- 项目隔离和跨项目拒绝。

### 证据中心

- 代码片段、扫描摘要、依赖信息、截图、人工备注、其他本地文件；
- 一个 Finding 多份证据；
- 证据受管复制、UUID 防覆盖、SHA-256；
- 绝对路径、项目根目录、`check_local_path`、路径遍历、符号链接/目录联接、50 MB 限制；
- 敏感信息人工确认；
- 删除证据保留源文件和 Finding；
- 证据与漏洞详情互跳。

## 3. 数据库与备份

Schema 保持 **v5**，未在本次收尾中修改。

最终数据库备份：

```text
D:\挖漏洞\SRC-Research-Assistant\storage\backups\src_research_phase5_final_20261105T061441Z.db
D:\挖漏洞\SRC-Research-Assistant\storage\backups\phase5_acceptance_final_20261105T061441Z.db
```

- 主库：147,456 字节，schema 5，`integrity_check=ok`；
- 验收库：352,256 字节，schema 5，`integrity_check=ok`；
- 验收库：41 findings / 3 evidence / 2 history；
- 外键违规：0；
- 快照目录内另有 `db/` 副本；
- 旧备份全部保留。

详细记录见 [PHASE5_DATABASE_BACKUP_INFO.md](PHASE5_DATABASE_BACKUP_INFO.md)。

## 4. 测试结果

完整命令：

```powershell
$env:QT_QPA_PLATFORM='offscreen'
& 'D:\挖漏洞\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider
```

结果：

```text
127 collected
126 passed
0 failed
1 skipped
36.25s
```

跳过项：

```text
当前 Windows 会话无法创建文件符号链接：
WinError 1314 客户端没有所需的特权
```

跳过项未被计入 passed，也没有删除测试或降低断言。

定向回归：

```text
21 passed, 1 skipped in 11.27s
```

## 5. 真实执行 / 模拟 / 未验证

### 真实执行

- 本地授权项目真实 Bandit 扫描：3 条真实源码 Finding；
- 第四阶段真实 pip-audit 数据迁移：19 条依赖 Finding；
- 真实本地 PNG 复制和 SHA-256；
- 真实 v4→v5 迁移；
- Qt offscreen 页面和交互。

### 模拟/测试夹具

- 三扫描器统一列表中的 Semgrep 行来自测试夹具；
- 符号链接 `Path.is_symlink` 分支为单元模拟；
- UI 测试使用临时数据库。

### 未验证

- Semgrep 真实运行；
- 真实文件符号链接创建；
- 报告模块和远程配置检查（未开发）。

## 6. 已知限制

1. **Semgrep**：Windows CA 存储初始化失败，待 Linux/WSL 补验；本阶段没有伪造 Semgrep 结果。
2. **符号链接**：当前 Windows 非特权会话无法创建真实文件符号链接；目录联接和路径越界已实际测试，`is_symlink` 分支为模拟单元测试。
3. 未实现跨扫描逻辑去重；“首次/最近”按每条 Finding 行时间展示。
4. 漏洞列表上限 1000，未实现分页。
5. 证据文件必须位于授权项目根目录内。
6. 本阶段未开发报告、远程检查、EXE 打包。

pip-audit 的 `severity_source`、保守 medium 和 affected range 限制没有被修改。

## 7. 归档

最终快照目录：

```text
D:\挖漏洞\SRC-Research-Assistant\docs\acceptance\phase5_final\
```

必需文件：

- `PHASE5_FINAL_SUMMARY.md`
- `PHASE5_TEST_REPORT.md`
- `PHASE5_DATABASE_BACKUP_INFO.md`
- `PHASE5_FILE_MANIFEST.txt`
- `PHASE5_ACCEPTANCE.json` — 第五阶段最终收尾验收记录。

另包含：

- `PHASE5_ACCEPTANCE_REPORT.md`
- `PHASE5_ARCHITECTURE.md`
- `phase5_acceptance_evidence.json` — 第五阶段原始验收证据数据。
- `phase5_vulnerability_management.png`
- `phase5_evidence_center.png`
- `db/` 两份数据库副本

> 注意：`phase5_acceptance.json` 是 `PHASE5_ACCEPTANCE.json` 在 Windows 大小写不敏感下的别名，不是独立归档文件；实际原始验收证据文件为 `phase5_acceptance_evidence.json`。

## 8. 结论

**收尾完成。**

依据：

- 主库和验收库均已备份；
- 备份可由 SQLite 打开，`integrity_check=ok`；
- Schema 保持 v5；
- 完整测试 126 passed / 0 failed / 1 skipped；
- 第五阶段回归通过；
- 最终归档目录和必需文件已生成；
- 旧数据和旧备份未删除；
- 未开始第六阶段。

第五阶段到此停止，等待用户确认。
