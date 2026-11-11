"""Launch the production application entrypoint and close it from a timer.

``main.py`` is a one-line call to :func:`app.application.main`.  This harness
calls that same function, so configuration, logging, database bootstrap, theme,
QApplication and MainWindow all execute through the real startup path.  A small
``show`` wrapper schedules automated checks and a standard window close.
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

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import ui.main_window as main_window_module  # noqa: E402
import app.application as application_module  # noqa: E402

RESULT: dict[str, object] = {
    "entrypoint": "app.application.main([])",
    "production_entry_file": "main.py",
    "started": False,
    "visible_after_show": False,
    "navigation_labels": [],
    "navigation_ok": False,
    "closed_normally": False,
    "screenshot": str(ROOT / "docs" / "acceptance" / "entrypoint_runtime.png"),
}
OUTPUT = ROOT / "docs" / "acceptance" / "entrypoint_acceptance.json"


class AcceptanceWindow(main_window_module.MainWindow):
    def show(self) -> None:  # type: ignore[override]
        super().show()
        QTimer.singleShot(900, self._run_checks)

    def _run_checks(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.processEvents()
        RESULT["started"] = True
        RESULT["visible_after_show"] = self.isVisible()
        RESULT["window_title"] = self.windowTitle()
        RESULT["navigation_labels"] = [
            self.nav_buttons[key].text().strip() for key in self.pages_by_key
        ]
        checks = []
        for key, page in self.pages_by_key.items():
            self.nav_buttons[key].click()
            app.processEvents()
            checks.append(
                {
                    "key": key,
                    "ok": self.stack.currentWidget() is page,
                    "page": type(self.stack.currentWidget()).__name__,
                }
            )
        RESULT["navigation_checks"] = checks
        RESULT["navigation_ok"] = all(item["ok"] for item in checks)
        self.navigate("projects")
        app.processEvents()
        screenshot = Path(str(RESULT["screenshot"]))
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        RESULT["screenshot_saved"] = bool(self.grab().save(str(screenshot), "PNG"))
        self.close()
        app.processEvents()
        RESULT["closed_normally"] = not self.isVisible()
        app.quit()


def main() -> int:
    original_window = main_window_module.MainWindow
    main_window_module.MainWindow = AcceptanceWindow
    try:
        exit_code = application_module.main([])
    finally:
        main_window_module.MainWindow = original_window
    RESULT["application_exit_code"] = exit_code
    RESULT["success"] = bool(
        RESULT["started"]
        and RESULT["visible_after_show"]
        and RESULT["navigation_ok"]
        and RESULT["closed_normally"]
        and RESULT["screenshot_saved"]
        and exit_code == 0
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(RESULT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(RESULT, ensure_ascii=False, indent=2))
    return 0 if RESULT["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
