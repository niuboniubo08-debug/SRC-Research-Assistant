# Git-1 主数据库 SHA-256 变化原因调查

调查日期：2026-11-10  
项目：`D:\挖漏洞\SRC-Research-Assistant`  
范围：只读调查 `storage/src_research.db`

## 0. 结论摘要

| 项目 | 结论 |
|---|---|
| 当前主库 SHA-256 | `ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8` |
| 早期 SHA-256 | `F03CFB81BF0CF4CEE3367E1413E26919E30FA763C2D1B792AA03B5300E3128BB` |
| 是否找到变化前副本 | **是**：`backups/src-research-assistant_phase5_final.zip` 内保存了 SHA 完全为 `F03CFB81...` 的主库副本 |
| 数据层面的变化是否已解释 | **是**：新增了 **6 条 `scan_logs`**（项目创建、设置活动项目和删除项目），并伴随 `sqlite_sequence` 变化；业务表仍为 0 行 |
| 变化原因是否已解释 | **数据变化已确认；操作来源为高可信推断**：C2B 报告中心的手工/等价 GUI 功能验证在主库创建并删除了两个项目；无法证明具体由哪个 Windows 会话或哪次点击执行 |
| 是否存在 2026-11-09 的独立数据库备份 | **否**：20 个 `.db` 中没有 2026-11-09 生成的副本；`F03CFB81...` 副本位于 2026-11-05 的历史 ZIP 中 |
| 数据库完整性 | `PRAGMA integrity_check = ok`；`foreign_key_check = 0`；`user_version = 5` |
| 是否允许进入 Git-2 独立备份阶段 | **`GIT2_BACKUP_ALLOWED = CONDITIONAL_GO`**：可由人工确认后做只读备份；不得恢复旧库或覆盖当前库 |

**总体判断：**

`F03CFB81...` 与 `ED315656...` 的差异不是 Schema 变化，也不是业务数据损坏。`F03CFB81...` 的精确副本在历史 ZIP 中存在；与当前库做原始页对比，唯一的业务数据差异是 `scan_logs` 从 0 行变为 6 行，另有序号表变化。6 条日志的创建/删除对象是 `XSS测试项目` 和 `安全项目B`，与 `storage/reports` 下两个 22:19/22:22 生成的 HTML 报告相互对应，最后一条日志时间 `2026-11-09T14:51:03Z` 与主库 mtime `2026-11-09 22:51:03` 完全一致。

因此，**哈希变化可以解释为：C2B 报告中心功能验证过程中，使用主库完成了“创建项目 → 导出报告 → 删除项目”的操作；项目删除后业务表虽然恢复为 0 行，但 `scan_logs` 作为审计记录保留，导致 SQLite 文件内容变化。**

---

## 1. 当前数据库状态

### 1.1 文件状态

| 检查项 | 结果 |
|---|---|
| 路径 | `D:\挖漏洞\SRC-Research-Assistant\storage\src_research.db` |
| 文件大小 | **147,456 bytes** |
| SHA-256 | `ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8` |
| 文件 mtime（本地） | **2026-11-09 22:51:03** |
| 文件 mtime（UTC） | 2026-11-09 14:51:03 |
| SQLite `user_version` | **5** |
| `PRAGMA integrity_check` | **ok** |
| `PRAGMA foreign_key_check` | **0 行** |
| 页大小 | 4,096 bytes |
| 页数 | **36** |
| `freelist_count` | 0 |
| `journal_mode` | `wal` |
| `-wal` 文件 | 0 bytes |
| `-shm` 文件 | 32,768 bytes |

主库以 WAL 模式打开。检查结束时 `-wal` 为 0 bytes，表示没有待提交的 WAL 帧；主数据库文件自身 SHA 在本次调查开始和结束时均为 `ED315656...`。

> 说明：本次调查只使用 SQLite URI `mode=ro`，没有执行 `INSERT`、`UPDATE`、`DELETE`、迁移或 `Database.initialize()`。只读连接访问 WAL 数据库时，SQLite 可能刷新 `-shm` 共享内存索引；本次结束时 `-shm` mtime 为 `2026-11-10 10:34:17`。这不改变主库文件内容，也不代表业务写入。主库没有 WAL 帧残留。

