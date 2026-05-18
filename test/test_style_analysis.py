import src.style_analysis as sa

def test_build_profile_non_empty():
    p = sa.build_style_profile("the silent moon drifts")
    assert p.avg_word_length > 0

def test_build_profile_empty():
    p = sa.build_style_profile("")
    assert p.avg_word_length == 0

def test_rank_words_returns_sorted():
    res = sa.rank_words_by_style(
        "the silent moon",
        ["gloom", "happy", "light"]
    )
    scores = [s for _, s in res]
    assert scores == sorted(scores, reverse=True)

def test_rate_style_score_range():
    p = sa.build_style_profile("the moon shines")
    score = sa.rate_style_score("light", p)
    assert 0 <= score <= 1