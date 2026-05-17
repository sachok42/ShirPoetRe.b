from dataclasses import dataclass
from utils import clean_words, syllable_count, word_sentiment


@dataclass
class StyleProfile:
    avg_syllables: float
    avg_polarity: float
    avg_subjectivity: float
    avg_word_length: float
    formality_ratio: float          # long words (>6 chars) / total


def build_style_profile(text: str) -> StyleProfile:
    words = clean_words(text)
    if not words:
        return StyleProfile(0, 0, 0, 0, 0)

    syllables   = [syllable_count(w) for w in words]
    sentiments  = [word_sentiment(w) for w in words]
    polarities  = [p for p, _ in sentiments]
    subjectivities = [s for _, s in sentiments]

    return StyleProfile(
        avg_syllables    = sum(syllables) / len(syllables),
        avg_polarity     = sum(polarities) / len(polarities),
        avg_subjectivity = sum(subjectivities) / len(subjectivities),
        avg_word_length  = sum(len(w) for w in words) / len(words),
        formality_ratio  = sum(1 for w in words if len(w) > 6) / len(words),
    )


def rate_style_score(word: str, profile: StyleProfile) -> float:
    """
    Score how well *word* fits *profile*.
    Lower distance = better fit; we return a 0–1 fitness score.
    """
    pol, subj = word_sentiment(word)
    syl  = syllable_count(word)
    wlen = len(word)
    formal = 1.0 if wlen > 6 else 0.0

    distance = (
        abs(syl  - profile.avg_syllables)    * 0.30 +
        abs(pol  - profile.avg_polarity)     * 0.25 +
        abs(subj - profile.avg_subjectivity) * 0.20 +
        abs(wlen - profile.avg_word_length)  * 0.15 +
        abs(formal - profile.formality_ratio)* 0.10
    )
    return round(1 / (1 + distance), 4)


def rank_words_by_style(text: str, candidates: list[str]) -> list[tuple[str, float]]:
    """
    Score each candidate word against the stylistic fingerprint of *text*.

    Returns a list of (word, score) sorted best-first.

    Example
    -------
    >>> rank_words_by_style("the silent moon drifts through pale clouds",
    ...                     ["gloom", "happy", "luminous", "swift", "gentle"])
    [('luminous', 0.93), ('gentle', 0.89), ('gloom', 0.81), ...]
    """
    profile = build_style_profile(text)
    scored  = [(w, rate_style_score(w, profile)) for w in candidates]
    return sorted(scored, key=lambda x: x[1], reverse=True)
