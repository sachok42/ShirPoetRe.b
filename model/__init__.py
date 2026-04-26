"""Minimal poetry next-word model interface.

Usage:
    import model
    word = model.predict("The moon is shining over")
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
import re
from typing import Iterable, Sequence

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_VOCAB_PATH = MODEL_DIR / "vocabulary.json"
FALLBACK_VOCABULARY = [
    "night",
    "light",
    "heart",
    "dream",
    "sky",
    "fire",
    "rain",
    "song",
    "echo",
    "time",
]

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё'-]+")
VOWELS = set("aeiouyаеёиоуыэюя")


def _tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def _syllable_count(word: str) -> int:
    count = sum(1 for char in word.lower() if char in VOWELS)
    return max(1, count)


def _resolve_vocab_path(path: str | Path | None) -> Path:
    if path is None:
        return DEFAULT_VOCAB_PATH
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return MODEL_DIR / candidate


def _extract_tokens(payload: object) -> list[str]:
    if isinstance(payload, list):
        return [str(item) for item in payload]

    if isinstance(payload, dict):
        for key in ("tokens", "vocabulary", "id_to_token", "itos"):
            value = payload.get(key)
            if isinstance(value, list):
                return [str(item) for item in value]

    return []


def _clean_tokens(tokens: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []

    for raw_token in tokens:
        token = raw_token.strip().lower()
        if not token:
            continue

        # Skip service tokens that are common in train-time vocabularies.
        if token.startswith("<") and token.endswith(">"):
            continue

        if token in seen:
            continue

        seen.add(token)
        cleaned.append(token)

    return cleaned


def _load_external_vocabulary(path: str | Path | None = None) -> list[str]:
    vocab_path = _resolve_vocab_path(path)

    try:
        payload = json.loads(vocab_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return FALLBACK_VOCABULARY.copy()

    tokens = _clean_tokens(_extract_tokens(payload))
    if not tokens:
        return FALLBACK_VOCABULARY.copy()

    return tokens


@dataclass
class DummyPoetryModel:
    """A tiny baseline model with the interface we can extend later."""

    vocabulary: list[str] | None = None
    seed: int = 7
    vocabulary_path: str | Path | None = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if self.vocabulary:
            cleaned = _clean_tokens(self.vocabulary)
            self.vocabulary = cleaned or FALLBACK_VOCABULARY.copy()
            return

        self.vocabulary = _load_external_vocabulary(self.vocabulary_path)

    def fit(self, texts: Sequence[str] | None = None) -> "DummyPoetryModel":
        """No-op training method for compatibility with future real models."""
        _ = texts
        return self

    def predict(
        self,
        context: str,
        top_k: int = 1,
        rhyme_with: str | None = None,
        target_syllables: int | None = None,
        forbidden_words: Sequence[str] | None = None,
    ) -> str | list[str]:
        """Return one next-word guess (or top-k guesses)."""
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if target_syllables is not None and target_syllables < 1:
            raise ValueError("target_syllables must be >= 1")

        tokens = _tokenize(context or "")
        ranked = self._rank_words(
            tokens=tokens,
            rhyme_with=rhyme_with,
            target_syllables=target_syllables,
            forbidden_words=forbidden_words,
        )

        if top_k == 1:
            return ranked[0]
        return ranked[:top_k]

    def save(self, path: str | Path) -> None:
        resolved_vocab_path = _resolve_vocab_path(self.vocabulary_path)
        payload = {
            "seed": self.seed,
            "vocabulary_path": str(resolved_vocab_path),
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "DummyPoetryModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        raw_vocabulary = payload.get("vocabulary")
        vocabulary = list(raw_vocabulary) if isinstance(raw_vocabulary, list) else None
        return cls(
            vocabulary=vocabulary,
            seed=int(payload.get("seed", 7)),
            vocabulary_path=payload.get("vocabulary_path"),
        )

    def _rank_words(
        self,
        tokens: list[str],
        rhyme_with: str | None = None,
        target_syllables: int | None = None,
        forbidden_words: Sequence[str] | None = None,
    ) -> list[str]:
        forbidden = {word.lower() for word in (forbidden_words or [])}
        candidates = [word for word in self.vocabulary if word.lower() not in forbidden]
        if not candidates:
            candidates = self.vocabulary.copy()

        if not tokens and rhyme_with is None and target_syllables is None and not forbidden:
            self._rng.shuffle(candidates)
            return candidates

        reference = tokens[-1] if tokens else ""
        rhythm_target = target_syllables if target_syllables is not None else (
            _syllable_count(reference) if reference else None
        )
        rhyme_reference = (rhyme_with or reference or "").lower()

        return sorted(
            candidates,
            key=lambda candidate: (
                0 if not rhyme_reference or self._rhymes(candidate, rhyme_reference) else 1,
                0 if rhythm_target is None else abs(_syllable_count(candidate) - rhythm_target),
                self._stable_score(candidate),
            ),
        )

    @staticmethod
    def _rhymes(word_a: str, word_b: str) -> bool:
        return len(word_a) >= 2 and len(word_b) >= 2 and word_a[-2:] == word_b[-2:]

    @staticmethod
    def _stable_score(word: str) -> int:
        return sum(ord(char) for char in word)


_MODEL = DummyPoetryModel()


def fit(texts: Sequence[str] | None = None) -> DummyPoetryModel:
    return _MODEL.fit(texts)


def predict(
    context: str,
    top_k: int = 1,
    rhyme_with: str | None = None,
    target_syllables: int | None = None,
    forbidden_words: Sequence[str] | None = None,
) -> str | list[str]:
    return _MODEL.predict(
        context=context,
        top_k=top_k,
        rhyme_with=rhyme_with,
        target_syllables=target_syllables,
        forbidden_words=forbidden_words,
    )


def reload_vocabulary(path: str | Path | None = None) -> list[str]:
    _MODEL.vocabulary_path = path
    _MODEL.vocabulary = _load_external_vocabulary(path)
    return _MODEL.vocabulary.copy()


def save(path: str | Path) -> None:
    _MODEL.save(path)


def load(path: str | Path) -> DummyPoetryModel:
    global _MODEL
    _MODEL = DummyPoetryModel.load(path)
    return _MODEL


__all__ = ["DummyPoetryModel", "fit", "predict", "save", "load", "reload_vocabulary"]
