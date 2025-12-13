# ASR Tkinter GUI (WSL)

Interfaz gráfica minimalista (blanco/negro) para transcribir audio **.wav** usando el checkpoint `best_model.pth`.

## Requisitos

- WSL2 en Windows 10 + un X Server (por ejemplo VcXsrv)
- Python 3.10+
- `uv`

## Instalación (con uv)

```bash
uv venv
uv sync
```

## Ejecutar

### 1) Arranca tu X server en Windows

Ejemplo (VcXsrv): ejecutar `XLaunch` y habilitar *Disable access control*.

### 2) Configura DISPLAY en WSL

En la misma terminal donde vas a ejecutar la app:

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
export LIBGL_ALWAYS_INDIRECT=1
```

### 3) Ejecuta la app

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
