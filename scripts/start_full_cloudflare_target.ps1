[CmdletBinding()]
param(
    [string]$PortalContext = "E:\AI\land-records-portal",
    [string]$CloudflaredTokenFile,
    [switch]$Collection,
    [switch]$Reset,
    [switch]$NoBuild,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot ".env"

function Get-DotEnvValue {
    param([string]$Name)

    foreach ($line in Get-Content -LiteralPath $envPath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed -match "^(?<key>[A-Za-z_][A-Za-z0-9_]*)=(?<value>.*)$" -and $Matches.key -eq $Name) {
            $value = $Matches.value.Trim()
            if (($value.StartsWith([char]34) -and $value.EndsWith([char]34)) -or
                ($value.StartsWith([char]39) -and $value.EndsWith([char]39))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            return $value
        }
    }

    return $null
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found on PATH. Start Docker Desktop and retry."
}

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Required environment file not found: $envPath"
}

if (-not (Test-Path -LiteralPath $PortalContext -PathType Container)) {
    throw "Portal directory not found: $PortalContext"
}

$configuredTokenFile = if ([string]::IsNullOrWhiteSpace($CloudflaredTokenFile)) {
    Get-DotEnvValue -Name "CLOUDFLARED_TARGET_TOKEN_FILE"
} else {
    $CloudflaredTokenFile
}

if ([string]::IsNullOrWhiteSpace($configuredTokenFile)) {
    throw "CLOUDFLARED_TARGET_TOKEN_FILE is not configured in .env and no token path was supplied."
}

if (-not [IO.Path]::IsPathRooted($configuredTokenFile)) {
    $configuredTokenFile = Join-Path $repoRoot $configuredTokenFile
}

if (-not (Test-Path -LiteralPath $configuredTokenFile -PathType Leaf)) {
    throw "Cloudflare token file configured for Docker Compose was not found."
}

# These are non-secret Compose inputs. Secret values remain in the ignored .env
# and in the token file outside the repository.
$env:DEMO_PORTAL_CONTEXT = $PortalContext
$env:CLOUDFLARED_TARGET_TOKEN_FILE = $configuredTokenFile
$env:WAF_SOURCE_VERIFICATION_MODE = "unverified"

Push-Location $repoRoot
try {
    $composeArgs = @(
        "compose",
        "--env-file", $envPath,
        "-p", "injection-alert-system",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.demo-target.yml",
        "-f", "docker-compose.target-cloudflare.yml",
        "-f", "docker-compose.app-cloudflare.yml"
    )

    if ($Collection) {
        $composeArgs += @("-f", "docker-compose.demo-target.collection.yml")
    }

    $composeArgs += @(
        "--profile", "demo-target",
        "--profile", "target-cloudflare"
    )

    Write-Host "Validating the merged Cloudflare target configuration..."
    & docker @composeArgs config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose configuration validation failed with exit code $LASTEXITCODE."
    }

    if ($ValidateOnly) {
        Write-Host "Configuration is valid. No containers were started."
        exit 0
    }

    if ($Reset) {
        Write-Host "Stopping the existing target stack; volumes are preserved..."
        & docker @composeArgs down --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose shutdown failed with exit code $LASTEXITCODE."
        }
    }

    $upArgs = $composeArgs + @("up", "-d", "--force-recreate")
    if (-not $NoBuild) {
        $upArgs += "--build"
    }

    Write-Host "Starting backend, frontend, demo portal, target WAF, bridge, and cloudflared..."
    & docker @upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose startup failed with exit code $LASTEXITCODE."
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
