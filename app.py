from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, filedialog
import tkinter as tk
import tempfile
import numpy as np

from asr_model import AsrTranscriber, load_transcriber
from audio_player import AudioPlayer


@dataclass(frozen=True)
class Theme:
    # Dark mode inspired by shadcn/ui
    bg: str = "#0a0a0a"  # zinc-950
    fg: str = "#fafafa"  # zinc-50
    muted: str = "#a3a3a3"  # zinc-400
    border: str = "#262626"  # zinc-800
    hover: str = "#171717"  # zinc-900
    btn_bg: str = "#0a0a0a"
    btn_fg: str = "#fafafa"
    btn_hover: str = "#262626"


class OutlineButton(tk.Button):
    def __init__(self, master: tk.Misc, theme: Theme, **kwargs):
        super().__init__(
            master,
            bg=theme.btn_bg,
            fg=theme.btn_fg,
            activebackground=theme.btn_hover,
            activeforeground=theme.btn_fg,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=theme.border,
            highlightcolor=theme.border,
            padx=14,
            pady=8,
            cursor="hand2",
            **kwargs,
        )
        self._theme = theme
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _event):
        if self["state"] != tk.DISABLED:
            self.configure(bg=self._theme.btn_hover)

    def _on_leave(self, _event):
        self.configure(bg=self._theme.btn_bg)


