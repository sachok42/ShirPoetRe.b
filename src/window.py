import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QMessageBox, QToolBar, QLabel
)
from PySide6.QtGui import QIcon, QAction

class TextIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text IDE")
        self.setGeometry(100, 100, 800, 600)
        self.is_dark_theme = False

        # Central widget - text editor
        self.editor = QTextEdit()
        self.setCentralWidget(self.editor)

        # Cursor position indicator below the editor, on the left side.
        self.cursor_info = QLabel()
        self.cursor_info.setText("Ln 1, Col 1")
        self.cursor_info.setStyleSheet("QLabel { background-color: transparent; padding: 0 6px; }")
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.addWidget(self.cursor_info)
        self.editor.cursorPositionChanged.connect(self.update_cursor_info)
        self.update_cursor_info()
        self.apply_theme()

        # Create menu
        self.create_menu()

        # Create toolbar
        self.create_toolbar()

    def create_menu(self):
        menu = self.menuBar()

        # File
        file_menu = menu.addMenu("File")

        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def create_toolbar(self):
        toolbar = QToolBar("Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction(QAction(QIcon(), "New", self, triggered=self.new_file))
        toolbar.addAction(QAction(QIcon(), "Open", self, triggered=self.open_file))
        toolbar.addAction(QAction(QIcon(), "Save", self, triggered=self.save_file))
        toolbar.addSeparator()
        self.theme_action = QAction("Night Theme", self)
        self.theme_action.setCheckable(True)
        self.theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.theme_action)

    def apply_theme(self):
        if self.is_dark_theme:
            self.setStyleSheet(
                "QMainWindow { background-color: #1e1e1e; color: #dcdcdc; }"
                "QTextEdit { background-color: #1e1e1e; color: #e8e8e8; "
                "border: 1px solid #2f2f2f; selection-background-color: #3a6ea5; }"
                "QToolBar, QStatusBar, QMenuBar, QMenu { background-color: #252526; color: #dcdcdc; }"
                "QToolBar QToolButton { background-color: #2d2d2d; color: #dcdcdc; "
                "border: 1px solid #3a3a3a; padding: 4px 8px; margin: 2px; }"
                "QToolBar QToolButton:hover { background-color: #3a3a3a; }"
                "QToolBar QToolButton:checked { background-color: #3a6ea5; color: #ffffff; border-color: #4e89c7; }"
                "QMenu::item:selected { background-color: #3a3d41; }"
                "QLabel { color: #dcdcdc; }"
            )
            self.cursor_info.setStyleSheet(
                "QLabel { background-color: transparent; color: #dcdcdc; padding: 0 6px; }"
            )
        else:
            self.setStyleSheet(
                "QMainWindow { background-color: #f2f2f2; color: #202020; }"
                "QTextEdit { background-color: #ffffff; color: #202020; "
                "border: 1px solid #cfcfcf; selection-background-color: #cce2ff; }"
                "QToolBar, QStatusBar, QMenuBar, QMenu { background-color: #f6f6f6; color: #202020; }"
                "QToolBar QToolButton { background-color: #ffffff; color: #202020; "
                "border: 1px solid #cfcfcf; padding: 4px 8px; margin: 2px; }"
                "QToolBar QToolButton:hover { background-color: #eef5ff; }"
                "QToolBar QToolButton:checked { background-color: #4a90e2; color: #ffffff; border-color: #357ab8; }"
                "QMenu::item:selected { background-color: #dcecff; }"
                "QLabel { color: #202020; }"
            )
            self.cursor_info.setStyleSheet(
                "QLabel { background-color: transparent; color: #202020; padding: 0 6px; }"
            )

    def toggle_theme(self, checked):
        self.is_dark_theme = checked
        self.theme_action.setText("Day Theme" if checked else "Night Theme")
        self.apply_theme()

    def update_cursor_info(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.cursor_info.setText(f"Ln {line}, Col {col}")

    def new_file(self):
        if not self.editor.toPlainText():
            return
        confirm = QMessageBox.question(self, "New File", "Save current document?",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if confirm == QMessageBox.Yes:
            self.save_file()
            self.editor.clear()
        elif confirm == QMessageBox.No:
            self.editor.clear()
        # Cancel — do nothing

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.editor.setPlainText(f.read())

    def save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextIDE()
    window.show()
    sys.exit(app.exec())
