import sys
from PySide6.QtWidgets import (
    QApplication
)
from text_IDE import TextIDE

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextIDE()
    window.show()
    sys.exit(app.exec())