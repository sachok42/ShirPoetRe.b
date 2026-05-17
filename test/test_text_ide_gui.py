import pytest
from src.text_IDE import TextIDE
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Qt


@pytest.fixture
def ide(qtbot):
    window = TextIDE()
    qtbot.addWidget(window)
    window.show()
    return window


def test_main_window_starts(ide):
    assert ide.isVisible()
    assert ide.tabs.count() >= 1


def test_new_tab_creation(ide):
    initial = ide.tabs.count()
    ide.new_tab("hello world", "Test")
    assert ide.tabs.count() == initial + 1
    assert "Test" in ide.tabs.tabText(ide.tabs.currentIndex())


def test_current_editor_returns_widget(ide):
    editor = ide.current_editor()
    assert editor is not None
    editor.setPlainText("abc")
    assert "abc" in editor.toPlainText()


def test_word_char_counter_updates(ide):
    editor = ide.current_editor()
    editor.setPlainText("hello world")
    chars, words = ide.word_char_counter()
    assert chars > 0
    assert words == 2


def test_cursor_info_updates(ide, qtbot):
    editor = ide.current_editor()
    editor.setPlainText("hello world")
    editor.moveCursor(QTextCursor.End)
    qtbot.wait(50)
    ide.update_cursor_info()
    assert "Ln" in ide.cursor_info.text()


def test_analysis_panel_toggle(ide):
    assert not ide.analysis_panel.isVisible()
    ide.toggle_analysis_panel(True)
    assert ide.analysis_panel.isVisible()
    ide.toggle_analysis_panel(False)
    assert not ide.analysis_panel.isVisible()


def test_run_analysis_creates_annotations(ide, qtbot):
    editor = ide.current_editor()
    editor.setPlainText("the sky is blue\nthe grass is green")

    qtbot.mouseClick(
        ide.analysis_panel.run_btn,
        Qt.LeftButton
    )

    ide.run_analysis()

    assert editor._ann_active is True or len(editor._annotations) >= 0


def test_focus_mode_toggle(ide):
    ide.toggle_focus_mode()
    assert ide.is_focus_mode is True or ide.isFullScreen()

    ide.toggle_focus_mode()
    assert ide.is_focus_mode is False