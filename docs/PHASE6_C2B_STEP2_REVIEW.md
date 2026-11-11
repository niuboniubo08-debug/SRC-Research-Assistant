# Phase 6C-2B Step 2 补充审查：快照新鲜度与覆盖目标一致性

日期：2026-11-09  
审查对象：`ui/report_page.py`、`ui/app_state.py`、`ui/main_window.py`、`ui/vulnerability_page.py`、`ui/evidence_page.py`、`reports/html_exporter.py`、`services/report_service.py`、`repositories/report_repository.py`、`tests/test_ui_report.py`  
审查方式：只读静态代码审查；未修改生产代码、测试、数据库或模板；未运行 pytest 或完整回归。  
最终结论：**快照新鲜度存在 Medium 级问题，覆盖目标一致性通过；不建议无条件关闭 C2B 步骤二。**

## 1. 审查范围与结论摘要

本轮只回答两个问题：

1. `ReportSnapshot` 是否可能在同一个项目/类型下被无限期复用，导致报告内容过期；
2. 覆盖成功前的第一次写入与用户确认后的第二次写入，是否始终针对同一个目标文件。

结论：

| 项目 | 结论 | 风险 |
|---|---|---|
| 快照新鲜度 | **不通过**：预览和导出都可能复用旧缓存；Finding/Evidence/Task 数据变化不会通知报告页；手动刷新也不会清除同项目/同类型快照 | **Medium** |
| 覆盖目标一致性 | **通过**：同一次导出中的两次 `write_html_report()` 使用同一个 Snapshot、同一个 Request、固定目录和稳定自动文件名 | **无目标错位风险**；仅保留既有并发 TOCTOU 边界 |

因此：

- **需要**快照新鲜度的最小修复；
- **不需要**为解决“确认覆盖后生成另一个文件”而修改导出器；
- 当前不建议把 C2B 步骤二标记为无条件关闭。

## 2. 快照新鲜度审查

### 2.1 实际调用链

报告页的缓存状态定义于 `ui/report_page.py:53-55`：

```text
_snapshot
_snapshot_project_id
_snapshot_type
```

预览入口 `generate_preview()`（`ui/report_page.py:335-348`）：

```text
generate_preview()
  -> self._ensure_snapshot()
  -> self._request_for(snapshot)
  -> render_html(snapshot, request)
```

导出入口 `export()`（`ui/report_page.py:350-383`）：

```text
export()
  -> self._ensure_snapshot()
  -> self._request_for(snapshot)
  -> self._write(snapshot, request, overwrite=False)
  -> [FileExistsError + confirm]
  -> self._write(snapshot, request, overwrite=True)
```

`_ensure_snapshot()` 的真实决策在 `ui/report_page.py:296-312`：

```python
if (
    self._snapshot is not None
    and self._snapshot_project_id == project_id
    and self._snapshot_type is selected_type
):
    return self._snapshot
snapshot = self._service.get_snapshot(project_id, selected_type)
self._snapshot = snapshot
...
return snapshot
```

也就是说，**只有在没有快照、项目变化或报告类型变化时才重新读取数据库**；相同项目、相同报告类型下，`_ensure_snapshot()` 直接返回原对象。

`ReportService.get_snapshot()` 本身没有缓存：每次调用都会在 `services/report_service.py:94-102` 产生新的 `generated_at`，并由 `repositories/report_repository.py:191-200` 生成新的 `snapshot_id`（`uuid.uuid4().hex`）。因此过期不是 Service 或 Repository 缓存导致的，而是 **ReportPage 的页面级缓存**。

### 2.2 五个问题的直接回答

#### 1) 点击预览时是否重新获取最新 ReportSnapshot？

**否。** `generate_preview()` 调用 `_ensure_snapshot()`；如果当前 `_snapshot` 的 `project_id` 和 `report_type` 与当前页面一致，就返回旧对象，不调用 `ReportService.get_snapshot()`。  
代码：`ui/report_page.py:296-306`、`:339`。

#### 2) 点击导出时是否重新获取最新 ReportSnapshot？

**否。** `export()` 同样先调用 `_ensure_snapshot()`（`ui/report_page.py:362`），因此会复用与预览相同的旧快照。  
这意味着：即使数据库中的 Finding、Evidence 或 Task 已更新，只要项目/类型没变，导出内容仍可能是旧数据。

#### 3) Finding、Evidence、Task 数据变化时，报告页能否感知？

**不能。** 当前没有报告页可用的数据变化信号：

