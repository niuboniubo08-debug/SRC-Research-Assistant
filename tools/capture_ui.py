"""Render deterministic demo screenshots with Qt's offscreen platform.

The demo database lives in a temporary directory and is removed afterwards.
It never connects to a real target.
"""

from __future__ import annotations

import gc
import logging
import os
import shutil
import sys
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from core.timeutil import utc_now  # noqa: E402
from ui.app_state import AppState  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_theme  # noqa: E402


def build_demo_context(temp_dir: Path):
    project_dir = temp_dir / "demo-source"
    project_dir.mkdir(parents=True)
    (project_dir / "app.py").write_text("print('demo only')\n", encoding="utf-8")
    config = {
        "app": {"name": "SRC Research Assistant", "version": "0.2.0", "environment": "demo"},
        "database": {"path": "storage/screenshot.db"},
        "storage": {
            "root": "storage",
            "projects": "storage/projects",
            "evidence": "storage/evidence",
            "reports": "storage/reports",
            "logs": "storage/logs",
        },
        "ui": {"theme": "dark", "window_width": 1440, "window_height": 900},
        "security": {
            "default_remote_access": "deny",
            "require_valid_authorization": True,
            "allow_wildcard_scope": False,
            "allow_redirect_following": False,
            "require_exact_remote_match": True,
        },
    }
    config_path = temp_dir / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    context = build_context(config_path, expire_overdue=False)
    now = utc_now()

    project = context.project_service.create_project(
        "客户 A · Web 安全研究",
        "combined",
        "在客户书面授权范围内进行源代码与配置复核；禁止拒绝服务与数据读取。",
        str(project_dir),
        "active",
    )
    context.project_service.create_project(
        "内部 Python SDK 审查",
        "local_audit",
        "本地依赖与源代码静态审计。",
        str(project_dir),
        "completed",
    )
    context.project_service.create_project(
        "客户 B · 配置核查",
        "authorized_test",
        "等待授权文件复核，暂不执行远程检测。",
        "",
        "paused",
    )
    valid = context.authorization_service.create_authorization(
        project.project_id,
        authorization_source="客户 A 书面授权 / SRC-2026-017",
        authorization_document="C:/demo/authorization-a.pdf",
        start_time=now - timedelta(days=5),
        end_time=now + timedelta(days=25),
        authorization_status="confirmed",
        notes="仅允许非破坏性 HTTPS/响应头检查，测试窗口 09:00-18:00。",
    )
    context.authorization_service.create_authorization(
        project.project_id,
        authorization_source="历史授权 / SRC-2025-092",
        authorization_document="C:/demo/authorization-old.pdf",
        start_time=now - timedelta(days=90),
        end_time=now - timedelta(days=30),
        authorization_status="expired",
        notes="已过期，仅保留审计记录。",
    )
    context.authorization_service.create_authorization(
        project.project_id,
        authorization_source="客户 A 补充授权（待审核）",
        authorization_document="",
        start_time=now,
        end_time=now + timedelta(days=10),
        authorization_status="pending",
        notes="尚未收到盖章文件。",
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="portal.example.com",
        authorization_id=valid.authorization_id,
        allowed_operations=["config_check"],
        notes="客户明确列出的生产域名",
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="ip",
        asset_value="203.0.113.20",
        authorization_id=valid.authorization_id,
        allowed_operations=["config_check"],
        notes="仅作为授权范围示例（文档保留地址）",
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="local_project",
        asset_value=str(project_dir),
        notes="本地源代码目录，与远程范围分开管理",
    )
    context.project_service.set_active_project(project.project_id)
    return context


def main() -> int:
    # Use a normal project-owned directory instead of tempfile.mkdtemp: some
    # confined Windows environments apply restrictive ACLs to temp dirs.
    temp_dir = ROOT / ".screenshot-demo"
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        # The offscreen Qt platform may not discover Windows fonts.  Register
        # the installed UI fonts explicitly so screenshot text is legible.
        for font_path in (
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/msyhbd.ttc"),
        ):
            if font_path.is_file():
                QFontDatabase.addApplicationFont(str(font_path))
        apply_theme(app)
        context = build_demo_context(temp_dir)
        state = AppState(context.project_service)
        window = MainWindow(context, state)
        window.resize(1440, 900)
        window.show()
        app.processEvents()

        output_dir = ROOT / "docs" / "screenshots"
        output_dir.mkdir(parents=True, exist_ok=True)

        window.navigate("projects")
        app.processEvents()
        window.project_page.refresh_all()
        app.processEvents()
        project_shot = output_dir / "phase2_project_management.png"
        window.grab().save(str(project_shot), "PNG")

        window.project_page.tabs.setCurrentIndex(2)
        app.processEvents()
        app.processEvents()
        auth_shot = output_dir / "phase2_authorization_management.png"
        window.grab().save(str(auth_shot), "PNG")

        window.project_page.tabs.setCurrentIndex(3)
        app.processEvents()
        app.processEvents()
        asset_shot = output_dir / "phase2_scope_assets.png"
        window.grab().save(str(asset_shot), "PNG")

        window.navigate("dashboard")
        app.processEvents()
        app.processEvents()
        dashboard_shot = output_dir / "phase2_dashboard.png"
        window.grab().save(str(dashboard_shot), "PNG")
        window.close()
        window.deleteLater()
        app.processEvents()
        print(project_shot)
        print(auth_shot)
        print(asset_shot)
        print(dashboard_shot)
        return 0
    finally:
        # The application log handler keeps app.log open on Windows; close it
        # before deleting the demo database directory.
        logging.shutdown()
        gc.collect()
        for _attempt in range(3):
            if not temp_dir.exists():
                break
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
