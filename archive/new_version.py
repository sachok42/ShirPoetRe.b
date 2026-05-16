"""
poem_analysis.py
────────────────
A toolkit for a poetry IDE.
No neural-network / API calls — everything runs locally.

Modules
-------
1. style_fit        – score candidate words against a text's stylistic fingerprint
2. rhythm           – detect metre, stress patterns, and feet in a poem
3. rhyme_check      – decide whether two lines rhyme; suggest minimal repairs if not
4. rhyme_repair     – propose replacement words / phrases that fix rhyme while
                      preserving sentiment
"""

import re
import string
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import pronouncing
from textblob import TextBlob

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def phones(word: str) -> list[str]:
    """Return all CMU phone strings for *word* (lower-cased)."""
    return pronouncing.phones_for_word(word.lower())


def syllable_count(word: str) -> int:
    """Count syllables via CMU dict; fall back to a vowel-run heuristic."""
    entries = phones(word)
    if entries:
        return pronouncing.syllable_count(entries[0])
    vowels = "aeiouAEIOU"
    count = sum(1 for a, b in zip("x" + word, word) if b in vowels and a not in vowels)
    return max(1, count)


def stress_pattern(word: str) -> str:
    """Return a stress string like '10' (primary=1, unstressed=0)."""
    entries = phones(word)
    if not entries:
        return "0" * syllable_count(word)
    return pronouncing.stresses(entries[0])


def sentiment(text: str) -> tuple[float, float]:
    """Return (polarity, subjectivity) in [-1..1] and [0..1]."""
    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity


def word_sentiment(word: str) -> tuple[float, float]:
    return sentiment(word)


