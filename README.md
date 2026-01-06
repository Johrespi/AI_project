# ASR Tkinter GUI

Proyecto académico para la materia **Inteligencia Artificial** en **ESPOL**.

Interfaz gráfica estilo Windows 95 para transcribir audio **.wav** usando el checkpoint `best_model.pth`.

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

## Modelo

Descarga el archivo `best_model.pth` desde [Google Drive](https://drive.google.com/drive/folders/1FE2NKyTdQzrxlJ3O9EXLB9n-1z5cBAfc) y colócalo en la raíz del proyecto.

Por defecto la app intenta cargar (en este orden):

1. `best_model.pth`
2. `checkpoint_epoch_40.pth`

## Instalación del proyecto

```bash
uv sync
```

## Uso

```bash
uv run asr-gui
```

## Grabación de audio desde la interfaz

- Haz clic en **Grabar** para iniciar la grabación desde el micrófono.
- Haz clic en **Detener** para finalizar y cargar el audio grabado.
- El archivo grabado se puede reproducir y transcribir igual que un archivo `.wav` cargado manualmente.

## Notas

- Solo soporta `.wav`.
- El audio se reproduce con `pygame` (pausa/reanuda y suele ser más estable en Windows).
- El modelo se carga al iniciar la app y la transcripción corre en un thread para no congelar la UI.
- En Linux necesitas tener instalado Tkinter (paquete del sistema `python3-tk`).
- En Windows, Tkinter viene incluido normalmente con Python (python.org). Si no abre la ventana, revisa que tu instalación incluya Tcl/Tk.
