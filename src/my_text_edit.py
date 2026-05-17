from line_number_area import LineNumberArea
from line_annotation import LineAnnotation
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics,
    QTextCursor, QTextBlockFormat,
    QSyntaxHighlighter, QTextCharFormat,
)
from PySide6.QtCore import Qt, QRect, QSize
import re

# Badge column width (pixels) reserved inside the gutter for the rhyme letter.
# The line-number gutter is widened by this amount when annotations are active.
BADGE_COL = 22

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


# ── Unknown-word highlighter ──────────────────────────────────────────────────

def _build_known_words() -> frozenset[str]:
    """
    Build a set of known English words from two sources:
      1. The CMU pronouncing dictionary (every word pronouncing knows).
      2. NLTK's 'words' corpus as a broad-coverage fallback.
    Both sources are already used by the project (pronouncing, nltk via textblob).
    """
    known: set[str] = set()

    # Source 1 – CMU dict (most reliable; if pronouncing knows it, it's real)
    try:
        import pronouncing
        try:
            known.update(e.lower() for e in pronouncing._cmu_entries().keys())
        except AttributeError:
            if hasattr(pronouncing, '_cmu'):
                known.update(k.lower() for k in pronouncing._cmu.keys())
    except Exception:
        pass

    # Source 2 – NLTK words corpus
    try:
        from nltk.corpus import words as _nltk_words
        known.update(w.lower() for w in _nltk_words.words())
    except LookupError:
        try:
            import nltk
            nltk.download("words", quiet=True)
            from nltk.corpus import words as _nltk_words
            known.update(w.lower() for w in _nltk_words.words())
        except Exception:
            pass
    except Exception:
        pass

    return frozenset(known)


# Populated on first use so startup stays fast.
_KNOWN_WORDS: frozenset[str] = frozenset()

def _known_words() -> frozenset[str]:
    global _KNOWN_WORDS
    if not _KNOWN_WORDS:
        _KNOWN_WORDS = _build_known_words()
    return _KNOWN_WORDS


class UnknownWordHighlighter(QSyntaxHighlighter):
    """
    Underlines words not found in the CMU pronouncing dictionary or the
    NLTK English words corpus, using an amber SpellCheck underline.
    Contractions ("don't", "it's") are handled by stripping the suffix
    before the lookup so they are never falsely flagged.
    """

    _WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)*")

    def __init__(self, document):
        super().__init__(document)
        self._fmt = QTextCharFormat()
        self._fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self._fmt.setUnderlineColor(QColor("#e0a030"))   # amber
        self._enabled = True

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        self.rehighlight()

    def highlightBlock(self, text: str):
        if not self._enabled:
            return
        known = _known_words()
        for m in self._WORD_RE.finditer(text):
            word = m.group(0).lower()
            # Strip possessive / contraction suffix for the lookup
            base = re.sub(r"'.*$", "", word)
            if base and base not in known and word not in known:
                self.setFormat(m.start(), m.end() - m.start(), self._fmt)


# ── Editor ────────────────────────────────────────────────────────────────────

