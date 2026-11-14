# Phase 6-D1B-1 JSON 报告业务需求核查

## 0. 结论摘要

```text
JSON_BUSINESS_REQUIREMENT = INSUFFICIENT_EVIDENCE
JSON_DEVELOPMENT_APPROVED = NO
D1B_2_BUSINESS_BASIS = NO
D1B_2_READINESS = NO_GO
PHASE6_D1B_1_STATUS = PASS
```

结论是 **INSUFFICIENT_EVIDENCE**，不是 `NOT_SUPPORTED`：

- 当前没有证据证明目标用户需要 JSON 报告；
- 但同样没有足够证据证明 JSON 在所有未来场景中都没有价值；
- 因此不能把“技术上可以生成 JSON”写成“业务上需要 JSON”，也不能把“没有找到需求”写成“用户永远不需要”。

本次调查 **没有批准 JSON 开发**，没有创建 JSON Contract，没有实现 exporter，也没有进入 D1B-2。

---

## 1. 调查范围和方法

### 1.1 范围

本次只读调查以下问题：

1. 当前目标用户及实际使用场景；
2. 用户是否需要把报告导入其他系统；
3. 是否存在真实自动化、CI/CD 或第三方系统对接需求；
4. 是否存在无法通过现有 HTML 报告解决的业务问题；
5. JSON 的安全、维护和兼容性成本；
6. 是否存在需求文档、用户反馈或其他需求证据。

### 1.2 方法

- 阅读当前产品说明：`README.md`；
- 阅读当前报告与架构材料：
  - `docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md`
  - `docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md`
  - `docs/PHASE6_B_REPORT.md`
  - `docs/PHASE6_C1_HTML_INVESTIGATION.md`
  - `docs/PHASE6_C2B_STEP3_ACCEPTANCE.md`
- 检索项目内与 `JSON`、`CI/CD`、第三方系统、自动化、机器可读、用户反馈、需求文档相关的内容；
- 检查是否存在 CI/CD 配置、需求/反馈文档或其他外部消费方接口；
- 只读查看当前 GUI 与报告能力说明，不启动应用，不运行测试，不打开数据库。

### 1.3 本次实际修改

```text
仅新增：
docs/PHASE6_D1B_1_JSON_BUSINESS_REQUIREMENTS.md

未修改生产代码、测试、数据库、Schema、GUI、HTML exporter 或模板。
未执行 Git add / commit / push。
```

调查开始时：

```text
HEAD = bffb5ac82bbebe7fef5992f87ff90494c9776ace
branch = main
staged = 0
worktree = M docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md
```

---

## 2. 目标用户及业务场景证据

### 2.1 当前能确认的用户定位

`README.md:3` 只给出了一个概括性定位：

> 面向合法授权软件安全研究的 Windows 桌面工作台。

`README.md:5` 进一步说明安全边界：只用于已取得明确书面授权的安全研究，不包含远程扫描、网站扫描、漏洞利用、密码爆破、自动攻击、证据上传或报告生成能力。

但当前文档没有提供：

- 用户角色清单（个人研究者、团队成员、评审者、客户等）；
- 每个角色的工作流；
- 报告的实际接收方；
- 报告生成频率；
- 用户如何使用报告；
- 任何用户访谈、试用反馈或工单记录。

因此，当前只能确认“本地桌面安全研究工作台”这一定位，不能从中推出某个用户需要机器可读 JSON。

### 2.2 当前实际业务链路

根据 `README.md:38-158` 和当前实现，现有链路是：

```text
本地项目
  -> 本地 Python 源代码审计 / 依赖漏洞审计
  -> Finding 管理
  -> 证据中心
  -> HTML 报告中心（本地预览与导出）
```

这是一套以人工操作、本地查看和人工交付为主的桌面流程。当前没有显示：

- 报告被某个自动化系统定时读取；
- 报告被上传到第三方平台；
- 报告进入 CI/CD 产物链；
- 报告作为其他系统的输入。

### 2.3 实际使用场景的证据强度

| 事项 | 当前证据 | 强度 |
|---|---|---|
| Windows 桌面工作台 | `README.md:3` | 明确 |
| 本地项目、本地审计、人工报告 | `README.md:38-158` | 明确 |
| 具体用户角色 | 未找到 | 不足 |
| 具体报告消费方 | 未找到 | 不足 |
| 使用频率/规模 | 未找到 | 不足 |
| 用户对 JSON 的明确诉求 | 未找到 | 不足 |

