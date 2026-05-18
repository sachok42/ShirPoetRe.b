import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QTextCursor

from archive.src3.window import TextIDE


@pytest.fixture
def ide(qtbot):
    window = TextIDE()
    qtbot.addWidget(window)
    window.show()
    return window

def test_current_editor(ide):
    assert ide.current_editor() is not None

def test_window_title(ide):
    assert ide.windowTitle() == "Simple Text IDE"

def first_tab_exists(ide):
    assert ide.tabs.count() >= 1

def test_initial_tab_title(ide):
    assert ide.tabs.tabText(0) == "Untitled"

def test_text_input(ide, qtbot):
    editor = ide.current_editor()
    qtbot.keyClicks(editor, "Hello World")
    assert editor.toPlainText() == "Hello World"

def test_multiline_text_input(ide):
    editor = ide.current_editor()
    editor.setPlainText("Hello\nWorld")
    assert editor.toPlainText() == "Hello\nWorld"
    assert editor.document().blockCount() == 2

def test_text_deletion(ide, qtbot):
    editor = ide.current_editor()
    qtbot.keyClicks(editor, "abcdef")
    qtbot.keyClick(editor, Qt.Key_Backspace)
    assert editor.toPlainText() == "abcde"

def test_word_char_counter_empty(ide):
    editor = ide.current_editor()
    editor.setPlainText("")
    chars, words = ide.word_char_counter()
    assert chars == 0
    assert words == 0

def test_word_char_counter_text(ide):
    editor = ide.current_editor()
    editor.setPlainText("Hello   world")
    chars, words = ide.word_char_counter()
    assert chars == len("Hello   world")
    assert words == 2

def test_word_char_counter_spaces(ide):
    editor = ide.current_editor()
    editor.setPlainText("       ")
    chars, words = ide.word_char_counter()
    assert chars == 7
    assert words == 0

def test_word_char_counter_multiline(ide):
    editor = ide.current_editor()
    editor.setPlainText("one\ntwo\nthree")
    chars, words = ide.word_char_counter()
    assert words == 3

def test_cursor_position_updates(ide, qtbot):
    editor = ide.current_editor()
    qtbot.keyClicks(editor, "abc")
    text = ide.cursor_info.text()
    assert "Ln 1" in text
    assert "Col 4" in text

def test_cursor_position_multiline(ide):
    editor = ide.current_editor()
    editor.setPlainText("abc\ndef")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    ide.update_cursor_info()
    text = ide.cursor_info.text()
    assert "Ln 2" in text

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
    editor = ide.current_editor()
    editor.setPlainText("a\nb\nc")
    blocks = editor.document().blockCount()
    assert blocks == 3

def test_line_number_area_exists(ide):
    editor = ide.current_editor()
    assert editor.line_number_area is not None

def test_status_bar_exists(ide):
    assert ide.statusBar() is not None

def test_cursor_info_label_exists(ide):
    assert ide.cursor_info is not None

def test_cursor_info_updates_after_text_change(ide):
    editor = ide.current_editor()
    editor.setPlainText("Hello")
    ide.update_cursor_info()
    text = ide.cursor_info.text()
    assert "Words 1" in text
    assert "Chars 5" in text

def test_new_tab_creation(ide):
    initial_count = ide.tabs.count()
    ide.new_tab()
    assert ide.tabs.count() == initial_count + 1

def test_close_tab(ide):
    ide.new_tab()
    initial_count = ide.tabs.count()
    ide.close_tab(1)
    assert ide.tabs.count() == initial_count - 1

def test_cannot_close_last_tab(ide):
    ide.close_tab(0)
    assert ide.tabs.count() == 1

def test_switch_tabs(ide):
    ide.new_tab(title="Second")
    ide.tabs.setCurrentIndex(1)
    assert ide.tabs.tabText(1) == "Second"

def test_tab_text_content_is_independent(ide):
    editor1 = ide.current_editor()
    editor1.setPlainText("First tab")
    ide.new_tab()
    editor2 = ide.current_editor()
    editor2.setPlainText("Second tab")
    assert editor1.toPlainText() == "First tab"
    assert editor2.toPlainText() == "Second tab"
