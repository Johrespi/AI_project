from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn


@dataclass(frozen=True)
class ModelConfig:
    n_mels: int
    hidden_size: int
    vocab_size: int
    num_lstm_layers: int
    dropout: float
    sample_rate: int
    n_fft: int
    hop_length: int
    win_length: int


class ASRCNN_BiLSTM(nn.Module):
    def __init__(
        self,
        n_mels: int = 80,
        hidden_size: int = 256,
        vocab_size: int = 30,
        num_lstm_layers: int = 4,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()

        self.n_mels = n_mels
        self.hidden_size = hidden_size
        self.vocab_size = vocab_size
        self.num_lstm_layers = num_lstm_layers

        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(32)

        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(64)

        self.relu = nn.ReLU()
        self.dropout_cnn = nn.Dropout(dropout)

        self.cnn_output_dim = 64 * (n_mels // 4 if n_mels // 4 > 0 else 1)

        self.lstm = nn.LSTM(
            input_size=self.cnn_output_dim,
            hidden_size=hidden_size,
            num_layers=num_lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_lstm_layers > 1 else 0.0,
        )

        self.fc = nn.Linear(hidden_size * 2, vocab_size)
        self.log_softmax = nn.LogSoftmax(dim=2)

    def forward(self, x: torch.Tensor, input_lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        x = x.unsqueeze(1)

        x = self.relu(self.bn1(self.conv1(x)))
        x = nn.functional.max_pool2d(x, kernel_size=2, stride=2)
        x = self.dropout_cnn(x)

        x = self.relu(self.bn2(self.conv2(x)))
        x = nn.functional.max_pool2d(x, kernel_size=2, stride=2)
        x = self.dropout_cnn(x)

        batch, channels, freq, time = x.size()
        x = x.permute(0, 3, 1, 2)
        x = x.reshape(batch, time, channels * freq)

        output_lengths = (input_lengths / (2**2)).long()

        x = nn.utils.rnn.pack_padded_sequence(
            x,
            output_lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )

        x, _ = self.lstm(x)
        x, _ = nn.utils.rnn.pad_packed_sequence(x, batch_first=True)

        x = self.fc(x)
        log_probs = self.log_softmax(x)

        return log_probs, output_lengths


class AsrTranscriber:
    def __init__(
        self,
        model: ASRCNN_BiLSTM,
        idx_to_char: dict[int, str],
        config: ModelConfig,
        device: torch.device,
    ) -> None:
        self.model = model
        self.idx_to_char = idx_to_char
        self.config = config
        self.device = device

    @staticmethod
    def _decode_greedy(
        log_probs: torch.Tensor, idx_to_char: dict[int, str], blank_idx: int = 0
    ) -> tuple[str, float]:
        probs = torch.exp(log_probs)
        max_probs, indices = torch.max(probs, dim=1)

        decoded_chars: list[str] = []
        confidences: list[float] = []
        prev_idx: int | None = None

        for idx, conf in zip(indices.cpu().numpy(), max_probs.cpu().numpy()):
            idx_int = int(idx)
            if idx_int != prev_idx and idx_int != blank_idx:
                decoded_chars.append(idx_to_char.get(idx_int, ""))
                confidences.append(float(conf))
            prev_idx = idx_int

        text = "".join(decoded_chars)
        confidence = float(sum(confidences) / len(confidences)) if confidences else 0.0
        return text, confidence

    def transcribe_wav(self, audio_path: str | Path) -> tuple[str, float]:
        import librosa

        audio_path = Path(audio_path)
        audio, _ = librosa.load(str(audio_path), sr=self.config.sample_rate, mono=True)

        mel = librosa.feature.melspectrogram(
            y=audio,
            sr=self.config.sample_rate,
            n_mels=self.config.n_mels,
            n_fft=self.config.n_fft,
            hop_length=self.config.hop_length,
            win_length=self.config.win_length,
            window="hamming",
            center=True,
            pad_mode="reflect",
        )
        mel_db = librosa.power_to_db(mel, ref=np.max)

        mel_tensor = torch.tensor(mel_db, dtype=torch.float32).unsqueeze(0).to(self.device)
        mel_length = torch.tensor([mel_tensor.size(2)], dtype=torch.long).to(self.device)

        with torch.no_grad():
            log_probs, _ = self.model(mel_tensor, mel_length)

        text, confidence = self._decode_greedy(log_probs[0], self.idx_to_char, blank_idx=0)
        return text, confidence


def _parse_model_config(raw: dict[str, Any]) -> ModelConfig:
    return ModelConfig(
        n_mels=int(raw["n_mels"]),
        hidden_size=int(raw["hidden_size"]),
        vocab_size=int(raw["vocab_size"]),
        num_lstm_layers=int(raw["num_lstm_layers"]),
        dropout=float(raw["dropout"]),
        sample_rate=int(raw["sample_rate"]),
        n_fft=int(raw["n_fft"]),
        hop_length=int(raw["hop_length"]),
        win_length=int(raw["win_length"]),
    )


def _coerce_idx_to_char(mapping: dict[Any, Any]) -> dict[int, str]:
    out: dict[int, str] = {}
    for k, v in mapping.items():
        out[int(k)] = str(v)
    return out


def load_transcriber(checkpoint_path: str | Path, device: torch.device | None = None) -> AsrTranscriber:
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

    checkpoint_path = Path(checkpoint_path)
    checkpoint = torch.load(str(checkpoint_path), map_location=device)

    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise ValueError("Checkpoint no tiene formato esperado (falta 'model_state_dict')")

    config = _parse_model_config(checkpoint["model_config"])  # type: ignore[arg-type]
    idx_to_char = _coerce_idx_to_char(checkpoint["idx_to_char"])  # type: ignore[arg-type]

    model = ASRCNN_BiLSTM(
        n_mels=config.n_mels,
        hidden_size=config.hidden_size,
        vocab_size=config.vocab_size,
        num_lstm_layers=config.num_lstm_layers,
        dropout=config.dropout,
    ).to(device)

    model.load_state_dict(checkpoint["model_state_dict"])  # type: ignore[arg-type]
    model.eval()

    return AsrTranscriber(model=model, idx_to_char=idx_to_char, config=config, device=device)
