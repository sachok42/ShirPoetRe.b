from PySide6.QtGui import (
    QIcon, QAction
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog,
    QMessageBox, QToolBar, QLabel, QTabWidget,
    QSplitter
)
from my_text_edit import MyTextEdit
from improved_rhyme_matching import detect_rhyme_scheme
from analysis_pannel import AnalysisPanel
from annotation_data import build_annotations


class TextIDE(QMainWindow):
    """
    Creates the main window of the IDE.
    Writes the cursor position and word counter in the bottom left corner.
    It has a menu and a toolbar for a file management. Also, there is a day/night theme switch.
    An optional Analysis panel (toggled from the toolbar) shows NLP results.
    Inline annotations (stress · foot · rhyme letter) are painted above each line
    in reserved space — they never overlap the poem text.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text IDE")
        self.setGeometry(100, 100, 800, 600)
        self.is_dark_theme = False
        self.is_focus_mode = False

        # Debounce timer: fires 600 ms after the user finishes a line
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self.auto_run_analysis)
        self._prev_block_count = 1

        # ── Splitter ──────────────────────────────────────────────────────────
        self.splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(self.splitter)

        # You can open several tabs simultaneously in IDE.
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_cursor_info)
        self.splitter.addWidget(self.tabs)

        # Analysis panel (hidden by default)
        self.analysis_panel = AnalysisPanel()
        self.analysis_panel.hide()
        self.splitter.addWidget(self.analysis_panel)
        self.splitter.setHandleWidth(1)

        # Cursor position indicator below the editor, on the left side.
        self.cursor_info = QLabel()
        self.cursor_info.setText("Ln 1, Col 1")
        self.cursor_info.setStyleSheet("QLabel { background-color: transparent; padding: 0 6px; }")

        # Upon starting the program you create a new tab
        self.new_tab()

        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.addWidget(self.cursor_info)
        self.current_editor().cursorPositionChanged.connect(self.update_cursor_info)
        self.current_editor().textChanged.connect(self.update_cursor_info)
        self.update_cursor_info()
        self.apply_theme()

        # Create menu
        self.create_menu()

        # Create toolbar
        self.create_toolbar()

        # Wire buttons
        self.analysis_panel.run_btn.clicked.connect(self.run_analysis)

    # ── Tab / editor management ───────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F12:
            self.toggle_focus_mode()
            event.accept()
            return
        super().keyPressEvent(event)

    def new_tab(self, text="", title="Untitled"):
        editor = MyTextEdit()
        editor.setPlainText(text)
        editor.cursorPositionChanged.connect(self.update_cursor_info)
        editor.textChanged.connect(self.update_cursor_info)
        editor.document().blockCountChanged.connect(self.on_block_count_changed)
        index = self.tabs.addTab(editor, title)
        self.tabs.setCurrentIndex(index)
        self._prev_block_count = editor.document().blockCount()

    def current_editor(self) -> MyTextEdit:
        return self.tabs.currentWidget()

    def close_tab(self, index):
        # Don't close the tab if it is the only remaining one.
        if self.tabs.count() == 1:
            return
        self.tabs.removeTab(index)

    # ── Auto-analysis triggers ────────────────────────────────────────────────

    def on_block_count_changed(self, new_count: int):
        """User pressed Enter (new block added) — start debounce timer."""
        if not self.analysis_panel.auto_analyse:
            return
        if new_count > self._prev_block_count:
            self._auto_timer.start(600)
        self._prev_block_count = new_count

    def auto_run_analysis(self):
        self.run_analysis(silent=True)

    # ── Core analysis ─────────────────────────────────────────────────────────

    def run_analysis(self, silent: bool = False):
        poem = self.current_editor().toPlainText()
        if not poem.strip():
            if not silent:
                QMessageBox.information(self, "Empty", "Write some lines first.")
            return

        if not silent and not self.analysis_panel.isVisible():
            self.analysis_panel.show()
            self.splitter.setSizes([560, 300])
            self.analysis_action.setChecked(True)

        annotations = build_annotations(poem)
        lines = [l for l in poem.splitlines() if l.strip()]
        try:
            scheme = detect_rhyme_scheme(lines)
        except Exception:
            scheme = []

        self.current_editor().set_annotations(annotations, poem)
        self.analysis_panel.update_summaries(poem, annotations, scheme)

    # ── Menu / toolbar ────────────────────────────────────────────────────────

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

        # Analysis
        analysis_menu = menu.addMenu("Analysis")

        run_action = QAction("Run Analysis", self)
        run_action.setShortcut("Ctrl+Shift+A")
        run_action.triggered.connect(self.run_analysis)
        analysis_menu.addAction(run_action)

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

        toolbar.addSeparator()

        self.analysis_action = QAction("Analysis", self)
        self.analysis_action.setCheckable(True)
        self.analysis_action.triggered.connect(self.toggle_analysis_panel)
        toolbar.addAction(self.analysis_action)

    # ── Theme (unchanged from original) ──────────────────────────────────────

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

    def toggle_analysis_panel(self, checked):
        if checked:
            self.analysis_panel.show()
            self.splitter.setSizes([560, 300])
        else:
            self.analysis_panel.hide()
            self.splitter.setSizes([self.width(), 0])

    # ── Status bar (unchanged from original) ─────────────────────────────────

    def word_char_counter(self):
        text = self.current_editor().toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        return char_count, word_count

    def update_cursor_info(self):
        cursor = self.current_editor().textCursor()
        line   = cursor.blockNumber() + 1
        col    = cursor.positionInBlock() + 1
        chars, words = self.word_char_counter()
        self.cursor_info.setText(f"Ln {line}, Col {col}, Words {words}, Chars {chars}")

    # ── File ops (unchanged from original) ───────────────────────────────────

    def new_file(self):
        self.new_tab()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            filename = file_path.split("/")[-1]
            self.new_tab(text, filename)

    def save_file(self):
        editor = self.current_editor()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save file", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            filename = file_path.split("/")[-1]
            self.tabs.setTabText(self.tabs.currentIndex(), filename)
