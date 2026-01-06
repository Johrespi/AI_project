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
    # Windows 95 Classic
    bg: str = "#c0c0c0"  # Gris clásico
    fg: str = "#000000"  # Texto negro
    muted: str = "#404040"  # Texto secundario

    # Bordes 3D
    highlight: str = "#ffffff"  # Borde superior/izquierdo (luz)
    shadow: str = "#808080"  # Borde inferior/derecho (sombra)
    dark_shadow: str = "#404040"  # Sombra más oscura

    # Barra de título
    title_bg: str = "#000080"  # Azul marino Windows 95
    title_fg: str = "#ffffff"  # Texto blanco

    # Botones
    btn_bg: str = "#c0c0c0"
    btn_fg: str = "#000000"
    btn_pressed: str = "#a0a0a0"

    # Area de texto
    input_bg: str = "#ffffff"
    input_fg: str = "#000000"


class Win95Button(tk.Frame):
    """Botón con efecto 3D estilo Windows 95."""

    def __init__(
        self, master: tk.Misc, theme: Theme, text: str = "", command=None, **kwargs
    ):
        super().__init__(master, bg=theme.bg)
        self._theme = theme
        self._command = command
        self._pressed = False
        self._disabled = False

        # Frame exterior para borde 3D
        self._outer_frame = tk.Frame(self, bg=theme.highlight)
        self._outer_frame.pack(fill=tk.BOTH, expand=True)

        # Frame interior para sombra
        self._inner_frame = tk.Frame(self._outer_frame, bg=theme.dark_shadow)
        self._inner_frame.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 2))

        # Frame del botón
        self._btn_frame = tk.Frame(self._inner_frame, bg=theme.btn_bg)
        self._btn_frame.pack(fill=tk.BOTH, expand=True, padx=(2, 0), pady=(2, 0))

        # Label del botón
        self._label = tk.Label(
            self._btn_frame,
            text=text,
            bg=theme.btn_bg,
            fg=theme.btn_fg,
            font=("Arial", 9),
            padx=12,
            pady=4,
            cursor="hand2",
        )
        self._label.pack(fill=tk.BOTH, expand=True)

        # Bindings
        for widget in [
            self._label,
            self._btn_frame,
            self._inner_frame,
            self._outer_frame,
        ]:
            widget.bind("<Button-1>", self._on_press)
            widget.bind("<ButtonRelease-1>", self._on_release)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_press(self, _event):
        if self._disabled:
            return
        self._pressed = True
        self._set_pressed_style()

    def _on_release(self, _event):
        if self._disabled:
            return
        if self._pressed and self._command:
            self._command()
        self._pressed = False
        self._set_normal_style()

    def _on_enter(self, _event):
        pass

    def _on_leave(self, _event):
        if self._pressed:
            self._pressed = False
            self._set_normal_style()

    def _set_pressed_style(self):
        """Estilo hundido cuando se presiona."""
        self._outer_frame.configure(bg=self._theme.dark_shadow)
        self._inner_frame.configure(bg=self._theme.highlight)
        self._btn_frame.configure(bg=self._theme.btn_pressed)
        self._label.configure(bg=self._theme.btn_pressed)

    def _set_normal_style(self):
        """Estilo normal elevado."""
        self._outer_frame.configure(bg=self._theme.highlight)
        self._inner_frame.configure(bg=self._theme.dark_shadow)
        self._btn_frame.configure(bg=self._theme.btn_bg)
        self._label.configure(bg=self._theme.btn_bg)

    def _set_disabled_style(self):
        """Estilo deshabilitado."""
        self._label.configure(fg=self._theme.shadow)
        self._label.configure(cursor="")

    def _set_enabled_style(self):
        """Estilo habilitado."""
        self._label.configure(fg=self._theme.btn_fg)
        self._label.configure(cursor="hand2")

    def configure(self, **kwargs):  # type: ignore[override]
        if "text" in kwargs:
            self._label.configure(text=kwargs.pop("text"))
        if "state" in kwargs:
            state = kwargs.pop("state")
            if state == tk.DISABLED:
                self._disabled = True
                self._set_disabled_style()
            else:
                self._disabled = False
                self._set_enabled_style()
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        super().configure(**kwargs)

    def __getitem__(self, key):
        if key == "state":
            return tk.DISABLED if self._disabled else tk.NORMAL
        return super().__getitem__(key)


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
            self.root.option_add("*Font", "Arial 9")
        except Exception:
            pass

        # Marco principal con borde 3D raised
        main_outer = tk.Frame(self.root, bg=self.theme.highlight)
        main_outer.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        main_inner = tk.Frame(main_outer, bg=self.theme.dark_shadow)
        main_inner.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 2))

        main_frame = tk.Frame(main_inner, bg=self.theme.bg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=(2, 0), pady=(2, 0))

        # Barra de título Windows 95
        title_bar = tk.Frame(main_frame, bg=self.theme.title_bg, height=24)
        title_bar.pack(fill=tk.X, padx=3, pady=(3, 0))
        title_bar.pack_propagate(False)

        title_label = tk.Label(
            title_bar,
            text="Transcriptor ASR (Español)",
            bg=self.theme.title_bg,
            fg=self.theme.title_fg,
            font=("Arial", 9, "bold"),
            anchor="center",
        )
        title_label.pack(fill=tk.BOTH, expand=True)

        # Contenedor principal
        container = tk.Frame(main_frame, bg=self.theme.bg)
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        subtitle = tk.Label(
            container,
            text="Sube un archivo .wav y obtén la transcripción.",
            bg=self.theme.bg,
            fg=self.theme.muted,
            font=("Arial", 9),
            anchor="center",
        )
        subtitle.pack(fill=tk.X, pady=(0, 12))

        action_row = tk.Frame(container, bg=self.theme.bg)
        action_row.pack(fill=tk.X)

        actions = tk.Frame(action_row, bg=self.theme.bg)
        actions.pack()

        self.btn_select = Win95Button(
            actions,
            self.theme,
            text="Seleccionar audio",
            command=self._on_select_audio,
        )
        self.btn_select.pack(side=tk.LEFT)

        self.btn_record = Win95Button(
            actions,
            self.theme,
            text="Grabar",
            command=self._on_start_recording,
        )
        self.btn_record.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_stop_record = Win95Button(
            actions,
            self.theme,
            text="Detener",
            command=self._on_stop_recording,
        )
        self.btn_stop_record.configure(state=tk.DISABLED)
        self.btn_stop_record.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_transcribe = Win95Button(
            actions,
            self.theme,
            text="Transcribir",
            command=self._on_transcribe,
        )
        self.btn_transcribe.configure(state=tk.DISABLED)
        self.btn_transcribe.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_copy = Win95Button(
            actions,
            self.theme,
            text="Copiar",
            command=self._on_copy,
        )
        self.btn_copy.configure(state=tk.DISABLED)
        self.btn_copy.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_play_pause = Win95Button(
            actions,
            self.theme,
            text="Reproducir",
            command=self._on_play_pause,
        )
        self.btn_play_pause.configure(state=tk.DISABLED)
        self.btn_play_pause.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_reset_audio = Win95Button(
            actions,
            self.theme,
            text="Reiniciar",
            command=self._on_reset_audio,
        )
        self.btn_reset_audio.configure(state=tk.DISABLED)
        self.btn_reset_audio.pack(side=tk.LEFT, padx=(10, 0))

        self.file_label = tk.Label(
            container,
            text="Archivo: (ninguno)",
            bg=self.theme.bg,
            fg=self.theme.muted,
            font=("Arial", 9),
            anchor="center",
        )
        self.file_label.pack(fill=tk.X, pady=(14, 6))

        self.status_var = tk.StringVar(value="Cargando modelo...")
        status = tk.Label(
            container,
            textvariable=self.status_var,
            bg=self.theme.bg,
            fg=self.theme.muted,
            font=("Arial", 9),
            anchor="center",
        )
        status.pack(fill=tk.X)

        # Text area con efecto sunken Windows 95
        text_outer = tk.Frame(container, bg=self.theme.dark_shadow)
        text_outer.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        text_inner = tk.Frame(text_outer, bg=self.theme.highlight)
        text_inner.pack(fill=tk.BOTH, expand=True, padx=(0, 2), pady=(0, 2))

        text_frame = tk.Frame(text_inner, bg=self.theme.input_bg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=(2, 0), pady=(2, 0))

        self.text = tk.Text(
            text_frame,
            wrap="word",
            bg=self.theme.input_bg,
            fg=self.theme.input_fg,
            insertbackground=self.theme.fg,
            relief="flat",
            padx=10,
            pady=8,
            font=("Arial", 9),
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
            filetypes=[("Audio WAV", "*.wav"), ("Todos los archivos", "*")],
        )
        if not filename:
            return

        path = Path(filename)
        if path.suffix.lower() != ".wav":
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
                    samplerate=self.sample_rate, channels=1, dtype="float32"
                ) as stream:
                    while self.is_recording:
                        audio_chunk, _ = stream.read(1024)
                        self.recorded_audio.append(audio_chunk)
            except Exception as exc:
                self.root.after(
                    0, lambda: self.status_var.set(f"Error grabando: {exc}")
                )
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
                    self.root.after(
                        0, lambda: self.status_var.set("No se grabó audio.")
                    )
                    self.root.after(0, self._reset_recording_state)
                    return

                # Concatenar todos los chunks de audio
                audio_data = np.concatenate(self.recorded_audio, axis=0)

                # Guardar como archivo WAV temporal
                from scipy.io import wavfile

                temp_dir = Path(tempfile.gettempdir())
                timestamp = threading.current_thread().name.split("-")[-1]
                wav_path = temp_dir / f"recording_{timestamp}.wav"

                # Convertir de float32 a int16 para WAV
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wavfile.write(str(wav_path), self.sample_rate, audio_int16)

                # Cargar el archivo grabado automáticamente
                self.root.after(0, lambda: self._load_recorded_audio(wav_path))

            except Exception as exc:
                self.root.after(
                    0, lambda: self.status_var.set(f"Error procesando grabación: {exc}")
                )
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
