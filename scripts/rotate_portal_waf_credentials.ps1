[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

if (-not $Apply) {
    throw 'No changes made. Pass -Apply to rotate the local WAF bridge credentials.'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw 'The ignored repository .env file is required; no credentials were changed.'
}

$credentialNames = @('WAF_INGEST_API_KEY', 'WAF_AUDIT_EVIDENCE_KEY')

function Set-RestrictedSecretFileAcl {
    param([Parameter(Mandatory = $true)][string]$Path)

    $currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $currentUserAce = '*' + $currentSid + ':(F)'
    & icacls.exe $Path /inheritance:r /Q | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not remove inherited permissions from a credential file.'
    }
    & icacls.exe $Path /grant:r $currentUserAce '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' /Q | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not apply the restricted credential-file permissions.'
    }

    $acl = Get-Acl -LiteralPath $Path
    $sddl = $acl.Sddl
    $userFullControl = '\(A;;FA;;;' + [regex]::Escape($currentSid) + '\)'
    if (-not $acl.AreAccessRulesProtected -or
        $sddl -notmatch $userFullControl -or
        $sddl -notmatch '\(A;;FA;;;BA\)' -or
        $sddl -notmatch '\(A;;FA;;;SY\)' -or
        $sddl -match '\(A;;[^;]*;;;AU\)|\(A;;[^;]*;;;BU\)') {
        throw 'Credential-file ACL verification failed.'
    }
}

$originalBytes = [System.IO.File]::ReadAllBytes($envPath)
$hasUtf8Bom = $originalBytes.Length -ge 3 -and
    $originalBytes[0] -eq 0xEF -and
    $originalBytes[1] -eq 0xBB -and
    $originalBytes[2] -eq 0xBF
$offset = if ($hasUtf8Bom) { 3 } else { 0 }
$utf8 = [System.Text.UTF8Encoding]::new($false, $true)
$text = $utf8.GetString($originalBytes, $offset, $originalBytes.Length - $offset)
$updatedText = $text
[Array]::Clear($originalBytes, 0, $originalBytes.Length)
$text = $null
$generatedValues = @{}

foreach ($name in $credentialNames) {
    $pattern = "(?m)^(?<prefix>$name[ \t]*=[ \t]*)(?<value>[^\r\n]*)(?<linebreak>\r?)$"
    $matches = [regex]::Matches($updatedText, $pattern)
    if ($matches.Count -ne 1) {
        throw "Expected exactly one $name entry in .env; no credentials were changed."
    }

    $randomBytes = [byte[]]::new(32)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($randomBytes)
    }
    finally {
        $generator.Dispose()
    }
    $encodedValue = [Convert]::ToBase64String($randomBytes)
    $newValue = $encodedValue.TrimEnd('=').Replace('+', '-').Replace('/', '_')
    [Array]::Clear($randomBytes, 0, $randomBytes.Length)
    $generatedValues[$name] = $newValue

    $evaluator = [System.Text.RegularExpressions.MatchEvaluator]{
        param($match)
        $match.Groups['prefix'].Value + $newValue + $match.Groups['linebreak'].Value
    }.GetNewClosure()
    $updatedText = [regex]::Replace($updatedText, $pattern, $evaluator, 1)
}

if (-not $PSCmdlet.ShouldProcess('.env', 'Atomically rotate the two WAF bridge credentials')) {
    return
}

$temporaryPath = Join-Path $repoRoot ('.env.rotate-' + [guid]::NewGuid().ToString('N') + '.tmp')
$backupPath = Join-Path $repoRoot ('.env.rotate-backup-' + [guid]::NewGuid().ToString('N') + '.tmp')
$temporaryPath = [System.IO.Path]::GetFullPath($temporaryPath)
$backupPath = [System.IO.Path]::GetFullPath($backupPath)
$envPath = [System.IO.Path]::GetFullPath($envPath)
try {
    $updatedBytes = $utf8.GetBytes($updatedText)
    if ($hasUtf8Bom) {
        $withBom = [byte[]]::new($updatedBytes.Length + 3)
        $withBom[0] = 0xEF
        $withBom[1] = 0xBB
        $withBom[2] = 0xBF
        [Array]::Copy($updatedBytes, 0, $withBom, 3, $updatedBytes.Length)
        $updatedBytes = $withBom
    }

    $stream = [System.IO.File]::Open(
        $temporaryPath,
        [System.IO.FileMode]::CreateNew,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    $stream.Dispose()

    # Restrict both the live environment file and the empty replacement file
    # before writing any rotated secret material to disk.
    Set-RestrictedSecretFileAcl -Path $envPath
    Set-RestrictedSecretFileAcl -Path $temporaryPath
    $stream = [System.IO.File]::Open(
        $temporaryPath,
        [System.IO.FileMode]::Truncate,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    try {
        $stream.Write($updatedBytes, 0, $updatedBytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }

    # This .NET runtime requires a non-null backup path. Both source and target
    # have an explicit least-privilege ACL; the unique backup is re-restricted
    # and deleted immediately after the atomic swap.
    if (-not [System.IO.File]::Exists($temporaryPath) -or
        -not [System.IO.File]::Exists($envPath) -or
        [System.IO.Path]::GetPathRoot($temporaryPath) -ne [System.IO.Path]::GetPathRoot($envPath) -or
        [System.IO.File]::Exists($backupPath)) {
        throw 'Atomic replacement preconditions failed; credentials were not changed.'
    }
    [System.IO.File]::Replace($temporaryPath, $envPath, $backupPath, $false)
    Set-RestrictedSecretFileAcl -Path $envPath
    if ([System.IO.File]::Exists($backupPath)) {
        Set-RestrictedSecretFileAcl -Path $backupPath
        [System.IO.File]::Delete($backupPath)
    }
    if ([System.IO.File]::Exists($backupPath)) {
        throw 'Credentials were replaced, but temporary backup cleanup failed.'
    }
    foreach ($name in $credentialNames) {
        Write-Output "Rotated $name; value withheld."
    }
}
finally {
    foreach ($path in @($temporaryPath, $backupPath)) {
        if ([System.IO.File]::Exists($path)) {
            [System.IO.File]::Delete($path)
        }
    }
    foreach ($name in $credentialNames) {
        if ($generatedValues.ContainsKey($name)) {
            $generatedValues[$name] = $null
        }
    }
    if ($null -ne $updatedBytes) {
        [Array]::Clear($updatedBytes, 0, $updatedBytes.Length)
    }
    $updatedText = $null
    $newValue = $null
    $encodedValue = $null
}