- `AppState` 只有 `project_changed` 和 `projects_changed` 两个信号（`ui/app_state.py:11-13`）；
- `VulnerabilityPage` 的 `data_loaded` 是页面内部信号（`ui/vulnerability_page.py:61`），没有连接到报告页；
- `EvidencePage` 的 `data_loaded` 同样是页面内部信号（`ui/evidence_page.py:58`），没有连接到报告页；
- `MainWindow._on_page_changed()` 只在切换到 `"reports"` 时调用 `report_page.refresh()`（`ui/main_window.py:232-248`）；
- 该 `refresh()` 不会无条件使快照失效（见下一问）。

因此，即使漏洞状态改变、证据新增/删除、扫描任务完成，报告页在自身可见且项目/类型未变时不会自动刷新快照。

#### 4) `_ensure_snapshot()` 是否可能复用过期快照？

**会，而且可以无限期复用。**  
只要：

```text
_snapshot is not None
_snapshot_project_id == 当前项目 ID
_snapshot_type == 当前报告类型
```

就返回旧 `_snapshot`。没有 TTL、版本号、数据库 revision、快照内容哈希或“数据已变化”标记。  
代码：`ui/report_page.py:301-306`。

#### 5) 手动刷新是否能够清除旧快照并重新生成预览？

**否。** 刷新按钮连接到 `self.refresh`（`ui/report_page.py:76-77`），而 `refresh()` 的逻辑在 `:246-270`：

- 无项目时：清除快照；
- 有项目且快照的项目/类型不匹配时：清除快照；
- 有项目且快照的项目/类型相同：**不清除，也不重新获取**；仅在 `_snapshot is None` 时更新“请先生成预览”的状态；
- 预览内容不会因为刷新而重新生成。

因此，当前“刷新”按钮不能解决同一项目/同一类型下的数据过期问题。

### 2.3 风险判断

**风险等级：Medium。**

原因：

- 不会造成越权、任意路径写入或跨项目读取；项目/类型隔离仍由 `_ensure_snapshot()` 的 ID/type 检查和 `ReportService` 的项目过滤共同保证；
- 但会产生**安全报告完整性/时效性问题**：报告可能显示旧的 Finding 状态、遗漏新增证据、遗漏新任务结果，或继续显示已修复问题；
- 用户界面没有明确的“快照已过期”提示；摘要中的 `generated_at` 只能反映旧快照生成时间，不能阻止用户误导出；
- 报告用于审计/交接时，过期快照可能导致错误判断。

### 2.4 最小修复建议

只修改 `ui/report_page.py`，不扩大到导出器或数据库：

1. 预览/导出的动作入口不再复用页面缓存的旧快照：
   - 新增 `_load_snapshot()`，每次 `generate_preview()` 和 `export()` 开始时调用 `ReportService.get_snapshot(project_id, type)`；
   - 或为 `_ensure_snapshot(force_refresh=True)` 增加显式强制路径。
2. 单次导出中的两次写入必须继续复用同一个局部 `snapshot` 和 `request`：
   - 在 `export()` 内只获取一次新快照；
   - 第一次 `overwrite=False` 和第二次 `overwrite=True` 使用同一个 `snapshot`、同一个 `request`；
   - 这样既修复跨动作的过期，又不破坏覆盖目标一致性。
3. `refresh()` 应当清除缓存并清空旧预览；刷新后提示用户重新生成预览。
4. 增加两个测试：
   - 预览后插入/修改 Finding，再导出，断言导出使用的是新快照；
   - 预览后点击刷新，断言 `_snapshot is None`，旧预览被清空。

**兼容性说明：** `_default_filename()` 基于 `snapshot.snapshot_id`（`reports/html_exporter.py:683-690`）。强制每次动作生成新快照会使自动文件名变化，因此重复导出通常不会命中上一份旧文件，而是生成新文件。这是更安全的行为，但会改变“重复导出触发覆盖确认”的用户体验；如果产品要求保持稳定的可覆盖文件名，应另行决定是否把文件名与快照 ID 解耦。本轮不实施该产品决策。

## 3. 覆盖目标一致性审查

### 3.1 实际调用链

`ui/report_page.py:350-383` 的导出逻辑：

```python
snapshot = self._ensure_snapshot()
request = self._request_for(snapshot)
try:
    artifact = self._write(snapshot, request, overwrite=False)
except FileExistsError:
    if not confirm(...):
        ...
    artifact = self._write(snapshot, request, overwrite=True)
```

`_write()`（`ui/report_page.py:385-398`）固定传入：

```python
write_html_report(
    snapshot,
    request,
    self._reports_dir,
    overwrite=overwrite,
    filename=None,
)
```

两次调用：

- `snapshot` 是同一个局部变量；
- `request` 是同一个局部变量；
- `reports_dir` 是同一个 `context.config.reports_dir`；
- `filename=None` 两次相同。

`reports/html_exporter.py:327-390` 的 `write_html_report()`：

