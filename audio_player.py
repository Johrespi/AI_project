from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class LoadedAudio:
    data: np.ndarray  # (frames, channels), int16
    sample_rate: int

    @property
    def channels(self) -> int:
        return int(self.data.shape[1])

    @property
    def frames(self) -> int:
        return int(self.data.shape[0])


class AudioPlayer:
    def __init__(self) -> None:
        self._loaded: LoadedAudio | None = None
        self._offset_frames: int = 0
        self._state: str = "stopped"  # stopped | playing | paused

        self._play_obj = None
        self._start_time: float | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def has_audio(self) -> bool:
        return self._loaded is not None

    def load(self, path: str | Path) -> None:
        import soundfile as sf

        data, sample_rate = sf.read(str(path), dtype="int16", always_2d=True)
        if data.size == 0:
            raise ValueError("Audio vacío")

        self._loaded = LoadedAudio(
            data=np.asarray(data, dtype=np.int16), sample_rate=int(sample_rate)
        )
        self.reset()

    def toggle_play_pause(self) -> None:
        if self._loaded is None:
            return

        if self._state == "playing":
            self._pause_internal()
            return

        self._play_internal()

    def reset(self) -> None:
        self.stop()
        self._offset_frames = 0
        self._state = "paused" if self._loaded is not None else "stopped"

    def stop(self) -> None:
        if self._play_obj is not None:
            try:
                self._play_obj.stop()
            except Exception:
                pass
        self._play_obj = None
        self._start_time = None

        if self._loaded is None:
            self._state = "stopped"
        elif self._state == "playing":
            self._state = "paused"

    def poll_finished(self) -> bool:
        if self._state != "playing" or self._play_obj is None:
            return False

        try:
            still_playing = bool(self._play_obj.is_playing())
        except Exception:
            still_playing = False

        if still_playing:
            return False

        self._offset_frames = 0
        self._state = "paused"
        self._play_obj = None
        self._start_time = None
        return True

    def _play_internal(self) -> None:
        if self._loaded is None:
            return

        import importlib

        sa = importlib.import_module("simpleaudio")

        if self._offset_frames >= self._loaded.frames:
            self._offset_frames = 0

        chunk = self._loaded.data[self._offset_frames :]
        if chunk.size == 0:
            self._offset_frames = 0
            return

        self._play_obj = sa.play_buffer(
            chunk.tobytes(),
            num_channels=self._loaded.channels,
            bytes_per_sample=2,
            sample_rate=self._loaded.sample_rate,
        )
        self._start_time = time.monotonic()
        self._state = "playing"

    def _pause_internal(self) -> None:
        if self._loaded is None:
            return

        if self._play_obj is not None:
            try:
                self._play_obj.stop()
            except Exception:
                pass

        if self._start_time is not None:
            elapsed = max(0.0, time.monotonic() - self._start_time)
            advanced = int(elapsed * self._loaded.sample_rate)
            self._offset_frames = min(
                self._loaded.frames, self._offset_frames + advanced
            )

        self._play_obj = None
        self._start_time = None
        self._state = "paused"