### 1.2 关键表计数

| 表 | 行数 | 说明 |
|---|---:|---|
| `projects` | 0 | 项目已删除 |
| `authorizations` | 0 | 无授权记录 |
| `scope_assets` | 0 | 无范围资产 |
| `scan_tasks` | 0 | 无扫描任务 |
| `findings` | 0 | 无漏洞记录 |
| `evidence` | 0 | 无证据记录 |
| `finding_status_history` | 0 | 无状态历史 |
| `reports` | 0 | 无报告登记行 |
| `scan_logs` | **6** | 六条项目生命周期审计日志 |
| `app_settings` | 0 | 无活动项目或设置 |

应用表共 **11 个**：`projects`、`authorizations`、`scope_assets`、`scan_tasks`、`findings`、`evidence`、`finding_status_history`、`reports`、`scan_logs`、`app_settings`、`authorization_history`。另有 SQLite 内部 `sqlite_sequence` 表。

索引共 **20 个**：18 个显式索引 + 2 个 SQLite 自动索引（`sqlite_autoindex_app_settings_1`、`sqlite_autoindex_scope_assets_1`）。

### 1.3 `scan_logs` 的时间范围

| 项目 | 值 |
|---|---|
| 最小 `created_at` | `2026-11-09T14:13:23Z` |
| 最大 `created_at` | `2026-11-09T14:51:03Z` |
| 行数 | 6 |
| 事件类型 | 全部为 `project_change` |
| `decision` | 全部为 `info` |

六条日志的记录内容见第 5 节。

---

## 2. 早期 SHA 记录的来源

### 2.1 文档记录

`F03CFB81...` 是可信的历史记录，不是单次口头记录。主要来源如下：

| 来源 | 内容 |
|---|---|
| `docs/acceptance/phase6_b_final/PHASE6_B_DATABASE_INFO.md:24-25` | Phase 6B 记录主库 SHA-256 before/after 均为 `f03cfb81...e3128bb` |
| `docs/acceptance/phase6_b_final/PHASE6_B_ACCEPTANCE.json:103-104` | 同一对 before/after SHA 记录 |
| `docs/PHASE6_C2A_SECURITY_FIX_1.md:171` | 主库 SHA 仍为 `F03CFB81...`，schema 5，`reports=0` |
| `docs/PHASE6_C2A_SEC02_WINDOWS_PATH_FIX_1.md:255-262` | 主库 SHA 仍为 `F03CFB81...`，schema 5 |
| `docs/PHASE6_C2A_SECURITY_FINAL_REVIEW.md:607-613` | 主库 SHA 仍为 `F03CFB81...` |
| `docs/PROJECT_HISTORY_PHASE6.md:812` | Phase 6 历史调查记录主库 SHA 为 `f03cfb81...`，schema 5，reports 0 |

因此，`F03CFB81...` 至少从 Phase 6B 封存阶段一直记录到 C2A 安全修复阶段。

### 2.2 `ED315656...` 的最早记录

`ED315656...` 已出现在 Phase 6C-2B Step 3 验收报告中：

```text
docs/PHASE6_C2B_STEP3_ACCEPTANCE.md:169
主数据库 storage/src_research.db 当前 SHA-256 为
ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8，
本轮未执行数据库写操作。
```

该句的含义是 **Step 3 验收运行本身没有写库**，不是说该 SHA 从 Phase 6B 到 Step 3 一直未变。结合主库 mtime `2026-11-09 22:51:03` 和 Step 3 报告生成时间（晚于 22:51），可以确认：**哈希变化发生在 Step 3 验收运行之前**。

### 2.3 精确 f03 副本

`F03CFB81...` 的精确字节副本存在于：

```text
backups/src-research-assistant_phase5_final.zip
  entry: SRC-Research-Assistant/storage/src_research.db
  entry size: 147,456
  entry date: 2026-11-05 11:43:40
  zip mtime: 2026-11-05 11:47:06
  SHA-256: F03CFB81BF0CF4CEE3367E1413E26919E30FA763C2D1B792AA03B5300E3128BB
```

