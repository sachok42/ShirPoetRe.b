"""ShirPoetRe — single entry point."""

import sys
from PySide6.QtWidgets import QApplication
from app import ShirPoetApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShirPoetApp()
    window.show()
    sys.exit(app.exec())