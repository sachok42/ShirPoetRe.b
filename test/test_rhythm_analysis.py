import src.rhythm_analysis as ra

def test_line_stress_runs():
    s = ra.line_stress("the cat sleeps")
    assert isinstance(s, str)

def test_analyse_rhythm_basic():
    poem = "the cat sleeps\nthe dog runs"
    r = ra.analyse_rhythm(poem)
    assert len(r.lines) == 2
    assert r.syllable_counts

def test_dominant_foot_optional():
    assert ra.dominant_foot("") is None

def test_regularly_score_bounds():
    poem = "a a\nb b"
    r = ra.analyse_rhythm(poem)
    assert 0 <= r.regularity_score <= 1