class MyTextEdit(QPlainTextEdit):
    """
    Text editor with per-line rhyme/rhythm annotations and unknown-word
    highlighting.

    Layout (no text is ever overlapped):
      • Rhyme-letter badge  – painted inside the line-number gutter, to the
                              right of the line number, vertically centred on
                              the text line.
      • Stress + foot info  – painted to the RIGHT of the line's last glyph,
                              on the same vertical centre as the text.
      • Unknown words       – underlined in amber by UnknownWordHighlighter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations: dict[str, LineAnnotation] = {}
        self._ann_active  = False

        self.line_number_area = LineNumberArea(self)

        # Attach the unknown-word highlighter to this editor's document
        self._highlighter = UnknownWordHighlighter(self.document())

        self.document().blockCountChanged.connect(self.update_line_number_area_width)
        self.verticalScrollBar().valueChanged.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.update_line_number_area)

        self.update_line_number_area_width()

    # ── Highlighter control ───────────────────────────────────────────────────

    def set_unknown_word_highlight(self, enabled: bool):
        """Toggle the amber unknown-word underline on or off."""
        self._highlighter.set_enabled(enabled)

    # ── Annotation data ───────────────────────────────────────────────────────

    def set_annotations(self, annotations: list[LineAnnotation], poem_text: str):
        """Push new annotation data; widen the gutter to fit the badge column."""
        self._annotations.clear()
        lines = [l for l in poem_text.splitlines() if l.strip()]
        for i, ann in enumerate(annotations):
            if i < len(lines):
                self._annotations[lines[i]] = ann

        self._ann_active = bool(annotations)
        self.update_line_number_area_width()
        self.viewport().update()

    def clear_annotations(self):
        self._annotations.clear()
        self._ann_active = False
        self.update_line_number_area_width()
        self.viewport().update()

    def annotation_for_block(self, block_text: str) -> "LineAnnotation | None":
        return self._annotations.get(block_text.strip())

    # ── Line number / gutter sizing ───────────────────────────────────────────

    def line_number_area_size(self) -> QSize:
        digits = len(str(self.document().blockCount()))
        num_w  = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        badge_w = BADGE_COL if self._ann_active else 0
        return QSize(num_w + badge_w, 0)

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

    # ── Gutter paint: line numbers + rhyme-letter badge ───────────────────────

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#2b2b2b"))

        gutter_w     = self.line_number_area.width()
        badge_col_x  = gutter_w - BADGE_COL
        num_w        = gutter_w - (BADGE_COL if self._ann_active else 0)

        ann_font = QFont(self.font())
        ann_font.setPointSize(max(6, self.font().pointSize() - 2))
        ann_font.setBold(True)
        ann_fm   = QFontMetrics(ann_font)

        block        = self.document().firstBlock()
        block_number = 0
        top    = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_h = int(bottom - top)
                y_top  = int(top)

                # ── Line number ───────────────────────────────────────────────
                painter.setFont(self.font())
                painter.setPen(QColor("#aaaaaa"))
                painter.drawText(
                    0, y_top,
                    num_w - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(block_number + 1),
                )

                # ── Rhyme-letter badge ────────────────────────────────────────
                if self._ann_active:
                    ann = self.annotation_for_block(block.text())
                    if ann is not None:
                        letter = ann.rhyme_letter
                        if letter and letter != "?":
                            painter.setFont(ann_font)
                            bw = ann_fm.horizontalAdvance(letter) + 6
                            bh = ann_fm.height() + 2
                            by = y_top + (line_h - bh) // 2
                            bx = badge_col_x + (BADGE_COL - bw) // 2
                            painter.fillRect(bx, by, bw, bh,
                                             QColor(rhyme_color(letter)))
                            painter.setPen(QColor("#ffffff"))
                            painter.drawText(bx, by, bw, bh,
                                             Qt.AlignCenter, letter)

            block  = block.next()
            top    = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

        painter.end()

    # ── Viewport paint: stress + foot/syllable info after each line ───────────

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self._ann_active or not self._annotations:
            return

        painter = QPainter(self.viewport())
        ann_font = QFont(self.font())
        ann_font.setPointSize(max(6, self.font().pointSize() - 3))
        ann_font.setItalic(True)
        painter.setFont(ann_font)
        fm      = QFontMetrics(ann_font)
        main_fm = self.fontMetrics()
        offset  = self.contentOffset()

        block = self.document().firstBlock()
        while block.isValid():
            ann = self.annotation_for_block(block.text())
            if ann is not None:
                br = self.blockBoundingGeometry(block).translated(offset)
                if br.bottom() >= event.rect().top() and br.top() <= event.rect().bottom():

                    line_h = int(br.height())
                    y_top  = int(br.top())
                    y_text_centre = y_top + (line_h - fm.height()) // 2

                    line_text = block.text()
                    text_px   = main_fm.horizontalAdvance(line_text)
                    x = int(br.left()) + text_px + 16

                    # ── Stress pattern ────────────────────────────────────────
                    if ann.stress:
                        painter.setPen(QColor("#777777"))
                        painter.drawText(
                            x, y_text_centre, 9999, fm.height(),
                            Qt.AlignLeft | Qt.AlignVCenter,
                            ann.stress,
                        )
                        x += fm.horizontalAdvance(ann.stress) + 10

                    # ── Foot · syllables ──────────────────────────────────────
                    if ann.foot:
                        painter.setPen(QColor("#aaaaaa"))
                        painter.drawText(
                            x, y_text_centre, 9999, fm.height(),
                            Qt.AlignLeft | Qt.AlignVCenter,
                            f"{ann.foot} · {ann.syllables} syl",
                        )

            block = block.next()

        painter.end()