"""Runtime acceptance for the actual Qt main window.

This uses the real AppContext, real SQLite database and real MainWindow under
Qt's offscreen platform.  It enters a Qt event loop, clicks every navigation
button, captures a screenshot and closes through QWidget.close().
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from ui.app_state import AppState  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

OUTPUT_JSON = ROOT / "docs" / "acceptance" / "ui_acceptance.json"
OUTPUT_PNG = ROOT / "docs" / "acceptance" / "ui_runtime.png"


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    for font_path in (
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
    ):
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    apply_theme(app)

    context = build_context()
    state = AppState(context.project_service)
    window = MainWindow(context, state)
    window.resize(1440, 900)
    window.show()
    app.processEvents()
    results: dict[str, object] = {
        "started": False,
        "window_title": window.windowTitle(),
        "visible_after_show": False,
        "navigation_labels": [],
        "navigation_checks": [],
        "all_pages_switched": False,
        "maximize_button": bool(window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint),
        "close_button": bool(window.windowFlags() & Qt.WindowType.WindowCloseButtonHint),
        "closed_normally": False,
        "screenshot": str(OUTPUT_PNG),
        "database": str(context.config.database_path),
    }

    def run_checks() -> None:
        app.processEvents()
        results["visible_after_show"] = window.isVisible()
        results["started"] = True
        results["navigation_labels"] = [
            window.nav_buttons[key].text().strip() for key in window.pages_by_key
        ]
        checks = []
        for key, page in window.pages_by_key.items():
            button = window.nav_buttons.get(key)
            if button is None:
                checks.append({"key": key, "ok": False, "reason": "missing nav button"})
                continue
            button.click()
            app.processEvents()
            checks.append(
                {
                    "key": key,
                    "ok": window.stack.currentWidget() is page,
                    "current_page": type(window.stack.currentWidget()).__name__,
                }
            )
        results["navigation_checks"] = checks
        results["all_pages_switched"] = all(item["ok"] for item in checks)
        window.navigate("projects")
        app.processEvents()
        window.project_page.refresh_all()
        app.processEvents()
        OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
        results["screenshot_saved"] = bool(window.grab().save(str(OUTPUT_PNG), "PNG"))
        window.close()
        app.processEvents()
        results["closed_normally"] = not window.isVisible()
        app.quit()

    QTimer.singleShot(700, run_checks)
    exit_code = app.exec()
    results["qt_event_loop_exit_code"] = exit_code
    results["success"] = bool(
        results["started"]
        and results["visible_after_show"]
        and results["all_pages_switched"]
        and results["maximize_button"]
        and results["close_button"]
        and results["closed_normally"]
        and results["screenshot_saved"]
        and exit_code == 0
    )
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
