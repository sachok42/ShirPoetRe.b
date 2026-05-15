import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from src.window import TextIDE


@pytest.fixture
def ide(qtbot):
    window = TextIDE()
    qtbot.addWidget(window)
    window.show()
    return window


def test_window_title(ide):
    assert ide.windowTitle() == "Simple Text IDE"


def test_text_input(ide, qtbot):
    qtbot.keyClicks(ide.editor, "Hello World")
    assert ide.editor.toPlainText() == "Hello World"


def test_word_char_counter_empty(ide):
    ide.editor.setPlainText("")
    chars, words = ide.word_char_counter()
    assert chars == 0
    assert words == 0


def test_word_char_counter_text(ide):
    ide.editor.setPlainText("Hello   world")
    chars, words = ide.word_char_counter()
    assert chars == len("Hello   world")
    assert words == 2


def test_word_char_counter_spaces(ide):
    ide.editor.setPlainText("       ")
    chars, words = ide.word_char_counter()
    assert chars == 7
    assert words == 0


def test_cursor_position_updates(ide, qtbot):
    qtbot.keyClicks(ide.editor, "abc")
    text = ide.cursor_info.text()
    assert "Ln 1" in text
    assert "Col 4" in text


def test_theme_toggle(ide):
    assert ide.is_dark_theme is False
    ide.toggle_theme(True)
    assert ide.is_dark_theme is True


def test_focus_mode_enable(ide, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    ide.toggle_focus_mode()
    assert ide.is_focus_mode is True
    assert ide.menuBar().isHidden()


def test_focus_mode_disable(ide, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    ide.toggle_focus_mode()
    ide.toggle_focus_mode()
    assert ide.is_focus_mode is False
    assert not ide.menuBar().isHidden()


def test_f12_focus_shortcut(ide, qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    qtbot.keyClick(ide, Qt.Key_F12)
    assert ide.is_focus_mode is True


def test_line_count(ide):
    ide.editor.setPlainText("a\nb\nc")
    blocks = ide.editor.document().blockCount()
    assert blocks == 3