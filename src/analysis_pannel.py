from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QWidget,
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar,
)
from line_annotation import LineAnnotation
from improved_rhyme_matching import suggest_rhyme_repairs
from style_analysis import rank_words_by_style
from rhythm_analysis import analyse_rhythm


def _make_group(title: str) -> QGroupBox:
    g = QGroupBox(title)
    g.setLayout(QVBoxLayout())
    g.layout().setContentsMargins(8, 12, 8, 8)
    g.layout().setSpacing(4)
    return g


def _score_row(label: str, value: float) -> QWidget:
    row = QWidget()
    hl  = QHBoxLayout(row)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(6)
    lbl = QLabel(label)
    lbl.setFixedWidth(80)
    hl.addWidget(lbl)
    bar = QProgressBar()
    bar.setRange(0, 100)
    bar.setValue(int(value * 100))
    bar.setTextVisible(False)
    bar.setFixedHeight(8)
    hl.addWidget(bar, 1)
    val = QLabel(f"{value:.2f}")
    val.setFixedWidth(34)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    hl.addWidget(val)
    return row


class AnalysisPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.setMaximumWidth(420)
        self._poem_text = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ── Run Analysis button ───────────────────────────────────────────────
        self.run_btn = QPushButton("Run Analysis")
        self.run_btn.setToolTip("Refresh inline annotations (Ctrl+Shift+A)")
        root.addWidget(self.run_btn)

        # ── Auto-run toggle ───────────────────────────────────────────────────
        self.auto_btn = QPushButton("Auto-Analyse: OFF")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setEnabled(True)
        self.auto_btn.toggled.connect(self._on_auto_toggled)
        root.addWidget(self.auto_btn)

        # ── Scrollable content ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self.content = QVBoxLayout(inner)
        self.content.setContentsMargins(0, 0, 0, 0)
        self.content.setSpacing(8)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # ── Scheme summary ────────────────────────────────────────────────────
        self.scheme_group = _make_group("Rhyme Scheme")
        self.scheme_lbl   = QLabel("Run analysis to detect rhyme scheme.")
        self.scheme_lbl.setWordWrap(True)
        self.scheme_group.layout().addWidget(self.scheme_lbl)
        self.content.addWidget(self.scheme_group)

        # ── Rhythm summary ────────────────────────────────────────────────────
        self.rhythm_group = _make_group("Rhythm Summary")
        self.rhythm_lbl   = QLabel("Run analysis to see rhythm summary.")
        self.rhythm_lbl.setWordWrap(True)
        self.rhythm_group.layout().addWidget(self.rhythm_lbl)
        self.content.addWidget(self.rhythm_group)

        # ── Repair group ──────────────────────────────────────────────────────
        self.repair_group = _make_group("Rhyme Repair")
        repair_hint = QLabel("Find replacement words that rhyme with the anchor line.")
        repair_hint.setWordWrap(True)
        self.repair_group.layout().addWidget(repair_hint)

        anchor_row = QHBoxLayout()
        anchor_row.addWidget(QLabel("Anchor:"))
        self.anchor_edit = QLineEdit()
        self.anchor_edit.setPlaceholderText("Line with the target rhyme...")
        anchor_row.addWidget(self.anchor_edit, 1)
        self.repair_group.layout().addLayout(anchor_row)

        broken_row = QHBoxLayout()
        broken_row.addWidget(QLabel("Broken:"))
        self.broken_edit = QLineEdit()
        self.broken_edit.setPlaceholderText("Line that doesn't rhyme yet...")
        broken_row.addWidget(self.broken_edit, 1)
        self.repair_group.layout().addLayout(broken_row)

        self.repair_btn = QPushButton("Find Repairs")
        self.repair_btn.setEnabled(True)
        self.repair_btn.clicked.connect(self.run_repair)
        self.repair_group.layout().addWidget(self.repair_btn)

        self.repair_results = QVBoxLayout()
        self.repair_group.layout().addLayout(self.repair_results)
        self.content.addWidget(self.repair_group)

        # ── Style group ───────────────────────────────────────────────────────
        self.style_group = _make_group("Style Fit")
        style_hint = QLabel("Score candidate words against the poem's style.")
        style_hint.setWordWrap(True)
        self.style_group.layout().addWidget(style_hint)

        self.candidates_edit = QLineEdit()
        self.candidates_edit.setPlaceholderText("gloom, luminous, swift, gentle...")
        self.style_group.layout().addWidget(self.candidates_edit)

        self.style_btn = QPushButton("Rank by Style")
        self.style_btn.setEnabled(True)
        self.style_btn.clicked.connect(self.run_style)
        self.style_group.layout().addWidget(self.style_btn)

        self.style_results = QVBoxLayout()
        self.style_group.layout().addLayout(self.style_results)
        self.content.addWidget(self.style_group)

        self.content.addStretch()

    # ── Auto toggle ───────────────────────────────────────────────────────────

    def _on_auto_toggled(self, checked: bool):
        self.auto_btn.setText(f"Auto-Analyse: {'ON' if checked else 'OFF'}")

    @property
    def auto_analyse(self) -> bool:
        return self.auto_btn.isChecked()

    # ── Summary update ────────────────────────────────────────────────────────

    def update_summaries(self, poem_text: str,
                         annotations: list[LineAnnotation],
                         scheme: list[str]):
        self._poem_text = poem_text

        scheme_str = " ".join(scheme) if scheme else "—"
        self.scheme_lbl.setText(f"Pattern:  {scheme_str}")

        self.clear_layout(self.rhythm_group.layout())
        if not poem_text.strip():
            self.rhythm_group.layout().addWidget(QLabel("No data."))
            return
        try:
            result = analyse_rhythm(poem_text)
            metre  = result.overall_metre.title() if result.overall_metre else "—"
            self.rhythm_group.layout().addWidget(QLabel(f"Dominant metre:  {metre}"))
            self.rhythm_group.layout().addWidget(
                _score_row("Regularity", result.regularity_score)
            )
        except Exception as e:
            self.rhythm_group.layout().addWidget(QLabel(f"Error: {e}"))

    # ── Repair ────────────────────────────────────────────────────────────────

    def run_repair(self):
        self.clear_layout(self.repair_results)
        anchor = self.anchor_edit.text().strip()
        broken = self.broken_edit.text().strip()
        if not anchor or not broken:
            self.repair_results.addWidget(QLabel("Fill both lines first."))
            return
        try:
            suggestions = suggest_rhyme_repairs(anchor, broken, top_n=6)
        except Exception as e:
            self.repair_results.addWidget(QLabel(f"Error: {e}"))
            return
        if not suggestions:
            self.repair_results.addWidget(
                QLabel("No rhyming words found for the anchor's last word.")
            )
            return
        for s in suggestions:
            lbl = QLabel(
                f"<b>{s['word']}</b>  (rhymes with \"{s['rhyme_with']}\")<br>"
                f"&rarr; <i>{s['example_line']}</i>"
            )
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            self.repair_results.addWidget(lbl)
            self.repair_results.addWidget(_score_row("Style fit", s["style_score"]))
            self.repair_results.addWidget(
                _score_row("Sentiment", 1 - min(s["sentiment_delta"], 1.0))
            )
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            self.repair_results.addWidget(sep)

    # ── Style ─────────────────────────────────────────────────────────────────

    def run_style(self):
        self.clear_layout(self.style_results)
        words_raw = self.candidates_edit.text().strip()
        if not words_raw:
            self.style_results.addWidget(QLabel("Enter candidate words first."))
            return
        if not self._poem_text.strip():
            self.style_results.addWidget(QLabel("Open a poem in the editor first."))
            return
        candidates = [w.strip() for w in words_raw.split(",") if w.strip()]
        try:
            ranked = rank_words_by_style(self._poem_text, candidates)
        except Exception as e:
            self.style_results.addWidget(QLabel(f"Error: {e}"))
            return
        for i, (word, score) in enumerate(ranked):
            self.style_results.addWidget(QLabel(f"#{i+1}  {word}"))
            self.style_results.addWidget(_score_row("Style fit", score))

    @staticmethod
    def clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                AnalysisPanel.clear_layout(item.layout())