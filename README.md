# ASR Tkinter GUI

Interfaz gráfica minimalista (blanco/negro) para transcribir audio **.wav** usando el checkpoint `best_model.pth`.

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
uv sync
```

## Ejecutar

```bash
uv run python app.py
```

## Modelo

Por defecto la app intenta cargar (en este orden):

- `best_model.pth`
- `checkpoint_epoch_40.pth`

Coloca el checkpoint en la raíz del proyecto.

## Notas

- Solo soporta `.wav`.
- El modelo se carga al iniciar la app y la transcripción corre en un thread para no congelar la UI.
- En Linux necesitas tener instalado Tkinter (paquete del sistema `python3-tk`).
- En Windows, Tkinter viene incluido normalmente con Python (python.org). Si no abre la ventana, revisa que tu instalación incluya Tcl/Tk.
