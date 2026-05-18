"""Final application wiring for ShirPoetRe.b."""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtWidgets import QToolBar, QMenu

import model
from src.poetry_tools import (
    WORD_RE,
    find_rhyme_candidates,
    find_rhymes,
    model_vocabulary,
    model_word_counts,
    next_word_candidates,
    smart_bulk_generate,
    normalize_word,
)
from src.rhyme_dialog import RhymeDialog
from src.window import TextIDE

class ShirPoetApp(TextIDE):
    """Text IDE with interactive AI drop-downs and anti-loop bulk generation."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShirPoetRe.b - Interactive AI Edition")
        self.editor = self.current_editor()
        self.tabs.currentChanged.connect(self._sync_current_editor)
        self._init_model()
        self._init_poetry_tools()

    def _sync_current_editor(self) -> None:
        self.editor = self.current_editor()

    def _init_model(self) -> None:
        try:
            model.load_artifacts(required=False)
            status = "Neural model loaded (Pure AI active)" if model.is_fitted() else "Using fallback vocabulary"
        except Exception as exc:
            status = f"Model load error: {exc}"
        self.statusBar().showMessage(status, 6000)

    def _init_poetry_tools(self) -> None:
        self.ai_action = self._make_action("Suggest word", "Ctrl+G", self.suggest_word)
        self.rhyme_action = self._make_action("Rhymes", "Ctrl+R", self.open_rhyme_dialog)
        self.bulk_action = self._make_action("Magic Bulk", "Ctrl+B", self.bulk_magic)

        # Оставили только 3 самые нужные кнопки, Analyse удален
        actions = (self.ai_action, self.rhyme_action, self.bulk_action)
        toolbar = self.findChild(QToolBar)
        if toolbar:
            toolbar.addSeparator()
            for action in actions:
                toolbar.addAction(action)

        poetry_menu = self.menuBar().addMenu("Poetry")
        for action in actions:
            poetry_menu.addAction(action)

        self.statusBar().showMessage("Ready. Press Ctrl+G for AI suggestions.", 3000)

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
        if editor is None: return ""
        cursor = editor.textCursor()
        selected = normalize_word(cursor.selectedText())
        if selected: return selected
        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return normalize_word(word_cursor.selectedText()) or normalize_word(self.editor_text())

    def insert_word(self, word: str) -> None:
        editor = self.current_editor()
        if editor is None: return
        text = self.editor_text()
        prefix = "" if not text or text.endswith((" ", "\n", "\t")) else " "
        editor.insertPlainText(prefix + word)
        self.statusBar().showMessage(f"AI Inserted: {word}", 2500)

    def replace_current_line_last_word(self, word: str) -> None:
        editor = self.current_editor()
        if editor is None: return
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

    def rhyme_candidates(self, word: str, limit: int = 24):
        return find_rhyme_candidates(word, model_vocabulary(model), model_word_counts(model), limit)

    # ==========================================
    # ИНТЕРАКТИВНОЕ МЕНЮ ДЛЯ SUGGEST (CTRL+G)
    # ==========================================
    def suggest_word(self) -> None:
        context = self.editor_text()
        if not context.strip():
            self.statusBar().showMessage("Type some context first.", 3000)
            return

        # Авто-рифма, если перешли на новую строку
        lines = self.non_empty_lines()
        target_rhyme = None
        if context.endswith('\n') and len(lines) >= 1:
            last_line_words = lines[-1].split()
            if last_line_words:
                target_rhyme = normalize_word(last_line_words[-1])

        # Получаем чистые предсказания от ИИ
        candidates = next_word_candidates(context, model, limit=8, rhyme_with=target_rhyme)

        if not candidates:
            self.statusBar().showMessage("AI needs more context...", 3500)
            return

        # --- СОЗДАЕМ ВСПЛЫВАЮЩЕЕ МЕНЮ ПРЯМО ПОД КУРСОРОМ ---
        editor = self.current_editor()
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #2b2b2b; color: white; border: 1px solid #444; }
            QMenu::item:selected { background-color: #3a6ea5; }
        """)

        for word in candidates:
            action = QAction(word, self)
            action.triggered.connect(lambda checked=False, w=word: self.insert_word(w))
            menu.addAction(action)

        # Вычисляем позицию курсора на экране
        cursor_rect = editor.cursorRect()
        global_pos = editor.mapToGlobal(cursor_rect.bottomRight())

        # Показываем меню
        menu.exec(global_pos)

    # ==========================================
    # ANTI-LOOP BULK MAGIC (CTRL+B)
    # ==========================================
    def bulk_magic(self) -> None:
        context = self.editor_text()
        self.statusBar().showMessage("AI is weaving lines...", 3000)

        try:
            # Используем наш новый генератор, который активно избегает повторов
            new_part = smart_bulk_generate(context, model, num_words=15)
            if new_part:
                self.current_editor().insertPlainText(" " + new_part)
            self.statusBar().showMessage("Bulk generation complete.", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Bulk failed: {e}", 4000)

    def open_rhyme_dialog(self) -> None:
        RhymeDialog(self).exec()

    def _suggest_word(self) -> None:
        self.suggest_word()

    def generate_line(self) -> None:
        self.bulk_magic()

    def continue_poem(self) -> None:
        self.bulk_magic()