class App:
    def __init__(self, root: Tk, checkpoint_path: Path):
        self.root = root
        self.theme = Theme()
        self.checkpoint_path = checkpoint_path

        self.transcriber: AsrTranscriber | None = None
        self.selected_audio_path: Path | None = None

        self.player = AudioPlayer()
        
        # Variables para grabación
        self.is_recording: bool = False
        self.recorded_audio: list = []
        self.sample_rate: int = 16000

        self._build_ui()
        self._start_model_load()
        self._start_player_poll()

    def _build_ui(self) -> None:
        self.root.title("ASR (ES)")
        self.root.configure(bg=self.theme.bg)
        self.root.minsize(760, 480)

        try:
            self.root.option_add("*Font", "SegoeUI 11")
        except Exception:
            pass

        container = tk.Frame(self.root, bg=self.theme.bg)
        container.pack(fill=tk.BOTH, expand=True, padx=28, pady=24)

        header = tk.Label(
            container,
            text="Transcriptor ASR (Español)",
            bg=self.theme.bg,
            fg=self.theme.fg,
            font=("Segoe UI", 18, "bold"),
            anchor="center",
        )
        header.pack(fill=tk.X)

        subtitle = tk.Label(
            container,
            text="Sube un archivo .wav y obtén la transcripción.",
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="center",
        )
        subtitle.pack(fill=tk.X, pady=(6, 18))

        action_row = tk.Frame(container, bg=self.theme.bg)
        action_row.pack(fill=tk.X)

        actions = tk.Frame(action_row, bg=self.theme.bg)
        actions.pack()

        self.btn_select = OutlineButton(
            actions,
            self.theme,
            text="Seleccionar audio",
            command=self._on_select_audio,
        )
        self.btn_select.pack(side=tk.LEFT)
        
        self.btn_record = OutlineButton(
            actions,
            self.theme,
            text="🎤 Grabar",
            command=self._on_start_recording,
        )
        self.btn_record.pack(side=tk.LEFT, padx=(10, 0))
        
        self.btn_stop_record = OutlineButton(
            actions,
            self.theme,
            text="⏹ Detener",
            command=self._on_stop_recording,
            state=tk.DISABLED,
        )
        self.btn_stop_record.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_transcribe = OutlineButton(
            actions,
            self.theme,
            text="Transcribir",
            command=self._on_transcribe,
            state=tk.DISABLED,
        )
        self.btn_transcribe.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_copy = OutlineButton(
            actions,
            self.theme,
            text="Copiar",
            command=self._on_copy,
            state=tk.DISABLED,
        )
        self.btn_copy.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_play_pause = OutlineButton(
            actions,
            self.theme,
            text="Reproducir",
            command=self._on_play_pause,
            state=tk.DISABLED,
        )
        self.btn_play_pause.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_reset_audio = OutlineButton(
            actions,
            self.theme,
            text="Reiniciar",
            command=self._on_reset_audio,
            state=tk.DISABLED,
        )
        self.btn_reset_audio.pack(side=tk.LEFT, padx=(10, 0))

        self.file_label = tk.Label(
            container,
            text="Archivo: (ninguno)",
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="center",
        )
        self.file_label.pack(fill=tk.X, pady=(14, 10))

        self.status_var = tk.StringVar(value="Cargando modelo…")
        status = tk.Label(
            container,
            textvariable=self.status_var,
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="center",
        )
        status.pack(fill=tk.X)

        # Text area
        text_frame = tk.Frame(
            container,
            bg=self.theme.bg,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.text = tk.Text(
            text_frame,
            wrap="word",
            bg=self.theme.bg,
            fg=self.theme.fg,
            insertbackground=self.theme.fg,
            relief="flat",
            padx=14,
            pady=12,
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self._set_text("Selecciona un archivo WAV para empezar.")

    def _set_text(self, value: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, value)
        self.text.configure(state=tk.DISABLED)

    def _start_model_load(self) -> None:
        self.btn_select.configure(state=tk.DISABLED)
        self.btn_record.configure(state=tk.DISABLED)
        self.btn_stop_record.configure(state=tk.DISABLED)
        self.btn_transcribe.configure(state=tk.DISABLED)
        self.btn_copy.configure(state=tk.DISABLED)
        self.btn_play_pause.configure(state=tk.DISABLED)
        self.btn_reset_audio.configure(state=tk.DISABLED)

        def load_worker():
            try:
                transcriber = load_transcriber(self.checkpoint_path)
                self.root.after(0, lambda: self._on_model_loaded(transcriber))
            except Exception as exc:
                self.root.after(0, lambda: self._on_model_failed(str(exc)))

        threading.Thread(target=load_worker, daemon=True).start()

    def _on_model_loaded(self, transcriber: AsrTranscriber) -> None:
        self.transcriber = transcriber
        self.status_var.set(f"Listo. Modelo en {transcriber.device.type.upper()}.")
        self.btn_select.configure(state=tk.NORMAL)
        self.btn_record.configure(state=tk.NORMAL)

    def _on_model_failed(self, message: str) -> None:
        self.status_var.set(f"Error cargando modelo: {message}")
        self.btn_select.configure(state=tk.NORMAL)
        self.btn_record.configure(state=tk.NORMAL)

    def _on_select_audio(self) -> None:
        filename = filedialog.askopenfilename(
            title="Selecciona un archivo WAV",
            filetypes=[
                ("Audio WAV", "*.wav"),
                ("Todos los archivos", "*")
            ],
        )
        if not filename:
            return

        path = Path(filename)
        if path.suffix.lower() != '.wav':
            self.status_var.set("Formato no soportado. Solo .wav.")
            return
        self.selected_audio_path = path
        self.file_label.configure(text=f"Archivo: {path.name}")
        self._set_text("")
        self.status_var.set("Listo para transcribir.")

        try:
            self.player.load(path)
            self._update_player_buttons()
            self.btn_play_pause.configure(state=tk.NORMAL)
            self.btn_reset_audio.configure(state=tk.NORMAL)
        except Exception as exc:
            self.status_var.set(f"Error reproduciendo audio: {exc}")
            self.btn_play_pause.configure(state=tk.DISABLED)
            self.btn_reset_audio.configure(state=tk.DISABLED)

        if self.transcriber is not None:
            self.btn_transcribe.configure(state=tk.NORMAL)

    def _on_transcribe(self) -> None:
        if self.transcriber is None:
            self.status_var.set("El modelo todavía no está listo.")
            return

        if self.selected_audio_path is None:
            self.status_var.set("Selecciona un archivo .wav primero.")
            return

        audio_path = self.selected_audio_path
        self.btn_select.configure(state=tk.DISABLED)
        self.btn_transcribe.configure(state=tk.DISABLED)
        self.btn_copy.configure(state=tk.DISABLED)
        self.status_var.set("Transcribiendo…")

        transcriber = self.transcriber
        if transcriber is None:
            self.status_var.set("El modelo todavía no está listo.")
            self.btn_select.configure(state=tk.NORMAL)
            return

        def worker():
            try:
                text, confidence = transcriber.transcribe_wav(audio_path)
                self.root.after(0, lambda: self._on_transcribe_done(text, confidence))
            except Exception as exc:
                self.root.after(0, lambda: self._on_transcribe_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_transcribe_done(self, text: str, confidence: float) -> None:
        self._set_text(text if text.strip() else "(transcripción vacía)")
        self.status_var.set(f"Hecho. Confianza aprox.: {confidence * 100:.1f}%")
        self.btn_select.configure(state=tk.NORMAL)
        self.btn_transcribe.configure(state=tk.NORMAL)
        self.btn_copy.configure(state=tk.NORMAL)

    def _on_transcribe_error(self, message: str) -> None:
        self.status_var.set(f"Error transcribiendo: {message}")
        self.btn_select.configure(state=tk.NORMAL)
        self.btn_transcribe.configure(state=tk.NORMAL)

    def _start_player_poll(self) -> None:
        def poll():
            finished = False
            try:
                finished = self.player.poll_finished()
            except Exception:
                finished = False

            if finished:
                self._update_player_buttons()

            self.root.after(200, poll)

        self.root.after(200, poll)

    def _update_player_buttons(self) -> None:
        state = self.player.state
        if state == "playing":
            self.btn_play_pause.configure(text="Pausar")
        else:
            self.btn_play_pause.configure(text="Reproducir")

    def _on_play_pause(self) -> None:
        if self.selected_audio_path is None:
            return

        try:
            self.player.toggle_play_pause()
            self._update_player_buttons()
        except Exception as exc:
            self.status_var.set(f"Error reproduciendo audio: {exc}")

    def _on_reset_audio(self) -> None:
        if self.selected_audio_path is None:
            return

        try:
            self.player.reset()
            self._update_player_buttons()
        except Exception as exc:
            self.status_var.set(f"Error reproduciendo audio: {exc}")

    def _on_copy(self) -> None:
        text = self.text.get("1.0", tk.END).strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Transcripción copiada al clipboard.")

    def _on_start_recording(self) -> None:
        """Inicia la grabación de audio desde el micrófono."""
        import sounddevice as sd
        
        self.is_recording = True
        self.recorded_audio = []
        
        self.btn_record.configure(state=tk.DISABLED)
        self.btn_stop_record.configure(state=tk.NORMAL)
        self.btn_select.configure(state=tk.DISABLED)
        self.btn_transcribe.configure(state=tk.DISABLED)
        self.status_var.set("🔴 Grabando audio...")
        
        def record_worker():
            """Worker thread para grabar audio sin bloquear la UI."""
            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32'
                ) as stream:
                    while self.is_recording:
                        audio_chunk, _ = stream.read(1024)
                        self.recorded_audio.append(audio_chunk)
            except Exception as exc:
                self.root.after(0, lambda: self.status_var.set(f"Error grabando: {exc}"))
                self.root.after(0, self._reset_recording_state)
        
        threading.Thread(target=record_worker, daemon=True).start()

    def _on_stop_recording(self) -> None:
        """Detiene la grabación y guarda el audio como archivo WAV."""
        self.is_recording = False
        self.btn_stop_record.configure(state=tk.DISABLED)
        self.status_var.set("Procesando grabación...")
        
        def process_worker():
            """Worker thread para procesar y guardar el audio grabado."""
            try:
                if not self.recorded_audio:
                    self.root.after(0, lambda: self.status_var.set("No se grabó audio."))
                    self.root.after(0, self._reset_recording_state)
                    return
                
                # Concatenar todos los chunks de audio
                audio_data = np.concatenate(self.recorded_audio, axis=0)
                
                # Guardar como archivo WAV temporal
                from scipy.io import wavfile
                temp_dir = Path(tempfile.gettempdir())
                timestamp = threading.current_thread().name.split('-')[-1]
                wav_path = temp_dir / f"recording_{timestamp}.wav"
                
                # Convertir de float32 a int16 para WAV
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wavfile.write(str(wav_path), self.sample_rate, audio_int16)
                
                # Cargar el archivo grabado automáticamente
                self.root.after(0, lambda: self._load_recorded_audio(wav_path))
                
            except Exception as exc:
                self.root.after(0, lambda: self.status_var.set(f"Error procesando grabación: {exc}"))
                self.root.after(0, self._reset_recording_state)
        
        threading.Thread(target=process_worker, daemon=True).start()

    def _load_recorded_audio(self, path: Path) -> None:
        """Carga el audio grabado en la interfaz."""
        self.selected_audio_path = path
        self.file_label.configure(text=f"Archivo: {path.name} (grabación)")
        self._set_text("")
        self.status_var.set("Grabación lista para transcribir.")
        
        try:
            self.player.load(path)
            self._update_player_buttons()
            self.btn_play_pause.configure(state=tk.NORMAL)
            self.btn_reset_audio.configure(state=tk.NORMAL)
        except Exception as exc:
            self.status_var.set(f"Error cargando grabación: {exc}")
            self.btn_play_pause.configure(state=tk.DISABLED)
            self.btn_reset_audio.configure(state=tk.DISABLED)
        
        if self.transcriber is not None:
            self.btn_transcribe.configure(state=tk.NORMAL)
        
        self._reset_recording_state()

    def _reset_recording_state(self) -> None:
        """Restaura el estado de los botones después de grabar."""
        self.btn_record.configure(state=tk.NORMAL)
        self.btn_stop_record.configure(state=tk.DISABLED)
        self.btn_select.configure(state=tk.NORMAL)


def main() -> None:
    root = Tk()

    checkpoint_path = Path(__file__).resolve().parent / "best_model.pth"
    if not checkpoint_path.exists():
        checkpoint_path = Path(__file__).resolve().parent / "checkpoint_epoch_40.pth"

    App(root, checkpoint_path)
    root.mainloop()


if __name__ == "__main__":
    main()
