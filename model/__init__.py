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
from typing import Sequence

DEFAULT_VOCABULARY = [
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


@dataclass
class DummyPoetryModel:
    """A tiny baseline model with the interface we can extend later."""

    vocabulary: list[str] | None = None
    seed: int = 7

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if not self.vocabulary:
            self.vocabulary = DEFAULT_VOCABULARY.copy()

    def fit(self, texts: Sequence[str] | None = None) -> "DummyPoetryModel":
        """No-op training method for compatibility with future real models."""
        _ = texts
        return self

    def predict(self, context: str, top_k: int = 1) -> str | list[str]:
        """Return one next-word guess (or top-k guesses)."""
        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        tokens = _tokenize(context or "")
        ranked = self._rank_words(tokens)

        if top_k == 1:
            return ranked[0]
        return ranked[:top_k]

    def save(self, path: str | Path) -> None:
        payload = {"vocabulary": self.vocabulary, "seed": self.seed}
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "DummyPoetryModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            vocabulary=list(payload.get("vocabulary") or DEFAULT_VOCABULARY),
            seed=int(payload.get("seed", 7)),
        )

    def _rank_words(self, tokens: list[str]) -> list[str]:
        if not tokens:
            shuffled = self.vocabulary.copy()
            self._rng.shuffle(shuffled)
            return shuffled

        target = tokens[-1]
        target_syllables = _syllable_count(target)

        return sorted(
            self.vocabulary,
            key=lambda candidate: (
                0 if self._rhymes(candidate, target) else 1,
                abs(_syllable_count(candidate) - target_syllables),
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


def predict(context: str, top_k: int = 1) -> str | list[str]:
    return _MODEL.predict(context, top_k=top_k)


def save(path: str | Path) -> None:
    _MODEL.save(path)


def load(path: str | Path) -> DummyPoetryModel:
    global _MODEL
    _MODEL = DummyPoetryModel.load(path)
    return _MODEL


__all__ = ["DummyPoetryModel", "fit", "predict", "save", "load"]
