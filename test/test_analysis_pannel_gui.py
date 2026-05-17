from src.analysis_pannel import AnalysisPanel


def test_panel_creation(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)
    panel.show()

    assert panel.isVisible()
    assert panel.scheme_lbl is not None


def test_auto_toggle_text(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)

    panel.auto_btn.setChecked(True)
    assert "ON" in panel.auto_btn.text()


def test_style_rank_empty_input(qtbot):
    panel = AnalysisPanel()
    qtbot.addWidget(panel)

    panel.candidates_edit.setText("")
    panel.run_style()

    assert panel.style_results.count() >= 1