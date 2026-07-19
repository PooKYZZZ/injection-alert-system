[CmdletBinding()]
param(
    [string]$EnvFile = ".env",
    [switch]$Build,
    [switch]$Reset,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = if ([IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $repoRoot $EnvFile
}

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Hosted startup requires a persistent env file at '$envPath'. Copy .env.example to .env and set the runtime values."
}

function Read-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed.StartsWith("export ")) {
            $trimmed = $trimmed.Substring(7).TrimStart()
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

function Assert-NarrowTrustedPeer {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "HOSTED_WAF_TRUSTED_PEER is required in the persistent env file; refusing to render hosted real-IP trust without it."
    }

    foreach ($entry in $Value.Split(",")) {
        $candidate = $entry.Trim()
        $parts = $candidate.Split("/", 2)
        if ($parts.Count -ne 2 -or [string]::IsNullOrWhiteSpace($parts[0])) {
            throw "HOSTED_WAF_TRUSTED_PEER must contain an IP address with an explicit CIDR prefix, such as 172.18.0.1/32."
        }

        try {
            $address = [Net.IPAddress]::Parse($parts[0])
        } catch {
            throw "HOSTED_WAF_TRUSTED_PEER contains an invalid IP address."
        }

        $prefix = 0
        if (-not [int]::TryParse($parts[1], [ref]$prefix)) {
            throw "HOSTED_WAF_TRUSTED_PEER contains an invalid CIDR prefix."
        }

        $maximum = if ($address.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork) { 32 } else { 128 }
        $minimum = if ($maximum -eq 32) { 24 } else { 64 }
        if ($prefix -lt $minimum -or $prefix -gt $maximum) {
            throw "HOSTED_WAF_TRUSTED_PEER must remain narrow (IPv4 /24-/32 or IPv6 /64-/128)."
        }
    }

    if ($Value -match "(?i)(^|,\s*)(0\.0\.0\.0/0|::/0|10\.0\.0\.0/8|172\.16\.0\.0/12|192\.168\.0\.0/16)(\s*,|$)") {
        throw "HOSTED_WAF_TRUSTED_PEER is too broad; refusing to trust an entire world or private address range."
    }
}

$trustedPeer = Read-DotEnvValue -Path $envPath -Name "HOSTED_WAF_TRUSTED_PEER"
$verificationValue = Read-DotEnvValue -Path $envPath -Name "WAF_SOURCE_VERIFICATION_MODE"
$verificationMode = if ($null -eq $verificationValue) { "" } else { $verificationValue.Trim().ToLowerInvariant() }

Assert-NarrowTrustedPeer -Value $trustedPeer
if ($verificationMode -ne "unverified") {
    throw "Hosted startup requires WAF_SOURCE_VERIFICATION_MODE=unverified; do not enable VERIFIED mode from this launcher."
}

# Make the persistent file authoritative over stale values inherited from an old shell.
$env:HOSTED_WAF_TRUSTED_PEER = $trustedPeer
$env:WAF_SOURCE_VERIFICATION_MODE = "unverified"

if ($ValidateOnly) {
    Write-Host "Hosted configuration valid: trusted peer $trustedPeer; verification mode unverified."
    exit 0
}

Push-Location $repoRoot
try {
    $composeArgs = @(
        "compose",
        "--env-file", $envPath,
        "-p", "injection-alert-system",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.demo-target.yml",
        "-f", "docker-compose.hosted-target.yml",
        "--profile", "demo-target"
    )
    $technicalComposeArgs = @(
        "compose",
        "--env-file", $envPath,
        "-p", "injection-alert-system",
        "-f", "docker-compose.yml",
        "-f", "docker-compose.demo-target.yml",
        "--profile", "technical-waf"
    )

    # Hosted mode must not leave a stale technical 8088 pair running from an
    # earlier profile. Remove only those two containers; volumes are untouched.
    & docker @technicalComposeArgs rm --stop --force modsecurity bridge
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose cleanup of the technical WAF pair failed with exit code $LASTEXITCODE."
    }

    if ($Reset) {
        Write-Host "Stopping the hosted target stack (volumes are preserved)..."
        & docker @composeArgs down --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose shutdown failed with exit code $LASTEXITCODE."
        }
    }

    $upArgs = $composeArgs + @("up", "-d", "--force-recreate")
    if ($Build) {
        $upArgs += "--build"
    }

    Write-Host "Starting hosted target with the persistent env file..."
    & docker @upArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose hosted startup failed with exit code $LASTEXITCODE."
    }

    & docker @composeArgs ps
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose hosted status check failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
