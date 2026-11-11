# 第四阶段架构：Python 依赖漏洞审计

## 1. 边界与复用

```text
DependencyPage (PySide6, QThread)
        │ 只调用 Service
        ▼
DependencyAuditService
  ├─ ProjectService（当前项目）
  ├─ ScopeValidator.check_local_path（依赖审计操作）
  ├─ 依赖文件识别（项目根目录）
  ├─ PipAuditScanner ── process_runner ── pip-audit
  ├─ Database（scan_tasks / findings）
  └─ AuditLogService（scan_logs / audit.jsonl）
```

复用：

- 现有 `ScanTask`、`ScanTaskStatus`；
- 现有 `Finding`；
- 现有 `AuditLogService`、`ProjectService`、`ScopeValidator`、`Database`；
- 现有项目/任务隔离结构；
- 现有统一子进程执行器与 UI/QThread 模式。

没有新建第二套任务或 Finding 模型。项目中没有既有 Repository 层，因此继续沿用现有 Service + `Database` 模式，没有为了套用模式做大规模重构。

## 2. 依赖文件识别

只检查当前授权本地项目根目录的直接文件：

- `requirements.txt`
- `pyproject.toml`

规则：

- 不递归读取任意目录，不跟随符号链接，不允许解析结果落在项目根目录外。
- `requirements.txt` 直接交给 pip-audit。
- `pyproject.toml` 只读取 PEP 621 `[project].dependencies`；在项目自有临时目录生成临时 requirements 文件，任务结束清理。
- 两者都存在时优先 `requirements.txt`。
- 无可审计依赖文件时不创建任务，UI 显示“未发现可审计依赖”。
- 文件存在但解析失败/为空时标记为不可审计，不伪造成功。
- `requirements.txt` 的行号用于直接依赖 Finding；传递依赖行号为 0。

## 3. pip-audit 适配器

`scanners/pip_audit_scanner.py`：

- 实现现有 `BaseScanner` 接口；
- 可用性：检查 Python 模块、可执行文件、版本探测；
- 通过 `process_runner` 调用，参数列表、`shell=False`；
- 使用：
  - `-r <requirements>`
  - `--format json`
  - `--progress-spinner off`
  - `--desc on`
  - `--aliases on`
  - `--vulnerability-service pypi`
  - 项目内 `--cache-dir`
- 子进程临时目录指向应用自有 `storage/tmp/pip-audit`，避免依赖用户默认缓存路径；
- 处理超时、取消、非零退出、空输出、JSON 解析失败；
- 对 pip-audit 重复返回的同一 ID 去重；
- 将依赖漏洞转换为统一 Finding。

## 4. Finding 映射

统一 Finding 必填字段沿用第三阶段，新增 `metadata`，数据库 v4 增加：

```text
findings.metadata_json
```

依赖漏洞 metadata 包含：

```json
{
  "dependency_name": "requests",
  "current_version": "2.19.0",
  "vulnerability_id": "PYSEC-2018-28",
  "aliases": ["CVE-2018-18074"],
  "affected_versions": "当前审计版本 2.19.0 命中；具体受影响范围见漏洞公告",
  "fix_versions": ["2.20.0"],
  "source": "pip-audit/PyPI",
  "vulnerability_service": "pypi",
  "dependency_file": "requirements.txt",
  "severity_source": "conservative-default"
}
```

pip-audit JSON 当前不提供 CVSS/severity 或结构化版本范围，因此：

- 缺省 severity 使用保守 medium；
- `severity_source` 明确标记；
- 受影响版本记录当前命中版本，并明确提示以漏洞公告为准；
- 不伪造 CVSS。

## 5. ScanTask 流程

```text
当前项目
  ↓
check_local_path(..., "dependency_audit")
  ↓
识别依赖文件 / 选择主文件
  ↓
创建 ScanTask(dependency_audit, pending)
  ↓
pip-audit 可用性检查
  ↓ 不可用 → failed
  ↓
running
  ↓
准备审计输入（pyproject → 临时 requirements）
  ↓
pip-audit JSON
  ↓
统一 Finding + metadata
  ↓
保存 findings
  ↓
completed / failed / cancelled
  ↓
UI 展示
```

语义：

- 空结果 + 至少审计到一个依赖 → `completed`，0 Finding；
- 未审计到任何依赖 → `failed`，避免把“没有扫描”伪装成“没有漏洞”；
- 工具不可用、执行失败、解析失败、超时 → `failed`；
- 用户取消 → `cancelled`；
- 未找到依赖文件 → 不创建任务，UI 明确提示。

## 6. UI

`DependencyPage`：

- 当前项目、本地路径、路径授权状态；
- 依赖文件列表、数量、主文件/可选文件；
- pip-audit 可用性和版本；
- 开始/取消、超时；
- 扫描状态、当前步骤、进度、完成时间、错误；
- 结果表：风险、依赖、版本、漏洞编号、修复建议、工具；
- 详情：依赖、版本、漏洞编号、别名、来源、受影响版本、漏洞说明、修复建议。

UI 不导入 `scanners`，通过 `DependencyAuditService` 调用。

## 7. 网络与安全

- 不扫描远程目标、不访问网站、不执行利用代码。
- pip-audit 会向公开漏洞服务查询依赖名称/版本，并通过 pip 解析/下载依赖到临时目录；不上传项目源码。
- 网络访问发生在后台工作线程，受超时/取消控制。
- 子进程参数列表调用，禁止 `shell=True`。
- 所有依赖审计任务和路径检查写入审计。
- 结果按 `project_id`、`task_id` 双重隔离。

## 8. 已知限制

- pip-audit JSON 不提供 CVSS，风险等级默认 medium，需要人工复核公告。
- pip-audit JSON 不提供精确 affected version range，metadata 记录命中版本和公告提示。
- pyproject 仅覆盖 PEP 621 `[project].dependencies`，不处理 Poetry/可选依赖组。
- 离线漏洞库未实现；网络失败会明确标记 failed。
- 应用异常强杀造成的 running 任务尚不会自动恢复。
