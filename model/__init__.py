"""Transformer-based poetry next-word model interface.

Usage:
    import model
    word = model.predict("The moon is shining over")
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import re
from typing import Iterable, Sequence

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    TORCH_AVAILABLE = True
except Exception:
    torch = None
    nn = None
    F = None
    TORCH_AVAILABLE = False

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_VOCAB_PATH = MODEL_DIR / "vocabulary.json"
DEFAULT_WEIGHTS_PATH = MODEL_DIR / "weights" / "small_poetry_transformer.pt"

DEFAULT_CONFIG = {
    "max_seq_len": 24,
    "d_model": 128,
    "nhead": 4,
    "num_layers": 2,
    "ff_dim": 256,
    "dropout": 0.1,
}

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
    return WORD_RE.findall((text or "").lower())


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


def _resolve_weights_path(path: str | Path | None) -> Path:
    if path is None:
        return DEFAULT_WEIGHTS_PATH
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return MODEL_DIR / candidate


def _extract_token_list(payload: object) -> list[str]:
    if isinstance(payload, list):
        return [str(item) for item in payload]

    if isinstance(payload, dict):
        for key in ("tokens", "vocabulary", "id_to_token", "itos"):
            value = payload.get(key)
            if isinstance(value, list):
                return [str(item) for item in value]

    return []


def _clean_tokens(tokens: Iterable[str], skip: set[str] | None = None) -> list[str]:
    skip = skip or set()
    seen: set[str] = set()
    cleaned: list[str] = []

    for raw_token in tokens:
        token = str(raw_token).strip().lower()
        if not token or token in skip:
            continue
        if token.startswith("<") and token.endswith(">"):
            continue
        if token in seen:
            continue
        seen.add(token)
        cleaned.append(token)

    return cleaned


def _load_vocabulary_file(path: str | Path | None = None) -> tuple[list[str], str, str]:
    vocab_path = _resolve_vocab_path(path)
    pad_token = "<pad>"
    unk_token = "<unk>"

    try:
        payload = json.loads(vocab_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return FALLBACK_VOCABULARY.copy(), pad_token, unk_token

    if isinstance(payload, dict):
        special = payload.get("special_tokens")
        if isinstance(special, dict):
            pad_token = str(special.get("pad", pad_token)).strip().lower() or "<pad>"
            unk_token = str(special.get("unk", unk_token)).strip().lower() or "<unk>"

    tokens = _clean_tokens(_extract_token_list(payload), skip={pad_token, unk_token})
    if not tokens:
        tokens = FALLBACK_VOCABULARY.copy()

    return tokens, pad_token, unk_token


def _normalize_config(config: dict[str, object] | None) -> dict[str, object]:
    merged = {**DEFAULT_CONFIG}
    if isinstance(config, dict):
        merged.update(config)

    return {
        "max_seq_len": int(merged["max_seq_len"]),
        "d_model": int(merged["d_model"]),
        "nhead": int(merged["nhead"]),
        "num_layers": int(merged["num_layers"]),
        "ff_dim": int(merged["ff_dim"]),
        "dropout": float(merged["dropout"]),
    }


if TORCH_AVAILABLE:

    class TransformerNextWordModel(nn.Module):
        """Small decoder-style transformer for next-word prediction."""

        def __init__(
            self,
            vocab_size: int,
            pad_id: int,
            max_seq_len: int,
            d_model: int,
            nhead: int,
            num_layers: int,
            ff_dim: int,
            dropout: float,
        ) -> None:
            super().__init__()
            self.pad_id = pad_id
            self.max_seq_len = max_seq_len
            self.token_embedding = nn.Embedding(vocab_size, d_model, padding_idx=pad_id)
            self.position_embedding = nn.Embedding(max_seq_len, d_model)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=ff_dim,
                dropout=dropout,
                batch_first=True,
            )
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
            self.norm = nn.LayerNorm(d_model)
            self.output = nn.Linear(d_model, vocab_size)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: [batch, seq_len]
            seq_len = x.size(1)
            pos_ids = torch.arange(seq_len, device=x.device).unsqueeze(0).expand_as(x)
            hidden = self.token_embedding(x) + self.position_embedding(pos_ids)

            # Prevent attending to future positions.
            causal_mask = torch.triu(
                torch.ones(seq_len, seq_len, device=x.device, dtype=torch.bool),
                diagonal=1,
            )
            pad_mask = x.eq(self.pad_id)

            hidden = self.transformer(
                hidden,
                mask=causal_mask,
                src_key_padding_mask=pad_mask,
            )
            hidden = self.norm(hidden)
            last_hidden = hidden[:, -1, :]
            return self.output(last_hidden)

else:

    class TransformerNextWordModel:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyTorch is required for TransformerNextWordModel")


class TransformerPoetryModel:
    """Transformer-backed next-word predictor with simple API."""

    def __init__(
        self,
        vocabulary: list[str] | None = None,
        vocabulary_path: str | Path | None = None,
        weights_path: str | Path | None = None,
        seed: int = 7,
        config: dict[str, object] | None = None,
        auto_load_weights: bool = True,
    ) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

        self.vocabulary_path = _resolve_vocab_path(vocabulary_path)
        self.weights_path = _resolve_weights_path(weights_path)
        self.config = _normalize_config(config)

        if vocabulary:
            cleaned = _clean_tokens(vocabulary)
            self.vocabulary = cleaned or FALLBACK_VOCABULARY.copy()
            self.pad_token = "<pad>"
            self.unk_token = "<unk>"
        else:
            self.vocabulary, self.pad_token, self.unk_token = _load_vocabulary_file(
                self.vocabulary_path
            )

        self._rebuild_mappings()
        self._weights_loaded = False

        self.device = None
        self._model = None

        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._initialize_network()

            if auto_load_weights:
                self._load_weights_if_available(self.weights_path)

    def _rebuild_mappings(self) -> None:
        self.itos = [self.pad_token, self.unk_token] + self.vocabulary
        self.stoi = {token: idx for idx, token in enumerate(self.itos)}
        self.pad_id = self.stoi[self.pad_token]
        self.unk_id = self.stoi[self.unk_token]

    def _initialize_network(self) -> None:
        if not TORCH_AVAILABLE:
            return

        self.max_seq_len = int(self.config["max_seq_len"])
        self._model = TransformerNextWordModel(
            vocab_size=len(self.itos),
            pad_id=self.pad_id,
            max_seq_len=self.max_seq_len,
            d_model=int(self.config["d_model"]),
            nhead=int(self.config["nhead"]),
            num_layers=int(self.config["num_layers"]),
            ff_dim=int(self.config["ff_dim"]),
            dropout=float(self.config["dropout"]),
        ).to(self.device)

    def _load_weights_if_available(self, path: str | Path | None) -> None:
        if not TORCH_AVAILABLE:
            self._weights_loaded = False
            return

        weights_path = _resolve_weights_path(path)
        if not weights_path.exists():
            self._weights_loaded = False
            return

        checkpoint = torch.load(weights_path, map_location=self.device)
        if not isinstance(checkpoint, dict):
            self._weights_loaded = False
            return

        loaded_config = checkpoint.get("config")
        if isinstance(loaded_config, dict):
            self.config = _normalize_config(loaded_config)
            self._initialize_network()

        state_dict = checkpoint.get("model_state_dict", checkpoint)
        try:
            self._model.load_state_dict(state_dict)
            self._model.eval()
            self._weights_loaded = True
            self.weights_path = weights_path
        except Exception:
            self._weights_loaded = False

    def _encode_context(self, context: str) -> list[int]:
        tokens = _tokenize(context)
        ids = [self.stoi.get(token, self.unk_id) for token in tokens][-self.max_seq_len :]
        if len(ids) < self.max_seq_len:
            ids = [self.pad_id] * (self.max_seq_len - len(ids)) + ids
        return ids

    def _fallback_rank(
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

    def fit(
        self,
        texts: Sequence[str] | None = None,
        epochs: int = 2,
        batch_size: int = 128,
        learning_rate: float = 3e-3,
    ) -> "TransformerPoetryModel":
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch is required for Transformer training")
        if not texts:
            return self

        samples: list[tuple[list[int], int]] = []
        for text in texts:
            ids = [self.stoi.get(token, self.unk_id) for token in _tokenize(text)]
            for i in range(1, len(ids)):
                context = ids[max(0, i - self.max_seq_len) : i]
                if len(context) < self.max_seq_len:
                    context = [self.pad_id] * (self.max_seq_len - len(context)) + context
                samples.append((context, ids[i]))

        if not samples:
            return self

        x = torch.tensor([context for context, _target in samples], dtype=torch.long, device=self.device)
        y = torch.tensor([target for _context, target in samples], dtype=torch.long, device=self.device)

        optimizer = torch.optim.AdamW(self._model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()

        self._model.train()
        for _epoch in range(max(1, epochs)):
            permutation = torch.randperm(x.size(0), device=self.device)
            for start in range(0, x.size(0), max(1, batch_size)):
                batch_idx = permutation[start : start + max(1, batch_size)]
                xb = x[batch_idx]
                yb = y[batch_idx]

                optimizer.zero_grad()
                logits = self._model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), max_norm=1.0)
                optimizer.step()

        self._model.eval()
        self._weights_loaded = True
        return self

    def predict(
        self,
        context: str,
        top_k: int = 1,
        rhyme_with: str | None = None,
        target_syllables: int | None = None,
        forbidden_words: Sequence[str] | None = None,
        temperature: float = 1.0,
    ) -> str | list[str]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if target_syllables is not None and target_syllables < 1:
            raise ValueError("target_syllables must be >= 1")
        if temperature <= 0:
            raise ValueError("temperature must be > 0")

        tokens = _tokenize(context)

        if not TORCH_AVAILABLE or self._model is None:
            ranked = self._fallback_rank(tokens, rhyme_with, target_syllables, forbidden_words)
            return ranked[0] if top_k == 1 else ranked[:top_k]

        context_ids = self._encode_context(context)
        x = torch.tensor([context_ids], dtype=torch.long, device=self.device)

        self._model.eval()
        with torch.no_grad():
            logits = self._model(x)[0] / float(temperature)
            log_probs = F.log_softmax(logits, dim=-1)

        forbidden = {word.lower() for word in (forbidden_words or [])}
        candidates = [token for token in self.vocabulary if token.lower() not in forbidden]
        if not candidates:
            candidates = self.vocabulary.copy()

        reference = tokens[-1] if tokens else ""
        rhythm_target = target_syllables if target_syllables is not None else (
            _syllable_count(reference) if reference else None
        )
        rhyme_reference = (rhyme_with or reference or "").lower()

        scored: list[tuple[str, float]] = []
        for token in candidates:
            idx = self.stoi.get(token, self.unk_id)
            score = float(log_probs[idx].item())

            if rhyme_reference and self._rhymes(token, rhyme_reference):
                score += 0.75

            if rhythm_target is not None:
                score -= 0.25 * abs(_syllable_count(token) - rhythm_target)

            scored.append((token, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        tokens_out = [token for token, _score in scored]

        if top_k == 1:
            return tokens_out[0]
        return tokens_out[:top_k]

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "format": "poetry_transformer_v1",
            "seed": self.seed,
            "config": self.config,
            "vocabulary_path": str(self.vocabulary_path),
            "weights_path": str(self.weights_path),
        }

        if TORCH_AVAILABLE and self._model is not None:
            payload["model_state_dict"] = self._model.state_dict()
            torch.save(payload, destination)
            return

        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TransformerPoetryModel":
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(f"Model file not found: {source}")

        if TORCH_AVAILABLE:
            checkpoint = torch.load(source, map_location="cpu")
        else:
            checkpoint = json.loads(source.read_text(encoding="utf-8"))

        if not isinstance(checkpoint, dict):
            raise ValueError("Unsupported model checkpoint format")

        model = cls(
            seed=int(checkpoint.get("seed", 7)),
            config=checkpoint.get("config"),
            vocabulary_path=checkpoint.get("vocabulary_path"),
            weights_path=source,
            auto_load_weights=False,
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
