# Git-3D：受限临时目录最小排除规则修订与最终 Dry-run

- 日期：2026-11-11
- 项目：`D:\挖漏洞\SRC-Research-Assistant`
- 目标：对 Git-3C 确认的 4 个 ACL 受限临时目录增加最小、精确的版本控制排除规则，并重新验证忽略规则与 `git add -n .`。
- 结论：`.gitignore` 精确规则已生效；4 条 ACL 警告在最终 dry-run 中不再出现；候选文件未包含禁止项；未执行真实暂存、提交或 remote 配置。

---

## 1. 修改范围

本轮只修改以下两个文件：

| 文件 | 类型 | 说明 |
|---|---|---|
| `.gitignore` | 修改 | 在既有 27 行规则后追加 5 行（1 行注释、1 行空行、3 条精确规则） |
| `docs/GIT_3D_FINAL_IGNORE_AND_DRYRUN.md` | 新增 | 本报告 |

没有修改：

- Python 源码、测试代码；
- 数据库或 Schema；
- `reports/html_exporter.py`、`reports/templates/`；
- `services/report_service.py`、`repositories/report_repository.py`；
- `config.yaml`；
- Windows ACL、目录所有权或受限目录内容；
- E 盘正式备份。

### `.gitignore` 修改前后

| 指标 | 修改前 | 修改后 |
|---|---:|---:|
| 字节数 | 382 | 496 |
| 行数 | 27 | 32 |
| SHA-256 | `B4550871B438DD17719F854C896B4720309E761031016CA0C188F5589D73A1D8` | `312E11686F9BD77DD5E71E778F4BE1EF580AC13BB1484442DB7D09E04068151C` |

追加内容位于原第 27 行之后：

```gitignore
# Investigated ACL-restricted temporary directories
/storage/_c1_pytest_tmp/
/storage/tmpv2ziyrtj/
/tmpcde5t8kh/
```

原 18 条规则全部保留；未替换为任何宽泛的 `tmp*/`、`storage/tmp*/` 或 `storage/*tmp*/` 规则。

---

## 2. 新增规则及理由

| 规则 | 对应路径 | 调查依据 | 为什么使用精确路径 |
|---|---|---|---|
| `/storage/_c1_pytest_tmp/` | `storage/_c1_pytest_tmp/pytest-of-lenovo`、`storage/_c1_pytest_tmp/tmp5kedbboy` | Git-3C 确认 `pytest-of-lenovo` 为 PYTEST_TEMP；同目录下的 `tmp5kedbboy` 为测试临时目录候选 | 覆盖测试临时根目录，不排除其他 `storage/tmp*` 或业务目录 |
| `/storage/tmpv2ziyrtj/` | `storage/tmpv2ziyrtj` | 名称、位置、创建时间指向测试/运行时临时目录；不可读取 | 精确排除单个已调查目录，避免误伤未来同前缀目录 |
| `/tmpcde5t8kh/` | `tmpcde5t8kh` | 位于项目根，名称/位置指向临时测试目录；不可读取 | 精确排除单个已调查目录，不使用根级 `tmp*` |

这些规则只影响 Git 的路径忽略判断，不改变目录存在性、ACL、内容或项目运行行为。

---

## 3. ACL 路径处理结果

本次采用“基于现有调查证据的项目级版本控制排除决策”。这是忽略规则决策，不是对目录内容的读取确认。

| 原路径 | Git-3C 分类 | Git-3D 规则 | 是否成功覆盖 | 是否需要读取目录内容 |
|---|---|---|---|---|
| `storage/tmpv2ziyrtj` | RUNTIME_TEMP / INFERENCE | `/storage/tmpv2ziyrtj/` | 是 | 否；未读取 |
| `storage/_c1_pytest_tmp/pytest-of-lenovo` | PYTEST_TEMP / CONFIRMED | `/storage/_c1_pytest_tmp/` | 是 | 否；未读取 |
| `storage/_c1_pytest_tmp/tmp5kedbboy` | PYTEST_TEMP / INFERENCE | `/storage/_c1_pytest_tmp/` | 是 | 否；未读取 |
| `tmpcde5t8kh` | RUNTIME_TEMP / INFERENCE | `/tmpcde5t8kh/` | 是 | 否；未读取 |

实际 `git check-ignore -v`：

```text
.gitignore:31:/storage/tmpv2ziyrtj/	storage/tmpv2ziyrtj
.gitignore:30:/storage/_c1_pytest_tmp/	storage/_c1_pytest_tmp/pytest-of-lenovo
.gitignore:30:/storage/_c1_pytest_tmp/	storage/_c1_pytest_tmp/tmp5kedbboy
.gitignore:32:/tmpcde5t8kh/	tmpcde5t8kh
```

本次通过版本控制规则排除，不修改 Windows ACL，不代表已经读取确认目录内部所有内容。没有执行 `takeown`、ACL 修改、目录删除或绕过 ACL 的读取。

---

## 4. Git 忽略验证

### 4.1 ACL 受限路径

