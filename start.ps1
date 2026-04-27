$ErrorActionPreference = "Stop"

$pythonCmd = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & py -3 --version *> $null
    $ErrorActionPreference = $previousErrorActionPreference
    if ($LASTEXITCODE -eq 0) {
        $pythonCmd = @("py", "-3")
    }
}

if (-not $pythonCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python --version *> $null
    $ErrorActionPreference = $previousErrorActionPreference
    if ($LASTEXITCODE -eq 0) {
        $pythonCmd = @("python")
    }
}

if (-not $pythonCmd) {
    Write-Host "Python non trovato."
    Write-Host "Installa Python 3.11 o superiore con:"
    Write-Host "winget install -e --id Python.Python.3.12"
    Write-Host ""
    Write-Host "Poi chiudi e riapri il terminale e rilancia:"
    Write-Host ".\start.bat"
    exit 1
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtualenv non trovato. Creazione in corso..."
    if ($pythonCmd.Count -gt 1) {
        & $pythonCmd[0] $pythonCmd[1..($pythonCmd.Count - 1)] -m venv .venv
    } else {
        & $pythonCmd[0] -m venv .venv
    }
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
