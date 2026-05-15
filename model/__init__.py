"""Keras Bi-LSTM poetry next-word model interface.

The model uses three artifacts created by the training notebook:
    model/weights/reema_bi_lstm_poem_generator.keras
    model/weights/tokenizer.json
    model/weights/training_config.json

Usage:
    import model
    word = model.predict("the moon")
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Sequence

try:
    import numpy as np
    from tensorflow.keras.models import load_model as keras_load_model
    from tensorflow.keras.preprocessing.sequence import pad_sequences
    from tensorflow.keras.preprocessing.text import tokenizer_from_json

    KERAS_AVAILABLE = True
except Exception:
    np = None
    keras_load_model = None
    pad_sequences = None
    tokenizer_from_json = None
    KERAS_AVAILABLE = False


MODEL_DIR = Path(__file__).resolve().parent
WEIGHTS_DIR = MODEL_DIR / "weights"

DEFAULT_MODEL_PATH = WEIGHTS_DIR / "reema_bi_lstm_poem_generator.keras"
DEFAULT_TOKENIZER_PATH = WEIGHTS_DIR / "tokenizer.json"
DEFAULT_CONFIG_PATH = WEIGHTS_DIR / "training_config.json"

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё'-]+")
VOWELS = set("aeiouyаеёиоуыэюя")


def _resolve_path(path: str | Path | None, default: Path) -> Path:
    if path is None:
        return default
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return MODEL_DIR / candidate


def _tokenize(text: str) -> list[str]:
    return WORD_RE.findall((text or "").lower())


def _syllable_count(word: str) -> int:
    count = sum(1 for char in word.lower() if char in VOWELS)
    return max(1, count)


def _rhymes(word_a: str, word_b: str) -> bool:
    return len(word_a) >= 2 and len(word_b) >= 2 and word_a[-2:] == word_b[-2:]


class KerasBiLSTMPoetryModel:
    """Thin inference wrapper around the trained Keras Bi-LSTM artifacts."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        tokenizer_path: str | Path | None = None,
        config_path: str | Path | None = None,
        lazy: bool = True,
    ) -> None:
        self.model_path = _resolve_path(model_path, DEFAULT_MODEL_PATH)
        self.tokenizer_path = _resolve_path(tokenizer_path, DEFAULT_TOKENIZER_PATH)
        self.config_path = _resolve_path(config_path, DEFAULT_CONFIG_PATH)

        self._model = None
        self._tokenizer = None
        self._config: dict[str, object] | None = None

        if not lazy:
            self.load_artifacts()

    def load_artifacts(self) -> "KerasBiLSTMPoetryModel":
        if not KERAS_AVAILABLE:
            raise RuntimeError(
                "TensorFlow/Keras is required to use the trained poetry model. "
                "Install TensorFlow or run this in Google Colab."
            )

        missing = [
            str(path)
            for path in (self.model_path, self.tokenizer_path, self.config_path)
            if not path.exists()
        ]
        if missing:
            raise FileNotFoundError("Missing model artifact(s): " + ", ".join(missing))

        self._model = keras_load_model(self.model_path)
        self._tokenizer = tokenizer_from_json(self.tokenizer_path.read_text(encoding="utf-8"))
        self._config = json.loads(self.config_path.read_text(encoding="utf-8"))
        return self

    @property
    def sequence_len(self) -> int:
        if self._config is None:
            self._config = json.loads(self.config_path.read_text(encoding="utf-8"))

        raw_value = self._config.get("sequence_len")
        if raw_value is None:
            raw_value = int(self._config.get("max_sequence_len", 16)) - 1
        return int(raw_value)

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self.load_artifacts()
        return self._tokenizer

    @property
    def keras_model(self):
        if self._model is None:
            self.load_artifacts()
        return self._model

    def predict(
        self,
        context: str,
        top_k: int = 1,
        rhyme_with: str | None = None,
        target_syllables: int | None = None,
        forbidden_words: Sequence[str] | None = None,
    ) -> str | list[str]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if target_syllables is not None and target_syllables < 1:
            raise ValueError("target_syllables must be >= 1")

        encoded = self.tokenizer.texts_to_sequences([context or ""])[0]
        padded = pad_sequences(
            [encoded],
            maxlen=self.sequence_len,
            truncating="pre",
            padding="pre",
        )
        probabilities = self.keras_model.predict(padded, verbose=0)[0]
        ranked_words = self._rank_predictions(
            probabilities=probabilities,
            top_k=top_k,
            rhyme_with=rhyme_with,
            target_syllables=target_syllables,
            forbidden_words=forbidden_words,
        )

        if top_k == 1:
            return ranked_words[0]
        return ranked_words

    def generate(self, context: str, num_words: int = 25) -> str:
        if num_words < 1:
            return context

        generated = context or ""
        for _ in range(num_words):
            next_word = self.predict(generated)
            generated = f"{generated} {next_word}".strip()
        return generated

    def save(self, path: str | Path) -> None:
        payload = {
            "model_path": str(self.model_path),
            "tokenizer_path": str(self.tokenizer_path),
            "config_path": str(self.config_path),
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "KerasBiLSTMPoetryModel":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            model_path=payload.get("model_path"),
            tokenizer_path=payload.get("tokenizer_path"),
            config_path=payload.get("config_path"),
            lazy=False,
        )

    def is_fitted(self) -> bool:
        return self.model_path.exists() and self.tokenizer_path.exists() and self.config_path.exists()

    def _rank_predictions(
        self,
        probabilities,
        top_k: int,
        rhyme_with: str | None,
        target_syllables: int | None,
        forbidden_words: Sequence[str] | None,
    ) -> list[str]:
        forbidden = {word.lower() for word in (forbidden_words or [])}
        index_word = self.tokenizer.index_word
        rhyme_reference = (rhyme_with or "").lower()

        candidate_ids = np.argsort(probabilities)[::-1]
        scored: list[tuple[str, float]] = []

        for idx in candidate_ids:
            word = index_word.get(int(idx))
            if not word:
                continue

            word = str(word).lower()
            if word in forbidden:
                continue

            score = float(probabilities[int(idx)])
            if rhyme_reference and _rhymes(word, rhyme_reference):
                score += 0.05
            if target_syllables is not None:
                score -= 0.01 * abs(_syllable_count(word) - target_syllables)

            scored.append((word, score))
            if len(scored) >= max(top_k * 20, top_k):
                break

        scored.sort(key=lambda item: item[1], reverse=True)
        return [word for word, _score in scored[:top_k]]


