import sys
import string
from PySide6.QtGui import QIcon, QAction, QPainter, QColor
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QFileDialog,
    QMessageBox, QToolBar, QLabel, QWidget, QTabWidget,
    QSplitter, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar,
)

# ── NLP imports (graceful fallback if deps missing) ──────────────────────────
try:
    from style_analysis import rank_words_by_style
    from rhyme_repair import suggest_rhyme_repairs
    from rhyme_analysis import check_rhyme
    from rhythm_analysis import analyse_rhythm
    NLP_AVAILABLE = True
except ImportError as _e:
    NLP_AVAILABLE = False
    _NLP_ERROR = str(_e)


# ═══════════════════════════════════════════════════════════════════════════════
#  ORIGINAL EDITOR WIDGETS  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

def _make_group(title: str) -> QGroupBox:
    g = QGroupBox(title)
    g.setLayout(QVBoxLayout())
    g.layout().setContentsMargins(8, 12, 8, 8)
    g.layout().setSpacing(4)
    return g


def _score_row(label: str, value: float) -> QWidget:
    """A single labelled progress-bar score row."""
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)

    lbl = QLabel(label)
    lbl.setFixedWidth(80)
    hl.addWidget(lbl)

    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(int(value * 100))
    bar.setTextVisible(False)
    bar.setFixedHeight(8)
    hl.addWidget(bar, 1)

    val = QLabel(f"{value:.2f}")
    val.setFixedWidth(34)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    hl.addWidget(val)
    return row


