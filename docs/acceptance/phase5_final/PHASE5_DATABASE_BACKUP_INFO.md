# 第五阶段数据库备份信息

- 生成时间：2026-11-05 14:14:41（Asia/Shanghai）
- 数据库 Schema：**v5**
- 项目版本：**0.5.0**
- 备份方式：SQLite Backup API（主库和第五阶段验收库分别创建）
- 旧备份：未删除、未覆盖

## 1. 数据库来源

| 数据库 | 绝对路径 | Schema | 核心数据 |
|---|---|---|---:|
| 主程序数据库 | `D:\挖漏洞\SRC-Research-Assistant\storage\src_research.db` | 5 | findings 0 / evidence 0 |
| 第五阶段验收数据库 | `D:\挖漏洞\SRC-Research-Assistant\storage\phase5_acceptance\acceptance.db` | 5 | findings 41 / evidence 3 / history 2 |

## 2. 主程序数据库备份

- 备份文件：`D:\挖漏洞\SRC-Research-Assistant\storage\backups\src_research_phase5_final_20261105T061441Z.db`
- 文件大小：**147,456 字节**
- 创建时间：**2026-11-05T14:14:41.225815+08:00**
- SHA-256：

```text
a2423fa7a81f95889f2211e6823b132cb1a3ae7cfc776f93246fbd6902569a1e
```

SQLite 验证：

```text
sqlite open: PASS
PRAGMA integrity_check: ok
PRAGMA user_version: 5
PRAGMA foreign_key_check: 0 violations
```

该主库当前没有 Finding/Evidence/ScanTask 数据，但 11 张核心业务表存在，备份可正常打开。

## 3. 第五阶段验收数据库备份

- 备份文件：`D:\挖漏洞\SRC-Research-Assistant\storage\backups\phase5_acceptance_final_20261105T061441Z.db`
- 文件大小：**352,256 字节**
- 创建时间：**2026-11-05T14:14:41.253921+08:00**
- SHA-256：

```text
4f12065263f91c5402a1630b5f6c48912c6a059f0e2608936be6ffeb50184259
```

SQLite 验证：

```text
sqlite open: PASS
PRAGMA integrity_check: ok
PRAGMA user_version: 5
PRAGMA foreign_key_check: 0 violations
```

核心表记录：

```text
projects=3
findings=41
evidence=3
finding_status_history=2
scan_tasks=4
```

状态分布：

```text
open=39
reviewing=1
confirmed=1
```

关联检查：

```text
evidence.project_id 与 finding.project_id 不一致: 0
孤立 evidence: 0
孤立 status history: 0
证据文件 SHA-256 与数据库记录一致: 是
```

## 4. 最终快照中的数据库副本

为便于归档，两个备份已复制到：

```text
D:\挖漏洞\SRC-Research-Assistant\docs\acceptance\phase5_final\db\
├── src_research_phase5_final_20261105T061441Z.db
└── phase5_acceptance_final_20261105T061441Z.db
```

副本验证：

| 文件 | Schema | integrity_check | 大小 | SHA-256 |
|---|---|---:|---:|---|
| `src_research_phase5_final_20261105T061441Z.db` | 5 | ok | 147,456 | `a2423fa7...2569a1e` |
| `phase5_acceptance_final_20261105T061441Z.db` | 5 | ok | 352,256 | `4f120652...50184259` |

## 5. 核心表检查

两个数据库均包含：

```text
app_settings
authorization_history
authorizations
evidence
finding_status_history
findings
projects
reports
scan_logs
scan_tasks
scope_assets
```

共 11 张表；第五阶段验收库外键违规为 0。

## 6. 旧备份保护

`backups/` 中已有的第一、二、三、四、五阶段 zip 快照均保留，未删除、未覆盖：

- `src-research-assistant_acceptance_final.zip`
- `src-research-assistant_phase2_20261104T145255Z.zip`
- `src-research-assistant_phase3_final.zip`
- `src-research-assistant_phase4_final.zip`
- `src-research-assistant_phase5_final.zip`

`storage/backups/` 中既有的 v1、v2、v3、v4 主库备份均保留。
