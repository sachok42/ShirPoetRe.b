import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QFileDialog,
    QMessageBox, QToolBar
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt

class TextIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text IDE")
        self.setGeometry(100, 100, 800, 600)

        # Central widget - text editor
        self.editor = QTextEdit()
        self.setCentralWidget(self.editor)

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