def clean_words(text: str) -> list[str]:
    """Tokenise text into lowercase alphabetic words."""
    return re.findall(r"[a-zA-Z]+", text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# 1. Style fit
# ─────────────────────────────────────────────────────────────────────────────

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


def style_score(word: str, profile: StyleProfile) -> float:
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
    scored  = [(w, style_score(w, profile)) for w in candidates]
    return sorted(scored, key=lambda x: x[1], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rhythm analysis
# ─────────────────────────────────────────────────────────────────────────────

FOOT_PATTERNS = {
    "iamb":      "01",
    "trochee":   "10",
    "dactyl":    "100",
    "anapest":   "001",
    "spondee":   "11",
    "amphibrach":"010",
    "pyrrhic":   "00",
}


def _line_stress(line: str) -> str:
    """Build the full stress string for a line of text."""
    words = clean_words(line)
    return "".join(stress_pattern(w) for w in words)


def _dominant_foot(stress: str) -> Optional[str]:
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
        stress = _line_stress(raw)
        syls   = sum(syllable_count(w) for w in clean_words(raw))
        foot   = _dominant_foot(stress)
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


# ─────────────────────────────────────────────────────────────────────────────
# 3. Rhyme check
# ─────────────────────────────────────────────────────────────────────────────

def _last_word(line: str) -> str:
    words = clean_words(line)
    return words[-1] if words else ""


def rhyme_ending(word: str) -> Optional[str]:
    """
    Extract the rhyming nucleus: vowel + everything after the last stressed vowel.
    Returns None if the word isn't in the CMU dictionary.
    """
    entries = phones(word)
    if not entries:
        return None
    phones_list = entries[0].split()
    # Find last stressed vowel
    for i in range(len(phones_list) - 1, -1, -1):
        if phones_list[i][-1] in "12":          # primary or secondary stress
            return " ".join(phones_list[i:])
    return " ".join(phones_list)


def words_rhyme(w1: str, w2: str) -> bool:
    ending1 = rhyme_ending(w1)
    ending2 = rhyme_ending(w2)
    if ending1 is None or ending2 is None:
        return False
    return ending1 == ending2


def rhyme_distance(w1: str, w2: str) -> int:
    """
    Levenshtein distance between two phone sequences.
    Used to measure how 'far' two words are from rhyming.
    """
    e1 = (rhyme_ending(w1) or "").split()
    e2 = (rhyme_ending(w2) or "").split()
    m, n = len(e1), len(e2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if e1[i-1] == e2[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[m][n]


def minimal_phone_repairs(target_ending: list[str],
                          current_ending: list[str]) -> list[list[str]]:
    """
    Return all edit paths of minimum cost that transform *current_ending*
    into *target_ending*, expressed as lists of operation strings.
    """
    m, n = len(target_ending), len(current_ending)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if target_ending[i-1] == current_ending[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)

    # Back-track all minimum-cost paths
    def backtrack(i, j) -> list[list[str]]:
        if i == 0 and j == 0:
            return [[]]
        paths = []
        if i > 0 and dp[i][j] == dp[i-1][j] + 1:
            for p in backtrack(i - 1, j):
                paths.append(p + [f"insert '{target_ending[i-1]}' at position {i}"])
        if j > 0 and dp[i][j] == dp[i][j-1] + 1:
            for p in backtrack(i, j - 1):
                paths.append(p + [f"delete '{current_ending[j-1]}' at position {j}"])
        if i > 0 and j > 0:
            cost = 0 if target_ending[i-1] == current_ending[j-1] else 1
            if dp[i][j] == dp[i-1][j-1] + cost:
                for p in backtrack(i - 1, j - 1):
                    if cost == 0:
                        paths.append(p)
                    else:
                        paths.append(p + [
                            f"replace '{current_ending[j-1]}' → '{target_ending[i-1]}' at position {j}"
                        ])
        return paths

    return backtrack(m, n)


@dataclass
class RhymeResult:
    word_a: str
    word_b: str
    rhymes: bool
    distance: int
    repair_options: list[list[str]] = field(default_factory=list)


def check_rhyme(line_a: str, line_b: str) -> RhymeResult:
    """
    Check whether the last words of *line_a* and *line_b* rhyme.

    If they don't, returns all minimal-edit repair paths (as phone-level
    operations) needed to make *line_b*'s ending match *line_a*'s ending.

    Example
    -------
    >>> r = check_rhyme("the moon shines bright", "the sun sets at night")
    >>> r.rhymes
    True

    >>> r = check_rhyme("I love the golden light", "the river runs below")
    >>> r.rhymes
    False
    >>> r.repair_options
    [["replace 'OW0' → 'AY1' ...", ...], ...]
    """
    w_a = _last_word(line_a)
    w_b = _last_word(line_b)

    rhymes   = words_rhyme(w_a, w_b)
    distance = rhyme_distance(w_a, w_b)

    repairs: list[list[str]] = []
    if not rhymes:
        end_a = (rhyme_ending(w_a) or "").split()
        end_b = (rhyme_ending(w_b) or "").split()
        if end_a and end_b:
            repairs = minimal_phone_repairs(end_a, end_b)

    return RhymeResult(
        word_a        = w_a,
        word_b        = w_b,
        rhymes        = rhymes,
        distance      = distance,
        repair_options= repairs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Rhyme repair with sentiment matching
# ─────────────────────────────────────────────────────────────────────────────

# A small built-in vocabulary drawn from common poetic words.
# In a real IDE this would be backed by a word-list file.
_POETIC_WORDS: list[str] = [
    "light", "night", "bright", "flight", "sight", "right", "might", "white",
    "dark", "spark", "bark", "mark", "heart", "start", "art", "part",
    "dream", "stream", "gleam", "beam", "seem", "team",
    "love", "dove", "above", "shove", "glove",
    "sky", "fly", "cry", "by", "high", "sigh", "lie", "die", "try", "why",
    "rain", "pain", "gain", "plain", "vain", "chain", "lane", "flame",
    "sea", "free", "tree", "be", "me", "see", "thee",
    "stone", "alone", "bone", "tone", "moan", "groan", "known",
    "fire", "desire", "higher", "lyre", "entire",
    "wind", "mind", "find", "blind", "kind", "behind",
    "time", "rhyme", "climb", "chime", "sublime",
    "deep", "sleep", "keep", "weep", "leap", "sweep",
    "cold", "bold", "gold", "old", "told", "hold", "fold",
    "grace", "place", "face", "space", "trace", "embrace",
    "soul", "whole", "role", "toll", "bowl", "stroll",
    "breath", "death", "beneath", "wreath",
    "shore", "more", "before", "door", "floor", "core", "roar",
    "rose", "close", "flows", "glows", "knows", "goes",
    "blue", "true", "through", "dew", "new", "grew",
    "silence", "violence", "reliance", "alliance",
    "sorrow", "tomorrow", "borrow",
    "gentle", "mental", "central",
    "shadow", "meadow", "follow", "hollow",
]


def rhymes_with(word: str, vocabulary: list[str]) -> list[str]:
    """Return all words in *vocabulary* that rhyme with *word*."""
    return [w for w in vocabulary if w.lower() != word.lower() and words_rhyme(word, w)]


def sentiment_distance(text: str, word: str) -> float:
    """Absolute polarity difference between a text block and a single word."""
    pol_text, _ = sentiment(text)
    pol_word, _ = word_sentiment(word)
    return abs(pol_text - pol_word)


def suggest_rhyme_repairs(
    anchor_line: str,
    broken_line: str,
    extra_vocabulary: Optional[list[str]] = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Suggest replacement *last words* for *broken_line* that:
      - rhyme with the last word of *anchor_line*
      - are as close in sentiment to *broken_line* as possible

    Returns up to *top_n* suggestions, each a dict with:
      'word'             – the suggested replacement
      'rhyme_with'       – the anchor word it rhymes with
      'sentiment_delta'  – how far its polarity is from the broken line's
      'style_score'      – how well it fits the broken line stylistically
      'example_line'     – broken_line with its last word swapped

    Example
    -------
    >>> suggest_rhyme_repairs(
    ...     "I wander under skies of blue",
    ...     "the clouds roll in and hide the sun"
    ... )
    [{'word': 'new', 'rhyme_with': 'blue', ...}, ...]
    """
    vocab = list(set(_POETIC_WORDS + (extra_vocabulary or [])))

    anchor_word = _last_word(anchor_line)
    rhyming     = rhymes_with(anchor_word, vocab)

    if not rhyming:
        return []

    scored = []
    for candidate in rhyming:
        sent_delta  = sentiment_distance(broken_line, candidate)
        style_score = style_score(candidate, build_style_profile(broken_line))
        example     = _swap_last_word(broken_line, candidate)
        scored.append({
            "word":           candidate,
            "rhyme_with":     anchor_word,
            "sentiment_delta": round(sent_delta, 4),
            "style_score":    style_score,
            "example_line":   example,
        })

    # Sort by sentiment closeness first, then style fit
    scored.sort(key=lambda x: (x["sentiment_delta"], -x["style_score"]))
    return scored[:top_n]


def _swap_last_word(line: str, new_word: str) -> str:
    """Replace the final word in *line* with *new_word*, preserving punctuation."""
    stripped = line.rstrip(string.punctuation + " ")
    trailing = line[len(stripped):]
    parts    = stripped.rsplit(None, 1)
    if len(parts) == 2:
        return parts[0] + " " + new_word + trailing
    return new_word + trailing


# ─────────────────────────────────────────────────────────────────────────────
# Quick demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("1. STYLE FIT")
    print("=" * 60)
    text = "the silent moon drifts through pale and hollow skies"
    candidates = ["gloom", "happy", "luminous", "swift", "gentle", "darkness", "bright"]
    ranked = rank_words_by_style(text, candidates)
    for word, score in ranked:
        print(f"  {word:<12} {score}")

    print()
    print("=" * 60)
    print("2. RHYTHM")
    print("=" * 60)
    poem = (
        "Shall I compare thee to a summer's day\n"
        "Thou art more lovely and more temperate\n"
        "Rough winds do shake the darling buds of May\n"
        "And summer's lease hath all too short a date"
    )
    rhythm = analyse_rhythm(poem)
    print(f"  Overall metre   : {rhythm.overall_metre}")
    print(f"  Regularity score: {rhythm.regularity_score}")
    for lr in rhythm.lines:
        print(f"  [{lr.syllables:2d} syl | {lr.dominant_foot}] {lr.stress}  '{lr.line}'")

    print()
    print("=" * 60)
    print("3. RHYME CHECK")
    print("=" * 60)
    for a, b in [
        ("the moon shines bright tonight", "the stars give off their light"),
        ("I love the golden light", "the river runs below"),
    ]:
        r = check_rhyme(a, b)
        print(f"  '{r.word_a}' / '{r.word_b}' → rhymes={r.rhymes}, distance={r.distance}")
        for opt in r.repair_options[:2]:
            print(f"    repair: {opt}")

    print()
    print("=" * 60)
    print("4. RHYME REPAIR")
    print("=" * 60)
    suggestions = suggest_rhyme_repairs(
        "I wander under skies of blue",
        "the clouds roll in and hide the sun",
    )
    for s in suggestions:
        print(f"  '{s['word']}' (Δsentiment={s['sentiment_delta']}, style={s['style_score']})")
        print(f"    → {s['example_line']}")