from src.my_text_edit import MyTextEdit


def test_editor_creation(qtbot):
    editor = MyTextEdit()
    qtbot.addWidget(editor)

    editor.setPlainText("hello world")
    assert editor.toPlainText() == "hello world"


def test_annotations_can_be_set(qtbot):
    editor = MyTextEdit()
    qtbot.addWidget(editor)

    from src.line_annotation import LineAnnotation

    ann = LineAnnotation(
        stress="10",
        foot="iamb",
        syllables=5,
        rhyme_letter="A"
    )

    editor.set_annotations([ann], "hello world")
    assert editor._ann_active is True


def test_clear_annotations(qtbot):
    editor = MyTextEdit()
    qtbot.addWidget(editor)

    editor.clear_annotations()
    assert editor._ann_active is False