### 2.4 文档一致性问题

`README.md:5` 仍写着“不包含……报告生成能力”，但同一文件的：

- `README.md:18` 写明已加入 HTML 报告中心；
- `README.md:43` 写明报告中心（HTML 报告）已实现；
- `README.md:162` 写明 HTML 报告已实现、PDF 已取消、JSON 未实施且未获批准。

这是当前产品文案的遗留冲突，不是 JSON 需求证据。它说明：

1. 当前文档仍需要维护；
2. 不能用旧的能力声明反推 JSON 已获批准；
3. 也不能因为文档写了“报告中心”就推定存在 JSON 消费方。

---

## 3. JSON 的实际需求证据

### 3.1 项目内直接证据

检索结果中，`JSON` 的出现主要分为四类：

1. **扫描器输入/输出格式**：Bandit、Semgrep、pip-audit 的 JSON 输出解析，例如 `README.md:86-100`；
2. **审计日志/历史序列化**：`scan_logs`、`authorization_history` 使用 JSON 文本保存结构化详情，例如 `docs/ARCHITECTURE.md:99,133,218`；
3. **报告架构中的未来输出格式**：`ReportFormat.JSON` 枚举、`docs/PHASE6_D1A...` 的潜在接入点；
4. **历史报告中对未来 JSON 的提及**：`docs/PHASE6_B_REPORT.md`、`docs/PHASE6_C1_HTML_INVESTIGATION.md` 等。

这些都不是“用户需要 JSON 报告”的直接证据。

尤其需要区分：

```text
扫描器输出 JSON
  ≠ 报告导出 JSON
  ≠ 用户需要报告 JSON
  ≠ JSON 已获产品批准
```

### 3.2 当前 JSON 的真实状态

项目当前对 JSON 报告的状态是：

- `README.md:162`：**JSON 报告导出尚未实施，也未获得实施批准**；
- `reports/__init__.py`：JSON report export is not implemented and has not been approved；
- `docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md:614-620`：
  - `JSON_CONSUMER = UNKNOWN`
  - `JSON_FIELD_CONTRACT = UNKNOWN`
  - `JSON_SCHEMA_VERSION = UNKNOWN`
  - `WHETHER_JSON_EXPORT_IS_PRODUCT_APPROVED = UNKNOWN / CURRENTLY NOT APPROVED`
- `docs/PHASE6_NEXT_STEP_CONTINUATION_AUDIT.md:363-372` 把“用户明确批准 JSON 报告导出”和“明确 JSON 消费方和使用场景”列为前置条件。

这些材料的共同含义是：

```text
JSON 是技术上可讨论的未来输出格式，
不是当前已确认的用户需求，
不是当前已批准的产品范围。
```

### 3.3 是否存在“无法用 HTML 解决”的具体问题

未找到以下任何具体问题：

- 某个下游系统只能读取 JSON；
- 某个 CI 任务需要解析报告；
- 某个团队需要把报告入库；
- 某个客户要求机器可读交付；
- HTML 报告在某个真实工作流中不可用；
- 用户明确表示需要 JSON 而非 HTML。

当前只有架构层面的“JSON 可能适合机器处理”这一般性判断。它不能替代具体业务问题。

### 3.4 结论

```text
JSON_REPORT_DIRECT_USER_REQUEST = NOT_FOUND
JSON_REPORT_CONCRETE_USE_CASE = NOT_FOUND
JSON_REPORT_UNMET_BUSINESS_PROBLEM = NOT_FOUND
JSON_REPORT_REQUIREMENT_EVIDENCE = INSUFFICIENT
```

---

## 4. CI/CD 和第三方系统对接证据

### 4.1 未发现 CI/CD 配置

本次在项目工作区内检查：

- `.github/**`
- `.gitlab-ci.yml`
- `Jenkinsfile`
- `azure-pipelines.yml`
- 其他 `*.yml` / `*.yaml`

除以下配置/规则文件外，没有发现 CI/CD 工作流：

- `config.yaml`
- `storage/acceptance/config.yaml`
- `storage/phase3_acceptance/config.yaml`
- `storage/phase4_acceptance/config.yaml`
- `storage/phase5_acceptance/config.yaml`
- `scanners/rules/python_security.yml`

未发现：

- GitHub Actions；
- GitLab CI；
- Jenkins；
- Azure Pipelines；
- 其他持续集成/持续交付脚本；
- 报告作为构建产物的消费链。

