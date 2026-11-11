"""Execute real, local-only acceptance scenarios for phase 2.

Creates an isolated SQLite database under ``storage/acceptance`` and drives the
real service layer.  No network target is contacted.  The expired-authorization
case advances real wall-clock time, not a mocked policy result.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from core.errors import AppError, NotFoundError, StorageError, ValidationError  # noqa: E402
from core.models import AuthStatus  # noqa: E402
from core.timeutil import local_display, to_db_time, utc_now  # noqa: E402

ACCEPTANCE_ROOT = ROOT / "storage" / "acceptance"
REPORT_JSON = ROOT / "docs" / "acceptance" / "phase2_acceptance.json"


@dataclass
class Step:
    section: str
    name: str
    status: str
    detail: str


class Recorder:
    def __init__(self) -> None:
        self.steps: list[Step] = []

    def add(self, section: str, name: str, ok: bool, detail: str) -> None:
        status = "PASS" if ok else "FAIL"
        self.steps.append(Step(section, name, status, detail))
        print(f"[{status}] {section} / {name}: {detail}")

    def check(self, section: str, name: str, condition: bool, detail: str) -> None:
        self.add(section, name, bool(condition), detail)

    def expect_error(
        self,
        section: str,
        name: str,
        func: Callable[[], Any],
        expected: type[BaseException],
    ) -> None:
        try:
            result = func()
        except expected as exc:
            self.add(section, name, True, f"按预期拒绝: {type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - acceptance needs unexpected error detail
            self.add(section, name, False, f"错误异常类型: {type(exc).__name__}: {exc}")
        else:
            self.add(section, name, False, f"意外成功返回: {result!r}")


def write_config() -> Path:
    if ACCEPTANCE_ROOT.exists():
        shutil.rmtree(ACCEPTANCE_ROOT)
    ACCEPTANCE_ROOT.mkdir(parents=True)
    config = {
        "app": {"name": "SRC Acceptance", "version": "0.2.0", "environment": "acceptance"},
        "database": {"path": "acceptance.db"},
        "storage": {
            "root": ".",
            "projects": "projects",
            "evidence": "evidence",
            "reports": "reports",
            "logs": "logs",
        },
        "ui": {"theme": "dark", "window_width": 1280, "window_height": 800},
        "security": {
            "default_remote_access": "deny",
            "require_valid_authorization": True,
            "allow_wildcard_scope": False,
            "allow_redirect_following": False,
            "require_exact_remote_match": True,
        },
    }
    path = ACCEPTANCE_ROOT / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return path


def main() -> int:
    recorder = Recorder()
    config_path = write_config()
    context = build_context(config_path, expire_overdue=False)
    projects = context.project_service
    auths = context.authorization_service
    scopes = context.scope_service
    validator = context.scope_validator
    audit = context.audit

    local_project = ACCEPTANCE_ROOT / "local_project"
    local_project.mkdir()
    (local_project / "app.py").write_text("print('local acceptance only')\n", encoding="utf-8")
    outside_dir = ACCEPTANCE_ROOT / "outside_scope"
    outside_dir.mkdir()
    doc = ACCEPTANCE_ROOT / "authorization.pdf"
    doc.write_text("LOCAL ACCEPTANCE DOCUMENT - NO REAL TARGET\n", encoding="utf-8")
    now = utc_now()

    # ------------------------------------------------------------ project CRUD
    temp_project = projects.create_project(
        "验收临时项目",
        "authorized_test",
        "用于 CRUD 验收的本地项目",
        str(local_project),
        "active",
    )
    recorder.check(
        "项目管理",
        "1 创建项目",
        temp_project.project_id > 0,
        f"ID={temp_project.project_id}, 名称={temp_project.project_name}",
    )
    queried = projects.get_project(temp_project.project_id)
    recorder.check(
        "项目管理",
        "2 查询项目",
        queried.project_id == temp_project.project_id,
        f"查询到 #{queried.project_id} {queried.project_name}",
    )
    updated = projects.update_project(
        temp_project.project_id,
        project_name="验收临时项目（已修改）",
        project_type="combined",
        description="修改已实际写入 SQLite",
        local_path=str(local_project),
        status="paused",
    )
    recorder.check(
        "项目管理",
        "3 修改项目",
        updated.project_name.endswith("已修改）") and updated.status.value == "paused",
        f"名称={updated.project_name}, 状态={updated.status_label}",
    )
    projects.set_active_project(temp_project.project_id)
    active = projects.get_active_project()
    recorder.check(
        "项目管理",
        "4 设置当前项目",
        active is not None and active.project_id == temp_project.project_id,
        f"当前项目=#{active.project_id if active else None}",
    )
    projects.delete_project(temp_project.project_id)
    recorder.expect_error(
        "项目管理",
        "5 删除测试项目",
        lambda: projects.get_project(temp_project.project_id),
        NotFoundError,
    )
    recorder.check(
        "项目管理",
        "5b 删除后当前项目清理",
        projects.get_active_project() is None,
        "当前项目已清空",
    )

    # ------------------------------------------------------ two isolated projects
    project_a = projects.create_project(
        "验收项目 A", "authorized_test", "授权范围测试", str(local_project), "active"
    )
    project_b = projects.create_project(
        "验收项目 B", "authorized_test", "数据隔离测试", str(local_project), "active"
    )
    projects.set_active_project(project_a.project_id)
    recorder.check(
        "数据隔离",
        "创建项目 A / B",
        project_a.project_id != project_b.project_id,
        f"A=#{project_a.project_id}, B=#{project_b.project_id}",
    )

    # ------------------------------------------------------------- authorization
    pending = auths.create_authorization(
        project_a.project_id,
        authorization_source="本地模拟授权：验收项目 A",
        authorization_document=str(doc),
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(days=30),
        authorization_status="pending",
        notes="仅本地验收，无真实目标",
    )
    recorder.check(
        "授权管理",
        "1 创建授权（待审核）",
        pending.authorization_status is AuthStatus.PENDING and not pending.is_effective(now),
        f"#{pending.authorization_id}, 状态={pending.status_label}, 有效={pending.is_effective(now)}",
    )
    valid_auth = auths.update_authorization(
        project_a.project_id,
        pending.authorization_id,
        authorization_source=pending.authorization_source,
        authorization_document=pending.authorization_document,
        start_time=pending.start_time,
        end_time=pending.end_time,
        authorization_status="confirmed",
        notes="已确认：仅用于本地验收",
    )
    recorder.check(
        "授权管理",
        "2 确认授权",
        valid_auth.is_effective(utc_now())
        and valid_auth.authorization_status is AuthStatus.CONFIRMED,
        f"#{valid_auth.authorization_id}, 有效={valid_auth.is_effective(utc_now())}",
    )
    recorder.expect_error(
        "授权管理",
        "2b 已确认必须有授权文件",
        lambda: auths.create_authorization(
            project_a.project_id,
            authorization_source="无文件授权",
            authorization_document="",
            start_time=now,
            end_time=now + timedelta(days=1),
            authorization_status="confirmed",
        ),
        ValidationError,
    )

    # --------------------------------------------------------------- local asset
    local_asset = scopes.create_asset(
        project_a.project_id,
        asset_type="local_project",
        asset_value=str(local_project),
        notes="本地测试项目路径",
    )
    local_decision = validator.check_local_path(project_a.project_id, str(local_project))
    local_outside = validator.check_local_path(project_a.project_id, str(outside_dir))
    recorder.check(
        "授权范围",
        "本地测试项目路径允许",
        local_decision.allowed,
        f"asset=#{local_asset.asset_id}, code={local_decision.code}",
    )
    recorder.check(
        "授权范围",
        "范围外本地路径拒绝",
        not local_outside.allowed,
        f"code={local_outside.code}",
    )

    # -------------------------------------------------------------- remote scope
    allowed_assets = []
    for host in ("example.test", "authorized.example.test"):
        allowed_assets.append(
            scopes.create_asset(
                project_a.project_id,
                asset_type="domain",
                asset_value=host,
                authorization_id=valid_auth.authorization_id,
                allowed_operations=["config_check"],
                notes="本地模拟域名，不解析、不访问",
            )
        )
    decision_example = validator.require_remote_access(
        project_a.project_id, "example.test", "config_check"
    )
    decision_sub = validator.require_remote_access(
        project_a.project_id, "authorized.example.test", "config_check"
    )
    recorder.check(
        "授权范围",
        "范围内目标正确允许",
        decision_example.allowed and decision_sub.allowed,
        f"example.test={decision_example.code}, authorized.example.test={decision_sub.code}",
    )
    outside = validator.check_remote_access(project_a.project_id, "outside.test", "config_check")
    recorder.check(
        "授权范围",
        "范围外目标必须拒绝",
        not outside.allowed,
        f"target=outside.test, code={outside.code}",
    )
    sibling = validator.check_remote_access(
        project_a.project_id, "other.example.test", "config_check"
    )
    recorder.check(
        "授权范围",
        "未明确登记的子域拒绝",
        not sibling.allowed,
        f"target=other.example.test, code={sibling.code}",
    )
    recorder.expect_error(
        "授权范围",
        "通配符资产拒绝",
        lambda: scopes.create_asset(
            project_a.project_id,
            asset_type="domain",
            asset_value="*.example.test",
            authorization_id=valid_auth.authorization_id,
            allowed_operations=["config_check"],
        ),
        ValidationError,
    )

    # --------------------------------------------------------- expired auth path
    short_start = utc_now()
    short_end = short_start + timedelta(seconds=8)
    short_auth = auths.create_authorization(
        project_a.project_id,
        authorization_source="短时授权：过期验收",
        authorization_document=str(doc),
        start_time=short_start - timedelta(minutes=1),
        end_time=short_end,
        authorization_status="confirmed",
        notes="用于真实时间过期测试",
    )
    short_asset = scopes.create_asset(
        project_a.project_id,
        asset_type="domain",
        asset_value="expired.example.test",
        authorization_id=short_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    before_expiry = validator.check_remote_access(
        project_a.project_id, "expired.example.test", "config_check"
    )
    recorder.check(
        "授权范围",
        "过期前允许",
        before_expiry.allowed,
        f"授权窗口至 {local_display(short_auth.end_time)}",
    )
    wait_seconds = max(0.0, (short_end + timedelta(seconds=1)).timestamp() - utc_now().timestamp())
    print(f"[WAIT] 真实时间等待 {wait_seconds:.1f}s，使短时授权自然到期...")
    time.sleep(wait_seconds)
    expired_decision = validator.check_remote_access(
        project_a.project_id, "expired.example.test", "config_check"
    )
    recorder.check(
        "授权范围",
        "过期授权必须拒绝",
        not expired_decision.allowed and expired_decision.code == "authorization_expired",
        f"code={expired_decision.code}, reason={expired_decision.reason}",
    )
    changed = auths.expire_overdue_authorizations(project_a.project_id)
    refreshed_short = auths.get_authorization(project_a.project_id, short_auth.authorization_id)
    recorder.check(
        "授权管理",
        "3 过期授权状态落库",
        refreshed_short.authorization_status is AuthStatus.EXPIRED and changed >= 1,
        f"状态={refreshed_short.status_label}, 本次更新={changed}",
    )
    recorder.expect_error(
        "安全绕过",
        "过期授权不能新建远程资产",
        lambda: scopes.create_asset(
            project_a.project_id,
            asset_type="domain",
            asset_value="after-expiry.example.test",
            authorization_id=short_auth.authorization_id,
            allowed_operations=["config_check"],
        ),
        ValidationError,
    )

    # --------------------------------------------------------------- revoked auth
    revoke_auth = auths.create_authorization(
        project_a.project_id,
        authorization_source="待撤销授权：验收",
        authorization_document=str(doc),
        start_time=utc_now() - timedelta(minutes=1),
        end_time=utc_now() + timedelta(days=1),
        authorization_status="confirmed",
    )
    revoke_asset = scopes.create_asset(
        project_a.project_id,
        asset_type="domain",
        asset_value="revoked.example.test",
        authorization_id=revoke_auth.authorization_id,
        allowed_operations=["config_check"],
    )
    auths.revoke_authorization(project_a.project_id, revoke_auth.authorization_id)
    revoked_decision = validator.check_remote_access(
        project_a.project_id, "revoked.example.test", "config_check"
    )
    recorder.check(
        "授权管理",
        "4 撤销授权",
        not revoked_decision.allowed and revoked_decision.code == "authorization_revoked",
        f"asset=#{revoke_asset.asset_id}, code={revoked_decision.code}",
    )
    recorder.check(
        "授权范围",
        "已撤销授权必须拒绝",
        not revoked_decision.allowed,
        f"code={revoked_decision.code}",
    )

    # ------------------------------------------------------------- project B data
    auth_b = auths.create_authorization(
        project_b.project_id,
        authorization_source="项目 B 本地模拟授权",
        authorization_document=str(doc),
        start_time=utc_now() - timedelta(minutes=1),
        end_time=utc_now() + timedelta(days=1),
        authorization_status="confirmed",
    )
    asset_b = scopes.create_asset(
        project_b.project_id,
        asset_type="domain",
        asset_value="project-b.example.test",
        authorization_id=auth_b.authorization_id,
        allowed_operations=["config_check"],
    )
    recorder.expect_error(
        "数据隔离",
        "项目 A 不能读取项目 B 的授权",
        lambda: auths.get_authorization(project_a.project_id, auth_b.authorization_id),
        NotFoundError,
    )
    recorder.expect_error(
        "数据隔离",
        "项目 A 不能读取项目 B 的资产",
        lambda: scopes.get_asset(project_a.project_id, asset_b.asset_id),
        NotFoundError,
    )
    assets_a = scopes.list_assets(project_a.project_id)
    recorder.check(
        "数据隔离",
        "项目资产列表隔离",
        all(asset.asset_id != asset_b.asset_id for asset in assets_a),
        f"项目 A 资产数={len(assets_a)}, 不包含 B 的 #{asset_b.asset_id}",
    )
    logs_a_before = audit.list_logs(project_a.project_id, limit=1000)
    a_ids_before = {log.log_id for log in logs_a_before}
    b_decision = validator.check_remote_access(
        project_b.project_id, "project-b.example.test", "config_check"
    )
    logs_a_after = audit.list_logs(project_a.project_id, limit=1000)
    logs_b = audit.list_logs(project_b.project_id, limit=1000)
    a_ids_after = {log.log_id for log in logs_a_after}
    b_ids = {log.log_id for log in logs_b}
    recorder.check(
        "数据隔离",
        "项目 B 检测不写入项目 A 日志",
        a_ids_before == a_ids_after,
        f"A 日志数 {len(a_ids_before)} → {len(a_ids_after)}",
    )
    recorder.check(
        "数据隔离",
        "A/B 检测记录集合不相交",
        not (a_ids_after & b_ids) and b_decision.allowed,
        f"A={len(a_ids_after)} 条, B={len(b_ids)} 条, 交集={len(a_ids_after & b_ids)}",
    )
    cross_project = validator.check_remote_access(
        project_b.project_id, "example.test", "config_check"
    )
    recorder.check(
        "数据隔离",
        "项目 B 不能使用项目 A 的范围",
        not cross_project.allowed,
        f"target=example.test, code={cross_project.code}",
    )

    # ---------------------------------------------------------- bypass resistance
    recorder.check(
        "安全绕过",
        "URL 不会被当作精确目标",
        not validator.check_remote_access(
            project_a.project_id, "https://example.test", "config_check"
        ).allowed,
        "check_remote_access(URL) 被拒绝",
    )
    tamper_target = "tamper.example.test"
    context.database.execute(
        "INSERT INTO scope_assets "
        "(project_id, asset_type, asset_value, authorization_id, allowed_operations, "
        "asset_status, notes, created_at, updated_at) "
        "VALUES (?, 'domain', ?, NULL, '[\"config_check\"]', 'active', "
        "'direct DB bypass attempt', ?, ?)",
        (
            project_a.project_id,
            tamper_target,
            to_db_time(utc_now()),
            to_db_time(utc_now()),
        ),
    )
    tamper_decision = validator.check_remote_access(
        project_a.project_id, tamper_target, "config_check"
    )
    recorder.check(
        "安全绕过",
        "绕过服务层直接插入资产仍拒绝",
        not tamper_decision.allowed and tamper_decision.code == "missing_authorization",
        f"code={tamper_decision.code}",
    )
    recorder.check(
        "安全绕过",
        "授权检查不依赖 UI 按钮状态",
        not outside.allowed,
        "直接调用后端服务仍返回拒绝",
    )

    # ------------------------------------------------------------------ summary
    total = len(recorder.steps)
    passed = sum(1 for step in recorder.steps if step.status == "PASS")
    failed = total - passed
    result = {
        "generated_at": to_db_time(utc_now()),
        "database": str(context.config.database_path),
        "audit_file": str(audit.audit_file),
        "total": total,
        "passed": passed,
        "failed": failed,
        "steps": [asdict(step) for step in recorder.steps],
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ACCEPTANCE_TOTAL={total} PASSED={passed} FAILED={failed}")
    print(f"ACCEPTANCE_JSON={REPORT_JSON}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AppError, StorageError) as exc:
        print(f"FATAL_ACCEPTANCE_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
