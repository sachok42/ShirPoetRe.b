"""PyTorch poetry next-word model interface.

The public API stays intentionally small:

    import model
    word = model.predict("The moon is shining over")

Training is handled by ``model/reema_bi_lstm_poem_generator_colab.ipynb``.
The trained artifacts are expected under ``model/data`` and
``model/data/weights``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
from typing import Any, Sequence
from zipfile import BadZipFile, ZipFile

try:  # PyTorch is optional for importing the package in lightweight envs.
    import torch
    import torch.nn.functional as F
    from torch import nn
except Exception:  # pragma: no cover - depends on local environment.
    torch = None
    F = None
    nn = None
    TORCH_AVAILABLE = False
else:
    TORCH_AVAILABLE = True


PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
WEIGHTS_DIR = DATA_DIR / "weights"
DATA_ARCHIVE_PATH = PACKAGE_DIR / "data.zip"
DATA_ARCHIVE_STAMP_PATH = DATA_DIR / ".data_zip_sha256"

DEFAULT_CORPUS_PATH = DATA_DIR / "poem.txt"
DEFAULT_VOCAB_PATH = DATA_DIR / "vocabulary.json"
DEFAULT_CONFIG_PATH = DATA_DIR / "training_config.json"
DEFAULT_WEIGHTS_PATH = WEIGHTS_DIR / "reema_bi_lstm_poem_generator.pt"
REQUIRED_DATA_FILES = (
    DEFAULT_CORPUS_PATH,
    DEFAULT_VOCAB_PATH,
    DEFAULT_CONFIG_PATH,
    DEFAULT_WEIGHTS_PATH,
)

PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"
SPECIAL_TOKENS = (PAD_TOKEN, UNK_TOKEN)

WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё]+(?:['’-][A-Za-zА-Яа-яЁё]+)*")
VOWELS = set("aeiouyаеёиоуыэюя")

FALLBACK_WORDS = [
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


def _tokenize(text: str) -> list[str]:
    normalized = (text or "").replace("’", "'").lower()
    return WORD_RE.findall(normalized)


def _syllable_count(word: str) -> int:
    count = sum(1 for char in word.lower() if char in VOWELS)
    return max(1, count)


def _rhymes(word_a: str, word_b: str) -> bool:
    if len(word_a) < 2 or len(word_b) < 2:
        return False

    suffix_len = 3 if min(len(word_a), len(word_b)) >= 4 else 2
    return word_a.lower()[-suffix_len:] == word_b.lower()[-suffix_len:]


def _ensure_special_tokens(tokens: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for token in SPECIAL_TOKENS:
        cleaned.append(token)
        seen.add(token)

    for raw_token in tokens:
        token = str(raw_token)
        if token and token not in seen:
            cleaned.append(token)
            seen.add(token)

    return cleaned


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_member_is_safe(member_name: str) -> bool:
    normalized = member_name.replace("\\", "/")
    member_path = Path(normalized)
    return (
        bool(normalized)
        and not member_path.is_absolute()
        and ".." not in member_path.parts
        and (normalized == "data/" or normalized.startswith("data/"))
    )


def _ensure_data_artifacts() -> None:
    """Extract packaged data.zip when data artifacts are missing or stale."""
    if not DATA_ARCHIVE_PATH.exists():
        return

    archive_hash = _file_sha256(DATA_ARCHIVE_PATH)
    previous_hash = (
        DATA_ARCHIVE_STAMP_PATH.read_text(encoding="utf-8").strip()
        if DATA_ARCHIVE_STAMP_PATH.exists()
        else ""
    )
    missing_required_file = any(not path.exists() for path in REQUIRED_DATA_FILES)

    if DATA_DIR.exists() and not missing_required_file and previous_hash == archive_hash:
        return

    try:
        with ZipFile(DATA_ARCHIVE_PATH) as archive:
            unsafe_members = [
                member.filename
                for member in archive.infolist()
                if not _zip_member_is_safe(member.filename)
            ]
            if unsafe_members:
                raise ValueError(f"Unsafe path in {DATA_ARCHIVE_PATH.name}: {unsafe_members[0]}")

            if DATA_DIR.exists():
                shutil.rmtree(DATA_DIR)
            archive.extractall(PACKAGE_DIR)
    except BadZipFile as exc:
        raise RuntimeError(f"Could not read packaged model data: {DATA_ARCHIVE_PATH}") from exc

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_ARCHIVE_STAMP_PATH.write_text(archive_hash + "\n", encoding="utf-8")


def _load_vocabulary_payload(payload: Any) -> list[str]:
    if isinstance(payload, list):
        return _ensure_special_tokens([str(token) for token in payload])

    if not isinstance(payload, dict):
        raise ValueError("Vocabulary must be a JSON list or object.")

    if "id_to_token" in payload:
        return _ensure_special_tokens([str(token) for token in payload["id_to_token"]])

    if "token_to_id" in payload:
        token_to_id = payload["token_to_id"]
        if not isinstance(token_to_id, dict):
            raise ValueError("token_to_id must be a JSON object.")

        pairs = sorted(token_to_id.items(), key=lambda item: int(item[1]))
        return _ensure_special_tokens([str(token) for token, _ in pairs])

    if "vocabulary" in payload:
        return _ensure_special_tokens([str(token) for token in payload["vocabulary"]])

    raise ValueError("Vocabulary JSON must contain id_to_token, token_to_id, or vocabulary.")


def _build_vocabulary_from_corpus(corpus_path: Path) -> list[str]:
    if not corpus_path.exists():
        return _ensure_special_tokens(FALLBACK_WORDS)

    counter: Counter[str] = Counter()
    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        counter.update(_tokenize(line))

    if not counter:
        return _ensure_special_tokens(FALLBACK_WORDS)

    return _ensure_special_tokens([word for word, _ in counter.most_common()])


def _load_vocabulary(vocab_path: Path, corpus_path: Path) -> tuple[list[str], dict[str, int]]:
    if vocab_path.exists():
        id_to_token = _load_vocabulary_payload(_read_json(vocab_path))
    else:
        id_to_token = _build_vocabulary_from_corpus(corpus_path)

    token_to_id = {token: idx for idx, token in enumerate(id_to_token)}
    return id_to_token, token_to_id


def _load_word_counts(corpus_path: Path, id_to_token: Sequence[str]) -> Counter[str]:
    counter: Counter[str] = Counter()

    if corpus_path.exists():
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            counter.update(_tokenize(line))

    if counter:
        return counter

    return Counter({token: 1 for token in id_to_token if token not in SPECIAL_TOKENS})


@dataclass(slots=True)
class ReemaModelConfig:
    """Configuration for the PyTorch version of the Reema Bi-LSTM model."""

    sequence_len: int = 32
    embedding_dim: int = 128
    hidden_dim: int = 128
    final_hidden_dim: int = 256
    dense_dim: int = 256
    embedding_dropout: float = 0.10
    dropout: float = 0.35
    dropout_after_bi: float = 0.30
    pad_idx: int = 0

    @classmethod
    def from_mapping(cls, payload: dict[str, Any] | None) -> "ReemaModelConfig":
        payload = dict(payload or {})
        sequence_len = payload.get("sequence_len")
        if sequence_len is None:
            sequence_len = int(payload.get("max_sequence_len", 21)) - 1

        return cls(
            sequence_len=int(sequence_len),
            embedding_dim=int(payload.get("embedding_dim", 128)),
            hidden_dim=int(payload.get("hidden_dim", 128)),
            final_hidden_dim=int(payload.get("final_hidden_dim", 256)),
            dense_dim=int(payload.get("dense_dim", 256)),
            embedding_dropout=float(payload.get("embedding_dropout", 0.10)),
            dropout=float(payload.get("dropout", 0.35)),
            dropout_after_bi=float(payload.get("dropout_after_bi", 0.30)),
            pad_idx=int(payload.get("pad_idx", 0)),
        )

    def to_dict(self, vocab_size: int | None = None) -> dict[str, Any]:
        return {
            "sequence_len": self.sequence_len,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "final_hidden_dim": self.final_hidden_dim,
            "dense_dim": self.dense_dim,
            "embedding_dropout": self.embedding_dropout,
            "dropout": self.dropout,
            "dropout_after_bi": self.dropout_after_bi,
            "pad_idx": self.pad_idx,
        }


def _load_config(config_path: Path) -> ReemaModelConfig:
    if not config_path.exists():
        return ReemaModelConfig()

    payload = _read_json(config_path)
    if isinstance(payload, dict) and "model_config" in payload:
        payload = payload["model_config"]
    if not isinstance(payload, dict):
        return ReemaModelConfig()

    return ReemaModelConfig.from_mapping(payload)


if TORCH_AVAILABLE:

    class ReemaBiLSTMPoemGenerator(nn.Module):
        """PyTorch port of the Reema-Khaseeb Bi-LSTM poem generator."""

        def __init__(self, vocab_size: int, config: ReemaModelConfig) -> None:
            super().__init__()
            self.config = config

            self.embedding = nn.Embedding(
                num_embeddings=vocab_size,
                embedding_dim=config.embedding_dim,
                padding_idx=config.pad_idx,
            )
            self.embedding_dropout = nn.Dropout(config.embedding_dropout)
            self.bi_lstm_1 = nn.LSTM(
                input_size=config.embedding_dim,
                hidden_size=config.hidden_dim,
                batch_first=True,
                bidirectional=True,
            )
            self.bi_lstm_2 = nn.LSTM(
                input_size=config.hidden_dim * 2,
                hidden_size=config.hidden_dim,
                batch_first=True,
                bidirectional=True,
            )
            self.sequence_norm = nn.LayerNorm(config.hidden_dim * 2)
            self.dropout_after_bi = nn.Dropout(config.dropout_after_bi)

            self.final_lstm = nn.LSTM(
                input_size=config.hidden_dim * 2,
                hidden_size=config.final_hidden_dim,
                batch_first=True,
            )
            self.final_norm = nn.LayerNorm(config.final_hidden_dim)
            self.dropout_after_final = nn.Dropout(config.dropout)

            self.dense = nn.Linear(config.final_hidden_dim, config.dense_dim)
            self.dense_norm = nn.LayerNorm(config.dense_dim)
            self.dropout_after_dense = nn.Dropout(config.dropout)
            self.output = nn.Linear(config.dense_dim, vocab_size)

        def forward(self, input_ids: "torch.Tensor") -> "torch.Tensor":
            embedded = self.embedding(input_ids)
            embedded = self.embedding_dropout(embedded)
            sequence, _ = self.bi_lstm_1(embedded)
            sequence, _ = self.bi_lstm_2(sequence)
            sequence = self.sequence_norm(sequence)
            sequence = self.dropout_after_bi(sequence)

            sequence, _ = self.final_lstm(sequence)
            pooled = sequence[:, -1, :]
            pooled = self.final_norm(pooled)
            pooled = self.dropout_after_final(pooled)

            features = F.relu(self.dense(pooled))
            features = self.dense_norm(features)
            features = self.dropout_after_dense(features)
            return self.output(features)

else:

    class ReemaBiLSTMPoemGenerator:  # pragma: no cover - only used without torch.
        def __init__(self, *_: Any, **__: Any) -> None:
            raise RuntimeError("PyTorch is required to instantiate the neural model.")


class PoetryNextWordModel:
    """Load a trained PyTorch model and expose next-word prediction."""

    def __init__(
        self,
        weights_path: str | Path | None = None,
        vocab_path: str | Path | None = None,
        config_path: str | Path | None = None,
        corpus_path: str | Path | None = None,
        device: str | None = None,
        autoload: bool = True,
    ) -> None:
        _ensure_data_artifacts()

        self.weights_path = Path(weights_path or DEFAULT_WEIGHTS_PATH)
        self.vocab_path = Path(vocab_path or DEFAULT_VOCAB_PATH)
        self.config_path = Path(config_path or DEFAULT_CONFIG_PATH)
        self.corpus_path = Path(corpus_path or DEFAULT_CORPUS_PATH)

        self.id_to_token, self.token_to_id = _load_vocabulary(self.vocab_path, self.corpus_path)
        self.word_counts = _load_word_counts(self.corpus_path, self.id_to_token)
        self.config = _load_config(self.config_path)
        self.config.pad_idx = self.token_to_id.get(PAD_TOKEN, 0)

        self.device = self._resolve_device(device)
        self._model: ReemaBiLSTMPoemGenerator | None = None
        self._weights_loaded = False

        if autoload:
            self.load_artifacts(required=False)

    def load_artifacts(
        self,
        weights_path: str | Path | None = None,
        vocab_path: str | Path | None = None,
        config_path: str | Path | None = None,
        required: bool = False,
    ) -> "PoetryNextWordModel":
        _ensure_data_artifacts()

        if weights_path is not None:
            self.weights_path = Path(weights_path)
        if vocab_path is not None:
            self.vocab_path = Path(vocab_path)
        if config_path is not None:
            self.config_path = Path(config_path)

        self.id_to_token, self.token_to_id = _load_vocabulary(self.vocab_path, self.corpus_path)
        self.word_counts = _load_word_counts(self.corpus_path, self.id_to_token)
        self.config = _load_config(self.config_path)
        self.config.pad_idx = self.token_to_id.get(PAD_TOKEN, 0)
        self._weights_loaded = False

        if not TORCH_AVAILABLE:
            if required:
                raise RuntimeError("PyTorch is not installed, so weights cannot be loaded.")
            return self

        self._initialize_network()

        if not self.weights_path.exists():
            if required:
                raise FileNotFoundError(f"Model weights were not found: {self.weights_path}")
            return self

        checkpoint = self._safe_torch_load(self.weights_path)
        state_dict = self._apply_checkpoint_metadata(checkpoint)
        if state_dict is None:
            raise ValueError(f"No model_state_dict was found in {self.weights_path}")

        self._initialize_network()
        assert self._model is not None
        self._model.load_state_dict(state_dict)
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

        candidates = self._predict_with_network(
            context=context,
            top_k=top_k,
            rhyme_with=rhyme_with,
            target_syllables=target_syllables,
            forbidden_words=forbidden_words,
            temperature=temperature,
        )

        if len(candidates) < top_k:
            fallback = self._fallback_rank(
                context=context,
                rhyme_with=rhyme_with,
                target_syllables=target_syllables,
                forbidden_words=forbidden_words,
            )
            candidates.extend(word for word in fallback if word not in candidates)

        if not candidates:
            return "" if top_k == 1 else []

        return candidates[0] if top_k == 1 else candidates[:top_k]

    def generate(
        self,
        context: str,
        num_words: int = 25,
        top_k: int = 10,
        temperature: float = 1.0,
    ) -> str:
        generated = context.strip()

        for _ in range(max(0, num_words)):
            next_word = self.predict(
                generated,
                top_k=top_k,
                forbidden_words=None,
                temperature=temperature,
            )
            if isinstance(next_word, list):
                next_word = next_word[0] if next_word else ""
            if not next_word:
                break
            generated = f"{generated} {next_word}".strip()

        return generated

    def reload_vocabulary(self, path: str | Path | None = None) -> list[str]:
        if path is not None:
            self.vocab_path = Path(path)
        self.id_to_token, self.token_to_id = _load_vocabulary(self.vocab_path, self.corpus_path)
        self.word_counts = _load_word_counts(self.corpus_path, self.id_to_token)
        self.config.pad_idx = self.token_to_id.get(PAD_TOKEN, 0)
        return self.vocabulary.copy()

    def is_fitted(self) -> bool:
        return self._weights_loaded

    @property
    def vocabulary(self) -> list[str]:
        return [token for token in self.id_to_token if token not in SPECIAL_TOKENS]

    def save(self, path: str | Path | None = None) -> None:
        if not TORCH_AVAILABLE or self._model is None:
            raise RuntimeError("There is no PyTorch model instance to save.")

        output_path = Path(path or self.weights_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self._model.state_dict(),
                "model_config": self.config.to_dict(vocab_size=len(self.id_to_token)),
                "id_to_token": self.id_to_token,
                "token_to_id": self.token_to_id,
            },
            output_path,
        )

    def _resolve_device(self, requested_device: str | None) -> str:
        if requested_device:
            return requested_device
        if TORCH_AVAILABLE and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _initialize_network(self) -> None:
        if not TORCH_AVAILABLE:
            return

        self._model = ReemaBiLSTMPoemGenerator(
            vocab_size=len(self.id_to_token),
            config=self.config,
        ).to(self.device)
        self._model.eval()

    def _safe_torch_load(self, path: Path) -> Any:
        assert TORCH_AVAILABLE
        try:
            return torch.load(path, map_location=self.device, weights_only=True)
        except TypeError:  # Older PyTorch versions do not support weights_only.
            return torch.load(path, map_location=self.device)

    def _apply_checkpoint_metadata(self, checkpoint: Any) -> dict[str, Any] | None:
        if not isinstance(checkpoint, dict):
            return None

        vocab_payload = checkpoint.get("vocabulary")
        if vocab_payload is None and "id_to_token" in checkpoint:
            vocab_payload = {
                "id_to_token": checkpoint.get("id_to_token"),
                "token_to_id": checkpoint.get("token_to_id"),
            }
        if vocab_payload is not None:
            self.id_to_token = _load_vocabulary_payload(vocab_payload)
            self.token_to_id = {token: idx for idx, token in enumerate(self.id_to_token)}
            self.word_counts = _load_word_counts(self.corpus_path, self.id_to_token)

        config_payload = checkpoint.get("model_config") or checkpoint.get("config")
        if isinstance(config_payload, dict):
            self.config = ReemaModelConfig.from_mapping(config_payload)

        self.config.pad_idx = self.token_to_id.get(PAD_TOKEN, 0)

        state_dict = checkpoint.get("model_state_dict") or checkpoint.get("state_dict")
        if state_dict is not None:
            return state_dict

        # Allow loading a plain state_dict saved directly with torch.save().
        if checkpoint and all(hasattr(value, "shape") for value in checkpoint.values()):
            return checkpoint

        return None

    def _encode_context(self, context: str) -> list[int]:
        tokens = _tokenize(context)[-self.config.sequence_len :]
        unk_idx = self.token_to_id.get(UNK_TOKEN, 1)
        pad_idx = self.token_to_id.get(PAD_TOKEN, 0)

        ids = [self.token_to_id.get(token, unk_idx) for token in tokens]
        padding = [pad_idx] * max(0, self.config.sequence_len - len(ids))
        return padding + ids[-self.config.sequence_len :]

    def _predict_with_network(
        self,
        context: str,
        top_k: int,
        rhyme_with: str | None,
        target_syllables: int | None,
        forbidden_words: Sequence[str] | None,
        temperature: float,
    ) -> list[str]:
        if not (TORCH_AVAILABLE and self._model is not None and self._weights_loaded):
            return []

        input_ids = torch.tensor([self._encode_context(context)], dtype=torch.long, device=self.device)
        with torch.no_grad():
            logits = self._model(input_ids)[0]

        logits = logits.clone()
        for token in SPECIAL_TOKENS:
            token_id = self.token_to_id.get(token)
            if token_id is not None:
                logits[token_id] = float("-inf")

        forbidden = {_normalize_word(word) for word in forbidden_words or []}
        for word in forbidden:
            token_id = self.token_to_id.get(word)
            if token_id is not None:
                logits[token_id] = float("-inf")

        temperature = max(float(temperature), 1e-6)
        probs = F.softmax(logits / temperature, dim=-1)
        limit = min(len(self.id_to_token), max(top_k * 5, top_k + 10))
        _, indices = torch.topk(probs, k=limit)

        candidates: list[str] = []
        for token_id in indices.tolist():
            word = self.id_to_token[token_id]
            if self._candidate_matches(word, rhyme_with, target_syllables, forbidden):
                candidates.append(word)
            if len(candidates) >= top_k:
                break

        return candidates

    def _fallback_rank(
        self,
        context: str,
        rhyme_with: str | None,
        target_syllables: int | None,
        forbidden_words: Sequence[str] | None,
    ) -> list[str]:
        tokens = _tokenize(context)
        anchor = _normalize_word(rhyme_with) if rhyme_with else (tokens[-1] if tokens else "")
        forbidden = {_normalize_word(word) for word in forbidden_words or []}

        if target_syllables is None and anchor:
            target_syllables = _syllable_count(anchor)

        candidates = [
            word
            for word in self.vocabulary
            if self._candidate_matches(word, anchor or None, target_syllables, forbidden)
        ]

        def score(word: str) -> tuple[int, int, int, str]:
            rhyme_penalty = 0 if anchor and _rhymes(word, anchor) else int(bool(anchor))
            syllable_penalty = (
                abs(_syllable_count(word) - target_syllables)
                if target_syllables is not None
                else 0
            )
            frequency_bonus = -self.word_counts.get(word, 0)
            return (rhyme_penalty, syllable_penalty, frequency_bonus, word)

        return sorted(candidates, key=score)

    def _candidate_matches(
        self,
        word: str,
        rhyme_with: str | None,
        target_syllables: int | None,
        forbidden: set[str],
    ) -> bool:
        normalized = _normalize_word(word)
        if not normalized or normalized in SPECIAL_TOKENS or normalized in forbidden:
            return False
        if rhyme_with and not _rhymes(normalized, rhyme_with):
            return False
        if target_syllables is not None and _syllable_count(normalized) != target_syllables:
            return False
        return True


def _normalize_word(word: str | None) -> str:
    tokens = _tokenize(word or "")
    return tokens[0] if tokens else ""


_MODEL = PoetryNextWordModel()


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


def generate(
    context: str,
    num_words: int = 25,
    top_k: int = 10,
    temperature: float = 1.0,
) -> str:
    return _MODEL.generate(
        context=context,
        num_words=num_words,
        top_k=top_k,
        temperature=temperature,
    )


def load_artifacts(
    weights_path: str | Path | None = None,
    vocab_path: str | Path | None = None,
    config_path: str | Path | None = None,
    required: bool = False,
) -> PoetryNextWordModel:
    return _MODEL.load_artifacts(
        weights_path=weights_path,
        vocab_path=vocab_path,
        config_path=config_path,
        required=required,
    )


def reload_vocabulary(path: str | Path | None = None) -> list[str]:
    return _MODEL.reload_vocabulary(path)


def is_fitted() -> bool:
    return _MODEL.is_fitted()


def save(path: str | Path | None = None) -> None:
    _MODEL.save(path)


def load(path: str | Path | None = None) -> PoetryNextWordModel:
    global _MODEL
    _MODEL = PoetryNextWordModel(weights_path=path or DEFAULT_WEIGHTS_PATH)
    return _MODEL


# Backward-compatible names from earlier project iterations.
ReemaPoetryModel = PoetryNextWordModel
TransformerPoetryModel = PoetryNextWordModel


__all__ = [
    "DATA_DIR",
    "WEIGHTS_DIR",
    "DEFAULT_CORPUS_PATH",
    "DEFAULT_VOCAB_PATH",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_WEIGHTS_PATH",
    "ReemaBiLSTMPoemGenerator",
    "ReemaModelConfig",
    "PoetryNextWordModel",
    "ReemaPoetryModel",
    "TransformerPoetryModel",
    "predict",
    "generate",
    "load_artifacts",
    "reload_vocabulary",
    "is_fitted",
    "save",
    "load",
    "TORCH_AVAILABLE",
]
