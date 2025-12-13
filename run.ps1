$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "uv no está instalado o no está en PATH." -ForegroundColor Red
  Write-Host "Instálalo con: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Yellow
  exit 1
}

uv run python app.py
