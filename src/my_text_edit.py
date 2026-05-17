from line_number_area import LineNumberArea
from line_annotation import LineAnnotation
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics,
    QTextCursor, QTextBlockFormat,
)
from PySide6.QtCore import Qt, QRect, QSize
from constants import ANN_MARGIN

RHYME_COLORS = [
    "#4a6fa5",  # A – blue
    "#b85c38",  # B – burnt orange
    "#4a8c5c",  # C – green
    "#7b5ea7",  # D – purple
    "#a07840",  # E – ochre
    "#3d8fa8",  # F – teal
    "#a84470",  # G – rose
    "#5a8060",  # H – sage
]
def rhyme_color(letter: str) -> str:
    idx = (ord(letter) - ord("A")) % len(RHYME_COLORS)
    return RHYME_COLORS[idx]

class MyTextEdit(QPlainTextEdit):
    """
    Text editor with per-line annotations painted above each poetry line.
    Annotations never overlap text: each block's top-margin is extended by
    ANN_MARGIN when annotation mode is active.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations: dict[str, LineAnnotation] = {}
        self._ann_active  = False    # True while block margins are expanded

        self.line_number_area = LineNumberArea(self)

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area)

        self.update_line_number_area_width()

    # ── Annotation data ───────────────────────────────────────────────────────

    def set_annotations(self, annotations: list[LineAnnotation], poem_text: str):
        """Push new annotation data and expand block margins to make room."""
        self._annotations.clear()
        lines = [l for l in poem_text.splitlines() if l.strip()]
        for i, ann in enumerate(annotations):
            if i < len(lines):
                self._annotations[lines[i]] = ann

        self._set_block_top_margins(ANN_MARGIN if annotations else 0)
        self._ann_active = bool(annotations)
        self.viewport().update()

    def clear_annotations(self):
        self._annotations.clear()
        self._set_block_top_margins(0)
        self._ann_active = False
        self.viewport().update()

    def _set_block_top_margins(self, margin_px: int):
        """
        Walk every block and set its top margin so the annotation strip
        has guaranteed empty space above the text glyphs.
        Uses a single QTextCursor edit block for efficiency.
        """
        doc    = self.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        fmt = QTextBlockFormat()
        fmt.setTopMargin(margin_px)

        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.mergeBlockFormat(fmt)

        cursor.endEditBlock()

    def _annotation_for_block(self, block_text: str) -> "LineAnnotation | None":
        return self._annotations.get(block_text.strip())

    # ── Line number area (unchanged logic) ───────────────────────────────────

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

        block        = self.document().firstBlock()
        block_number = 0
        top    = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#aaaaaa"))
                painter.drawText(
                    0, int(top),
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(block_number + 1),
                )
            block  = block.next()
            top    = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    # ── Annotation painting ───────────────────────────────────────────────────

    def paintEvent(self, event):
        super().paintEvent(event)       # draw normal text first

        if not self._ann_active or not self._annotations:
            return

        painter = QPainter(self.viewport())
        ann_font = QFont(self.font())
        ann_font.setPointSize(max(6, self.font().pointSize() - 3))
        ann_font.setItalic(True)
        painter.setFont(ann_font)
        fm     = QFontMetrics(ann_font)
        ann_h  = fm.height()
        offset = self.contentOffset()

        block = self.document().firstBlock()
        while block.isValid():
            ann = self._annotation_for_block(block.text())
            if ann is not None:
                br = self.blockBoundingGeometry(block).translated(offset)
                if br.bottom() >= event.rect().top() and br.top() <= event.rect().bottom():
                    # Paint inside the top-margin strip we reserved — text is below it
                    y = int(br.top()) + 1
                    x = 4

                    # ── Rhyme letter badge ────────────────────────────────────
                    letter = ann.rhyme_letter
                    if letter and letter != "?":
                        badge_w = fm.horizontalAdvance(letter) + 6
                        painter.fillRect(x, y, badge_w, ann_h - 1,
                                         QColor(rhyme_color(letter)))
                        painter.setPen(QColor("#ffffff"))
                        painter.drawText(x + 3, y, badge_w, ann_h,
                                         Qt.AlignLeft | Qt.AlignVCenter, letter)
                        x += badge_w + 5

                    # ── Stress pattern ────────────────────────────────────────
                    if ann.stress:
                        painter.setPen(QColor("#777777"))
                        painter.drawText(x, y, 9999, ann_h,
                                         Qt.AlignLeft | Qt.AlignVCenter, ann.stress)
                        x += fm.horizontalAdvance(ann.stress) + 8

                    # ── Foot · syllables ──────────────────────────────────────
                    if ann.foot:
                        painter.setPen(QColor("#aaaaaa"))
                        painter.drawText(x, y, 9999, ann_h,
                                         Qt.AlignLeft | Qt.AlignVCenter,
                                         f"{ann.foot} · {ann.syllables} syl")
            block = block.next()

        painter.end()
