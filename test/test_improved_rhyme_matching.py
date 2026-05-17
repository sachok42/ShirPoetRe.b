import src.improved_rhyme_matching as irm

def test_phoneme_functions_safe():
    assert isinstance(irm.phones_for("cat"), list)

def test_rhyme_nucleus_empty_safe():
    assert irm.rhyme_nucleus([]) == ""

def test_soft_rhyme_same_word_false():
    assert irm.soft_rhyme("blue", "blue") is False

def test_detect_rhyme_scheme_runs():
    lines = ["the sky is blue", "the grass is green"]
    scheme = irm.detect_rhyme_scheme(lines)
    assert len(scheme) == 2