"""Reusable poem helpers for ShirPoetRe.b.

Use this module for non-UI logic: next-word cleanup, rhyme search, rhyme checks,
and compact analysis text. The main window imports these helpers and stays small.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from typing import Iterable

try:
    import pronouncing
except Exception:  # pragma: no cover - depends on local environment.
    pronouncing = None

try:
    from src.rhythm_analysis import analyse_rhythm
except Exception:  # pragma: no cover - optional dependency path.
    analyse_rhythm = None

try:
    from src.style_analysis import rank_words_by_style
except Exception:  # pragma: no cover - optional dependency path.
    rank_words_by_style = None


WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['’-][A-Za-zА-Яа-яЁё]+)*")
VOWELS = set("aeiouyаеёиоуыэюя")

COMMON_WORDS = {
    "a", "after", "all", "an", "and", "any", "are", "around", "as", "at", "be", "because",
    "again", "before", "between", "but", "by", "does", "down", "each", "every", "for", "from",
    "had", "has", "have", "he", "her", "here", "his", "how", "i", "if", "in",
    "is", "it", "just", "like", "me", "my", "no", "nor", "not", "of", "on",
    "much", "now", "one", "or", "our", "out", "over", "shall", "she", "so", "some", "such", "that", "the",
    "their", "them", "then", "there", "these", "they", "though", "this",
    "those", "through", "thy", "till", "to", "toward", "under", "up", "upon", "was", "we",
    "well", "were", "what", "when", "where", "which", "while", "who", "whom",
    "whose", "why", "with", "will", "without", "would", "yet", "you", "your",
}

AUXILIARY_WORDS = {
    "am", "are", "be", "been", "being", "can", "could", "did", "do", "does",
    "doth", "had", "has", "hath", "have", "is", "may", "might", "must",
    "shall", "should", "was", "were", "will", "would",
}

OBJECT_PRONOUNS = {"me", "you", "him", "her", "us", "them", "thee"}
ARTICLES = {"a", "an", "the"}
PREPOSITIONS = {"at", "by", "for", "from", "in", "of", "on", "through", "to", "under", "with"}
NOUN_PHRASE_STARTERS = ARTICLES | {"my", "your", "his", "her", "our", "their", "this", "that", "these", "those"}

SUBJECT_PRONOUNS = {
    "he": ("is", "was", "has", "had", "will", "would", "can", "may", "shall"),
    "she": ("is", "was", "has", "had", "will", "would", "can", "may", "shall"),
    "it": ("is", "was", "has", "had", "will", "would", "can", "may"),
    "i": ("am", "was", "have", "had", "will", "would", "can", "may", "shall"),
    "you": ("are", "were", "have", "had", "will", "would", "can", "may"),
    "we": ("are", "were", "have", "had", "will", "would", "can", "may"),
    "they": ("are", "were", "have", "had", "will", "would", "can", "may"),
    "there": ("is", "was", "are", "were"),
}

NOUN_PHRASE_LINKERS = ("is", "was", "will", "shall", "has", "had", "would", "may")

POETIC_WORDS = [
    "light", "night", "bright", "flight", "sight", "heart", "art", "part",
    "dream", "stream", "gleam", "love", "above", "dove", "glove", "shove",
    "sky", "fly", "cry", "high", "rain", "pain", "chain", "sea", "free",
    "tree", "alone", "stone", "tone", "fire", "desire", "wind", "mind",
    "kind", "time", "rhyme", "chime", "deep", "sleep", "keep", "gold",
    "old", "hold", "grace", "place", "face", "soul", "whole", "breath",
    "death", "shore", "more", "before", "blue", "true", "through",
    "shadow", "meadow", "hollow", "silence", "violence", "reliance",
    "defiance", "science", "island",
]


@dataclass(frozen=True)
class RhymeCheck:
    word_a: str
    word_b: str
    rhymes: bool
    distance: int
    ending_a: str
    ending_b: str


@dataclass(frozen=True)
class RhymeCandidate:
    word: str
    kind: str  # "exact" or "near"
    syllables: int
    distance: int


def normalize_word(text: str) -> str:
    words = WORD_RE.findall((text or "").replace("’", "'").lower())
    return words[-1] if words else ""


def clean_words(text: str) -> list[str]:
    return [word.lower() for word in WORD_RE.findall(text or "")]


def syllable_count(word: str) -> int:
    word = normalize_word(word)
    if pronouncing is not None:
        entries = pronouncing.phones_for_word(word)
        if entries:
            return max(1, pronouncing.syllable_count(entries[0]))

    count = 0
    was_vowel = False
    for char in word:
        is_vowel = char in VOWELS
        if is_vowel and not was_vowel:
            count += 1
        was_vowel = is_vowel
    return max(1, count)


def phonetic_ending(word: str) -> tuple[str, ...]:
    word = normalize_word(word)
    if not word or pronouncing is None:
        return ()

    entries = pronouncing.phones_for_word(word)
    if not entries:
        return ()

    phones = entries[0].split()
    for index in range(len(phones) - 1, -1, -1):
        if phones[index][-1:] in {"1", "2"}:
            return tuple(phones[index:])
    return tuple(phones[-2:])


def fallback_ending(word: str) -> str:
    word = normalize_word(word)
    if not word:
        return ""
    for index in range(len(word) - 1, -1, -1):
        if word[index] in VOWELS:
            return word[index:]
    return word[-3:]


def rhyme_ending(word: str) -> str:
    phonetic = phonetic_ending(word)
    return " ".join(phonetic) if phonetic else fallback_ending(word)


def levenshtein(left: Iterable[str], right: Iterable[str]) -> int:
    a = list(left)
    b = list(right)
    rows = len(a) + 1
    cols = len(b) + 1
    dp = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        dp[i][0] = i
    for j in range(cols):
        dp[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[-1][-1]


def words_rhyme(word_a: str, word_b: str) -> bool:
    word_a = normalize_word(word_a)
    word_b = normalize_word(word_b)
    if not word_a or not word_b or word_a == word_b:
        return False

    phonetic_a = phonetic_ending(word_a)
    phonetic_b = phonetic_ending(word_b)
    if phonetic_a and phonetic_b:
        return phonetic_a == phonetic_b
    if pronouncing is not None and (phonetic_a or phonetic_b):
        return False
    return fallback_ending(word_a) == fallback_ending(word_b)


def check_rhyme(line_a: str, line_b: str) -> RhymeCheck:
    word_a = normalize_word(line_a)
    word_b = normalize_word(line_b)
    phonetic_a = phonetic_ending(word_a)
    phonetic_b = phonetic_ending(word_b)
    if phonetic_a and phonetic_b:
        distance = levenshtein(phonetic_a, phonetic_b)
    else:
        distance = levenshtein(fallback_ending(word_a), fallback_ending(word_b))

    return RhymeCheck(
        word_a=word_a,
        word_b=word_b,
        rhymes=words_rhyme(word_a, word_b),
        distance=distance,
        ending_a=rhyme_ending(word_a),
        ending_b=rhyme_ending(word_b),
    )


def replace_last_word(text: str, new_word: str) -> str:
    return re.sub(
        r"([A-Za-zА-Яа-яЁё]+(?:['’-][A-Za-zА-Яа-яЁё]+)*)([^A-Za-zА-Яа-яЁё]*)$",
        new_word + r"\2",
        text.rstrip(),
    )


def model_vocabulary(model_module) -> list[str]:
    vocabulary = getattr(getattr(model_module, "_MODEL", None), "vocabulary", [])
    return [str(word).lower() for word in vocabulary if WORD_RE.fullmatch(str(word)) and str(word).isalpha()]


def model_word_counts(model_module) -> dict[str, int]:
    counts = getattr(getattr(model_module, "_MODEL", None), "word_counts", {})
    return dict(counts)


def _corpus_path(model_module) -> Path | None:
    path = getattr(getattr(model_module, "_MODEL", None), "corpus_path", None)
    return Path(path) if path else None


@lru_cache(maxsize=4)
def _cached_ngram_model(corpus_path: str, mtime_ns: int) -> tuple[Counter[str], dict[str, Counter[str]], dict[tuple[str, str], Counter[str]]]:
    del mtime_ns  # Part of the cache key; the value itself is not needed.
    path = Path(corpus_path)
    try:
        tokens = clean_words(path.read_text(encoding="utf-8"))
    except OSError:
        return Counter(), {}, {}

    unigrams: Counter[str] = Counter(tokens)
    bigrams: defaultdict[str, Counter[str]] = defaultdict(Counter)
    trigrams: defaultdict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for first, second in zip(tokens, tokens[1:]):
        bigrams[first][second] += 1
    for first, second, third in zip(tokens, tokens[1:], tokens[2:]):
        trigrams[(first, second)][third] += 1

    return unigrams, dict(bigrams), dict(trigrams)


def _ngram_model(model_module) -> tuple[Counter[str], dict[str, Counter[str]], dict[tuple[str, str], Counter[str]]]:
    path = _corpus_path(model_module)
    if path is None or not path.exists():
        return Counter(), {}, {}
    return _cached_ngram_model(str(path), path.stat().st_mtime_ns)


def _is_useful_word(word: str) -> bool:
    return (
        bool(WORD_RE.fullmatch(word))
        and word.isalpha()
        and word not in COMMON_WORDS
        and (len(word) > 2 or word in {"be", "me", "we"})
    )


def _near_rhyme_distance(target: str, candidate: str) -> int | None:
    target_phones = phonetic_ending(target)
    candidate_phones = phonetic_ending(candidate)
    if target_phones and candidate_phones:
        distance = levenshtein(target_phones, candidate_phones)
        same_vowel = target_phones[:1] == candidate_phones[:1]
        same_tail = target_phones[-1:] == candidate_phones[-1:]
        return distance if distance <= 1 and (same_vowel or same_tail) else None

    # If only one word has a dictionary pronunciation, do not mix phonetic
    # comparison with spelling fallback. That produces noisy false matches.
    if pronouncing is not None and (target_phones or candidate_phones):
        return None

    target_end = fallback_ending(target)
    candidate_end = fallback_ending(candidate)
    if target_end and candidate_end and target_end[-2:] == candidate_end[-2:]:
        return levenshtein(target_end, candidate_end)
    return None


def find_rhyme_candidates(
    word: str,
    vocabulary: list[str],
    counts: dict[str, int] | None = None,
    limit: int = 24,
) -> list[RhymeCandidate]:
    """Return exact rhymes first, then near rhymes to avoid empty-looking results."""
    target = normalize_word(word)
    if not target:
        return []

    counts = counts or {}
    pool = list(dict.fromkeys(POETIC_WORDS + vocabulary))
    target_syllables = syllable_count(target)
    direct = {candidate.lower() for candidate in pronouncing.rhymes(target)} if pronouncing else set()

    exact: list[RhymeCandidate] = []
    near: list[RhymeCandidate] = []
    for candidate in pool:
        candidate = normalize_word(candidate)
        if candidate == target or not _is_useful_word(candidate):
            continue

        if words_rhyme(target, candidate):
            exact.append(RhymeCandidate(candidate, "exact", syllable_count(candidate), 0))
            continue

        distance = _near_rhyme_distance(target, candidate)
        if distance is not None:
            near.append(RhymeCandidate(candidate, "near", syllable_count(candidate), distance))

    def score(item: RhymeCandidate) -> tuple[int, int, int, int, str]:
        known_penalty = 0 if counts.get(item.word, 0) else 1
        source_penalty = 0 if item.word in direct else 1
        syllable_gap = abs(item.syllables - target_syllables)
        frequency_bonus = -min(counts.get(item.word, 0), 500)
        return (known_penalty, source_penalty, item.distance, syllable_gap + frequency_bonus, item.word)

    ranked = sorted(dict.fromkeys(exact), key=score)
    if len(ranked) < limit:
        ranked.extend(item for item in sorted(dict.fromkeys(near), key=score) if item.word not in {r.word for r in ranked})
    return ranked[:limit]


def find_rhymes(word: str, vocabulary: list[str], counts: dict[str, int] | None = None, limit: int = 24) -> list[str]:
    return [candidate.word for candidate in find_rhyme_candidates(word, vocabulary, counts, limit)]


def _candidate_score(context: str, candidate: str, index: int) -> tuple[int, float, int, str]:
    stopword_penalty = 1 if candidate in COMMON_WORDS else 0
    recent_penalty = 1 if candidate in clean_words(context)[-8:] else 0
    style_penalty = 0.0
    if rank_words_by_style is not None:
        try:
            style_penalty = -dict(rank_words_by_style(context, [candidate])).get(candidate, 0.0)
        except Exception:
            style_penalty = 0.0
    return (stopword_penalty + recent_penalty, style_penalty, index, candidate)


def _context_allows_common(tokens: list[str], candidate: str) -> bool:
    if candidate not in COMMON_WORDS:
        return True
    if not tokens:
        return False

    previous = tokens[-1]
    before_previous = tokens[-2] if len(tokens) >= 2 else ""

    if candidate in AUXILIARY_WORDS:
        return previous in SUBJECT_PRONOUNS or previous not in COMMON_WORDS
    if candidate in OBJECT_PRONOUNS:
        return previous not in COMMON_WORDS or previous in AUXILIARY_WORDS
    if candidate in ARTICLES:
        return previous in AUXILIARY_WORDS or previous in PREPOSITIONS
    if candidate == "not":
        return previous in AUXILIARY_WORDS
    if candidate in {"and", "or", "but"}:
        return previous not in COMMON_WORDS and before_previous not in {"and", "or", "but"}
    if candidate in PREPOSITIONS:
        return previous not in PREPOSITIONS and (previous not in COMMON_WORDS or previous in OBJECT_PRONOUNS)
    return False


def _add_scored_candidate(
    scored: dict[str, tuple[float, int]],
    tokens: list[str],
    word: str,
    points: float,
    order: int,
) -> None:
    word = normalize_word(word)
    if not word or not WORD_RE.fullmatch(word) or not word.isalpha() or len(word) <= 1:
        return
    if tokens and word == tokens[-1]:
        return
    if not _context_allows_common(tokens, word):
        return

    current_score, current_order = scored.get(word, (0.0, order))
    scored[word] = (current_score + points, min(current_order, order))


def next_word_candidates(context: str, model_module, limit: int = 12) -> list[str]:
    tokens = clean_words(context)
    if not tokens:
        return []

    scored: dict[str, tuple[float, int]] = {}
    unigrams, bigrams, trigrams = _ngram_model(model_module)
    order = 0

    previous = tokens[-1]
    if previous in SUBJECT_PRONOUNS:
        for rank, word in enumerate(SUBJECT_PRONOUNS[previous]):
            _add_scored_candidate(scored, tokens, word, 420 - rank * 12, order)
            order += 1
    elif previous not in COMMON_WORDS and len(tokens) >= 2 and tokens[-2] in NOUN_PHRASE_STARTERS:
        for rank, word in enumerate(NOUN_PHRASE_LINKERS):
            _add_scored_candidate(scored, tokens, word, 250 - rank * 10, order)
            order += 1

    if len(tokens) >= 2:
        for rank, (word, count) in enumerate(trigrams.get((tokens[-2], tokens[-1]), Counter()).most_common(30)):
            _add_scored_candidate(scored, tokens, word, 260 + min(count * 18, 180) - rank * 3, order)
            order += 1

    for rank, (word, count) in enumerate(bigrams.get(previous, Counter()).most_common(40)):
        _add_scored_candidate(scored, tokens, word, 170 + min(count * 8, 160) - rank * 2, order)
        order += 1

    recent_content = [word for word in dict.fromkeys(tokens[-12:]) if word not in COMMON_WORDS]
    try:
        result = model_module.predict(
            context,
            top_k=60,
            forbidden_words=recent_content,
            temperature=0.8,
        )
    except Exception:
        result = []

    model_words = result if isinstance(result, list) else [result]
    for rank, word in enumerate(model_words):
        normalized = normalize_word(str(word))
        grammar_bonus = 70 if normalized in AUXILIARY_WORDS and _context_allows_common(tokens, normalized) else 0
        _add_scored_candidate(scored, tokens, normalized, 120 + grammar_bonus - rank * 2, order)
        order += 1

    # Content-word pass: keeps poetic options available after grammar is handled.
    try:
        result = model_module.predict(
            context,
            top_k=40,
            forbidden_words=list(COMMON_WORDS | set(recent_content)),
            temperature=1.0,
        )
    except Exception:
        result = []

    content_words = result if isinstance(result, list) else [result]
    for rank, word in enumerate(content_words):
        _add_scored_candidate(scored, tokens, str(word), 70 - rank, order)
        order += 1

    if not scored:
        for rank, (word, count) in enumerate(unigrams.most_common(80)):
            _add_scored_candidate(scored, tokens, word, min(count, 60) - rank, order)
            order += 1

    ranked = sorted(
        scored,
        key=lambda word: (
            -scored[word][0],
            _candidate_score(context, word, scored[word][1]),
        ),
    )
    return ranked[:limit]


def analysis_report(text: str, model_module) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    report = [f"Lines: {len(lines)}", f"Words: {len(clean_words(text))}"]

    if analyse_rhythm is not None:
        try:
            rhythm = analyse_rhythm(text)
            report.extend([
                "",
                "Rhythm",
                f"Metre guess: {rhythm.overall_metre or 'unknown'}",
                f"Regularity: {rhythm.regularity_score} (1.0 is most even)",
                "Syllables by line: " + (", ".join(map(str, rhythm.syllable_counts)) or "n/a"),
            ])
        except Exception as exc:
            report.extend(["", "Rhythm", f"Could not analyse rhythm: {exc}"])
    else:
        syllables = [sum(syllable_count(word) for word in clean_words(line)) for line in lines]
        report.extend(["", "Rhythm", "Syllables by line: " + (", ".join(map(str, syllables)) or "n/a")])

    if len(lines) >= 2:
        rhyme = check_rhyme(lines[-2], lines[-1])
        report.extend([
            "",
            "Last Two Lines",
            f"Ending words: {rhyme.word_a} / {rhyme.word_b}",
            f"Rhyme: {'yes' if rhyme.rhymes else 'no'}",
            f"Sound distance: {rhyme.distance}",
        ])
        if not rhyme.rhymes:
            fixes = find_rhymes(rhyme.word_a, model_vocabulary(model_module), model_word_counts(model_module), limit=5)
            if fixes:
                report.append("Try ending the last line with:")
                report.extend(f"- {replace_last_word(lines[-1], word)}" for word in fixes)

    suggestions = next_word_candidates(text, model_module, limit=6)
    if suggestions:
        report.extend(["", "Next-word Ideas", ", ".join(suggestions)])

    return report
