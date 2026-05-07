import sys
from PySide6.QtGui import QIcon, QAction, QPainter, QColor, QKeySequence, QShortcut
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog,
    QMessageBox, QToolBar, QLabel, QWidget
)

class LineNumberArea(QWidget):
    """
    Line enumerator for the written text. Number is written to the left to each text block
    """

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.line_number_area_size()

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class MyTextEdit(QPlainTextEdit):
    """
    Personal class for the Text area. Uses LineNumberArea representative to enumerate and show the line numbers.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.line_number_area = LineNumberArea(self)

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area)

        self.update_line_number_area_width()

    def line_number_area_size(self):
        digits = len(str(self.document().blockCount()))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return QSize(space, 0)

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_size().width(), 0, 0, 0)

    def update_line_number_area(self):
        self.line_number_area.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(),
                  self.line_number_area_size().width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2b2b2b"))

        block = self.document().firstBlock()
        block_number = 0

        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        # Enumerate each line of text and write line numbers in the LineNumberArea
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#aaaaaa"))
                painter.drawText(
                    0, int(top),
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

class TextIDE(QMainWindow):
    """
    Creates the main window of the IDE.
    Writes the cursor position and word counter in the bottom left corner.
    It has a menu and a toolbar for a file management. Also, there is a day/night theme switch.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text IDE")
        self.setGeometry(100, 100, 800, 600)
        self.is_dark_theme = False
        self.is_focus_mode = False

        # Central widget - text editor
        self.editor = MyTextEdit()
        self.setCentralWidget(self.editor)

        # Cursor position indicator below the editor, on the left side.
        self.cursor_info = QLabel()
        self.cursor_info.setText("Ln 1, Col 1")
        self.cursor_info.setStyleSheet("QLabel { background-color: transparent; padding: 0 6px; }")
        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.addWidget(self.cursor_info)
        self.editor.cursorPositionChanged.connect(self.update_cursor_info)
        self.editor.textChanged.connect(self.update_cursor_info)
        self.update_cursor_info()
        self.apply_theme()

        # Create menu
        self.create_menu()

        # Create toolbar
        self.create_toolbar()

        self.focus_shortcut = QShortcut(QKeySequence("F12"), self)
        self.focus_shortcut.activated.connect(self.toggle_focus_mode)

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

        toolbar.addSeparator()
        self.focus_action = QAction("Focus Mode", self)
        self.focus_action.setCheckable(True)
        self.focus_action.triggered.connect(self.toggle_focus_mode)
        toolbar.addAction(self.focus_action)

    def apply_theme(self):
        if self.is_dark_theme:
            self.setStyleSheet(
                "QMainWindow { background-color: #1e1e1e; color: #dcdcdc; }"
                "QPlainTextEdit { background-color: #1e1e1e; color: #e8e8e8; "
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
                "QPlainTextEdit { background-color: #ffffff; color: #202020; "
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

    def toggle_focus_mode(self):
        self.is_focus_mode = not (self.is_focus_mode)

        if self.is_focus_mode:
            # Hide UI elements
            self.menuBar().hide()
            for tool in self.findChildren(QToolBar):
                tool.hide()
            #self.statusBar().hide()    Add this line to hide word/char counters

            self.showFullScreen()
            QMessageBox.information(
                self,
                "Focus Mode",
                "Focus Mode is now enabled\n\nPress F12 to exit."
            )

            self.focus_action.setChecked(True)
        else:
            self.menuBar().show()
            for tool in self.findChildren(QToolBar):
                tool.show()
            #self.statusBar().show()    Add this line if you hid it previously in the function
            self.showNormal()
            self.focus_action.setChecked(False)

    def word_char_counter(self):
        text = self.editor.toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        return char_count, word_count

    def update_cursor_info(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        chars, words = self.word_char_counter()
        self.cursor_info.setText(f"Ln {line}, Col {col}, Words {words}, Chars {chars}")

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
