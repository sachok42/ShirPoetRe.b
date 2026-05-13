"""Transformer-based poetry next-word model interface.

Usage:
    import model
    word = model.predict("The moon is shining over")
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
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
    return WORD_RE.findall((text or "").lower())


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

        if not TORCH_AVAILABLE or self._model is None:
            ranked = self._fallback_rank(tokens, rhyme_with, target_syllables, forbidden_words)
            return ranked[0] if top_k == 1 else ranked[:top_k]

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

        if TORCH_AVAILABLE and "model_state_dict" in checkpoint:
            model._model.load_state_dict(checkpoint["model_state_dict"])
            model._model.eval()
            model._weights_loaded = True

        return model

    def reload_vocabulary(self, path: str | Path | None = None) -> list[str]:
        self.vocabulary_path = _resolve_vocab_path(path)
        self.vocabulary, self.pad_token, self.unk_token = _load_vocabulary_file(
            self.vocabulary_path
        )
        self._rebuild_mappings()

        if TORCH_AVAILABLE:
            self._initialize_network()
            self._load_weights_if_available(self.weights_path)

        return self.vocabulary.copy()

    def is_fitted(self) -> bool:
        return bool(self._weights_loaded)

    @staticmethod
    def _rhymes(word_a: str, word_b: str) -> bool:
        return len(word_a) >= 2 and len(word_b) >= 2 and word_a[-2:] == word_b[-2:]

    @staticmethod
    def _stable_score(word: str) -> int:
        return sum(ord(char) for char in word)


_MODEL = TransformerPoetryModel()


def fit(
    texts: Sequence[str] | None = None,
    epochs: int = 2,
    batch_size: int = 128,
    learning_rate: float = 3e-3,
) -> TransformerPoetryModel:
    return _MODEL.fit(
        texts=texts,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
    )


def predict(
    context: str,
    top_k: int = 1,
    rhyme_with: str | None = None,
    target_syllables: int | None = None,
    forbidden_words: Sequence[str] | None = None,
    temperature: float = 1.0,
) -> str | list[str]:
    return _MODEL.predict(
        context=context,
        top_k=top_k,
        rhyme_with=rhyme_with,
        target_syllables=target_syllables,
        forbidden_words=forbidden_words,
        temperature=temperature,
    )


def reload_vocabulary(path: str | Path | None = None) -> list[str]:
    return _MODEL.reload_vocabulary(path)


def is_fitted() -> bool:
    return _MODEL.is_fitted()


def save(path: str | Path) -> None:
    _MODEL.save(path)


def load(path: str | Path) -> TransformerPoetryModel:
    global _MODEL
    _MODEL = TransformerPoetryModel.load(path)
    return _MODEL


__all__ = [
    "TransformerNextWordModel",
    "TransformerPoetryModel",
    "fit",
    "predict",
    "save",
    "load",
    "reload_vocabulary",
    "is_fitted",
    "TORCH_AVAILABLE",
]
