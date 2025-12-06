# Script to run Llama service
# Llama service for IELTS speaking scoring using Ollama LLM

# Ensure we're in the correct directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "Starting Llama Service..." -ForegroundColor Green
Write-Host "Working directory: $(Get-Location)" -ForegroundColor Gray
Write-Host "  Service will run on port 11435" -ForegroundColor Yellow
Write-Host "  Connecting to Ollama server on port 11434" -ForegroundColor Yellow
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found! Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Try to check/start Ollama server automatically
Write-Host "Checking Ollama server..." -ForegroundColor Cyan
& "$PSScriptRoot\start-ollama.ps1"
$ollamaServerStarted = $LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null

if (-not $ollamaServerStarted) {
    Write-Host "Could not start Ollama server automatically." -ForegroundColor Yellow
    Write-Host "  Please start it manually:" -ForegroundColor Yellow
    Write-Host "    ollama serve" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  And make sure you have downloaded a model:" -ForegroundColor Yellow
    Write-Host "    ollama pull llama3.1:latest" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "Ollama server check completed" -ForegroundColor Green
    Write-Host ""
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Check virtual environment
Write-Host "Checking virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Virtual environment Python not found!" -ForegroundColor Red
    exit 1
}

# Install dependencies if needed
if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install dependencies!" -ForegroundColor Red
        exit 1
    }
}

# Set environment variables for Ollama (optional, defaults are used if not set)
$OLLAMA_BASE_URL = $env:OLLAMA_BASE_URL
$OLLAMA_MODEL = $env:OLLAMA_MODEL

if (-not $OLLAMA_BASE_URL) {
    $OLLAMA_BASE_URL = "http://localhost:11434"
    Write-Host "Using default OLLAMA_BASE_URL: $OLLAMA_BASE_URL" -ForegroundColor Gray
} else {
    Write-Host "Using OLLAMA_BASE_URL from environment: $OLLAMA_BASE_URL" -ForegroundColor Gray
}

if (-not $OLLAMA_MODEL) {
    # Default model is llama3.1:latest
    $OLLAMA_MODEL = "llama3.1:latest"
    Write-Host "Using default OLLAMA_MODEL: $OLLAMA_MODEL" -ForegroundColor Gray
} else {
    Write-Host "Using OLLAMA_MODEL from environment: $OLLAMA_MODEL" -ForegroundColor Gray
}

# Set environment variables
$env:OLLAMA_BASE_URL = $OLLAMA_BASE_URL
$env:OLLAMA_MODEL = $OLLAMA_MODEL

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  Port: 11435" -ForegroundColor White
Write-Host "  OLLAMA_BASE_URL = $env:OLLAMA_BASE_URL" -ForegroundColor White
Write-Host "  OLLAMA_MODEL = $env:OLLAMA_MODEL" -ForegroundColor White
Write-Host ""
Write-Host "Starting service on http://localhost:11435..." -ForegroundColor Green
Write-Host "  Note: Make sure Ollama server is running on $env:OLLAMA_BASE_URL" -ForegroundColor Gray
Write-Host "  If Ollama runs on different port, set: `$env:OLLAMA_BASE_URL='http://localhost:PORT'" -ForegroundColor Gray
Write-Host ""

# Run the service using Python from venv
$pythonExe = Join-Path $PWD "venv\Scripts\python.exe"
$uvicornExe = Join-Path $PWD "venv\Scripts\uvicorn.exe"

# Verify app.main exists
if (-not (Test-Path "app\main.py")) {
    Write-Host "Error: app\main.py not found!" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Check if uvicorn is available
if (Test-Path $uvicornExe) {
    Write-Host "Starting with uvicorn executable..." -ForegroundColor Gray
    & $uvicornExe app.main:app --host 0.0.0.0 --port 11435 --reload
} elseif (Test-Path $pythonExe) {
    Write-Host "Starting with python -m uvicorn..." -ForegroundColor Gray
    & $pythonExe -m uvicorn app.main:app --host 0.0.0.0 --port 11435 --reload
} else {
    Write-Host "Python executable not found in venv!" -ForegroundColor Red
    Write-Host "Trying system python..." -ForegroundColor Yellow
    python -m uvicorn app.main:app --host 0.0.0.0 --port 11435 --reload
}

if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Host "Service exited with error code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

