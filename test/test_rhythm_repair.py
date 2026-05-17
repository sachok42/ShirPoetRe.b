import src.rhythm_repair as rr

def test_synonyms_returns_list():
    assert isinstance(rr.synonyms("light"), list)

def test_swap_word_basic():
    out = rr._swap_word("hello world", "world", "moon")
    assert "moon" in out

def test_infer_target_syllables_none_or_int():
    val = rr.infer_target_syllables("a\nb")
    assert val is None or isinstance(val, int)

def test_suggest_rhythm_repairs_empty_or_list():
    res = rr.suggest_rhythm_repairs("hello world test", 5)
    assert isinstance(res, list)