四条路径均已命中 `.gitignore`，如上表；`git check-ignore` 退出码均为 `0`。

### 4.2 正常重要文件代表样本

以下实际存在路径均**未**被忽略（`git check-ignore` 退出码非 0）：

- `app/application.py`
- `tests/test_ui_report.py`
- `README.md`
- `requirements.txt`
- `pytest.ini`
- `config.yaml`
- `storage/acceptance/config.yaml`
- `docs/GIT_3C_ACL_AND_CANDIDATE_AUDIT.md`
- `docs/acceptance/phase3_acceptance.json`
- `docs/acceptance/PHASE3_TEST_REPORT.md`
- `reports/templates/base.html`
- `storage/evidence/.gitkeep`
- `storage/acceptance/authorization.pdf`
- `docs/acceptance/phase5_vulnerability_management.png`

### 4.3 原有禁止项代表样本

以下路径均被忽略，规则未被新规则覆盖或删除：

```text
pytest-of-lenovo                         /pytest-of-*/
.pytest_cache                            .pytest_cache/
storage/src_research.db                  *.db
storage/src_research.db-wal              *.db-wal
storage/src_research.db-shm              *.db-shm
storage/logs/app.log                     /storage/logs/*.log
storage/logs/audit.jsonl                 /storage/logs/*.jsonl
storage/reports/project_1_...html        /storage/reports/*.html
backups                                  /backups/
storage/backups                          /storage/backups/
```

未发现正常源码、测试、文档、验收材料、配置、授权 PDF、Evidence PNG 或报告模板被新增规则误排除。

---

## 5. Dry-run 结果

### 5.1 规则生效后、本报告生成前

```text
命令：git add -n .
退出码：0
警告数：0
候选文件数：221
候选总大小：4,298,195 bytes
```

与 Git-3C 的对比：

| 指标 | Git-3C 生成后 | Git-3D 规则生效后 | 差异 |
|---|---:|---:|---:|
| 候选数 | 221 | 221 | 0 |
| 候选字节 | 4,298,081 | 4,298,195 | +114 |

差异来自 `.gitignore` 本体的规则追加（382→496 bytes），不是新文件进入或重要文件丢失。4 条 ACL 警告不再出现；受限目录未进入候选。

### 5.2 禁止项检查

候选清单中：

```text
pytest-of-lenovo/  : 0
__pycache__/       : 0
.pytest_cache/     : 0
*.pyc              : 0
*.db               : 0
*.db-wal           : 0
*.db-shm           : 0
/backups/          : 0
/storage/backups/  : 0
storage/logs/*     : 0
/storage/reports/*.html : 0
.env               : 0
```

`UNEXPECTED_CANDIDATE_FILES=NO`。

### 5.3 本报告自身的影响

本报告生成后实际增加 1 个候选文件：

```text
候选文件数：222
REPORT_BYTES=8180
TOTAL_BYTES=4306375
```

该变化仅来自本报告；最终 total 为 `git add -n .` 的实际统计值。

---

## 6. Git 工作区状态

```text
REAL_STAGING_PERFORMED = NO
COMMIT_CREATED = NO
REMOTE_CONFIGURED = NO
```

- `git diff --cached --name-only`：空（0 行）。
- `HEAD`：不存在；`git rev-parse --verify HEAD` 退出码 128。
- 分支：`main`。
- remote：无输出。
- `git status --short`：仅显示未跟踪的项目根/目录；没有已暂存文件。
- 未执行 `git add .`、`git add -A`、`git commit`、`git remote add`、`git push`。
- 未执行 `git init`（仓库已存在）；未修改 Git 索引。

---

## 7. 最终状态

```text
GITIGNORE_FINAL_STATUS = PASS
ACL_WARNING_STATUS = RESOLVED
UNEXPECTED_CANDIDATE_FILES = NO
IMPORTANT_FILES_MISSING = NO
REAL_STAGING_PERFORMED = NO
COMMIT_CREATED = NO
REMOTE_CONFIGURED = NO
FIRST_COMMIT_READINESS = GO
```

判定说明：

- **PASS**：3 条精确规则生效，4 个受限路径全部命中，正常样本未被误伤。
- **RESOLVED**：规则生效后的 `git add -n .` 为 0 条 ACL 警告；这表示 Git 不再枚举这些已忽略目录，不代表目录 ACL 已修复。
- **NO（未发现意外候选）**：221 个候选中 0 个禁止项；报告自身增加 1 个候选。
- **NO（未发现重要文件缺失）**：重要正常样本均未 ignored；受限目录内容未读取，因此该项限定为“已知项目文件范围”，不声称验证了不可枚举内容。
- **GO**：在人工接受“受限临时目录已被精确排除、内容未读取”这一前提后，可进入 Git-4 首次真实暂存审计；本轮不执行 Git-4。

本次不进入：

- Git-4 真实暂存；
- `git commit`；
- GitHub/remote；
- Phase 6P-2 文档清理；
- Phase 6D。
