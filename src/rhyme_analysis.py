from utils import clean_words, phones
from dataclasses import dataclass, field
from typing import Optional
from hypothesis import given, strategies as st

# @given(st.text())
def last_word(line: str) -> str:
    words = clean_words(line)
    return words[-1] if words else ""

# @given(st.text())
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

# @given(st.text(), st.text())
def words_rhyme(w1: str, w2: str) -> bool:
    ending1 = rhyme_ending(w1)
    ending2 = rhyme_ending(w2)
    if ending1 is None or ending2 is None:
        return False
    return ending1 == ending2

# @given(st.text(), st.text())
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

# @given(st.lists(st.text()), st.lists(st.text()))
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

# @given(st.text(), st.text())
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
    w_a = last_word(line_a)
    w_b = last_word(line_b)

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

