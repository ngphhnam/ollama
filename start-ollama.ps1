# Script to check and start Ollama server
# This script will check if Ollama is running and start it if needed

$OLLAMA_PORT = 11434
$OLLAMA_HOST = $env:OLLAMA_HOST

# Use default if not set
if (-not $OLLAMA_HOST) {
    $OLLAMA_HOST = "127.0.0.1:$OLLAMA_PORT"
}

Write-Host "Checking Ollama server..." -ForegroundColor Cyan

# Check if Ollama is installed
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "Ollama found: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "Ollama is not installed!" -ForegroundColor Red
    Write-Host "Please install Ollama from: https://ollama.ai/download" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation, Ollama usually runs automatically." -ForegroundColor Gray
    Write-Host "If not, run: ollama serve" -ForegroundColor Gray
    exit 1
}

# Check if Ollama server is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$OLLAMA_PORT/api/tags" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "Ollama server is already running on port $OLLAMA_PORT" -ForegroundColor Green
        
        # Check if model is available
        Write-Host "Checking for models..." -ForegroundColor Cyan
        $modelsResponse = Invoke-WebRequest -Uri "http://localhost:$OLLAMA_PORT/api/tags" -UseBasicParsing
        $models = $modelsResponse.Content | ConvertFrom-Json
        
        if ($models.models -and $models.models.Count -gt 0) {
            Write-Host "Found models:" -ForegroundColor Green
            foreach ($model in $models.models) {
                Write-Host "  - $($model.name)" -ForegroundColor White
            }
        } else {
            Write-Host "No models found. Please download a model:" -ForegroundColor Yellow
            Write-Host "  ollama pull llama3.1:8b" -ForegroundColor Gray
        }
        
        exit 0
    }
} catch {
    # Server not running, continue to start it
    Write-Host "Ollama server is not running. Starting..." -ForegroundColor Yellow
}

# Start Ollama server
Write-Host "Starting Ollama server on $OLLAMA_HOST..." -ForegroundColor Yellow
Write-Host "  This will open in a new window" -ForegroundColor Gray
Write-Host ""

# Set OLLAMA_HOST environment variable
$env:OLLAMA_HOST = $OLLAMA_HOST

# Start Ollama in a new window
Start-Process ollama -ArgumentList "serve" -WindowStyle Normal

Write-Host "Waiting for Ollama server to start (this may take 20-30 seconds)..." -ForegroundColor Gray

# Wait and retry connection (Ollama can take longer to start)
$maxRetries = 10
$retryDelay = 3
$serverReady = $false

for ($i = 1; $i -le $maxRetries; $i++) {
    Start-Sleep -Seconds $retryDelay
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$OLLAMA_PORT/api/tags" -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Ollama server is running successfully!" -ForegroundColor Green
            $serverReady = $true
            break
        }
    } catch {
        if ($i -lt $maxRetries) {
            Write-Host "  Attempt ${i}/${maxRetries}: Server not ready yet, waiting..." -ForegroundColor Gray
        }
    }
}

if (-not $serverReady) {
    Write-Host "Ollama server is starting but not ready yet." -ForegroundColor Yellow
    Write-Host "  The Python service will automatically retry connection when it starts." -ForegroundColor Gray
    Write-Host "  You can also check Ollama status manually:" -ForegroundColor Gray
    Write-Host "    ollama list" -ForegroundColor White
    Write-Host ""
} else {
    # Check for models
    Write-Host ""
    Write-Host "Checking for models..." -ForegroundColor Cyan
    try {
        $modelsResponse = Invoke-WebRequest -Uri "http://localhost:$OLLAMA_PORT/api/tags" -UseBasicParsing
        $models = $modelsResponse.Content | ConvertFrom-Json
        
        if ($models.models -and $models.models.Count -gt 0) {
            Write-Host "Available models:" -ForegroundColor Green
            foreach ($model in $models.models) {
                Write-Host "  - $($model.name)" -ForegroundColor White
            }
        } else {
            Write-Host "No models found. Please download a model:" -ForegroundColor Yellow
            Write-Host "  ollama pull llama3.1:8b" -ForegroundColor Gray
            Write-Host "  or" -ForegroundColor Gray
            Write-Host "  ollama pull llama3.1:latest" -ForegroundColor Gray
        }
    } catch {
        Write-Host "Could not check models. Server might still be initializing." -ForegroundColor Yellow
    }
}

