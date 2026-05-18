"""Reusable poem helpers for ShirPoetRe.b.

UPDATED: Pure AI Engine.
Removed all statistical n-gram fallbacks. The system now strictly uses
the neural model for suggestions and features a custom Anti-Loop bulk generator.
"""

from __future__ import annotations

import re
import random
from dataclasses import dataclass
from typing import Iterable

try:
    import pronouncing
except Exception:
    pronouncing = None

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['’-][A-Za-zА-Яа-яЁё]+)*")
VOWELS = set("aeiouyаеёиоуыэюя")

# Оставляем только базовые списки для рифм
POETIC_WORDS = [
    "light", "night", "bright", "flight", "sight", "heart", "art", "part",
    "dream", "stream", "gleam", "love", "above", "dove", "glove", "shove",
    "sky", "fly", "cry", "high", "rain", "pain", "chain", "sea", "free",
    "tree", "alone", "stone", "tone", "fire", "desire", "wind", "mind",
    "kind", "time", "rhyme", "chime", "deep", "sleep", "keep", "gold",
    "old", "hold", "grace", "place", "face", "soul", "whole", "breath",
    "death", "shore", "more", "before", "blue", "true", "through"
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
    kind: str
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
    count = sum(1 for char in word if char in VOWELS)
    return max(1, count)

def model_vocabulary(model_module) -> list[str]:
    vocabulary = getattr(getattr(model_module, "_MODEL", None), "vocabulary", [])
    return [str(word).lower() for word in vocabulary if WORD_RE.fullmatch(str(word))]

def model_word_counts(model_module) -> dict[str, int]:
    counts = getattr(getattr(model_module, "_MODEL", None), "word_counts", {})
    return dict(counts)

# --- ПУРЕ ИИ: НИКАКИХ СТАТИСТИЧЕСКИХ ЗАГЛУШЕК ---
def next_word_candidates(context: str, model_module, limit: int = 10, rhyme_with: str = None) -> list[str]:
    """Strictly relies on the neural network. Extremely creative setting."""
    recent = clean_words(context)[-15:]

    try:
        # Просим ИИ выдать максимум креатива (temp 1.5)
        # Запрещаем последние 5 слов, чтобы он не топтался на месте
        result = model_module.predict(
            context,
            top_k=40,
            forbidden_words=recent[-5:],
            temperature=1.5,
            rhyme_with=rhyme_with
        )
    except Exception:
        return []

    raw = result if isinstance(result, list) else ([result] if result else [])

    cleaned = []
    for candidate in raw:
        word = normalize_word(str(candidate))
        if word and word not in ["<pad>", "<unk>"] and word not in cleaned:
            cleaned.append(word)

    return cleaned[:limit]

# --- КАСТОМНЫЙ ANTI-LOOP ГЕНЕРАТОР ---
def smart_bulk_generate(context: str, model_module, num_words: int = 15) -> str:
    """Overwrites Yura's looping generator with an active anti-loop engine."""
    generated = []
    current_context = context

    for _ in range(num_words):
        recent_words = clean_words(current_context)[-10:]
        # ЖЕСТКИЙ БАН: запрещаем слова, которые мы только что сгенерировали, и недавние из контекста
        forbidden = list(set(recent_words[-3:] + generated[-5:]))

        try:
            preds = model_module.predict(
                current_context,
                top_k=20,
                forbidden_words=forbidden,
                temperature=1.4
            )
        except Exception:
            break

        if not preds: break

        candidates = preds if isinstance(preds, list) else [preds]
        valid = [normalize_word(str(w)) for w in candidates if w not in ["<pad>", "<unk>"]]
        valid = [w for w in valid if w]

        if not valid: break

        # Выбираем случайное слово из топ-3, чтобы сломать математические циклы
        word = random.choice(valid[:min(3, len(valid))])
        generated.append(word)
        current_context += " " + word

    return " ".join(generated)

# Остальные функции для рифм и отчетов (без изменений, так как рифмы работают хорошо)
def phonetic_ending(word: str) -> tuple[str, ...]:
    word = normalize_word(word)
    if not word or pronouncing is None: return ()
    entries = pronouncing.phones_for_word(word)
    if not entries: return ()
    phones = entries[0].split()
    for index in range(len(phones) - 1, -1, -1):
        if phones[index][-1:] in {"1", "2"}:
            return tuple(phones[index:])
    return tuple(phones[-2:])

def fallback_ending(word: str) -> str:
    word = normalize_word(word)
    if not word: return ""
    for index in range(len(word) - 1, -1, -1):
        if word[index] in VOWELS: return word[index:]
    return word[-3:]

def levenshtein(left: Iterable[str], right: Iterable[str]) -> int:
    a, b = list(left), list(right)
    rows, cols = len(a) + 1, len(b) + 1
    dp = [[0] * cols for _ in range(rows)]
    for i in range(rows): dp[i][0] = i
    for j in range(cols): dp[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[-1][-1]

def words_rhyme(word_a: str, word_b: str) -> bool:
    word_a, word_b = normalize_word(word_a), normalize_word(word_b)
    if not word_a or not word_b or word_a == word_b: return False
    phonetic_a, phonetic_b = phonetic_ending(word_a), phonetic_ending(word_b)
    if phonetic_a and phonetic_b: return phonetic_a == phonetic_b
    if pronouncing is not None and (phonetic_a or phonetic_b): return False
    return fallback_ending(word_a) == fallback_ending(word_b)

def _near_rhyme_distance(target: str, candidate: str) -> int | None:
    target_phones, candidate_phones = phonetic_ending(target), phonetic_ending(candidate)
    if target_phones and candidate_phones:
        distance = levenshtein(target_phones, candidate_phones)
        same_vowel = target_phones[:1] == candidate_phones[:1]
        same_tail = target_phones[-1:] == candidate_phones[-1:]
        return distance if distance <= 1 and (same_vowel or same_tail) else None
    if pronouncing is not None and (target_phones or candidate_phones): return None
    target_end, candidate_end = fallback_ending(target), fallback_ending(candidate)
    if target_end and candidate_end and target_end[-2:] == candidate_end[-2:]:
        return levenshtein(target_end, candidate_end)
    return None

def find_rhyme_candidates(word: str, vocabulary: list[str], counts: dict[str, int] | None = None, limit: int = 24) -> list[RhymeCandidate]:
    target = normalize_word(word)
    if not target: return []
    counts = counts or {}
    pool = list(dict.fromkeys(POETIC_WORDS + vocabulary))
    target_syllables = syllable_count(target)
    direct = {c.lower() for c in pronouncing.rhymes(target)} if pronouncing else set()

    exact, near = [], []
    for candidate in pool:
        candidate = normalize_word(candidate)
        if candidate == target or not candidate.isalpha(): continue
        if words_rhyme(target, candidate):
            exact.append(RhymeCandidate(candidate, "exact", syllable_count(candidate), 0))
            continue
        distance = _near_rhyme_distance(target, candidate)
        if distance is not None:
            near.append(RhymeCandidate(candidate, "near", syllable_count(candidate), distance))

    def score(item: RhymeCandidate) -> tuple[int, int, int, int, str]:
        return (0 if counts.get(item.word, 0) else 1, 0 if item.word in direct else 1, item.distance, abs(item.syllables - target_syllables) - min(counts.get(item.word, 0), 500), item.word)

    ranked = sorted(dict.fromkeys(exact), key=score)
    if len(ranked) < limit:
        ranked.extend(item for item in sorted(dict.fromkeys(near), key=score) if item.word not in {r.word for r in ranked})
    return ranked[:limit]

def find_rhymes(word: str, vocabulary: list[str], counts: dict[str, int] | None = None, limit: int = 24) -> list[str]:
    return [candidate.word for candidate in find_rhyme_candidates(word, vocabulary, counts, limit)]

def check_rhyme(line_a: str, line_b: str) -> RhymeCheck:
    word_a, word_b = normalize_word(line_a), normalize_word(line_b)
    phonetic_a, phonetic_b = phonetic_ending(word_a), phonetic_ending(word_b)
    distance = levenshtein(phonetic_a, phonetic_b) if phonetic_a and phonetic_b else levenshtein(fallback_ending(word_a), fallback_ending(word_b))
    return RhymeCheck(word_a, word_b, words_rhyme(word_a, word_b), distance, "", "")

def analysis_report(text: str, model_module) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    report = [f"Lines: {len(lines)}", f"Words: {len(clean_words(text))}"]
    syllables = [sum(syllable_count(w) for w in clean_words(l)) for l in lines]
    report.extend(["", "Rhythm", "Syllables by line: " + (", ".join(map(str, syllables)) or "n/a")])
    return report