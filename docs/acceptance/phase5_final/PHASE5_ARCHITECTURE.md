# 第五阶段架构：漏洞管理中心与证据中心

## 1. 阶段边界

本阶段只管理第三、第四阶段已经产生的本地 Finding，以及用户确认的本地证据。

不包含：

- 远程配置检查、网络探测；
- 漏洞利用、自动攻击；
- HTML/PDF/JSON 报告；
- EXE 打包；
- 证据上传、执行或外部同步。

现有 `ScopeValidator`、项目隔离、授权管理和路径校验没有被删除或放宽。

## 2. 分层与 Repository

项目原有架构没有 Repository 层，第三/第四阶段由 Service 直接访问 `Database`。第五阶段只为新模块增加了两个聚焦 Repository，没有重写既有服务：

```text
VulnerabilityPage / EvidencePage (PySide6, QThread)
              │
              ▼
VulnerabilityService             EvidenceService
  ├─ VulnerabilityRepository       ├─ EvidenceRepository
  ├─ EvidenceRepository            ├─ VulnerabilityRepository
  ├─ ProjectService                ├─ ProjectService
  ├─ AuditLogService               ├─ ScopeValidator
  └─ Database                      ├─ AuditLogService
                                   └─ config.evidence_dir
```

- `repositories/vulnerability_repository.py`：统一列表 SQL、项目过滤、状态更新、状态历史、任务关联。
- `repositories/evidence_repository.py`：证据 CRUD、项目/Finding 过滤。
- Service 负责参数校验、项目归属、状态枚举、审计和证据文件安全。
- UI 不导入扫描器、不直接写 SQL。

## 3. 统一 Finding 读取

`VulnerabilityRepository` 查询 `findings` 并 JOIN `projects`，同时计算证据数量：

```sql
SELECT f.*, p.project_name,
       (SELECT COUNT(*) FROM evidence e
        WHERE e.project_id = f.project_id
          AND e.finding_id = f.finding_id) AS evidence_count
FROM findings f
JOIN projects p ON p.project_id = f.project_id
```

不把 Bandit、Semgrep、pip-audit 的原始字段混合成新的“猜测字段”。统一字段保持 Finding 原有语义，原始规则/文件/元数据按来源展示。

## 4. 状态工作流

状态：

```text
open → reviewing → confirmed
  ├→ false_positive
  ├→ fixed
  └→ accepted_risk
```

- 状态值由 `FindingStatus` 枚举集中定义。
- 修改状态只更新 `findings.status`、`status_changed_at`、`updated_at`。
- 同一事务追加 `finding_status_history`，记录 from/to、note、changed_by、changed_at。
- 人工备注使用 `findings.manual_notes`，与状态变更分开。
- 不提供删除 Finding 的入口；修改状态不会删除原始 Finding。

## 5. Schema v5

v5 是前向迁移，迁移前自动备份。

### findings

SQLite 无法原地修改 CHECK 约束，因此 v5 在一个显式事务中重建表：

- 保留原 `finding_id`、项目/任务、风险、描述、评分、扫描器、文件、metadata 等全部字段；
- 允许 `reviewing`；
- 新增 `manual_notes`、`status_changed_at`、`last_seen_at`；
- 按 `detected_at/created_at` 回填 `last_seen_at`；
- 重建原有索引并增加状态索引。

### evidence

在现有表上增加：

- `evidence_type`；
- `title`；
- `source`。

保留原 `evidence_id`、`project_id`、`finding_id`、`file_path`、`file_name`、`sha256`、`captured_at`、`description`、`created_at`。

### finding_status_history

新增追加式状态变更历史表，带 `project_id`、`finding_id` 外键和索引。

### 回滚策略

- v5 DDL 使用显式 `BEGIN IMMEDIATE`，失败时 rollback。
- 迁移前将数据库复制到 `storage/backups/<name>_v4_<timestamp>.db`。
- 失败后原 v4 库保持可打开；备份可用于恢复。
- 迁移测试覆盖“部分 DDL 后抛错”的回滚和备份恢复。

## 6. 证据安全

### 文本证据

- 代码片段、扫描器摘要、依赖信息、人工备注保存为 `description`。
- 不产生本地文件。

### 文件证据

截图和其他本地文件：

1. 只接受绝对路径；
2. 项目必须有本地路径和有效本地资产；
3. `ScopeValidator.check_local_path(..., "evidence_import")` 必须允许；
4. 源文件解析后必须位于项目根目录内；
5. 拒绝源路径本身是符号链接；
6. 解析后的路径若因目录联接/父级链接越界，同样拒绝；
7. 上限 50 MB；
8. 复制到 `storage/evidence/project_<id>/<uuid>_<safe_name>`，不覆盖同名文件；
9. 计算复制后文件的 SHA-256，保存来源相对路径、原文件名、哈希；
10. 数据库写入失败时清理已复制文件。

### 删除

- UI 明确二次确认。
- 先删除证据记录，再删除受管副本。
- 只删除证据目录内的受管文件；原始项目文件和源文件保留。
- 永不删除关联 Finding。

### 禁止项

- 不自动执行证据；
- 不自动上传；
- 不读取项目外文件；
- 不把证据路径解释为可执行命令。

## 7. UI

### 漏洞管理

- 顶部项目/风险/工具/状态筛选和关键词搜索；
- 列表在 QThread 中读取；
- 详情包含完整说明、风险来源、工具版本、规则、项目、任务、首次/最近发现、源码/依赖信息、原始 metadata；
- 状态保存和备注保存；
- 状态历史、关联证据列表；
- 证据按钮打开添加对话框，或跳转证据中心。

### 证据中心

- 项目/类型筛选、关键词搜索；
- 列表在 QThread 中读取；
- 添加证据对话框要求人工确认敏感信息，文件类型必须选择项目内文件；
- 详情显示受管路径、原文件名、来源、SHA-256；
- 查看关联漏洞、删除证据。

QThread 生命周期按 worker 实例绑定 finished 槽，避免旧线程完成后误删新线程。

## 8. 审计

新增审计事件：

- `finding_status_changed`
- `finding_notes_updated`
- `evidence_created`
- `evidence_deleted`

审计写入失败不会导致证据文件读取越权；路径校验先于文件复制，证据审计不改变原始 Finding。

## 9. 已知限制

- 未合并重复扫描产生的逻辑相同 Finding；“首次/最近”按每条 Finding 的记录时间展示。
- 文件符号链接的真实创建在当前 Windows 非特权会话被拒绝；目录联接越界和模拟 `is_symlink` 分支已测试。
- Semgrep 实际运行仍受第三阶段 Windows CA 存储限制。
- 证据只支持项目根目录内的文件；项目外截图需先由用户复制到项目根目录。
- 本阶段未实现报告、远程检测或证据导出。