这是 ZIP 内的历史副本，不是 2026-11-09 的新备份，也没有被解压或复制到工作区。该 ZIP 的数据库条目与 Phase 6B 记录的 f03 哈希完全一致，可以作为变化前比较基准。

---

## 3. 是否存在变化前副本

### 3.1 已检查范围

已只读枚举项目内全部 `.db` 文件（共 20 个），并读取以下信息：

- 文件大小；
- 文件 mtime；
- SHA-256；
- `PRAGMA user_version`；
- 关键表行数；
- 可读取时的 `PRAGMA integrity_check`。

同时检查了 `storage/backups`、`docs/acceptance`、`storage/phase*_acceptance` 和 5 个历史 ZIP。

### 3.2 关键副本对照

| 副本 | 大小 | mtime | Schema | 主库业务表 | `scan_logs` | SHA-256 |
|---|---:|---|---|---:|---:|---|
| ZIP 内 f03 基准 | 147,456 | 2026-11-05 11:43:40（条目） | v5 | 0 | 0（页 17 根页 0 个 cell） | `F03CFB81...` |
| `storage/backups/src_research_phase5_final_20261105T061441Z.db` | 147,456 | 2026-11-05 14:14:41 | v5 | 0 | 0 | `A2423FA7...` |
| 当前主库 | 147,456 | **2026-11-09 22:51:03** | v5 | 0 | **6** | `ED315656...` |

补充：

- `docs/acceptance/phase5_final/db/src_research_phase5_final_20261105T061441Z.db` 与 `storage/backups` 中的 A242 副本相同。
- `A242...` 不是 f03，不能替代 f03 作为“Phase 6B 基线”的精确比较对象。
- 没有任何 2026-11-09 生成的 `.db` 或 ZIP 备份。
- 没有找到 f03 的松散 `.db` 副本；f03 只在历史 ZIP 中以条目形式存在。

**结论：** 变化前的可信副本存在，但不是 2026-11-09 的独立备份，而是 2026-11-05 Phase 5 历史 ZIP 中的 f03 精确副本。

---

## 4. 当前库与 f03 副本的实际差异

### 4.1 比较方法

使用只读方式：

1. 读取 ZIP 条目的原始字节并验证 SHA-256 为 f03；
2. 读取当前 `storage/src_research.db` 的原始字节；
3. 按 4,096-byte 页比较；
4. 用当前库的 SQLite `mode=ro` 查询 `sqlite_master` 的 rootpage、表计数和完整性。

没有解压 ZIP、没有复制数据库、没有创建临时数据库文件、没有执行任何 SQL 写操作。

### 4.2 页级差异

两个文件均为：

- 36 页；
- 4,096 bytes/页；
- 147,456 bytes；
- `user_version = 5`。

发生字节差异的页：

| 页 | 当前类型 / cell 数 | f03 类型 / cell 数 | 说明 |
|---:|---|---|---|
| 2 | table leaf / 0 | table leaf / 0 | `projects` 根页，业务行均为 0；页内空闲布局不同 |
| 3 | table leaf / 3 | table leaf / 1 | `sqlite_sequence`；新增自增序号记录 |
| 4 | index leaf / 0 | index leaf / 0 | 空索引页 |
| **17** | **table leaf / 6** | **table leaf / 0** | **`scan_logs` 根页：当前 6 行，f03 0 行** |
| 18 | index leaf / 6 | index leaf / 0 | `scan_logs` 相关索引，当前 6 项 |
| 19 | index leaf / 6 | index leaf / 0 | `scan_logs` 相关索引，当前 6 项 |
| 27 | table leaf / 0 | table leaf / 0 | `app_settings` 根页，均为 0 行 |
| 28 | index leaf / 0 | index leaf / 0 | 空索引页 |

关键点：

- `scan_logs` 根页（page 17）从 **0 个 cell 变为 6 个 cell**；
- 两个 `scan_logs` 索引叶页（18、19）从 0 个 cell 变为 6 个 cell；
- `sqlite_sequence` 从 1 个 cell 变为 3 个 cell；
- `projects`、`app_settings` 等业务表的根页仍然是 0 个 cell；
- 没有出现 `findings`、`evidence`、`scan_tasks`、`reports` 等业务记录的变化。

