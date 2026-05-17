"""Final application wiring for ShirPoetRe.b."""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import QMessageBox, QToolBar

import model
from src.poetry_tools import (
    WORD_RE,
    analysis_report,
    find_rhyme_candidates,
    find_rhymes,
    model_vocabulary,
    model_word_counts,
    next_word_candidates,
    normalize_word,
)
from src.rhyme_dialog import RhymeDialog
from src.window import TextIDE


class ShirPoetApp(TextIDE):
    """Text IDE plus practical poetry helpers."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShirPoetRe.b")
        self.editor = self.current_editor()
        self.tabs.currentChanged.connect(self._sync_current_editor)
        self._init_model()
        self._init_poetry_tools()

    def _sync_current_editor(self) -> None:
        self.editor = self.current_editor()

    def _init_model(self) -> None:
        try:
            model.load_artifacts(required=False)
            status = "Neural model loaded" if model.is_fitted() else "Using fallback vocabulary"
        except Exception as exc:
            status = f"Model load error: {exc}"
        self.statusBar().showMessage(status, 6000)

    def _init_poetry_tools(self) -> None:
        self.ai_action = self._make_action("Suggest word", "Ctrl+G", self.suggest_word)
        self.rhyme_action = self._make_action("Rhymes", "Ctrl+R", self.open_rhyme_dialog)
        self.analyse_action = self._make_action("Analyse", "Ctrl+Shift+A", self.show_poem_analysis)

        actions = (self.ai_action, self.rhyme_action, self.analyse_action)
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.addSeparator()
            for action in actions:
                toolbar.addAction(action)

        poetry_menu = self.menuBar().addMenu("Poetry")
        for action in actions:
            poetry_menu.addAction(action)

        self.statusBar().showMessage("ShirPoetRe.b is ready", 3000)

    def _make_action(self, text: str, shortcut: str, slot) -> QAction:
        action = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    def editor_text(self) -> str:
        editor = self.current_editor()
        return editor.toPlainText() if editor else ""

    def non_empty_lines(self) -> list[str]:
        return [line.strip() for line in self.editor_text().splitlines() if line.strip()]

    def current_word_hint(self) -> str:
        editor = self.current_editor()
        if editor is None:
            return ""

        cursor = editor.textCursor()
        selected = normalize_word(cursor.selectedText())
        if selected:
            return selected

        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return normalize_word(word_cursor.selectedText()) or normalize_word(self.editor_text())

    def insert_word(self, word: str) -> None:
        editor = self.current_editor()
        if editor is None:
            return

        text = self.editor_text()
        prefix = "" if not text or text.endswith((" ", "\n", "\t")) else " "
        editor.insertPlainText(prefix + word)
        self.statusBar().showMessage(f"Inserted: {word}", 2500)

    def replace_current_line_last_word(self, word: str) -> None:
        editor = self.current_editor()
        if editor is None:
            return

        cursor = editor.textCursor()
        block = cursor.block()
        matches = list(WORD_RE.finditer(block.text()))
        if not matches:
            self.insert_word(word)
            return

        last_match = matches[-1]
        cursor.setPosition(block.position() + last_match.start())
        cursor.setPosition(block.position() + last_match.end(), QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(word)
        editor.setTextCursor(cursor)
        self.statusBar().showMessage(f"Replaced line ending with: {word}", 2500)

    def rhyme_candidates(self, word: str, limit: int = 24):
        return find_rhyme_candidates(word, model_vocabulary(model), model_word_counts(model), limit)

    def find_rhymes(self, word: str, limit: int = 24) -> list[str]:
        return find_rhymes(word, model_vocabulary(model), model_word_counts(model), limit)

    def next_word_candidates(self, context: str, limit: int = 12) -> list[str]:
        return next_word_candidates(context, model, limit)

    def suggest_word(self) -> None:
        context = self.editor_text()
        if not context.strip():
            self.statusBar().showMessage("Type a little context first.", 3000)
            return

        candidates = self.next_word_candidates(context, limit=12)
        if not candidates:
            self.statusBar().showMessage("No useful suggestion found.", 3500)
            return

        self.insert_word(candidates[0])
        if len(candidates) > 1:
            self.statusBar().showMessage("Other options: " + ", ".join(candidates[1:6]), 5000)

    def open_rhyme_dialog(self) -> None:
        RhymeDialog(self).exec()

    def show_poem_analysis(self) -> None:
        text = self.editor_text().strip()
        if not text:
            self.statusBar().showMessage("Nothing to analyse yet.", 3000)
            return

        QMessageBox.information(self, "Poem analysis", "\n".join(analysis_report(text, model)))

    def _suggest_word(self) -> None:
        self.suggest_word()

    # Compatibility: old buttons/tests may call these, but generation is no longer a feature.
    def generate_line(self) -> None:
        self.statusBar().showMessage("Line generation was removed. Use Rhymes and Suggest word instead.", 4500)

    def continue_poem(self) -> None:
        self.generate_line()
