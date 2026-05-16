"""
rhyme_check.py
──────────────
Decide whether two lines rhyme; suggest minimal phonetic repairs if not.

Public API
----------
check_rhyme(line_a, line_b) -> RhymeResult
"""

from dataclasses import dataclass, field
from typing import Optional

from poem_utils import _phones, _clean_words


@dataclass
class RhymeResult:
    word_a: str
    word_b: str
    rhymes: bool
    distance: int
    repair_options: list[list[str]] = field(default_factory=list)


def _last_word(line: str) -> str:
    words = _clean_words(line)
    return words[-1] if words else ""


def _rhyme_ending(word: str) -> Optional[str]:
    """
    Extract the rhyming nucleus: everything from the last stressed vowel onward.
    Returns None when the word isn't in the CMU dictionary.
    """
    entries = _phones(word)
    if not entries:
        return None
    phones = entries[0].split()
    for i in range(len(phones) - 1, -1, -1):
        if phones[i][-1] in "12":           # primary or secondary stress
            return " ".join(phones[i:])
    return " ".join(phones)


def _words_rhyme(w1: str, w2: str) -> bool:
    e1, e2 = _rhyme_ending(w1), _rhyme_ending(w2)
    return e1 is not None and e2 is not None and e1 == e2


def _edit_distance(seq_a: list[str], seq_b: list[str]) -> int:
    """Standard Levenshtein distance between two phone sequences."""
    m, n = len(seq_a), len(seq_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost    = 0 if seq_a[i-1] == seq_b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[m][n]


def _all_minimal_repairs(target: list[str], current: list[str]) -> list[list[str]]:
    """
    Return every edit path of minimum cost that transforms *current* into *target*.
    Each path is a list of human-readable operation strings.
    """
    m, n = len(target), len(current)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): dp[i][0] = i
    for j in range(n + 1): dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost    = 0 if target[i-1] == current[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)

    def backtrack(i: int, j: int) -> list[list[str]]:
        if i == 0 and j == 0:
            return [[]]
        paths = []
        if i > 0 and dp[i][j] == dp[i-1][j] + 1:
            for p in backtrack(i - 1, j):
                paths.append(p + [f"insert '{target[i-1]}' at position {i}"])
        if j > 0 and dp[i][j] == dp[i][j-1] + 1:
            for p in backtrack(i, j - 1):
                paths.append(p + [f"delete '{current[j-1]}' at position {j}"])
        if i > 0 and j > 0:
            cost = 0 if target[i-1] == current[j-1] else 1
            if dp[i][j] == dp[i-1][j-1] + cost:
                for p in backtrack(i - 1, j - 1):
                    if cost == 0:
                        paths.append(p)
                    else:
                        paths.append(p + [
                            f"replace '{current[j-1]}' → '{target[i-1]}' at position {j}"
                        ])
        return paths

    return backtrack(m, n)


def check_rhyme(line_a: str, line_b: str) -> RhymeResult:
    """
    Check whether the last words of *line_a* and *line_b* rhyme.

    If they don't, returns all minimal-edit repair paths as phone-level
    operation lists needed to make *line_b*'s ending match *line_a*'s.

    Example
    -------
    >>> r = check_rhyme("the moon shines bright tonight", "the stars give off their light")
    >>> r.rhymes
    True

    >>> r = check_rhyme("I love the golden light", "the river runs below")
    >>> r.rhymes
    False
    >>> r.repair_options
    [["replace 'OW1' → 'AY1' at position 1", "insert 'T' at position 2"], ...]
    """
    w_a = _last_word(line_a)
    w_b = _last_word(line_b)

    rhymes   = _words_rhyme(w_a, w_b)
    end_a    = (_rhyme_ending(w_a) or "").split()
    end_b    = (_rhyme_ending(w_b) or "").split()
    distance = _edit_distance(end_a, end_b)

    repairs: list[list[str]] = []
    if not rhymes and end_a and end_b:
        repairs = _all_minimal_repairs(end_a, end_b)

    return RhymeResult(
        word_a         = w_a,
        word_b         = w_b,
        rhymes         = rhymes,
        distance       = distance,
        repair_options = repairs,
    )