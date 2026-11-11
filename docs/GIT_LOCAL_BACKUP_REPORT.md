# SRC Research Assistant — Git-2B 本地完整备份报告

## 1. 结论摘要

本次在 E 盘完成了一次**本地完整备份**，并使用 SQLite Backup API 对正式数据库逐库备份。普通文件、数据库备份、清单和恢复验证均通过。

| 结论项 | 结果 |
|---|---|
| `LOCAL_BACKUP_STATUS` | **PASS_WITH_LIMITATIONS** |
| `DATABASE_BACKUP_STATUS` | **PASS** |
| `RESTORE_VALIDATION_STATUS` | **PASS** |
| `SOURCE_PROJECT_UNCHANGED` | **YES** |
| `PHYSICAL_INDEPENDENT_BACKUP` | **NO** |

说明：所有校验项通过，但备份目标 E 盘与源项目 D 盘位于**同一块物理 SSD**，因此这是本地备份，不是物理独立备份，不能抵御整块磁盘损坏。

## 2. 备份时间与目标

- 备份时间：`2026-11-10T11:14:53+08:00`（Asia/Shanghai）
- 备份目标：`E:\SRC-Research-Assistant_Backups\backup_20261110_110447`
- 清单文件：`E:\SRC-Research-Assistant_Backups\backup_20261110_110447\BACKUP_MANIFEST.json`
- 清单大小：70,281 字节
- 清单 SHA-256：`d7df2f089d270c101d3344dbf9b1795dfda3ba471acd05358b5e2b8195bc3f3c`
- 备份目录文件数：247（246 个数据文件 + 1 个清单）
- 备份目录总大小：12,952,436 字节（12,882,155 字节数据 + 70,281 字节清单）
- 目标目录在创建前不存在；未覆盖任何已有备份。

## 3. E 盘与写入验证

- E 盘存在：NTFS、Fixed、Healthy。
- 容量：31,456,227,328 字节；备份前剩余约 31,385,235,456 字节。
- 最小写入验证：在 E 盘根目录创建随机临时文件，写入固定文本，重新读取并逐字符比对通过，删除后确认不存在。
- 验证文件已清理；未写入 E 盘根目录其他内容。
- 备份目标目录随后创建，未覆盖既有内容。

## 4. 备份范围与排除规则

### 4.1 备份范围

- 项目源码、测试、配置、文档、验收材料、历史归档、证据、报告和审计日志。
- 20 个正式 `.db` 文件，逐个使用 `sqlite3.Connection.backup()` 生成备份，不以直接复制 `.db` 冒充一致性备份。
- `BACKUP_MANIFEST.json` 记录普通文件相对路径、大小、SHA-256，以及数据库的源路径、备份路径、大小、SHA-256、Schema 版本和检查结果。

### 4.2 排除规则

| 路径/规则 | 原因 | 文件数 | 字节数 |
|---|---|---:|---:|
| `pytest-of-lenovo/**` | 可再生的 pytest 临时输出 | 2,415 | 104,478,924 |
| `.pytest_cache/**` | 可再生的 pytest 缓存 | 5 | 17,803 |
| `**/__pycache__/**` | 可再生的 Python 字节码缓存 | 92 | 1,826,838 |
| `**/*.db-wal` / `*.db-shm` | SQLite 临时 sidecar；正式数据库使用 Backup API | 40 | 655,360 |
| `tmpcde5t8kh/` | 空临时目录 | 0 | 0 |

排除项合计：2,552 个文件 / 106,978,925 字节；清单中逐项记录目录、sidecar 文件路径和排除原因。

### 4.3 对上一轮 382 个“非临时文件”的澄清

上一轮 Git-2A 统计的 382 个非临时文件**仍然包含 97 个缓存文件**（`.pytest_cache` 5 个 + `__pycache__` 92 个），并非可直接复制的普通文件数。

本次重新按排除规则统计：

- 全部文件：2,798 个 / 119,861,080 字节
- 排除目录（pytest 临时 + 两类缓存）：2,512 个 / 106,323,565 字节
- 排除 sidecar：40 个 / 655,360 字节
- 普通文件：226 个 / 10,207,467 字节
- 正式数据库：20 个 / 2,674,688 字节
- 实际备份数据文件：246 个 / 12,882,155 字节

相比上一轮的 2,797 个文件，本轮多出的 1 个文件是 `docs/GIT_DATABASE_HASH_INVESTIGATION.md`（Git-1 报告）；因此本次总数为 2,798。该 Git-1 报告已包含在本次备份中。

## 5. 文件数量与大小统计