1. `render_html(snapshot, request)`；
2. `target_name = _validate_filename(filename or _default_filename(snapshot))`（`:349`）；
3. `candidate = root / target_name`（`:350`）；
4. 检查 `candidate` 不是 symlink/junction（`:353-360`）；
5. 使用原始 `candidate` 作为 `target`（`:364`）；
6. `target.exists() and not overwrite` 时抛出 `FileExistsError`（`:371-372`）；
7. `_atomic_write(target, payload, overwrite=overwrite)`（`:378`）。

`_default_filename()`（`reports/html_exporter.py:683-690`）只使用：

```text
project_{project_id}_{report_type}_{snapshot_id 前 12 个字母数字}.html
```

不使用当前时间、标题、用户输入路径或随机数；同一 `snapshot` 对象得到同一个文件名。

`_atomic_write()`（`reports/html_exporter.py:719-754`）：

- `overwrite=False`：`_publish_exclusive()`，通过 `os.link()` 原子排他发布（`:693-716`）；
- `overwrite=True`：`os.replace(temporary, target)`（`:734-736`）；
- 两种路径的 `target` 都是同一个原始 `candidate`。

### 3.2 四个问题的直接回答

#### 1) 两次调用是否使用同一 Snapshot 和 Request？

**是。** `export()` 在 `:362-363` 获取一次 `snapshot` 和一次 `request`，两次 `_write()` 都传入这两个局部变量；没有在 `FileExistsError` 分支重新调用 `_ensure_snapshot()` 或 `_request_for()`。

#### 2) 自动文件名是否稳定？

**是（针对同一个 Snapshot）。** `_default_filename()` 只依赖 `snapshot.project_id`、`snapshot.report_type.value` 和 `snapshot.snapshot_id`；同一个对象重复调用结果相同。  
`request.requested_at` 虽然存在（`ui/report_page.py:331`），但**不参与文件名**。

#### 3) 两次调用是否保证指向同一个目标文件？

**是。** 两次都：

```text
reports_dir = self._reports_dir
filename = None
snapshot = 同一个对象
```

因此 `_default_filename()` 产生同一个 `target_name`，`target` 都是 `root / target_name`。第一次 `overwrite=False` 抛出的 `FileExistsError`，第二次 `overwrite=True` 仍写同一个 `target`。

#### 4) 是否可能出现用户确认覆盖后，实际生成另一个文件的情况？

**在正常的顺序调用路径中，不会。**  
当前代码没有“失败后重新生成快照”“失败后重新计算文件名”“切换到备用名称”“尝试另一个扩展名”或“回退到随机临时名”的逻辑。第二次写入的目标由同一个 `snapshot` 和同一个固定目录决定。

需要区分的两个既有边界：

- **并发替换**：如果另一个进程在第一次失败和第二次 `os.replace()` 之间替换了同路径文件，第二次仍写同一路径，但覆盖的内容可能已不是用户确认时看到的版本。这是既有 C2A/R1 的 TOCTOU 限制，不是“生成另一个文件”。
- **目标是目录**：`target.exists() and not overwrite` 在 `target.is_dir()` 检查之前（`reports/html_exporter.py:371-374`），因此目录也会先触发 `FileExistsError`，用户确认后再由 `overwrite=True` 路径报“报告目标不是文件”。这会造成一次无效的覆盖确认，但不会创建另一个文件，也不会替换目录。该行为属于低风险 UX 边界，不建议在本轮扩大修改。

### 3.3 风险判断

**覆盖目标一致性：通过；无目标错位风险。**

剩余风险：

- 并发 TOCTOU：既有已知限制，**Low/记录在案**；
- 目录目标先触发覆盖确认：**Low UX**，不改变目标路径，不产生另一个文件。

本轮不建议为“覆盖目标一致性”修改 `ui/report_page.py` 或 `reports/html_exporter.py`。

## 4. 具体代码位置