因此，当前没有可验证的 CI/CD 对接需求。

### 4.2 未发现第三方系统接口

当前项目没有：

- 报告上传 API；
- 报告推送 webhook；
- 第三方缺陷平台/工单系统连接器；
- 报告消费者配置；
- 外部系统认证/凭据配置；
- 机器可读报告的下游协议或 schema 协商记录。

`README.md:166-168` 中列出的“外部漏洞记录批量导入”仍是未实现占位项，且方向是“导入”，不是“报告导出给第三方”。

### 4.3 不能把未来可能性写成当前需求

可以设想未来把 JSON 报告接入 CI/CD 或第三方平台，但本次没有找到：

- 已确认的对接方；
- 已确认的字段需求；
- 已确认的传输方式；
- 已确认的验收标准；
- 已确认的时间表或负责人。

因此，CI/CD/第三方对接只能记为 **UNKNOWN / NOT FOUND**，不能写成“已确认需求”。

```text
CI_CD_INTEGRATION_REQUIREMENT = NOT_FOUND
THIRD_PARTY_INTEGRATION_REQUIREMENT = NOT_FOUND
CI_CD_CONSUMER = UNKNOWN
```

---

## 5. HTML 是否已经满足现有需求

### 5.1 当前 HTML 能力

`README.md:18,43,162` 与当前实现说明：

- HTML 报告中心已实现；
- 支持本地预览和导出；
- 报告中心当前只暴露 HTML 格式；
- PDF 已取消；
- JSON 未实施、未批准。

`docs/PHASE6_C2B_STEP3_ACCEPTANCE.md` 的验收范围也明确只验收 HTML 报告、GUI、快照一致性和安全边界，不验收 PDF/JSON/报告历史。

### 5.2 现有证据说明什么

当前能说明的是：

- HTML 是唯一已交付的报告格式；
- 现有用户工作流被描述为本地桌面操作；
- 没有发现 HTML 在真实交付中失败或被拒绝的记录；
- 没有发现“必须使用 JSON 才能完成”的任务。

当前不能说明的是：

- 所有用户都满意 HTML；
- HTML 已覆盖所有未来集成场景；
- 没有潜在用户会需要机器可读格式。

因此，对 HTML 的判断应当是：

```text
HTML_CURRENTLY_MEETS_DOCUMENTED_NEEDS = YES_WITH_LIMITED_EVIDENCE
HTML_UNMET_REQUIREMENT_FOUND = NO
```

“未发现未满足需求”不等于“已证明没有未满足需求”；这是本条的证据边界。

### 5.3 现有产品文案的风险

`README.md:5` 的旧表述与当前 HTML 实现冲突，说明文档维护仍有缺口。这个缺口会影响需求判断的可信度，但不能反过来被解释为 JSON 需求。

---

## 6. JSON 的预期收益与维护成本

### 6.1 可能的收益（均为假设，不是当前已证实收益）

如果未来存在明确消费方，JSON 可能带来：

- 机器可读，便于自动化处理；
- 便于版本比较和差异分析；
- 便于导入工单/资产/漏洞平台；
- 便于测试断言和结构化归档。

但这些收益目前没有对应的：

- 消费方；
- 使用频率；
- 业务指标；
- 验收标准；
- 真实工作流。

所以不能把它们写成当前收益。

### 6.2 已能识别的成本

根据 `docs/PHASE6_D1A_REPORT_ARCHITECTURE_INVESTIGATION.md:585-609`，JSON 至少引入：

1. **字段 allowlist / projection**
   - `ReportSnapshot.project` 含 `local_path`、`description`；
   - `ReportFinding.file_path`、`ReportEvidence.file_path` 是原始路径；
   - `ReportTaskSummary.target`、`error_message` 可能包含内部信息；
   - 不能直接 `dataclasses.asdict()` 或 `json.dumps(snapshot)`。

2. **HTML 与 JSON 的数据选择分叉**
   - 当前 `_select_findings()` / `_select_evidence()` 在 HTML exporter 内；
   - JSON 若另写一套，可能对同一快照输出不同范围；
   - 需要额外的一致性测试和契约维护。

3. **Schema/契约版本**
   - 当前 `JSON_CONSUMER`、`JSON_FIELD_CONTRACT`、`JSON_SCHEMA_VERSION` 均为 UNKNOWN；
   - 一旦有外部消费方，字段变更需要兼容策略。

