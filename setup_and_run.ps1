param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 4200,
  [switch]$SkipPythonInstall,
  [switch]$SkipNodeInstall
)

$ErrorActionPreference = "Stop"

function Test-Command {
  param([string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-NativeCommand {
  # Runs a native exe (winget/pip/npm) with its normal stdout/stderr visible.
  # Windows PowerShell 5.1 treats each stderr line from a native command as an
  # error record while $ErrorActionPreference = "Stop" is in effect, which
  # aborts the script even when the command actually succeeds (e.g. npm's
  # deprecation warnings, pip's notices). Run with "Continue" instead and
  # check the real exit code ourselves.
  #
  # Network-bound steps (npm/pip/winget hitting a registry) occasionally fail
  # with a transient error (e.g. a brief DNS hiccup reported as Node's
  # UV_EAI_FAMILY / exit code -4082) that succeeds immediately on retry, so
  # retry a few times with a short backoff before giving up for good.
  param(
    [Parameter(Mandatory = $true)][ScriptBlock]$ScriptBlock,
    [Parameter(Mandatory = $true)][string]$FailureMessage,
    [int]$Retries = 2
  )
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    for ($attempt = 1; $attempt -le ($Retries + 1); $attempt++) {
      & $ScriptBlock | Out-Host
      if ($LASTEXITCODE -eq 0) { return }
      if ($attempt -le $Retries) {
        Write-Host "$FailureMessage (exit code $LASTEXITCODE) - retrying ($attempt/$Retries)..."
        Start-Sleep -Seconds 3
      }
    }
  } finally {
    $ErrorActionPreference = $previous
  }
  throw "$FailureMessage (exit code $LASTEXITCODE) after $($Retries + 1) attempts"
}

function Ensure-Winget {
  if (-not (Test-Command "winget")) {
    throw "winget is not available. Install Python and Node.js manually, then re-run this script."
  }
}

function Ensure-Python {
  if (Test-Command "python") { return }
  if ($SkipPythonInstall) {
    throw "Python is not installed or not on PATH."
  }
  Ensure-Winget
  Write-Host "Installing Python via winget..."
  Invoke-NativeCommand -FailureMessage "winget install of Python failed" -ScriptBlock {
    winget install -e --id Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements
  }
  if (-not (Test-Command "python")) {
    throw "Python installation completed but python is still not on PATH. Restart PowerShell and try again."
  }
}

function Test-NodeVersionOk {
  param([string]$VersionString)
  # Mirrors frontend/package.json "engines": Angular 22 requires one of these ranges.
  try {
    $parts = $VersionString.TrimStart("v").Split(".")
    $major = [int]$parts[0]; $minor = [int]$parts[1]; $patch = [int]$parts[2]
  } catch {
    return $false
  }
  if ($major -eq 22 -and (($minor -gt 22) -or ($minor -eq 22 -and $patch -ge 3))) { return $true }
  if ($major -eq 24 -and $minor -ge 15) { return $true }
  if ($major -ge 26) { return $true }
  return $false
}

function Write-NodeUpgradeHelp {
  Write-Host "Required Node.js version: ^22.22.3, ^24.15.0, or >=26.0.0 (Angular 22's minimum)."
  Write-Host "winget's Node.js LTS package may not satisfy this yet."
  Write-Host "Recommended: install via nvm-windows (https://github.com/coreybutler/nvm-windows)"
  Write-Host "  nvm install 22.23.2"
  Write-Host "  nvm use 22.23.2"
  Write-Host "Or download a binary directly from https://nodejs.org/."
}

function Ensure-Node {
  if ((Test-Command "node") -and (Test-Command "npm")) {
    $currentVersion = (node --version).Trim()
    if (Test-NodeVersionOk $currentVersion) { return }
    Write-Host "Found Node.js $currentVersion, but this project requires a newer version."
    Write-NodeUpgradeHelp
    throw "Incompatible Node.js version: $currentVersion"
  }
  if ($SkipNodeInstall) {
    Write-NodeUpgradeHelp
    throw "Node.js/npm is not installed or not on PATH."
  }
  Ensure-Winget
  Write-Host "Installing Node.js LTS via winget..."
  Invoke-NativeCommand -FailureMessage "winget install of Node.js failed" -ScriptBlock {
    winget install -e --id OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
  }
  if (-not ((Test-Command "node") -and (Test-Command "npm"))) {
    throw "Node.js installation completed but node/npm is still not on PATH. Restart PowerShell and try again."
  }
  $installedVersion = (node --version).Trim()
  if (-not (Test-NodeVersionOk $installedVersion)) {
    Write-Host "winget installed Node.js $installedVersion, which is too old for this project."
    Write-NodeUpgradeHelp
    throw "Incompatible Node.js version: $installedVersion"
  }
}

function Stop-ProcessOnPort {
  # Frees a TCP port before we try to bind it, so re-running this script doesn't
  # hit "port already in use" (uvicorn) or the interactive "use a different
  # port? (Y/n)" prompt (ng serve) from a server left running by a previous run.
  #
  # uvicorn --reload runs as a watcher process that spawns the actual server as
  # a child. Killing only the watcher orphans a live child still holding the
  # port, so walk the full parent/child chain for every PID found on the port.
  param([int]$Port)

  $seen = New-Object System.Collections.Generic.HashSet[int]
  $toKill = New-Object System.Collections.Generic.Queue[int]

  $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($ownerPid in $owners) { $toKill.Enqueue($ownerPid) }

  $allProcesses = Get-CimInstance Win32_Process
  while ($toKill.Count -gt 0) {
    $currentPid = $toKill.Dequeue()
    if (-not $seen.Add($currentPid)) { continue }
    foreach ($child in ($allProcesses | Where-Object { $_.ParentProcessId -eq $currentPid })) {
      $toKill.Enqueue($child.ProcessId)
    }
  }

  if ($seen.Count -eq 0) { return }
  Write-Host "Port $Port is in use; stopping process(es): $($seen -join ', ')"
  foreach ($targetPid in $seen) {
    Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 1
}

function Get-TerminalHost {
  # Prefer Windows PowerShell if present; fall back to PowerShell 7+ (pwsh).
  if (Test-Command "powershell") { return "powershell" }
  if (Test-Command "pwsh") { return "pwsh" }
  throw "Neither 'powershell' nor 'pwsh' was found on PATH. Cannot launch the backend/frontend in new windows."
}

function New-RandomSecret {
  # RandomNumberGenerator]::Fill() is .NET Core/5+ only and doesn't exist on the
  # .NET Framework runtime that Windows PowerShell 5.1 uses. RNGCryptoServiceProvider
  # works on both 5.1 and pwsh 7+.
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
  try {
    $rng.GetBytes($bytes)
  } finally {
    $rng.Dispose()
  }
  return ([System.BitConverter]::ToString($bytes)).Replace("-", "").ToLower()
}

function Ensure-BackendEnv {
  param([string]$EnvPath)
  if (Test-Path $EnvPath) { return }
  Write-Host "Creating backend/.env with a generated JWT secret (fill in GOOGLE_API_KEY manually)..."
  $secret = New-RandomSecret
  @(
    "GOOGLE_API_KEY=",
    "JWT_SECRET_KEY=$secret"
  ) -join "`n" | Set-Content -Path $EnvPath -Encoding utf8
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
# Use backend/venv so this matches the manual setup documented in README.md
$VenvDir = Join-Path $BackendDir "venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

Ensure-Python
Ensure-Node

if (-not (Test-Path $BackendDir)) { throw "backend folder not found: $BackendDir" }
if (-not (Test-Path $FrontendDir)) { throw "frontend folder not found: $FrontendDir" }

Write-Host "Setting up Python environment..."
if (-not (Test-Path $PythonExe)) {
  Invoke-NativeCommand -FailureMessage "python -m venv failed" -ScriptBlock {
    python -m venv $VenvDir
  }
}

Invoke-NativeCommand -FailureMessage "pip upgrade failed" -ScriptBlock {
  & $PythonExe -m pip install --upgrade pip
}
Invoke-NativeCommand -FailureMessage "pip install of backend requirements failed" -ScriptBlock {
  & $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

Write-Host "Setting up frontend dependencies..."
Push-Location $FrontendDir
try {
  if (Test-Path (Join-Path $FrontendDir "package-lock.json")) {
    Invoke-NativeCommand -FailureMessage "npm ci failed" -ScriptBlock { npm ci }
  } else {
    Invoke-NativeCommand -FailureMessage "npm install failed" -ScriptBlock { npm install }
  }
} finally {
  Pop-Location
}

$BackendEnvPath = Join-Path $BackendDir ".env"
Ensure-BackendEnv -EnvPath $BackendEnvPath
$envContent = Get-Content $BackendEnvPath -Raw
if ($envContent -notmatch "GOOGLE_API_KEY=\S") {
  Write-Host "Warning: GOOGLE_API_KEY is empty in backend/.env. The AI tutor chat will not work until you set it."
}

$TerminalHost = Get-TerminalHost
$BackendCmd = "& `"$PythonExe`" -m uvicorn app.main:app --reload --host 0.0.0.0 --port $BackendPort"
$FrontendCmd = "npm start -- --port $FrontendPort"

Stop-ProcessOnPort -Port $BackendPort
Stop-ProcessOnPort -Port $FrontendPort

Write-Host "Starting backend..."
Start-Process -FilePath $TerminalHost -WorkingDirectory $BackendDir -ArgumentList @("-NoExit", "-Command", $BackendCmd) | Out-Null

Write-Host "Starting frontend..."
Start-Process -FilePath $TerminalHost -WorkingDirectory $FrontendDir -ArgumentList @("-NoExit", "-Command", $FrontendCmd) | Out-Null

Write-Host "Backend: http://localhost:$BackendPort/docs"
Write-Host "Frontend: http://localhost:$FrontendPort"
