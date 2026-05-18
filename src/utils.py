import re

try:
    import pronouncing
except Exception:  # pragma: no cover - depends on local environment.
    pronouncing = None

try:
    from textblob import TextBlob
except Exception:  # pragma: no cover - depends on local environment.
    TextBlob = None


def phones(word: str) -> list[str]:
    """Return all CMU phone strings for *word* (lower-cased)."""
    if pronouncing is None:
        return []
    return pronouncing.phones_for_word(word.lower())


def syllable_count(word: str) -> int:
    """Count syllables via CMU dict; fall back to a vowel-run heuristic."""
    entries = phones(word)
    if entries and pronouncing is not None:
        return pronouncing.syllable_count(entries[0])
    vowels = "aeiouAEIOU"
    count = sum(1 for a, b in zip("x" + word, word) if b in vowels and a not in vowels)
    return max(1, count)


def stress_pattern(word: str) -> str:
    """Return a stress string like '10' (primary=1, unstressed=0)."""
    entries = phones(word)
    if not entries:
        return "0" * syllable_count(word)
    if pronouncing is None:
        return "0" * syllable_count(word)
    return pronouncing.stresses(entries[0])


def sentiment(text: str) -> tuple[float, float]:
    """Return (polarity, subjectivity) in [-1..1] and [0..1]."""
    if TextBlob is None:
        return 0.0, 0.0
    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity


def word_sentiment(word: str) -> tuple[float, float]:
    return sentiment(word)


def clean_words(text: str) -> list[str]:
    """Tokenise text into lowercase alphabetic words."""
    return re.findall(r"[a-zA-Z]+", text.lower())