### 4.3 当前 SQL 计数与页级证据一致

当前 SQLite 只读查询：

```text
projects=0
authorizations=0
scope_assets=0
scan_tasks=0
findings=0
evidence=0
finding_status_history=0
reports=0
scan_logs=6
app_settings=0
```

这与页级差异一致：**唯一的持久业务记录变化是 6 条 `scan_logs`，另有序号表变化；没有其他业务表记录增长。**

### 4.4 能否解释 SHA 变化

**可以解释数据层面的 SHA 变化。**

SQLite 文件不是“逻辑表的可重现序列化”。插入 `scan_logs`、更新索引、写入 `sqlite_sequence`、删除项目后保留审计日志，会改变表页、索引页、页头 change counter 和空闲空间布局。因此：

```text
f03（0 条 logs） + 6 条项目生命周期日志 + 序号/索引/页布局变化
= ED315656...
```

这解释的是**文件字节变化**，不是仅靠“表为空”就能推断文件相同。若仅看业务表的 0 行，确实会误以为哈希应保持不变。

---

## 5. 六条 `scan_logs` 的具体来源

### 5.1 数据库中的六条记录

| 时间（UTC） | 本地时间 | 操作 | 目标 | 说明 |
|---|---|---|---|---|
| 2026-11-09T14:13:23Z | 22:13:23 | `create_project` | `XSS测试项目` | 创建项目 #1 |
| 2026-11-09T14:13:38Z | 22:13:38 | `set_active_project` | `XSS测试项目` | 设置活动项目 #1 |
| 2026-11-09T14:21:23Z | 22:21:23 | `create_project` | `安全项目B` | 创建项目 #2 |
| 2026-11-09T14:21:25Z | 22:21:25 | `set_active_project` | `安全项目B` | 设置活动项目 #2 |
| 2026-11-09T14:51:00Z | 22:51:00 | `delete_project` | `安全项目B` | 删除项目 #2 |
| 2026-11-09T14:51:03Z | 22:51:03 | `delete_project` | `XSS测试项目` | 删除项目 #1 |

所有行的 `event_type` 都是 `project_change`，`decision` 都是 `info`。删除后 `scan_logs.project_id` 为 `NULL`，但 `details_json` 保留了项目 ID。

### 5.2 与 `storage/logs/audit.jsonl` 的对应

`storage/logs/audit.jsonl` 共 6 行，时间、操作、目标和消息与数据库 `scan_logs` 一一对应，例如：

```json
{"created_at": "2026-11-09T14:13:23Z", "event_type": "project_change",
 "operation": "create_project", "target": "XSS测试项目",
 "message": "创建项目 #1", "details": {"project_id": 1, ...}}
```

该文件 mtime 也是 **2026-11-09 22:51:03**，与主库 mtime 相同。说明最后一次项目删除同时写入了数据库和审计 JSONL。

### 5.3 与两个 HTML 报告产物的对应

`storage/reports` 中存在两个先于本次调查的 HTML 文件：

| 文件 | 大小 | mtime | 标题中的项目 |
|---|---:|---|---|
| `project_1_project_summary_c296b0982419.html` | 9,545 | 2026-11-09 22:19:47 | `XSS测试项目` |
| `project_2_project_summary_a312f270d9a9.html` | 9,537 | 2026-11-09 22:22:42 | `安全项目B` |

两个文件的项目名与 `scan_logs` 中的 `XSS测试项目`、`安全项目B` 一致，生成时间也位于对应项目创建之后、删除之前：

```text
22:13 创建项目 #1
22:19 导出 project_1 报告
22:21 创建项目 #2
22:22 导出 project_2 报告
22:51 连续删除项目 #2 和 #1
```

这说明当时使用了真实主库中的两个项目做了报告中心/项目管理的功能验证。

### 5.4 代码路径

这些日志不是报告导出器直接写入的，而是项目生命周期服务写入审计：

