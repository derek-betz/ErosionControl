[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Ensure-Winget {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required. Install App Installer from the Microsoft Store."
    }
}

function Install-Python {
    Write-Host "Installing Python 3.12 via winget..."
    winget install -e --id Python.Python.3.12 --source winget --accept-source-agreements --accept-package-agreements
}

function Get-Python312 {
    $pythonExe = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $pythonExe) {
        return $null
    }
    return $pythonExe.Trim()
}

function Ensure-Python {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        Ensure-Winget
        Install-Python
    }
    $pythonExe = Get-Python312
    if (-not $pythonExe) {
        Ensure-Winget
        Install-Python
        $pythonExe = Get-Python312
    }
    if (-not $pythonExe) {
        throw "Python 3.12 is not available after install."
    }
    return $pythonExe
}

function Ensure-PythonPath {
    param([string]$PythonExe)

    $pythonDir = Split-Path $PythonExe
    $pythonScripts = Join-Path $pythonDir "Scripts"
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $entries = @()
    if ($userPath) {
        $entries = $userPath -split ';' | Where-Object { $_ }
    }
    $entries = $entries | Where-Object { $_ -notin @($pythonDir, $pythonScripts) }
    $newEntries = @($pythonDir, $pythonScripts) + $entries
    [Environment]::SetEnvironmentVariable("Path", ($newEntries -join ';'), "User")

    $currentEntries = $env:PATH -split ';' | Where-Object { $_ }
    $currentEntries = $currentEntries | Where-Object { $_ -notin @($pythonDir, $pythonScripts) }
    $env:PATH = (@($pythonDir, $pythonScripts) + $currentEntries) -join ';'
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $repoRoot
try {
    $pythonExe = Ensure-Python
    Ensure-PythonPath -PythonExe $pythonExe

    Write-Host "Installing development dependencies..."
    & $pythonExe -m pip install --upgrade pip
    & $pythonExe -m pip install -e ".[dev]"

    if (-not $SkipTests) {
        Write-Host "Running tests..."
        & $pythonExe scripts\run_tests.py
    } else {
        Write-Host "Skipping tests."
    }

    & $pythonExe --version
} finally {
    Pop-Location
}