4. **安全与隐私**
   - 原始绝对路径、项目描述、任务目标/错误、Finding/Evidence 路径均可能敏感；
   - JSON 需要独立 allowlist、编码和大小限制；
   - 不能假设 HTML 的文本截断/转义等于 JSON 的安全策略。

5. **维护与测试**
   - 新增 exporter、测试、GUI 入口和文档；
   - 需要覆盖空结果、敏感字段、三种报告类型、文件名/覆盖/失败清理；
   - 若接入报告历史，还会引入 `reports` 表写入和保留策略。

### 6.3 成本收益判断

在当前没有消费者、没有字段契约、没有 CI/CD 需求的情况下：

```text
EXPECTED_BENEFIT = HYPOTHETICAL
IMPLEMENTATION_COST = NON_TRIVIAL
SECURITY_COST = NON_TRIVIAL
MAINTENANCE_COST = NON_TRIVIAL
COST_BENEFIT_JUSTIFICATION = NOT_ESTABLISHED
```

技术可实现的收益不能自动覆盖上述成本。

---

## 7. 未知事项和证据不足之处

```text
TARGET_USER_ROLES = UNKNOWN
REPORT_CONSUMER = UNKNOWN
JSON_REPORT_USE_CASE = UNKNOWN
REPORT_FREQUENCY = UNKNOWN
JSON_FIELD_CONTRACT = UNKNOWN
JSON_SCHEMA_VERSION = UNKNOWN
REPORT_RETENTION_POLICY = UNKNOWN
THIRD_PARTY_INTEGRATION = UNKNOWN
CI_CD_INTEGRATION = UNKNOWN
USER_FEEDBACK = NOT_FOUND
REQUIREMENTS_DOCUMENT = NOT_FOUND
PRODUCT_APPROVAL_FOR_JSON = NOT_APPROVED
```

证据不足的具体表现：

1. 没有用户访谈、试用记录、问卷或工单；
2. 没有明确的报告接收方；
3. 没有下游系统或 CI/CD 消费链；
4. 没有 JSON 字段/版本要求；
5. 没有报告安全分级和保留策略；
6. 没有对 HTML 不足之处的真实记录；
7. 现有产品文档仍有一处“报告生成能力未包含”的旧表述，与已实现的 HTML 报告冲突；
8. 项目没有遥测/使用统计，无法从使用数据推断需求。

这些未知事项不能由实现者自行填补，也不能用“以后可能会用”替代。

---

## 8. 是否存在足以进入 D1B-2 的业务依据

### 8.1 判断

```text
D1B_2_BUSINESS_BASIS = NO
D1B_2_READINESS = NO_GO
```

理由：

- 没有已确认的 JSON 消费方；
- 没有已确认的业务场景；
- 没有 CI/CD 或第三方系统对接证据；
- 没有 HTML 无法解决的具体问题；
- 没有需求文档或用户反馈；
- JSON 的字段、版本、安全 allowlist 和验收标准都未确定；
- 当前 JSON 仍为 `NOT_APPROVED`。

在这些条件未满足前，进入 D1B-2（JSON Contract/Approval）会把“架构上可接入”误当成“业务上需要接入”，并把临时字段选择固化为事实标准。

### 8.2 允许的下一步（仅限决策，不是实现）

若未来要重新评估，建议先完成：

1. 明确一个真实消费方和一份真实报告使用场景；
2. 明确 JSON 的字段 allowlist、禁止字段和版本策略；
3. 明确是否写 `reports` 历史表；
4. 明确安全分级、保留和删除策略；
5. 再决定是否进入 D1B-2。

这不是本次任务的实施授权。

---

## 9. 最终声明

```text
JSON_DEVELOPMENT_APPROVED = NO
JSON_CONTRACT_CREATED = NO
JSON_EXPORTER_CREATED = NO
JSON_OUTPUT_CREATED = NO
GUI_MODIFIED = NO
HTML_EXPORTER_MODIFIED = NO
DATABASE_MODIFIED = NO
SCHEMA_MODIFIED = NO
PRODUCTION_CODE_MODIFIED = NO
TEST_CODE_MODIFIED = NO
GIT_MUTATION = NO
TESTS_RUN = NO
```

本次调查只新增了本报告，没有批准 JSON 开发，也没有进入 JSON 契约设计或任何编码工作。

```text
PHASE6_D1B_1_STATUS = PASS
FINAL_CONCLUSION = INSUFFICIENT_EVIDENCE
```
