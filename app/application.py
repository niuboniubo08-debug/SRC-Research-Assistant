"""Qt application lifecycle and command-line switches."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

from app.bootstrap import build_context
from app.config import application_root

LOGGER = logging.getLogger("src_assistant")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SRC Research Assistant")
    parser.add_argument("--config", help="配置文件路径（默认使用程序目录下 config.yaml）")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="初始化/升级数据库、输出表结构检查结果后退出",
    )
    parser.add_argument("--version", action="store_true", help="显示版本后退出")
    return parser.parse_args(argv)


def _print_database_summary(context) -> None:
    summary = context.database_summary()
    print(f"数据库: {summary['path']}")
    print(f"架构版本: {summary['schema_version']}")
    print(f"健康状态: {summary['message']}")
    print("数据表:")
    for table in summary["tables"]:
        print(f"  - {table}")


def _install_exception_hook() -> None:
    def handle(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        LOGGER.error("未捕获异常\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None,
                    "程序错误",
                    f"发生未处理错误：\n{exc_value}\n\n详细信息已写入日志。",
                )
        except Exception:
            pass

    sys.excepthook = handle


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])
    if args.version:
        from app import __version__

        print(f"SRC Research Assistant {__version__}")
        return 0

    try:
        context = build_context(args.config)
    except Exception as exc:
        print(f"启动失败: {exc}", file=sys.stderr)
        return 1

    if args.init_db:
        _print_database_summary(context)
        return 0

    try:
        from PySide6.QtWidgets import QApplication
        from ui.app_state import AppState
        from ui.main_window import MainWindow
        from ui.theme import apply_theme

        app = QApplication.instance() or QApplication(sys.argv)
        app.setApplicationName(context.config.name)
        app.setOrganizationName("SRC Research")
        app.setApplicationVersion(context.config.version)
        apply_theme(app)
        _install_exception_hook()

        state = AppState(context.project_service)
        window = MainWindow(context, state)
        window.show()
        return app.exec()
    except Exception as exc:
        LOGGER.exception("图形界面启动失败")
        print(f"图形界面启动失败: {exc}", file=sys.stderr)
        return 1


def config_path_from_cli() -> Path:
    """Convenience for diagnostics (kept small and side-effect free)."""

    return application_root() / "config.yaml"
