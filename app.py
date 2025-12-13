from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import Tk, filedialog
import tkinter as tk

from asr_model import AsrTranscriber, load_transcriber


@dataclass(frozen=True)
class Theme:
    bg: str = "#ffffff"
    fg: str = "#0a0a0a"
    muted: str = "#737373"
    border: str = "#e5e5e5"
    hover: str = "#f5f5f5"


class OutlineButton(tk.Button):
    def __init__(self, master: tk.Misc, theme: Theme, **kwargs):
        super().__init__(
            master,
            bg=theme.bg,
            fg=theme.fg,
            activebackground=theme.hover,
            activeforeground=theme.fg,
            relief="flat",
            bd=1,
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
            self.configure(bg=self._theme.hover)

    def _on_leave(self, _event):
        self.configure(bg=self._theme.bg)


class App:
    def __init__(self, root: Tk, checkpoint_path: Path):
        self.root = root
        self.theme = Theme()
        self.checkpoint_path = checkpoint_path

        self.transcriber: AsrTranscriber | None = None
        self.selected_audio_path: Path | None = None

        self._build_ui()
        self._start_model_load()

    def _build_ui(self) -> None:
        self.root.title("ASR (ES) - Minimal")
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
            anchor="w",
        )
        header.pack(fill=tk.X)

        subtitle = tk.Label(
            container,
            text="Sube un archivo .wav y obtén la transcripción.",
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="w",
        )
        subtitle.pack(fill=tk.X, pady=(6, 18))

        action_row = tk.Frame(container, bg=self.theme.bg)
        action_row.pack(fill=tk.X)

        self.btn_select = OutlineButton(
            action_row,
            self.theme,
            text="Seleccionar WAV",
            command=self._on_select_audio,
        )
        self.btn_select.pack(side=tk.LEFT)

        self.btn_transcribe = OutlineButton(
            action_row,
            self.theme,
            text="Transcribir",
            command=self._on_transcribe,
            state=tk.DISABLED,
        )
        self.btn_transcribe.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_copy = OutlineButton(
            action_row,
            self.theme,
            text="Copiar",
            command=self._on_copy,
            state=tk.DISABLED,
        )
        self.btn_copy.pack(side=tk.RIGHT)

        self.file_label = tk.Label(
            container,
            text="Archivo: (ninguno)",
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="w",
        )
        self.file_label.pack(fill=tk.X, pady=(14, 10))

        self.status_var = tk.StringVar(value="Cargando modelo…")
        status = tk.Label(
            container,
            textvariable=self.status_var,
            bg=self.theme.bg,
            fg=self.theme.muted,
            anchor="w",
        )
        status.pack(fill=tk.X)

        # Text area
        text_frame = tk.Frame(container, bg=self.theme.bg, highlightthickness=1, highlightbackground=self.theme.border)
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
        self._set_text("Selecciona un WAV para empezar.")

    def _set_text(self, value: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, value)
        self.text.configure(state=tk.DISABLED)

    def _start_model_load(self) -> None:
        self.btn_select.configure(state=tk.DISABLED)
        self.btn_transcribe.configure(state=tk.DISABLED)
        self.btn_copy.configure(state=tk.DISABLED)

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

    def _on_model_failed(self, message: str) -> None:
        self.status_var.set(f"Error cargando modelo: {message}")
        self.btn_select.configure(state=tk.NORMAL)

    def _on_select_audio(self) -> None:
        filename = filedialog.askopenfilename(
            title="Selecciona un archivo WAV",
            filetypes=[("Audio WAV", "*.wav"), ("Todos los archivos", "*")],
        )
        if not filename:
            return

        path = Path(filename)
        self.selected_audio_path = path
        self.file_label.configure(text=f"Archivo: {path.name}")
        self._set_text("")
        self.status_var.set("Listo para transcribir.")

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

    def _on_copy(self) -> None:
        text = self.text.get("1.0", tk.END).strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Transcripción copiada al clipboard.")


def main() -> None:
    root = Tk()

    checkpoint_path = Path(__file__).resolve().parent / "best_model.pth"
    if not checkpoint_path.exists():
        checkpoint_path = Path(__file__).resolve().parent / "checkpoint_epoch_40.pth"

    App(root, checkpoint_path)
    root.mainloop()


if __name__ == "__main__":
    main()