_MODEL = KerasBiLSTMPoetryModel()


def fit(*args, **kwargs) -> KerasBiLSTMPoetryModel:
    raise NotImplementedError(
        "Training is handled by model/train_small_poetry_model.ipynb. "
        "After training, place the .keras model, tokenizer.json, and "
        "training_config.json in model/weights/."
    )


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


def generate(context: str, num_words: int = 25) -> str:
    return _MODEL.generate(context=context, num_words=num_words)


def is_fitted() -> bool:
    return _MODEL.is_fitted()


def save(path: str | Path) -> None:
    _MODEL.save(path)


def load(path: str | Path) -> KerasBiLSTMPoetryModel:
    global _MODEL
    _MODEL = KerasBiLSTMPoetryModel.load(path)
    return _MODEL


def load_artifacts(
    model_path: str | Path | None = None,
    tokenizer_path: str | Path | None = None,
    config_path: str | Path | None = None,
) -> KerasBiLSTMPoetryModel:
    global _MODEL
    _MODEL = KerasBiLSTMPoetryModel(
        model_path=model_path,
        tokenizer_path=tokenizer_path,
        config_path=config_path,
        lazy=False,
    )
    return _MODEL


__all__ = [
    "KerasBiLSTMPoetryModel",
    "KERAS_AVAILABLE",
    "fit",
    "predict",
    "generate",
    "is_fitted",
    "save",
    "load",
    "load_artifacts",
]
