import src.utils as utils

def test_clean_words_basic():
    assert utils.clean_words("Hello, world!") == ["hello", "world"]

def test_syllable_count_fallback():
    assert utils.syllable_count("qzx") >= 1

def test_stress_pattern_length():
    pattern = utils.stress_pattern("hello")
    assert set(pattern).issubset({"0", "1"})
    assert len(pattern) >= 1

def test_sentiment_returns_tuple():
    pol, subj = utils.sentiment("I love this")
    assert isinstance(pol, float)
    assert isinstance(subj, float)