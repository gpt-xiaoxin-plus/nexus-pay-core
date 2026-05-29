$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$envFile = Join-Path $root "config\runtime.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

$opai = Join-Path $root ".venv\Scripts\opai.exe"
if (-not (Test-Path $opai)) {
    $opai = Join-Path $root ".venv\bin\opai"
}
if (-not (Test-Path $opai)) {
    throw "Local virtualenv is missing. Run ./setup.sh on macOS/Linux or install the package in .venv first."
}
if (-not $env:OPAI_HEROSMS_API_KEY -and -not $env:OPAI_HEROSMS_API_KEY_FILE) {
    throw "Missing Hero-SMS API key. Set OPAI_HEROSMS_API_KEY or OPAI_HEROSMS_API_KEY_FILE in config/runtime.env."
}

& $opai worker run @args
