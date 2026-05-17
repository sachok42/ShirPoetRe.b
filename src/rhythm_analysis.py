from utils import clean_words, stress_pattern, syllable_count
from dataclasses import dataclass
from typing import Optional
from collections import Counter

FOOT_PATTERNS = {
    "iamb":      "01",
    "trochee":   "10",
    "dactyl":    "100",
    "anapest":   "001",
    "spondee":   "11",
    "amphibrach":"010",
    "pyrrhic":   "00",
}


def line_stress(line: str) -> str:
    """Build the full stress string for a line of text."""
    words = clean_words(line)
    return "".join(stress_pattern(w) for w in words)


def dominant_foot(stress: str) -> Optional[str]:
    """Find the most frequently occurring metrical foot in *stress*."""
    if not stress:
        return None
    counts: dict[str, int] = Counter()
    for name, pattern in FOOT_PATTERNS.items():
        n = len(pattern)
        hits = sum(1 for i in range(len(stress) - n + 1) if stress[i:i+n] == pattern)
        if hits:
            counts[name] = hits
    return counts.most_common(1)[0][0] if counts else None


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


def analyse_rhythm(poem: str) -> PoemRhythm:
    """
    Analyse the rhythmic structure of *poem* (newline-separated lines).

    Returns a PoemRhythm with per-line stress patterns, dominant feet,
    an overall metre guess, and a regularity score.

    Example
    -------
    >>> r = analyse_rhythm("Shall I compare thee to a summer's day\\nThou art more lovely and more temperate")
    >>> r.overall_metre
    'iamb'
    """
    raw_lines = [l for l in poem.splitlines() if l.strip()]
    line_data: list[LineRhythm] = []

    for raw in raw_lines:
        stress = line_stress(raw)
        syls   = sum(syllable_count(w) for w in clean_words(raw))
        foot   = dominant_foot(stress)
        # rough feet count: syllables / avg foot size
        avg_foot_size = len(FOOT_PATTERNS.get(foot, "xx")) if foot else 2
        line_data.append(LineRhythm(
            line         = raw,
            stress       = stress,
            syllables    = syls,
            dominant_foot= foot,
            feet_count   = max(1, syls // avg_foot_size),
        ))

    # Overall metre = most common dominant foot across lines
    foot_votes = [l.dominant_foot for l in line_data if l.dominant_foot]
    overall = Counter(foot_votes).most_common(1)[0][0] if foot_votes else None

    # Regularity: how consistent are syllable counts across lines?
    syl_counts = [l.syllables for l in line_data]
    if len(syl_counts) > 1:
        mean = sum(syl_counts) / len(syl_counts)
        variance = sum((s - mean) ** 2 for s in syl_counts) / len(syl_counts)
        regularity = round(1 / (1 + variance ** 0.5), 4)
    else:
        regularity = 1.0

    return PoemRhythm(
        lines            = line_data,
        overall_metre    = overall,
        regularity_score = regularity,
        syllable_counts  = syl_counts,
    )