class AnalysisPanel(QWidget):
    """
    Collapsible side panel with four NLP sections:
      Rhythm · Rhyme · Repair · Style
    Each section is a QGroupBox that populates when Run Analysis is clicked,
    or (for Repair/Style) when their own button is pressed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ── Run Analysis button ───────────────────────────────────────────────
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.setToolTip("Analyse rhythm and rhyme of the current poem (Ctrl+Shift+A)")
        if not NLP_AVAILABLE:
            self.run_btn.setEnabled(False)
            self.run_btn.setToolTip(f"NLP modules not found: {_NLP_ERROR}")
        root.addWidget(self.run_btn)

        # ── Scrollable content ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self.content = QVBoxLayout(inner)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(8)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── Rhythm group ──────────────────────────────────────────────────────
        self.rhythm_group = _make_group("Rhythm")
        self.rhythm_placeholder = QLabel("Press 'Run Analysis' to analyse the poem.")
        self.rhythm_placeholder.setWordWrap(True)
        self.rhythm_group.layout().addWidget(self.rhythm_placeholder)
        self.content.addWidget(self.rhythm_group)

        # ── Rhyme group ───────────────────────────────────────────────────────
        self.rhyme_group = _make_group("Rhyme")
        self.rhyme_placeholder = QLabel("Press 'Run Analysis' to check rhymes.")
        self.rhyme_placeholder.setWordWrap(True)
        self.rhyme_group.layout().addWidget(self.rhyme_placeholder)
        self.content.addWidget(self.rhyme_group)

        # ── Repair group ──────────────────────────────────────────────────────
        self.repair_group = _make_group("Rhyme Repair")
        repair_hint = QLabel("Find replacement words that rhyme with the anchor line.")
        repair_hint.setWordWrap(True)
        self.repair_group.layout().addWidget(repair_hint)

        anchor_row = QHBoxLayout()
        anchor_row.addWidget(QLabel("Anchor:"))
        self.anchor_edit = QLineEdit()
        self.anchor_edit.setPlaceholderText("Line with the target rhyme...")
        anchor_row.addWidget(self.anchor_edit, 1)
        self.repair_group.layout().addLayout(anchor_row)

        broken_row = QHBoxLayout()
        broken_row.addWidget(QLabel("Broken:"))
        self.broken_edit = QLineEdit()
        self.broken_edit.setPlaceholderText("Line that doesn't rhyme yet...")
        broken_row.addWidget(self.broken_edit, 1)
        self.repair_group.layout().addLayout(broken_row)

        self.repair_btn = QPushButton("Find Repairs")
        self.repair_btn.setEnabled(NLP_AVAILABLE)
        self.repair_btn.clicked.connect(self._run_repair)
        self.repair_group.layout().addWidget(self.repair_btn)

        self.repair_results = QVBoxLayout()
        self.repair_group.layout().addLayout(self.repair_results)
        self.content.addWidget(self.repair_group)

        # ── Style group ───────────────────────────────────────────────────────
        self.style_group = _make_group("Style Fit")
        style_hint = QLabel("Score candidate words against the poem's style.")
        style_hint.setWordWrap(True)
        self.style_group.layout().addWidget(style_hint)

        self.candidates_edit = QLineEdit()
        self.candidates_edit.setPlaceholderText("gloom, luminous, swift, gentle...")
        self.style_group.layout().addWidget(self.candidates_edit)

        self.style_btn = QPushButton("Rank by Style")
        self.style_btn.setEnabled(NLP_AVAILABLE)
        self.style_btn.clicked.connect(self._run_style)
        self.style_group.layout().addWidget(self.style_btn)

        self.style_results = QVBoxLayout()
        self.style_group.layout().addLayout(self.style_results)
        self.content.addWidget(self.style_group)

        self.content.addStretch()

        # poem text is set by the main window before each run
        self._poem_text = ""

    # ── Public API ────────────────────────────────────────────────────────────

    def set_poem(self, text: str):
        self._poem_text = text

    def run_all(self, poem_text: str):
        self._poem_text = poem_text
        self._run_rhythm()
        self._run_rhyme()

    # ── Rhythm ────────────────────────────────────────────────────────────────

    def _run_rhythm(self):
        self._clear_layout(self.rhythm_group.layout())

        if not self._poem_text.strip():
            self.rhythm_group.layout().addWidget(QLabel("No text to analyse."))
            return

        try:
            result = analyse_rhythm(self._poem_text)
        except Exception as e:
            self.rhythm_group.layout().addWidget(QLabel(f"Error: {e}"))
            return

        metre = result.overall_metre.title() if result.overall_metre else "—"
        self.rhythm_group.layout().addWidget(QLabel(f"Dominant metre:  {metre}"))
        self.rhythm_group.layout().addWidget(_score_row("Regularity", result.regularity_score))

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        self.rhythm_group.layout().addWidget(sep)

        for lr in result.lines:
            foot = lr.dominant_foot.title() if lr.dominant_foot else "?"
            stress = _format_stress(lr.stress)
            line_lbl = QLabel(
                f"<b>{foot}</b> · {lr.syllables} syl<br>"
                f"<tt>{stress}</tt><br>"
                f"<i>{lr.line}</i>"
            )
            line_lbl.setWordWrap(True)
            line_lbl.setTextFormat(Qt.RichText)
            self.rhythm_group.layout().addWidget(line_lbl)

            sep2 = QFrame()
            sep2.setFrameShape(QFrame.HLine)
            self.rhythm_group.layout().addWidget(sep2)

    # ── Rhyme ─────────────────────────────────────────────────────────────────

    def _run_rhyme(self):
        self._clear_layout(self.rhyme_group.layout())

        lines = [l for l in self._poem_text.splitlines() if l.strip()]
        if len(lines) < 2:
            self.rhyme_group.layout().addWidget(QLabel("Need at least 2 lines."))
            return

        try:
            # Check consecutive pairs (AABB) and alternating pairs (ABAB)
            checked = set()
            pairs = [(i, i + 1) for i in range(len(lines) - 1)]
            if len(lines) >= 4:
                pairs += [(i, i + 2) for i in range(len(lines) - 2)]

            for a, b in pairs:
                if (a, b) in checked:
                    continue
                checked.add((a, b))

                r = check_rhyme(lines[a], lines[b])
                icon = "✓" if r.rhymes else "✗"
                lbl = QLabel(
                    f"{icon} L{a+1}/L{b+1}:  "
                    f"<b>{r.word_a}</b> ↔ <b>{r.word_b}</b>  "
                    f"(distance {r.distance})"
                )
                lbl.setTextFormat(Qt.RichText)
                lbl.setWordWrap(True)
                self.rhyme_group.layout().addWidget(lbl)

                if not r.rhymes and r.repair_options:
                    hint = r.repair_options[0]
                    hint_text = "; ".join(hint[:2])
                    hint_lbl = QLabel(f"   → {hint_text}")
                    hint_lbl.setWordWrap(True)
                    self.rhyme_group.layout().addWidget(hint_lbl)

                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                self.rhyme_group.layout().addWidget(sep)

        except Exception as e:
            self.rhyme_group.layout().addWidget(QLabel(f"Error: {e}"))

    # ── Repair ────────────────────────────────────────────────────────────────

    def _run_repair(self):
        self._clear_layout(self.repair_results)

        anchor = self.anchor_edit.text().strip()
        broken = self.broken_edit.text().strip()

        if not anchor or not broken:
            self.repair_results.addWidget(QLabel("Fill both lines first."))
            return

        try:
            suggestions = suggest_rhyme_repairs(anchor, broken, top_n=5)
        except Exception as e:
            self.repair_results.addWidget(QLabel(f"Error: {e}"))
            return

        if not suggestions:
            self.repair_results.addWidget(QLabel("No rhyming alternatives found."))
            return

        for s in suggestions:
            lbl = QLabel(
                f"<b>{s['word']}</b>  (rhymes with \"{s['rhyme_with']}\")<br>"
                f"&rarr; <i>{s['example_line']}</i>"
            )
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            self.repair_results.addWidget(lbl)
            self.repair_results.addWidget(_score_row("Style fit", s["style_score"]))
            self.repair_results.addWidget(
                _score_row("Sentiment", 1 - min(s["sentiment_delta"], 1.0))
            )
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            self.repair_results.addWidget(sep)

    # ── Style ─────────────────────────────────────────────────────────────────

    def _run_style(self):
        self._clear_layout(self.style_results)

        words_raw = self.candidates_edit.text().strip()
        if not words_raw:
            self.style_results.addWidget(QLabel("Enter candidate words first."))
            return
        if not self._poem_text.strip():
            self.style_results.addWidget(QLabel("Open a poem in the editor first."))
            return

        candidates = [w.strip() for w in words_raw.split(",") if w.strip()]
        try:
            ranked = rank_words_by_style(self._poem_text, candidates)
        except Exception as e:
            self.style_results.addWidget(QLabel(f"Error: {e}"))
            return

        for i, (word, score) in enumerate(ranked):
            self.style_results.addWidget(QLabel(f"#{i+1}  {word}"))
            self.style_results.addWidget(_score_row("Style fit", score))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                AnalysisPanel._clear_layout(item.layout())


def _format_stress(stress: str) -> str:
    """Turn '010100' into '/ o / o' for readability."""
    return " ".join("/" if c == "1" else "o" for c in stress)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW  (original code preserved; analysis panel bolted on the right)
# ═══════════════════════════════════════════════════════════════════════════════

class TextIDE(QMainWindow):
    """
    Creates the main window of the IDE.
    Writes the cursor position and word counter in the bottom left corner.
    It has a menu and a toolbar for a file management. Also, there is a day/night theme switch.
    An optional Analysis panel (toggled from the toolbar) exposes NLP tools.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Text IDE")
        self.setGeometry(100, 100, 800, 600)
        self.is_dark_theme = False
        self.is_focus_mode = False

        # ── Splitter: editor tabs on the left, analysis panel on the right ───
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

        # Wire Run Analysis button inside the panel to the same handler
        self.analysis_panel.run_btn.clicked.connect(self.run_analysis)

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
        index = self.tabs.addTab(editor, title)
        self.tabs.setCurrentIndex(index)

    def current_editor(self):
        return self.tabs.currentWidget()

    def close_tab(self, index):
        # Don't close the tab if it is the only remaining one.
        if self.tabs.count() == 1:
            return
        self.tabs.removeTab(index)

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

        # Analysis (new menu)
        analysis_menu = menu.addMenu("Analysis")

        run_action = QAction("Run Analysis", self)
        run_action.setShortcut("Ctrl+Shift+A")
        run_action.triggered.connect(self.run_analysis)
        if not NLP_AVAILABLE:
            run_action.setEnabled(False)
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

        # New: toggle the analysis panel
        self.analysis_action = QAction("Analysis", self)
        self.analysis_action.setCheckable(True)
        self.analysis_action.triggered.connect(self.toggle_analysis_panel)
        toolbar.addAction(self.analysis_action)

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
        """Show or hide the analysis panel."""
        if checked:
            self.analysis_panel.show()
            self.splitter.setSizes([560, 300])
        else:
            self.analysis_panel.hide()
            self.splitter.setSizes([self.width(), 0])

    def run_analysis(self):
        """Run rhythm + rhyme analysis on the current tab's text."""
        if not NLP_AVAILABLE:
            QMessageBox.warning(self, "NLP Unavailable", f"Could not import NLP modules:\n{_NLP_ERROR}")
            return

        poem = self.current_editor().toPlainText()
        if not poem.strip():
            QMessageBox.information(self, "Empty", "Write some lines first.")
            return

        # Make sure the panel is visible
        if not self.analysis_panel.isVisible():
            self.analysis_panel.show()
            self.splitter.setSizes([560, 300])
            self.analysis_action.setChecked(True)

        self.analysis_panel.run_all(poem)

    def word_char_counter(self):
        text = self.current_editor().toPlainText()
        char_count = len(text)
        word_count = len(text.split())
        return char_count, word_count

    def update_cursor_info(self):
        cursor = self.current_editor().textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        chars, words = self.word_char_counter()
        self.cursor_info.setText(f"Ln {line}, Col {col}, Words {words}, Chars {chars}")

    def new_file(self):
        self.new_tab()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open file", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            filename = file_path.split("/")[-1]
            self.new_tab(text, filename)

    def save_file(self):
        editor = self.current_editor()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save file", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            filename = file_path.split("/")[-1]
            self.tabs.setTabText(self.tabs.currentIndex(), filename)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextIDE()
    window.show()
    sys.exit(app.exec())