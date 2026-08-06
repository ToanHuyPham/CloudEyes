[CmdletBinding()]
param(
    [string]$PythonVersion = "3.11",
    [string]$VenvPath = ".venv",
    [switch]$RuntimeOnly,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Command)
    if ($DryRun) { Write-Host "+ $($Command -join ' ')"; return }
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $($Command -join ' ')" }
}

if (-not (Test-Path "pyproject.toml")) {
    throw "Run this script from the CloudEyes repository root."
}

$python = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        try {
            if ($candidate -eq "py") {
                & py "-$PythonVersion" -c "import sys; assert sys.version_info >= (3,11)"
                if ($LASTEXITCODE -eq 0) { $python = @("py", "-$PythonVersion"); break }
            } else {
                & $candidate -c "import sys; assert sys.version_info >= (3,11)"
                if ($LASTEXITCODE -eq 0) { $python = @($candidate); break }
            }
        } catch { }
    }
}

if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Python 3.11+ not found and winget is unavailable. Install Python manually."
    }
    Invoke-Step winget install --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements
    $python = @("py", "-3.11")
}

Invoke-Step @python -m venv $VenvPath
$venvPython = Join-Path $VenvPath "Scripts\python.exe"
Invoke-Step $venvPython -m pip install --upgrade pip
if ($RuntimeOnly) {
    Invoke-Step $venvPython -m pip install -e .
} else {
    Invoke-Step $venvPython -m pip install -e ".[dev]"
}

Write-Host "[CloudEyes] Installation complete."
Write-Host "Activate with: $VenvPath\Scripts\Activate.ps1"