| 项目 | 数量 | 大小（字节） |
|---|---:|---:|
| 源项目全部文件 | 2,798 | 119,861,080 |
| 源项目普通文件 | 226 | 10,207,467 |
| 源项目正式数据库 | 20 | 2,674,688 |
| 源项目排除文件 | 2,552 | 106,978,925 |
| 备份普通文件 | 226 | 10,207,467 |
| 备份数据库 | 20 | 2,674,688 |
| 备份数据文件合计 | 246 | 12,882,155 |
| 备份清单 | 1 | 70,281 |
| 备份目录合计 | 247 | 12,952,436 |

## 6. 20 个数据库的实际扫描与备份结果

- 重新扫描到的正式数据库：**20 个**。
- 成功通过 SQLite Backup API 备份：**20 / 20**。
- 所有备份数据库均可重新打开；`PRAGMA integrity_check` 全部为 `ok`；`PRAGMA foreign_key_check` 全部为 0 行。
- Schema 版本覆盖 0、2、3、4、5；备份数据库的 Schema 版本和表数量与源数据库一致。
- 备份数据库 SHA-256 与源 `.db` 不要求相同：SQLite Backup API 可能重新组织页面、压缩空闲页，因此哈希不同是预期行为；一致性以完整性、Schema、表数量和记录内容为准。

| 数据库相对路径 | 源大小 | Schema | 备份完整性 | 备份 FK 行 | 备份 SHA-256 前缀 |
|---|---:|---:|---|---:|---|
| `docs\acceptance\phase5_final\db\phase5_acceptance_final_20261105T061441Z.db` | 352,256 | 5 | ok | 0 | `4f12065263f91c54` |
| `docs\acceptance\phase5_final\db\src_research_phase5_final_20261105T061441Z.db` | 147,456 | 5 | ok | 0 | `a2423fa7a81f9588` |
| `storage\src_research.db` | 147,456 | 5 | ok | 0 | `8854f6b845822507` |
| `storage\acceptance\acceptance.db` | 126,976 | 2 | ok | 0 | `17e4696ec4bcbfb6` |
| `storage\acceptance\backups\acceptance_v1_20261104T150611Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\backups\phase5_acceptance_final_20261105T061441Z.db` | 352,256 | 5 | ok | 0 | `4f12065263f91c54` |
| `storage\backups\src_research_phase5_final_20261105T061441Z.db` | 147,456 | 5 | ok | 0 | `a2423fa7a81f9588` |
| `storage\backups\src_research_v1_20261104T143150Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\backups\src_research_v2_20261105T020152Z.db` | 114,688 | 2 | ok | 0 | `2a74770dadde5b44` |
| `storage\backups\src_research_v3_20261105T024055Z.db` | 131,072 | 3 | ok | 0 | `950c61429b6f93fe` |
| `storage\backups\src_research_v4_20261105T034341Z.db` | 131,072 | 4 | ok | 0 | `6c9a506081c6772b` |
| `storage\phase3_acceptance\acceptance.db` | 151,552 | 3 | ok | 0 | `7d76e55694fe8cbe` |
| `storage\phase3_acceptance\backups\acceptance_v1_20261105T021157Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\phase3_acceptance\backups\acceptance_v2_20261105T021157Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\phase4_acceptance\acceptance.db` | 245,760 | 4 | ok | 0 | `d7e38a40fad0749c` |
| `storage\phase4_acceptance\backups\acceptance_v1_20261105T025235Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\phase4_acceptance\backups\acceptance_v2_20261105T025236Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\phase4_acceptance\backups\acceptance_v3_20261105T025236Z.db` | 4,096 | 0 | ok | 0 | `867839bc25b30558` |
| `storage\phase5_acceptance\acceptance.db` | 352,256 | 5 | ok | 0 | `4f12065263f91c54` |
| `storage\phase5_acceptance\backups\acceptance_v4_20261105T033702Z.db` | 245,760 | 4 | ok | 0 | `d7e38a40fad0749c` |

主数据库 `storage\src_research.db`：

- 源 SHA-256：`ed3156560fcfe14c88715245cda8a3a919f3ce24d108ebcec9bf81e1536e15f8`
- 备份 SHA-256：`8854f6b845822507e63ec225d9c17790a07b5c206ea30296d8c30378aa51142d`
- 源大小 / 备份大小：147,456 / 147,456 字节
- 两侧 Schema：v5；表数量：11；完整性：ok；FK 行：0

## 7. 普通文件 SHA-256 校验

- 备份普通文件：226 / 226 通过大小与 SHA-256 校验。
- 每个文件的源 SHA-256 与备份 SHA-256 一致。
- 目标目录实际数据文件集合与清单集合完全一致：无额外文件、无缺失文件。
- 清单本身 SHA-256 与 staging 中的原件一致，并已放入备份目录。
- 敏感内容（配置文件、授权附件、日志、证据、截图、报告 HTML）未在终端或报告中输出；清单只记录路径、大小和哈希。

