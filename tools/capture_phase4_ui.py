"""Capture the dependency audit page using real phase-4 acceptance results."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.bootstrap import build_context  # noqa: E402
from ui.app_state import AppState  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_theme  # noqa: E402

CONFIG = ROOT / "storage" / "phase4_acceptance" / "config.yaml"
OUTPUT = ROOT / "docs" / "acceptance" / "phase4_dependency_audit.png"


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
    context = build_context(CONFIG, expire_overdue=False)
    state = AppState(context.project_service)
    window = MainWindow(context, state)
    window.resize(1440, 900)
    window.show()
    window.navigate("dependencies")

    def capture() -> None:
        page = window.dependency_page
        page.refresh_all()
        app.processEvents()
        if page.findings_table.rowCount() > 0:
            page.findings_table.selectRow(0)
            app.processEvents()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        ok = window.grab().save(str(OUTPUT), "PNG")
        print(f"SCREENSHOT={OUTPUT}")
        print(f"SCREENSHOT_OK={ok}")
        print(f"FINDINGS_ROWS={page.findings_table.rowCount()}")
        print(f"DEPENDENCY_FILES={page.dependency_files_label.text()}")
        window.close()
        app.quit()

    QTimer.singleShot(900, capture)
    app.exec()
    logging.shutdown()
    return 0 if OUTPUT.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