- `services/project_service.py:78-113` `create_project()` 在创建项目的同一事务中调用 `self._audit.record(...)`；
- `services/project_service.py:169-187` `delete_project()` 在删除项目前调用 `self._audit.record(...)`，然后删除 `projects` 行；
- `services/audit_service.py:74-102` `AuditLogService.record()` 同时追加 `storage/logs/audit.jsonl` 并插入 `scan_logs`；
- `database/schema.py:106-110` `scan_logs.project_id` 外键为 `REFERENCES projects(project_id) ON DELETE SET NULL`，所以删除项目后日志保留、`project_id` 变 `NULL`。

报告导出路径本身只读取快照并写 HTML 文件，不调用 `scan_logs` 插入。因此，导致数据库变化的是**创建/删除项目**操作，而不是 `write_html_report()`。

---

## 6. 变化原因的确认、推断与 UNKNOWN

### 6.1 已确认的事实

1. 当前主库哈希为 `ED315656...`，大小 147,456，mtime `2026-11-09 22:51:03`。
2. 早期记录为 `F03CFB81...`，其精确字节副本存在于 Phase 5 历史 ZIP 中。
3. f03 与当前库页数、页大小相同；f03 的 `scan_logs` 根页为 0 个 cell，当前为 6 个 cell。
4. 当前业务表全部为 0 行，唯一非空业务相关表是 `scan_logs`，共 6 行。
5. 六条日志的时间、操作和目标明确；`audit.jsonl` 六行与数据库完全对应。
6. 六条日志对应两个项目的创建、设置活动和删除，项目名与两个 HTML 报告标题一致。
7. 最后一条日志 `14:51:03Z` 与主库 mtime `22:51:03` 一致。
8. 当前 `integrity_check=ok`，`foreign_key_check=0`，`user_version=5`，没有 Schema 变化。
9. 没有 2026-11-09 的独立数据库备份。

### 6.2 高可信推断

**高可信推断（HIGH_CONFIDENCE）：**

> 2026-11-09 22:13–22:51 之间，使用主库进行了 C2B 报告中心/项目管理的手工或等价 GUI 功能验证：创建 `XSS测试项目` 和 `安全项目B`，分别导出两个项目综合报告，然后删除两个项目。项目删除使业务表恢复为 0 行，但六条审计日志保留，导致 SQLite 文件内容和 SHA-256 改变。

支持证据：

- 六条日志是 `project_change`，不是报告导出事件；
- 两个 HTML 报告标题和项目名与日志一致；
- 报告生成时间位于创建和删除之间；
- 文件 mtime 与最后一条删除日志精确到秒一致；
- 项目删除后 `scan_logs` 按外键 `SET NULL` 保留，符合当前结果。

### 6.3 不能确认的 UNKNOWN

以下事项仍为 **UNKNOWN**，不能写成已确认：

- 具体是哪个 Windows 用户会话、哪个进程、哪次鼠标操作触发了创建/删除；
- 为什么使用生产主库而不是临时数据库；
- 是否存在未被审计记录的其他外部进程（当前证据只覆盖有审计日志的操作）；
- f03 ZIP 内数据库的完整 SQL 行计数无法在不解压的情况下通过 SQL 直接读取；本报告使用原始页 cell 数（`scan_logs` 根页 0）和有记录的 Phase 6B 基线来比较；
- 2026-11-09 是否存在已被删除、未留存的临时数据库副本；当前没有发现。

### 6.4 不属于原因的事项

根据现有证据，以下不是本次哈希变化的原因：

- **不是 Schema 迁移**：`user_version=5` 与 f03 一致，表和索引结构未变；
- **不是报告导出器直接写库**：`write_html_report()` 只写 HTML 文件，不插入 `scan_logs`；
- **不是测试框架使用主库**：`tests/conftest.py:39-41` 使用 `tmp_path / "test.db"`，`tests/test_ui_report.py` 使用 `make_context(tmp_path)`；测试不会写 `storage/src_research.db`；
- **不是 Git 盘点本身**：Git 盘点在 2026-11-10 进行，主库 mtime 为 2026-11-09 22:51:03，早于盘点；
- **不是 Phase 6C-2B Step 3 验收运行**：Step 3 报告记录当时的 SHA 已经是 `ED315656...`，且该轮没有执行主库写操作。

---

## 7. 完整性与 Schema 检查

### 7.1 当前库