| 主题 | 文件与行号 | 说明 |
|---|---|---|
| 页面缓存字段 | `ui/report_page.py:53-55` | `_snapshot`/`_snapshot_project_id`/`_snapshot_type` |
| 预览入口 | `ui/report_page.py:335-348` | `generate_preview()` 调用 `_ensure_snapshot()` |
| 导出入口 | `ui/report_page.py:350-383` | 获取一次 snapshot/request，两次 `_write()` |
| 缓存复用条件 | `ui/report_page.py:296-306` | 相同项目/类型直接返回旧快照 |
| 刷新逻辑 | `ui/report_page.py:246-270` | 相同项目/类型不清除、不重取 |
| 刷新按钮 | `ui/report_page.py:76-77` | 连接到 `self.refresh` |
| 固定目录 | `ui/report_page.py:52` | `context.config.reports_dir` |
| 两次写入 | `ui/report_page.py:364-375` | 同一 snapshot/request，overwrite 仅变化 |
| 自动文件名 | `reports/html_exporter.py:683-690` | 基于 snapshot ID，稳定 |
| 目标构造 | `reports/html_exporter.py:345-374` | 原始 candidate、symlink/junction 检查、存在性检查 |
| 排他发布 | `reports/html_exporter.py:693-716` | `os.link()`，不覆盖 |
| 覆盖发布 | `reports/html_exporter.py:734-736` | `os.replace()`，同一 target |
| 应用状态信号 | `ui/app_state.py:11-13` | 只有项目信号，无数据 revision |
| 页面刷新分发 | `ui/main_window.py:232-248` | 仅导航时调用 `report_page.refresh()` |
| 漏洞页内部信号 | `ui/vulnerability_page.py:42-62` | `data_loaded` 未连接报告页 |
| 证据页内部信号 | `ui/evidence_page.py:39-59` | `data_loaded` 未连接报告页 |
| 快照生成 | `services/report_service.py:94-102` | 每次调用重新读取；页面未调用 |
| 快照 ID | `repositories/report_repository.py:191-200` | `uuid.uuid4().hex` |

## 5. 风险汇总

| 编号 | 问题 | 等级 | 结论 | 是否本轮修复 |
|---|---|---|---|---|
| R-01 | 同项目/同类型下预览和导出复用旧快照 | **Medium** | 确认存在 | 建议最小修复，未实施 |
| R-02 | Finding/Evidence/Task 变化不通知报告页 | **Medium** | 与 R-01 同一根因 | 随 R-01 处理 |
| R-03 | 手动刷新不清除旧快照 | **Medium** | 确认存在 | 随 R-01 处理 |
| R-04 | 覆盖重试目标不一致 | **无** | 未发现 | 不需要 |
| R-05 | 并发替换同路径内容 | **Low（既有）** | 既有 TOCTOU 限制 | 不在本轮扩大 |
| R-06 | 目录目标先触发覆盖确认 | **Low UX** | 不产生另一个文件 | 不建议本轮扩大 |

## 6. 实际修改文件清单

本轮只新增：

```text
docs/PHASE6_C2B_STEP2_REVIEW.md
```

没有修改生产代码、测试、数据库、Schema 或模板。  
没有运行 pytest、完整回归、真实导出或数据库写入。

审查时边界文件哈希：

```text
ui/report_page.py                 18,278  F558F8D21895FC29C2A95E8DF3F43643B1CC1EBF6AE03765059BC6DD3AC363F6
ui/app_state.py                    1,354  B300CEB3362DFBB0E7E6A26F08540E756A86464B86E493D44203FB71E0E05BFD
ui/main_window.py                 13,264  0F673ECC499C8C85ADF880E0F4EB9F3E7FE4C0EC9190DE20B6C8E7B0DE036F69
ui/vulnerability_page.py          23,436  C8517760A50E798C168A8C1A565ADDED5EDF6006D28011B3F49C16B3074D9AB9
ui/evidence_page.py               17,146  3EA86D20AC9A6727507C054CEEFF27D1AD16C18F46F3E9BDDCF2420934A1A54B
reports/html_exporter.py          24,953  207AA3571B4D1900472CFCD8FB75856DCF354335AD81AB905AA35B69D3FAB480
services/report_service.py        13,179  7E0E56A5B4E69BE1EE6F36B0B16AE2C02B40F50416DC1DD43C1697034D9CFFCD
repositories/report_repository.py 11,847  1553BEADF2ADD1F85FE8A5F0271114AAB485BE6F47C3160BDCA4A0A1902F4636
tests/test_ui_report.py           10,321  3A8205BAFC0484832C019A5B7056BC2C5CFC557E6021C69CA4F203D30A895E9C
```

## 7. 是否建议正式关闭 C2B 步骤二

**不建议无条件关闭。**

建议状态：

```text
STEP_2_REVIEW = COMPLETED_WITH_FINDING
CLOSURE = NOT_CLOSED_PENDING_SNAPSHOT_FRESHNESS_FIX
TARGET_CONSISTENCY = PASS
```

理由：

- 覆盖目标一致性已通过，导出器不需要为目标错位修改；
- 快照新鲜度是 Medium 级报告完整性问题，且当前手动刷新不能修复；
- 最小修复范围可限制在 `ui/report_page.py` 与相应 UI 测试；
- 完成最小修复并补做目标测试后，再考虑正式关闭 C2B 步骤二。

本轮到此停止，未开始 C2B 步骤三，未开始 JSON/PDF，未修改任何生产代码或测试。
