from PySide6.QtWidgets import QWidget

class LineNumberArea(QWidget):
    """
    Line enumerator for the written text. Number is written to the left to each text block.
    """

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.line_number_area_size()

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