| 检查项 | 结果 |
|---|---|
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | 0 行 |
| `PRAGMA user_version` | 5 |
| 应用表 | 11 |
| 显式索引 | 18 |
| 自动索引 | 2 |
| `reports` 行数 | 0 |
| 业务表（projects/findings/evidence/tasks/assets） | 全部 0 |
| `scan_logs` | 6 |

### 7.2 f03 基准

- ZIP 条目 SHA 为 `F03CFB81...`，大小 147,456；
- 页数 36，页大小 4,096；
- Phase 6B 档案记录 `user_version=5`、`integrity_check=ok`、11 张应用表、18 个索引；
- f03 的 `projects`、`app_settings` 根页均为 0 个 cell；`scan_logs` 根页为 0 个 cell。

### 7.3 结论

当前数据库**没有完整性错误、没有外键违规、没有 Schema 变化**。六条审计日志是合法的历史记录；删除项目后保留日志是 `scan_logs` 外键 `ON DELETE SET NULL` 的预期行为，不是残留脏数据。

---

## 8. 是否允许进入 Git-2 独立备份阶段

**结论：`GIT2_BACKUP_ALLOWED = CONDITIONAL_GO`。**

允许进入 Git-2 的前提：

1. 人工接受“六条日志来自 C2B 项目生命周期功能验证”的高可信推断；
2. Git-2 只复制**当前** `storage/src_research.db`，并记录：
   - 大小 147,456；
   - SHA-256 `ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8`；
   - `user_version=5`；
   - `integrity_check=ok`；
   - `foreign_key_check=0`；
3. 备份目标放在版本库外或明确忽略的位置；
4. 不恢复 f03，不覆盖当前库，不执行迁移；
5. 不把 f03 当作当前运行库，也不修改六条历史日志。

不建议无条件执行的原因：

- 没有 2026-11-09 的独立备份，无法从时间点备份做二次对照；
- 具体操作者/会话仍是 UNKNOWN；
- 但**数据层面的差异已经可由 f03 与当前库的页级对比解释**，当前库完整性正常。

因此，Git-2 可以做“保留当前真相”的独立备份，但不应做任何自动恢复或历史回滚。

---

## 9. 本轮实际修改文件

仅新增本文档：

```text
docs/GIT_DATABASE_HASH_INVESTIGATION.md
```

未修改：

- 生产代码：否；
- 测试代码：否；
- 数据库内容或 Schema：否（仅只读 SQLite 查询）；
- `config.yaml`：否；
- Phase 5/6 已封存文件：否；
- `.gitignore`：否；
- Git 仓库：未初始化；
- 依赖：未安装/升级/卸载；
- 备份：未创建；
- 测试：未运行。

**数据库文件核对：**

```text
调查开始时记录的主库 SHA: ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8
调查结束时主库 SHA:       ED3156560FCFE14C88715245CDA8A3A919F3CE24D108EBCEC9BF81E1536E15F8
主库文件 mtime:           2026-11-09 22:51:03
主库大小:                 147456
```

只读连接可能刷新了 SQLite 的 `-shm` 缓存（32,768 bytes）；`-wal` 为 0 bytes。主数据库文件本身未发生字节变化。

---

## 10. 最终回答

1. **当前数据库状态**：147,456 bytes，SHA `ED315656...`，v5，完整性 ok，外键 0，业务表 0，`scan_logs=6`。
2. **早期 SHA 来源**：Phase 6B 档案记录 `F03CFB81...`；精确字节副本在 `backups/src-research-assistant_phase5_final.zip`。
3. **变化前副本**：有，f03 精确副本；没有 2026-11-09 的新备份。
4. **SHA 变化能否解释**：能。f03 到当前库的唯一业务数据变化是六条项目生命周期 `scan_logs`，另有序号表/索引页布局变化。
5. **完整性与 Schema**：`integrity_check=ok`，`foreign_key_check=0`，`user_version=5`，11 张应用表，无 Schema 变化。
6. **原因可信度**：**数据差异 CONFIRMED；操作来源 HIGH_CONFIDENCE，但具体操作者/会话 UNKNOWN**。
7. **是否允许 Git-2**：**CONDITIONAL_GO**；可做只读独立备份，不得恢复旧库或覆盖当前库。
