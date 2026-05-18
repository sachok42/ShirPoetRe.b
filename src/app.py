"""ShirPoetRe — merged application entry point.

Combines the full TextIDE (analysis panel, auto-analysis, inline
stress/rhyme annotations, focus mode, unknown-word highlighting) with the
AI poetry tools (Ctrl+G word suggestions, Ctrl+R rhyme dialog, Ctrl+B
bulk generation) that were previously in a separate launcher.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import QMenu, QToolBar

import model
from poetry_tools import (
    WORD_RE,
    find_rhyme_candidates,
    find_rhymes,
    model_vocabulary,
    model_word_counts,
    next_word_candidates,
    smart_bulk_generate,
    normalize_word,
)
from rhyme_dialog import RhymeDialog

# Inherit the FULL TextIDE (analysis panel, auto-analysis, annotations …)
# not the older window.py version.
from text_IDE import TextIDE


class ShirPoetApp(TextIDE):
    """
    Full poetry IDE.

    Inherits from TextIDE everything it already provides:
      • Tabbed editor with line numbers and rhyme-letter badges
      • Inline stress / foot / syllable annotations (auto-updated on Enter)
      • Analysis panel (Ctrl+Shift+A) with rhyme scheme, rhythm summary
      • Unknown-word amber underline
      • Focus mode (F12), day/night theme, file management

    Adds AI poetry tools on top:
      • Ctrl+G  – pop-up word suggestions from the neural model
      • Ctrl+R  – rhyme finder dialog
      • Ctrl+B  – anti-loop bulk line generation
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShirPoetRe — Poetry IDE")
        # keep a reference that stays current when tabs switch
        self.editor = self.current_editor()
        self.tabs.currentChanged.connect(self._sync_current_editor)
        self._init_model()
        self._init_poetry_tools()

    # ── internal helpers ──────────────────────────────────────────────────────

    def _sync_current_editor(self) -> None:
        self.editor = self.current_editor()

    def _init_model(self) -> None:
        try:
            model.load_artifacts(required=False)
            status = (
                "Neural model loaded (Pure AI active)"
                if model.is_fitted()
                else "Using fallback vocabulary"
            )
        except Exception as exc:
            status = f"Model load error: {exc}"
        self.statusBar().showMessage(status, 6000)

    def _init_poetry_tools(self) -> None:
        self.ai_action = self._make_action(
            "Suggest word", "Ctrl+G", self.suggest_word
        )
        self.rhyme_action = self._make_action(
            "Rhymes", "Ctrl+R", self.open_rhyme_dialog
        )
        self.bulk_action = self._make_action(
            "Magic Bulk", "Ctrl+B", self.bulk_magic
        )

        actions = (self.ai_action, self.rhyme_action, self.bulk_action)

        # Append to the existing toolbar created by TextIDE.__init__
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.addSeparator()
            for action in actions:
                toolbar.addAction(action)

        # Add a dedicated Poetry menu
        poetry_menu = self.menuBar().addMenu("Poetry")
        for action in actions:
            poetry_menu.addAction(action)

        self.statusBar().showMessage(
            "Ready — Ctrl+G suggest · Ctrl+R rhymes · Ctrl+B bulk", 4000
        )

    def _make_action(self, text: str, shortcut: str, slot) -> QAction:
        action = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(slot)
        return action

    # ── editor accessors ──────────────────────────────────────────────────────

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
        self.schedule_auto_analysis(800)

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
        cursor.setPosition(
            block.position() + last_match.end(),
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(word)
        editor.setTextCursor(cursor)
        self.schedule_auto_analysis(800)

    def rhyme_candidates(self, word: str, limit: int = 24):
        return find_rhyme_candidates(
            word, model_vocabulary(model), model_word_counts(model), limit
        )

    # ── AI actions ────────────────────────────────────────────────────────────

    def suggest_word(self) -> None:
        """Ctrl+G: show a pop-up menu of AI-suggested next words."""
        context = self.editor_text()
        if not context.strip():
            self.statusBar().showMessage("Type some context first.", 3000)
            return

        # Auto-rhyme hint when the user just pressed Enter
        lines = self.non_empty_lines()
        target_rhyme = None
        if context.endswith("\n") and lines:
            last_words = lines[-1].split()
            if last_words:
                target_rhyme = normalize_word(last_words[-1])

        candidates = next_word_candidates(
            context, model, limit=8, rhyme_with=target_rhyme
        )
        if not candidates:
            self.statusBar().showMessage("AI needs more context…", 3500)
            return

        editor = self.current_editor()
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #2b2b2b; color: white; border: 1px solid #444; }"
            "QMenu::item:selected { background-color: #3a6ea5; }"
        )
        for word in candidates:
            action = QAction(word, self)
            action.triggered.connect(lambda checked=False, w=word: self.insert_word(w))
            menu.addAction(action)

        cursor_rect = editor.cursorRect()
        global_pos = editor.mapToGlobal(cursor_rect.bottomRight())
        menu.exec(global_pos)

    def bulk_magic(self) -> None:
        """Ctrl+B: anti-loop bulk word generation."""
        context = self.editor_text()
        self.statusBar().showMessage("AI is weaving lines…", 3000)
        try:
            new_part = smart_bulk_generate(context, model, num_words=15)
            if new_part:
                self.current_editor().insertPlainText(" " + new_part)
            self.statusBar().showMessage("Bulk generation complete.", 3000)
        except Exception as exc:
            self.statusBar().showMessage(f"Bulk failed: {exc}", 4000)
        finally:
            # Bulk inserts words without pressing Enter, so blockCountChanged
            # never fires.  Explicitly reschedule analysis so annotations and
            # the analysis panel reflect the new text.
            self.schedule_auto_analysis(800)

    def open_rhyme_dialog(self) -> None:
        """Ctrl+R: open the rhyme finder dialog."""
        RhymeDialog(self).exec()

    # Aliases kept for any internal callers
    def generate_line(self) -> None:
        self.bulk_magic()

    def continue_poem(self) -> None:
        self.bulk_magic()