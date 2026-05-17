from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QWidget,
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QPushButton, QScrollArea, QFrame, QProgressBar, QSpinBox,
)
from line_annotation import LineAnnotation
from improved_rhyme_matching import suggest_rhyme_repairs
from style_analysis import rank_words_by_style
from rhythm_analysis import analyse_rhythm
from rhythm_repair import suggest_rhythm_repairs, infer_target_syllables


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

        # ── Rhyme Repair group ────────────────────────────────────────────────
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

        # ── Rhythm Repair group ───────────────────────────────────────────────
        self.rhythm_repair_group = _make_group("Rhythm Repair")
        rr_hint = QLabel(
            "Suggest synonym swaps that bring a line's syllable count "
            "closer to the poem's dominant metre. "
            "Paste the offending line below; target syllables are inferred "
            "automatically or can be set manually."
        )
        rr_hint.setWordWrap(True)
        self.rhythm_repair_group.layout().addWidget(rr_hint)

        self.rr_line_edit = QLineEdit()
        self.rr_line_edit.setPlaceholderText("Paste the line to fix...")
        self.rhythm_repair_group.layout().addWidget(self.rr_line_edit)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target syllables:"))
        self.rr_target_spin = QSpinBox()
        self.rr_target_spin.setRange(1, 40)
        self.rr_target_spin.setValue(10)          # iambic pentameter default
        self.rr_target_spin.setToolTip(
            "Set the desired syllable count. "
            "Click 'Auto' to infer it from the poem."
        )
        target_row.addWidget(self.rr_target_spin)
        self.rr_auto_btn = QPushButton("Auto")
        self.rr_auto_btn.setToolTip("Infer target from the poem's median line length")
        self.rr_auto_btn.setFixedWidth(44)
        self.rr_auto_btn.clicked.connect(self._infer_target)
        target_row.addWidget(self.rr_auto_btn)
        target_row.addStretch()
        self.rhythm_repair_group.layout().addLayout(target_row)

        self.rr_btn = QPushButton("Find Rhythm Repairs")
        self.rr_btn.clicked.connect(self.run_rhythm_repair)
        self.rhythm_repair_group.layout().addWidget(self.rr_btn)

        self.rr_results = QVBoxLayout()
        self.rhythm_repair_group.layout().addLayout(self.rr_results)
        self.content.addWidget(self.rhythm_repair_group)

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

    # ── Infer target syllables from poem ─────────────────────────────────────

    def _infer_target(self):
        if not self._poem_text.strip():
            return
        target = infer_target_syllables(self._poem_text)
        if target is not None:
            self.rr_target_spin.setValue(target)

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
            # Auto-update the target spin to the poem's median when analysis runs
            target = infer_target_syllables(poem_text)
            if target is not None:
                self.rr_target_spin.setValue(target)
        except Exception as e:
            self.rhythm_group.layout().addWidget(QLabel(f"Error: {e}"))

    # ── Rhyme Repair ──────────────────────────────────────────────────────────

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

    # ── Rhythm Repair ─────────────────────────────────────────────────────────

    def run_rhythm_repair(self):
        self.clear_layout(self.rr_results)
        line = self.rr_line_edit.text().strip()
        if not line:
            self.rr_results.addWidget(QLabel("Paste a line first."))
            return

        target = self.rr_target_spin.value()
        from utils import clean_words, syllable_count
        current = sum(syllable_count(w) for w in clean_words(line))

        header = QLabel(
            f"Current: <b>{current}</b> syllables &nbsp;→&nbsp; Target: <b>{target}</b>"
        )
        header.setTextFormat(Qt.RichText)
        self.rr_results.addWidget(header)

        if current == target:
            self.rr_results.addWidget(QLabel("Line already matches the target — no repairs needed."))
            return

        try:
            suggestions = suggest_rhythm_repairs(line, target, top_n=6)
        except Exception as e:
            self.rr_results.addWidget(QLabel(f"Error: {e}"))
            return

        if not suggestions:
            self.rr_results.addWidget(
                QLabel("No synonym swaps found that improve the syllable count.")
            )
            return

        for s in suggestions:
            new_count = current + (s.syllable_delta if current < target else -s.syllable_delta)
            lbl = QLabel(
                f"<b>{s.original_word}</b> &rarr; <b>{s.replacement}</b> "
                f"&nbsp;({new_count} syl)<br>"
                f"<i>{s.example_line}</i>"
            )
            lbl.setTextFormat(Qt.RichText)
            lbl.setWordWrap(True)
            self.rr_results.addWidget(lbl)
            self.rr_results.addWidget(_score_row("Style fit", s.style_score))
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            self.rr_results.addWidget(sep)

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