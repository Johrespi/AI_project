# ASR Tkinter GUI

Proyecto académico para la materia **Inteligencia Artificial** en **ESPOL**.

Interfaz gráfica minimalista (blanco/negro) para transcribir audio **.wav** usando el checkpoint `best_model.pth`.

Incluye función para **grabar audio desde la interfaz** y transcribirlo directamente.

## Requisitos

- Python 3.10+
- `uv`

## Instalación de uv

- Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`
- Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`

Reabre la terminal y verifica con:

```bash
uv --version
```


## Instalación del proyecto (con uv)

```bash
uv venv
uv pip install sounddevice scipy
uv sync
```

> **Nota:** Si tienes problemas con `uv sync` o `uv pip` en VS Code, ejecuta los comandos anteriores directamente desde PowerShell fuera de VS Code.


## Ejecutar

```bash
uv run python app.py
```

## Modelo

Por defecto la app intenta cargar (en este orden):

- `best_model.pth`
- `checkpoint_epoch_40.pth`

Coloca el checkpoint en la raíz del proyecto.

## Grabación de audio desde la interfaz

- Haz clic en **🎤 Grabar** para iniciar la grabación desde el micrófono.
- Haz clic en **⏹ Detener** para finalizar y cargar el audio grabado.
- El archivo grabado se puede reproducir y transcribir igual que un archivo `.wav` cargado manualmente.

## Notas

- Solo soporta `.wav`.
- El audio se reproduce con `pygame` (pausa/reanuda y suele ser más estable en Windows).
- El modelo se carga al iniciar la app y la transcripción corre en un thread para no congelar la UI.
- En Linux necesitas tener instalado Tkinter (paquete del sistema `python3-tk`).
- En Windows, Tkinter viene incluido normalmente con Python (python.org). Si no abre la ventana, revisa que tu instalación incluya Tcl/Tk.
