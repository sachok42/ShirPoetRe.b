from __future__ import annotations
from rhythm_analysis import analyse_rhythm
import re
from dataclasses import dataclass, field

from utils import syllable_count, clean_words, stress_pattern
from style_analysis import build_style_profile, rate_style_score

# ── nltk lazy imports ─────────────────────────────────────────────────────────
try:
    from nltk.corpus import wordnet as _wn
    _wn.synsets("test")          # trigger corpus load; raises if not downloaded
except LookupError:
    import nltk as _nltk
    _nltk.download("wordnet", quiet=True)
    _nltk.download("omw-1.4",  quiet=True)
    from nltk.corpus import wordnet as _wn


# ── helpers ───────────────────────────────────────────────────────────────────

def synonyms(word: str) -> list[str]:
    """
    Return a deduplicated list of single-token synonyms for *word* via WordNet.
    Multi-word lemmas (containing '_') are skipped.
    """
    seen: set[str] = set()
    result: list[str] = []
    for syn in _wn.synsets(word.lower()):
        for lemma in syn.lemmas():
            name = lemma.name().lower()
            if "_" not in name and name != word.lower() and name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _line_syllables(line: str) -> int:
    return sum(syllable_count(w) for w in clean_words(line))


def _swap_word(line: str, original: str, replacement: str) -> str:
    """Case-insensitive whole-word replacement (first occurrence)."""
    pattern = re.compile(r'\b' + re.escape(original) + r'\b', re.IGNORECASE)
    return pattern.sub(replacement, line, count=1)


# ── public API ────────────────────────────────────────────────────────────────

@dataclass
class RhythmRepairSuggestion:
    original_word:   str
    replacement:     str
    example_line:    str
    syllable_delta:  int     # how much closer to target (positive = improvement)
    style_score:     float
    synonyms_tried:  int


def suggest_rhythm_repairs(
    line: str,
    target_syllables: int,
    top_n: int = 6,
) -> list[RhythmRepairSuggestion]:
    """
    Suggest single-word synonym swaps that move *line*'s syllable count
    toward *target_syllables*.

    Strategy
    --------
    1. For each content word in the line, look up WordNet synonyms.
    2. Keep synonyms whose syllable count is in the right direction
       (fewer syllables if the line is too long, more if too short).
    3. Rank survivors by (syllable improvement DESC, style fit DESC).

    Parameters
    ----------
    line              : the poetry line to repair
    target_syllables  : desired syllable count (e.g. 10 for iambic pentameter)
    top_n             : maximum suggestions to return

    Returns
    -------
    List of RhythmRepairSuggestion, best first.

    Example
    -------
    >>> suggestions = suggest_rhythm_repairs(
    ...     "the luminous and glimmering moon drifts silently above",
    ...     target_syllables=10,
    ... )
    >>> suggestions[0].example_line
    'the bright and glimmering moon drifts silently above'
    """
    current_syls = _line_syllables(line)
    delta_needed = target_syllables - current_syls   # negative → line too long

    if delta_needed == 0:
        return []   # line already fits

    words = clean_words(line)
    profile = build_style_profile(line)
    results: list[RhythmRepairSuggestion] = []

    for word in words:
        orig_syls  = syllable_count(word)
        synonyms_list   = synonyms(word)
        tried      = len(synonyms_list)

        for syn in synonyms_list:
            syn_syls   = syllable_count(syn)
            word_delta = syn_syls - orig_syls   # how this swap changes line length

            # Only keep swaps that move in the right direction
            if delta_needed > 0 and word_delta <= 0:
                continue
            if delta_needed < 0 and word_delta >= 0:
                continue

            # How much does the gap close?
            improvement = min(abs(word_delta), abs(delta_needed))

            example = _swap_word(line, word, syn)
            results.append(RhythmRepairSuggestion(
                original_word  = word,
                replacement    = syn,
                example_line   = example,
                syllable_delta = improvement,
                style_score    = rate_style_score(syn, profile),
                synonyms_tried = tried,
            ))

    # Best first: biggest syllable improvement, then style
    results.sort(key=lambda r: (-r.syllable_delta, -r.style_score))

    # Deduplicate on example_line (same swap may appear from multiple synsets)
    seen: set[str] = set()
    unique: list[RhythmRepairSuggestion] = []
    for r in results:
        if r.example_line not in seen:
            seen.add(r.example_line)
            unique.append(r)
        if len(unique) >= top_n:
            break

    return unique


def infer_target_syllables(poem_text: str) -> int | None:
    """
    Guess the target syllable count per line from the poem's median line length.
    Returns None if the poem has fewer than 2 non-empty lines.
    """
    result = analyse_rhythm(poem_text)
    counts = sorted(result.syllable_counts)
    if len(counts) < 2:
        return None
    # median
    mid = len(counts) // 2
    return counts[mid] if len(counts) % 2 else (counts[mid - 1] + counts[mid]) // 2
