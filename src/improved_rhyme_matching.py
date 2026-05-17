import pronouncing
from style_analysis import build_style_profile, rate_style_score
from rhyme_analysis import last_word
from utils import sentiment, word_sentiment
import string


def phones_for(word: str) -> list[str]:
    """Return the first CMU phone list for *word*, or []."""
    entries = pronouncing.phones_for_word(word.lower())
    return entries[0].split() if entries else []


def rhyme_nucleus(phones: list[str]) -> str:
    """
    Extract the rhyming nucleus: last stressed-or-final vowel + everything after.
    Stress digits are stripped so AY1 == AY2 == AY.
    Returns "" if no vowel found.
    """
    # walk backwards to find last vowel (has digit suffix in CMU)
    for i in range(len(phones) - 1, -1, -1):
        p = phones[i]
        if p[-1].isdigit():                          # it's a vowel phoneme
            nucleus = [p[:-1]] + phones[i + 1:]      # strip digit, keep rest
            return " ".join(nucleus)
    return ""


def near_rhyme_nucleus(phones: list[str]) -> str:
    """
    Looser match: just the vowel itself (no trailing consonants).
    Catches slant-rhymes like "love / above / shove".
    """
    for i in range(len(phones) - 1, -1, -1):
        if phones[i][-1].isdigit():
            return phones[i][:-1]           # bare vowel name, no stress, no coda
    return ""


def soft_rhyme(w1: str, w2: str) -> bool:
    """
    True when w1 and w2 rhyme by the normalised nucleus (stress-insensitive),
    OR share the same bare vowel nucleus as a near-rhyme fallback.
    """
    if w1.lower() == w2.lower():
        return False
    p1, p2 = phones_for(w1), phones_for(w2)
    if not p1 or not p2:
        return False
    n1, n2 = rhyme_nucleus(p1), rhyme_nucleus(p2)
    if n1 and n2 and n1 == n2:
        return True
    # near-rhyme: same vowel nucleus regardless of coda
    v1, v2 = near_rhyme_nucleus(p1), near_rhyme_nucleus(p2)
    return bool(v1 and v2 and v1 == v2)


# ═══════════════════════════════════════════════════════════════════════════════
#  RHYME SCHEME DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_rhyme_scheme(lines: list[str]) -> list[str]:
    """
    Assign a rhyme-scheme letter to each line using soft_rhyme().
    Lines whose last word has no CMU entry get '?'.
    """
    endings = [last_word(l) for l in lines]
    letters: list[str] = ["?"] * len(lines)
    next_letter = ord("A")

    for i, word in enumerate(endings):
        if letters[i] != "?":
            continue
        if not word or not phones_for(word):
            continue
        letters[i] = chr(next_letter)
        for j in range(i + 1, len(endings)):
            if letters[j] == "?" and soft_rhyme(word, endings[j]):
                letters[j] = chr(next_letter)
        next_letter += 1

    return letters


# ═══════════════════════════════════════════════════════════════════════════════
#  RHYME REPAIR  — uses full CMU dictionary via pronouncing.rhymes_for_word()
#  instead of the tiny _POETIC_WORDS list, so it always finds candidates.
# ═══════════════════════════════════════════════════════════════════════════════



def swap_last_word(line: str, new_word: str) -> str:
    stripped = line.rstrip(string.punctuation + " ")
    trailing = line[len(stripped):]
    parts    = stripped.rsplit(None, 1)
    return (parts[0] + " " + new_word + trailing) if len(parts) == 2 \
        else (new_word + trailing)


def suggest_rhyme_repairs(
    anchor_line: str,
    broken_line: str,
    top_n: int = 6,
) -> list[dict]:
    """
    Find replacement last-words for *broken_line* that rhyme with *anchor_line*.

    Strategy:
      1. Use pronouncing.rhymes_for_word() — returns every CMU word that
         shares the exact phoneme ending with the anchor word.  This gives
         hundreds of candidates without any curated vocabulary.
      2. If that returns < 3 hits, fall back to soft_rhyme() over a broad
         common-English word list so near-rhymes are included.
      3. Rank survivors by (sentiment_delta ASC, style_score DESC).
    """

    anchor_word = last_word(anchor_line)
    if not anchor_word:
        return []

    # ── Step 1: exact CMU rhymes (pronouncing library does the heavy lifting) ──
    candidates: list[str] = pronouncing.rhymes(anchor_word.lower())

    # ── Step 2: soft-rhyme fallback when CMU exact list is thin ───────────────
    if len(candidates) < 3:
        # Search across every word the CMU dict knows
        all_words = set()
        for entry in pronouncing.phones_for_word.__module__ and []:
            pass
        # Faster: iterate pronouncing's internal dict
        try:
            cmu_words = list(pronouncing._cmu_entries().keys())
        except Exception:
            cmu_words = []
        candidates = [w for w in cmu_words
                      if w != anchor_word.lower() and soft_rhyme(anchor_word, w)]

    if not candidates:
        return []

    # ── Step 3: score each candidate ──────────────────────────────────────────
    profile = build_style_profile(broken_line)
    pol_broken, _ = sentiment(broken_line)
    scored = []
    for word in candidates:
        try:
            pol_word, _ = word_sentiment(word)
            sent_delta  = abs(pol_broken - pol_word)
            style_score = rate_style_score(word, profile)
            scored.append({
                "word":            word,
                "rhyme_with":      anchor_word,
                "sentiment_delta": round(sent_delta, 4),
                "style_score":     style_score,
                "example_line":    swap_last_word(broken_line, word),
            })
        except Exception:
            continue

    scored.sort(key=lambda x: (x["sentiment_delta"], -x["style_score"]))
    return scored[:top_n]
