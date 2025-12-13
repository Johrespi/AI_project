from __future__ import annotations

from pathlib import Path


class AudioPlayer:
    def __init__(self) -> None:
        self._loaded_path: Path | None = None
        self._sample_rate: int | None = None
        self._channels: int | None = None

        self._state: str = "stopped"  # stopped | playing | paused
        self._paused_by_user: bool = False
        self._started_once: bool = False

    @property
    def state(self) -> str:
        return self._state

    @property
    def has_audio(self) -> bool:
        return self._loaded_path is not None

    def load(self, path: str | Path) -> None:
        import soundfile as sf

        path = Path(path)

        with sf.SoundFile(str(path)) as f:
            if f.frames <= 0:
                raise ValueError("Audio vacío")
            sample_rate = int(f.samplerate)
            channels = int(f.channels)

        self._loaded_path = path
        self._ensure_mixer(sample_rate=sample_rate, channels=channels)

        import pygame

        pygame.mixer.music.load(str(path))
        self._sample_rate = sample_rate
        self._channels = channels
        self._state = "paused"
        self._paused_by_user = False
        self._started_once = False

    def toggle_play_pause(self) -> None:
        if self._loaded_path is None:
            return

        import pygame

        if self._state == "playing":
            pygame.mixer.music.pause()
            self._state = "paused"
            self._paused_by_user = True
            return

        if self._state != "paused":
            self._state = "paused"

        if self._paused_by_user:
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.play()
            self._started_once = True

        self._state = "playing"
        self._paused_by_user = False

    def reset(self) -> None:
        self.stop()
        self._state = "paused" if self._loaded_path is not None else "stopped"
        self._paused_by_user = False
        self._started_once = False

    def stop(self) -> None:
        if self._loaded_path is None:
            self._state = "stopped"
            self._paused_by_user = False
            self._started_once = False
            return

        try:
            import pygame

            pygame.mixer.music.stop()
        except Exception:
            pass

        if self._state == "playing":
            self._state = "paused"
        self._paused_by_user = False

    def poll_finished(self) -> bool:
        if self._state != "playing" or self._loaded_path is None:
            return False

        try:
            import pygame

            still_playing = bool(pygame.mixer.music.get_busy())
        except Exception:
            still_playing = False

        if still_playing:
            return False

        self._state = "paused"
        self._paused_by_user = False
        self._started_once = False
        return True

    def _ensure_mixer(self, sample_rate: int, channels: int) -> None:
        import pygame

        init = pygame.mixer.get_init()
        if init is not None:
            current_sample_rate, _format, current_channels = init
            if int(current_sample_rate) == int(sample_rate) and int(
                current_channels
            ) == int(channels):
                return
            pygame.mixer.quit()

        pygame.mixer.init(frequency=int(sample_rate), channels=int(channels))
