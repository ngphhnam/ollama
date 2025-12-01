# Script to run Llama service
# Llama service for IELTS speaking scoring using Ollama LLM

Write-Host "Starting Llama Service..." -ForegroundColor Green
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
    Write-Host "    ollama pull llama3.1:8b" -ForegroundColor Gray
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

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install dependencies if needed
if (-not (Test-Path "venv\Lib\site-packages\fastapi")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -q -r requirements.txt
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

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 11435 --reload

