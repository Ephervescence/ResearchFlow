param(
  [string]$BackendUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$startedBackend = $null

function Test-TcpPort {
  param(
    [string]$HostName,
    [int]$Port,
    [int]$TimeoutMs = 2000
  )

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $connection = $client.BeginConnect($HostName, $Port, $null, $null)
    if (-not $connection.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
      return $false
    }
    $client.EndConnect($connection)
    return $true
  }
  catch {
    return $false
  }
  finally {
    $client.Close()
  }
}

Push-Location "$PSScriptRoot\..\backend"
try {
  if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend/.env from .env.example"
  }

  Write-Host "Checking Python package imports..."
  python -c "from app.main import app; print(app.title)"

  if (-not (Test-TcpPort -HostName "127.0.0.1" -Port 5432)) {
    throw "PostgreSQL is not reachable at 127.0.0.1:5432. Start PostgreSQL and ensure backend/.env DATABASE_URL points to the running database."
  }

  Write-Host "Running Alembic migrations..."
  alembic upgrade head

  Write-Host "Checking database schema..."
  python scripts/check_database.py

  try {
    Invoke-WebRequest -Uri "$BackendUrl/health" -UseBasicParsing | Out-Null
    Write-Host "Backend is already running at $BackendUrl"
  }
  catch {
    Write-Host "Starting backend at $BackendUrl ..."
    $startedBackend = Start-Process -FilePath "python" -ArgumentList @(
      "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"
    ) -WorkingDirectory (Get-Location) -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 5
  }

  Write-Host "Running API smoke test against $BackendUrl ..."
  python scripts/smoke_research.py --base-url $BackendUrl
}
finally {
  if ($null -ne $startedBackend -and -not $startedBackend.HasExited) {
    Stop-Process -Id $startedBackend.Id -Force
    Write-Host "Stopped backend process $($startedBackend.Id)"
  }
  Pop-Location
}
