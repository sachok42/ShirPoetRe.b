"""Short launcher for ShirPoetRe.b."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.app import ShirPoetApp
from src.poetry_tools import check_rhyme as _check_rhyme_text
from src.rhyme_dialog import RhymeDialog


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShirPoetApp()
    window.show()
    sys.exit(app.exec())
