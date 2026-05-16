"""
poem_utils.py
─────────────
Shared low-level helpers used across the poem analysis modules.
No public API here — import from the specific modules instead.
"""

import re

import pronouncing
from textblob import TextBlob


def _phones(word: str) -> list[str]:
    """Return all CMU phone strings for *word* (lower-cased)."""
    return pronouncing.phones_for_word(word.lower())


def _syllable_count(word: str) -> int:
    """Count syllables via CMU dict; fall back to a vowel-run heuristic."""
    entries = _phones(word)
    if entries:
        return pronouncing.syllable_count(entries[0])
    vowels = "aeiouAEIOU"
    count = sum(1 for a, b in zip("x" + word, word) if b in vowels and a not in vowels)
    return max(1, count)


def _stress_pattern(word: str) -> str:
    """Return a stress string like '10' (primary=1, unstressed=0)."""
    entries = _phones(word)
    if not entries:
        return "0" * _syllable_count(word)
    return pronouncing.stresses(entries[0])


def _sentiment(text: str) -> tuple[float, float]:
    """Return (polarity, subjectivity) in [-1..1] and [0..1]."""
    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity


def _word_sentiment(word: str) -> tuple[float, float]:
    return _sentiment(word)


def _clean_words(text: str) -> list[str]:
    """Tokenise text into lowercase alphabetic words."""
    return re.findall(r"[a-zA-Z]+", text.lower())