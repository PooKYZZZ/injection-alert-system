[CmdletBinding()]
param(
    [switch]$Reset,
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    $composeArgs = @(
        "compose",
        "-p", "injection-alert-system",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.demo-target.yml",
        "--profile", "technical-waf",
        "--profile", "demo-target"
    )

    if ($Reset) {
        Write-Host "Stopping the existing full local stack (volumes are preserved)..."
        & docker @composeArgs down --remove-orphans
    }

    Write-Host "Building and starting backend, frontend, technical WAF, bridge, and demo target..."
    $upArgs = $composeArgs + @("up", "-d", "--force-recreate")
    if (-not $NoBuild) {
        $upArgs += "--build"
    }
    & docker @upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed with exit code $LASTEXITCODE."
    }

    Write-Host "`nRunning services:"
    & docker @composeArgs ps
}
finally {
    Pop-Location
}
