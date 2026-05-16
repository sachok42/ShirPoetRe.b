"""
rhythm.py
─────────
Detect metre, stress patterns, and metrical feet in a poem.

Public API
----------
analyse_rhythm(poem) -> PoemRhythm
"""

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from poem_utils import _clean_words, _syllable_count, _stress_pattern


FOOT_PATTERNS: dict[str, str] = {
    "iamb":       "01",
    "trochee":    "10",
    "dactyl":     "100",
    "anapest":    "001",
    "spondee":    "11",
    "amphibrach": "010",
    "pyrrhic":    "00",
}


@dataclass
class LineRhythm:
    line: str
    stress: str
    syllables: int
    dominant_foot: Optional[str]
    feet_count: int


@dataclass
class PoemRhythm:
    lines: list[LineRhythm]
    overall_metre: Optional[str]
    regularity_score: float         # 0 = chaotic, 1 = perfectly regular
    syllable_counts: list[int]


def _line_stress(line: str) -> str:
    """Build the full stress string for a single line."""
    return "".join(_stress_pattern(w) for w in _clean_words(line))


def _dominant_foot(stress: str) -> Optional[str]:
    """Find the most frequently occurring metrical foot in *stress*."""
    if not stress:
        return None
    counts: dict[str, int] = Counter()
    for name, pattern in FOOT_PATTERNS.items():
        n    = len(pattern)
        hits = sum(1 for i in range(len(stress) - n + 1) if stress[i:i+n] == pattern)
        if hits:
            counts[name] = hits
    return counts.most_common(1)[0][0] if counts else None


def _regularity_score(syllable_counts: list[int]) -> float:
    """Return 1 for perfectly even lines, approaching 0 as variance grows."""
    if len(syllable_counts) < 2:
        return 1.0
    mean     = sum(syllable_counts) / len(syllable_counts)
    variance = sum((s - mean) ** 2 for s in syllable_counts) / len(syllable_counts)
    return round(1 / (1 + variance ** 0.5), 4)


def _analyse_line(raw: str) -> LineRhythm:
    stress    = _line_stress(raw)
    syls      = sum(_syllable_count(w) for w in _clean_words(raw))
    foot      = _dominant_foot(stress)
    foot_size = len(FOOT_PATTERNS.get(foot, "xx")) if foot else 2
    return LineRhythm(
        line          = raw,
        stress        = stress,
        syllables     = syls,
        dominant_foot = foot,
        feet_count    = max(1, syls // foot_size),
    )


def analyse_rhythm(poem: str) -> PoemRhythm:
    """
    Analyse the rhythmic structure of *poem* (newline-separated lines).

    Returns a PoemRhythm with per-line stress patterns, dominant feet,
    an overall metre guess, and a regularity score.

    Example
    -------
    >>> r = analyse_rhythm("Shall I compare thee to a summer's day\\n"
    ...                    "Thou art more lovely and more temperate")
    >>> r.overall_metre
    'iamb'
    """
    raw_lines  = [l for l in poem.splitlines() if l.strip()]
    lines      = [_analyse_line(raw) for raw in raw_lines]

    foot_votes = [l.dominant_foot for l in lines if l.dominant_foot]
    overall    = Counter(foot_votes).most_common(1)[0][0] if foot_votes else None

    syl_counts = [l.syllables for l in lines]

    return PoemRhythm(
        lines            = lines,
        overall_metre    = overall,
        regularity_score = _regularity_score(syl_counts),
        syllable_counts  = syl_counts,
    )