## 8. 数据库完整性检查

- 20 个源数据库均以只读方式打开检查；未执行迁移、写入或恢复。
- 20 个备份数据库均以只读方式重新打开检查。
- 完整性检查：20 / 20 为 `ok`。
- 外键检查：20 / 20 为 0 行。
- Schema 版本与表数量：20 / 20 与源数据库一致。
- 主数据库业务表计数（源与恢复副本一致）：`projects=0`、`authorizations=0`、`scope_assets=0`、`scan_tasks=0`、`findings=0`、`evidence=0`、`reports=0`、`scan_logs=6`。

## 9. 隔离恢复验证

- 选择主数据库备份副本：`E:\SRC-Research-Assistant_Backups\backup_20261110_110447\storage\src_research.db`
- 复制到隔离临时位置：`D:\挖漏洞\_git2b_restore_20261110_110447\restored_src_research.db`
- 恢复副本大小：147,456 字节
- 恢复副本 SHA-256：`8854f6b845822507e63ec225d9c17790a07b5c206ea30296d8c30378aa51142d`
- 重新打开：成功
- `PRAGMA integrity_check`：`ok`
- `PRAGMA foreign_key_check`：0 行
- `PRAGMA user_version`：5
- 表数量：11
- 业务表计数与源数据库一致（含 `scan_logs=6`）
- 恢复验证结论：**PASS**

隔离副本仅用于验证，未覆盖 D 盘原始主数据库；验证后临时目录已清理，正式备份保留。

## 10. 失败项、未验证项与工具限制

### 10.1 正式备份失败项

无。普通文件 226/226、数据库 20/20、清单校验均通过。

### 10.2 发现并绕过的环境限制

- 直接让 Python 子进程写入 E 盘备份目录时出现 `PermissionError [WinError 5]`；这是当前 DSH/Windows 文件权限环境限制，不是项目数据错误。
- 采用的处理：SQLite Backup API 先将 20 个数据库备份到 D 盘隔离 staging，再由 PowerShell 复制到 E 盘正式备份目录；普通文件由 PowerShell 复制。
- staging 目录仅用于中转，已清理；正式备份在 E 盘。该限制不影响备份完整性，但说明备份执行依赖 PowerShell 的 E 盘写权限。

### 10.3 未验证/不能声称的事项

- **未**进行真实物理磁盘损坏测试；E 与 D 同盘，`PHYSICAL_INDEPENDENT_BACKUP = NO`。
- **未**实现异地/离线副本；本备份不能抵御整块 SSD 损坏、勒索软件或整机丢失。
- **未**验证从恢复副本启动完整 GUI 应用；恢复验证仅覆盖 SQLite 打开、完整性、Schema 和业务表计数。
- 源数据库的 `-wal`/`-shm` sidecar 未被复制或当作独立备份；本次只核对了 sidecar 的数量和大小未变，未保存其逐文件备份前后哈希基线。
- 未初始化 Git、未修改 `.gitignore`、未配置 GitHub 远程。
- 本报告在备份完成后新增，不属于本次备份快照；备份快照的源文件数为 2,798，包含 Git-1 报告，不包含本报告。

## 11. 源项目与源数据库是否被修改

**未修改。**

- 未执行 Git 初始化、暂存或提交。
- 未修改源码、测试、配置、HTML 模板、数据库 Schema 或迁移。
- 未恢复或覆盖 D 盘原始数据库。
- 未删除或覆盖已有数据库、备份或历史文件。
- 源普通文件 226/226 的 SHA-256 与备份前记录一致。
- 源正式数据库 20/20 的主文件 SHA-256 与备份前记录一致；主数据库 `storage\src_research.db` 仍为 `ed315656...`。
- 源数据库 sidecar 数量/大小与备份前一致：40 个 / 655,360 字节。
- 备份操作对源数据库使用只读打开；没有业务写入。

## 12. E、D 同一物理 SSD 的风险

- D 盘：Disk 0 / Partition 4。
- E 盘：Disk 0 / Partition 6。
- 物理磁盘：Lexar SSD NM7A1 1TB，NVMe、GPT、Online。
- 序列号：`0000_0006_2601_1951_CAF2_5B05_1000_06D8.`。

因此：

- 本备份是**同一物理 SSD 上的本地目录副本**。
- 不能称为物理独立备份。
- 不能抵御 SSD 控制器、整盘固件、分区表或整机故障。
- 如需物理独立保障，应另行复制到不同物理介质或离线位置；本轮未执行。
