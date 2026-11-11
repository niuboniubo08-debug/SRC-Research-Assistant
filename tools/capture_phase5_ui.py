"""Capture phase-5 vulnerability and evidence pages with real acceptance data."""

from __future__ import annotations

import logging
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

CONFIG = ROOT / "storage" / "phase5_acceptance" / "config.yaml"
VULN_OUTPUT = ROOT / "docs" / "acceptance" / "phase5_vulnerability_management.png"
EVIDENCE_OUTPUT = ROOT / "docs" / "acceptance" / "phase5_evidence_center.png"


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

    def select_pip_finding() -> None:
        page = window.vulnerability_page
        page.refresh()
        app.processEvents()
        for row in range(page.table.rowCount()):
            item = page.table.item(row, 4)
            if item is not None and item.text() == "pip-audit":
                page.table.selectRow(row)
                break
        app.processEvents()
        VULN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        ok = window.grab().save(str(VULN_OUTPUT), "PNG")
        print(f"VULN_SCREENSHOT={VULN_OUTPUT}")
        print(f"VULN_SCREENSHOT_OK={ok}")
        print(f"VULN_ROWS={page.table.rowCount()}")
        print(f"VULN_TITLE={page.detail_title.text()}")
        print(f"VULN_EVIDENCE={page.evidence_list.count()}")
        QTimer.singleShot(500, capture_evidence)

    def capture_evidence() -> None:
        window.navigate("evidence")
        page = window.evidence_page
        page.refresh()
        app.processEvents()
        selected = 0
        for row in range(page.table.rowCount()):
            item = page.table.item(row, 1)
            if item is not None and item.text() == "截图":
                selected = row
                break
        if page.table.rowCount() > 0:
            page.table.selectRow(selected)
            app.processEvents()
        EVIDENCE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        ok = window.grab().save(str(EVIDENCE_OUTPUT), "PNG")
        print(f"EVIDENCE_SCREENSHOT={EVIDENCE_OUTPUT}")
        print(f"EVIDENCE_SCREENSHOT_OK={ok}")
        print(f"EVIDENCE_ROWS={page.table.rowCount()}")
        print(f"EVIDENCE_TITLE={page.detail_title.text()}")
        window.close()
        app.quit()

    window.navigate("vulnerabilities")
    QTimer.singleShot(1600, select_pip_finding)
    app.exec()
    logging.shutdown()
    return 0 if VULN_OUTPUT.is_file() and EVIDENCE_OUTPUT.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
