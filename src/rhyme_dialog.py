"""Small rhyme window used by the main app.

The user flow is intentionally simple: enter a word, pick a rhyme, then insert it
or replace the current line ending.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from src.poetry_tools import check_rhyme, normalize_word, syllable_count


class RhymeDialog(QDialog):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Rhymes")
        self.resize(520, 430)

        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("word to rhyme with")
        self.find_button = QPushButton("Find")

        search_row = QHBoxLayout()
        search_row.addWidget(self.word_input)
        search_row.addWidget(self.find_button)

        self.results = QListWidget()
        self.result_label = QLabel("Exact rhymes are shown first; near rhymes fill the rest.")

        self.insert_button = QPushButton("Insert")
        self.replace_button = QPushButton("Replace line ending")
        button_row = QHBoxLayout()
        button_row.addWidget(self.insert_button)
        button_row.addWidget(self.replace_button)

        self.rhyme_status = QLabel("")
        self.refresh_status_button = QPushButton("Check last two lines")

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self.results)
        layout.addWidget(self.result_label)
        layout.addLayout(button_row)
        layout.addWidget(self.refresh_status_button)
        layout.addWidget(self.rhyme_status)

        self.find_button.clicked.connect(self.refresh_rhymes)
        self.word_input.returnPressed.connect(self.refresh_rhymes)
        self.insert_button.clicked.connect(self.insert_selected)
        self.replace_button.clicked.connect(self.replace_selected)
        self.results.itemDoubleClicked.connect(lambda _item: self.insert_selected())
        self.refresh_status_button.clicked.connect(self.refresh_last_line_status)

        hint = self.app.current_word_hint()
        if hint:
            self.word_input.setText(hint)
            self.refresh_rhymes()
        self.refresh_last_line_status()

    def selected_word(self) -> str:
        item = self.results.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def refresh_rhymes(self) -> None:
        target = normalize_word(self.word_input.text())
        self.results.clear()
        if not target:
            self.result_label.setText("Enter a word first.")
            return

        candidates = self.app.rhyme_candidates(target, limit=24)
        for candidate in candidates:
            label = f"{candidate.word}   {candidate.kind}, {candidate.syllables} syl"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, candidate.word)
            self.results.addItem(item)

        exact_count = sum(1 for candidate in candidates if candidate.kind == "exact")
        near_count = len(candidates) - exact_count
        if candidates:
            self.result_label.setText(f"Showing {len(candidates)}: {exact_count} exact, {near_count} near.")
        else:
            self.result_label.setText(f"No rhymes found for '{target}'.")

    def insert_selected(self) -> None:
        word = self.selected_word()
        if word:
            self.app.insert_word(word)

    def replace_selected(self) -> None:
        word = self.selected_word()
        if word:
            self.app.replace_current_line_last_word(word)

    def refresh_last_line_status(self) -> None:
        lines = self.app.non_empty_lines()
        if len(lines) < 2:
            self.rhyme_status.setText("Last two lines: not enough text yet.")
            return

        result = check_rhyme(lines[-2], lines[-1])
        verdict = "rhyme" if result.rhymes else "do not rhyme"
        self.rhyme_status.setText(
            f"Last two lines: {result.word_a} / {result.word_b} {verdict} "
            f"(distance {result.distance})."
        )

        if result.word_a and not normalize_word(self.word_input.text()):
            self.word_input.setText(result.word_a)
            self.refresh_rhymes()
