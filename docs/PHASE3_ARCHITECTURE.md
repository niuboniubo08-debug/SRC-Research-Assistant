# 第三阶段架构：本地 Python 源代码审计

## 1. 分层与边界

```text
SourceAuditPage (PySide6, QThread)
        │ 只调用 Service 层
        ▼
ScanService
  ├─ ProjectService（读取当前项目本地路径）
  ├─ ScopeValidator.check_local_path（复用，并补充存在/目录/权限）
  ├─ BaseScanner 注册表
  │    ├─ BanditScanner ── process_runner ── python -m bandit
  │    └─ SemgrepScanner ─ process_runner ── semgrep.exe（当前环境不可用）
  ├─ Database（scan_tasks / findings）
  └─ AuditLogService（scan_logs + audit.jsonl）

UI 不导入 scanners；scanners 不导入 UI。
外部工具调用统一由 process_runner 以参数列表 + shell=False 执行。
```

## 2. 扫描调用链

```text
当前项目
  ↓
project.local_path
  ↓
ScopeValidator.check_local_path(project_id, path, "source_audit")
  ↓ 拒绝 → 不创建任务，审计记录拒绝
  ↓ 允许
创建 ScanTask(pending)
  ↓
检查所选扫描器可用性
  ↓ 无可用 → failed，错误信息明确
  ↓
running → 逐个 scanner.scan(target, options)
  ↓
Bandit/Semgrep JSON → Finding → findings 表
  ↓
completed / failed / cancelled
  ↓
SourceAuditPage 查询任务和 Finding 展示
```

## 3. 统一扫描器接口

```python
class BaseScanner(ABC):
    name: str
    display_name: str
    version: str
    def is_available(self, refresh=False) -> ScannerAvailability: ...
    def scan(self, target, options: ScanOptions) -> ScanOutput: ...
```

`ScanOptions` 包含超时、取消事件和额外环境变量。`ScanOutput` 只包含统一
`Finding`、警告和必要的元数据，不把原始 JSON 交给业务层或 UI。

异常类型：`ScannerUnavailable`、`ScannerExecutionError`、`ScannerParseError`、
`ScannerTimeoutError`、`ScanCancelled`。

## 4. 子进程安全

- `Popen([...], shell=False)`，参数不经过字符串拼接；
- stdout/stderr 由后台 reader 线程持续排空，避免管道阻塞；
- 超时/取消后 terminate，必要时 kill；
- 捕获上限 8 MiB，防止异常工具输出耗尽内存；
- Windows 使用 `CREATE_NO_WINDOW`，不弹控制台。

## 5. 数据库 v3

无新增业务表，扩展现有表：

`scan_tasks`：

- `current_scanner`
- `progress`
- `error_message`
- `scanners_json`
- `cancel_requested`
- `cancelled_at`

`findings`：

- `confidence`
- `file_path`
- `line_number`
- `rule_id`
- `scanner_name`
- `scanner_version`
- `detected_at`

新增索引：

- `idx_findings_task(project_id, task_id, risk_level)`
- `idx_findings_scanner(project_id, scanner_name, risk_level)`
- `idx_scan_tasks_status(project_id, status, created_at DESC)`

迁移通过 `PRAGMA table_info` 检查后逐列添加，可安全重试；v2 数据库在迁移前复制备份。

## 6. 状态语义

| 状态 | 语义 |
|---|---|
| pending | 任务已创建，尚未运行 |
| running | 正在执行扫描器 |
| completed | 至少一个扫描器成功执行；0 Finding 仍是 completed |
| failed | 扫描器执行/解析失败、超时，或所有所选扫描器不可用 |
| cancelled | 用户取消或取消事件在扫描前已触发；永远不是 completed |

部分成功：某个扫描器失败时，其他成功扫描器的 Finding 已保存，但任务最终为
`failed`，错误信息保留；取消时已产生的结果也保留，但任务为 `cancelled`。

## 7. UI 线程模型

- 页面通过 `ScanWorker(QThread)` 调用 `ScanService.run_scan`。
- 进度、完成、异常通过 Qt Signal 回到主线程。
- 取消通过 `threading.Event` 传递；进程执行器轮询并终止外部工具。
- 扫描期间顶部项目选择器禁用，防止项目切换歧义。
- 主窗口关闭时调用 `source_audit_page.shutdown()`，请求取消并等待线程。

## 8. Semgrep 当前状态

- 规则：`scanners/rules/python_security.yml`，7 条本地 Python 基础安全规则。
- 不使用 registry、不自动下载规则。
- 命令使用 `--config <local rules> --json --metrics=off --disable-version-check`。
- 当前 Windows 会话中 Semgrep 原生二进制在证书存储初始化阶段失败：
  `CertOpenSystemStore returned NULL`。
- 因此 UI/Service 将其标记为不可用；解析器和规则结构有测试，但没有伪造真实结果。

## 9. 数据与隐私

- Finding 只保存规则元数据、相对文件路径、行号、说明和建议，不保存源码文件内容。
- Bandit 的硬编码凭据规则 B105/B106/B107 会脱敏，不写入具体凭据值。
- 扫描结果按 `project_id` 和 `task_id` 双层筛选。
- 没有远程 URL、DNS 或 HTTP 扫描实现。
