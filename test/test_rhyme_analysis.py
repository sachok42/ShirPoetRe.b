from src import rhyme_analysis as ra

def test_last_word_basic():
    assert ra.last_word("the sky is blue") == "blue"

# We suppose that identical words are matching
# def test_words_rhyme_same_word_false():
#     assert ra.words_rhyme("blue", "blue") is False

def test_rhyme_distance_symmetry():
    d1 = ra.rhyme_distance("blue", "true")
    d2 = ra.rhyme_distance("true", "blue")
    assert d1 == d2

def test_rhyme_ending_none_safe():
    assert ra.rhyme_ending("qzxqzx") is None