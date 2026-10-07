[CmdletBinding()]
param(
    [switch]$Reset,
    [switch]$NoBuild,
    [switch]$Collection
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".local/env/.env"
Push-Location $repoRoot
try {
    $composeFiles = @(
        "-f", "docker/compose/base.yml",
        "-f", "docker/compose/overlays/local.yml",
        "-f", "docker/compose/overlays/demo-target.yml"
    )
    if ($Collection) {
        $composeFiles += @(
            "-f", "docker/compose/overlays/demo-target.collection.yml"
        )
    }

    $composeArgs = @(
        "compose",
        "--project-directory", $repoRoot,
        "--env-file", $envPath,
        "-p", "injection-alert-system"
    ) + $composeFiles + @(
        "--profile", "technical-waf",
        "--profile", "demo-target"
    )

    if ($Reset) {
        Write-Host "Stopping the existing full local stack (volumes are preserved)..."
        & docker @composeArgs down --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose shutdown failed with exit code $LASTEXITCODE."
        }
    }

    $collectionDescription = if ($Collection) { " with collection audit logging" } else { "" }
    Write-Host "Building and starting backend, frontend, technical WAF, bridge, and demo target$collectionDescription..."
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
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose status check failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
