[CmdletBinding()]
param(
    [string]$FastApiBaseUrl = $(
        if ([string]::IsNullOrWhiteSpace($env:FASTAPI_BASE_URL)) {
            "http://127.0.0.1:8000"
        } else {
            $env:FASTAPI_BASE_URL
        }
    ),
    [string]$TimeZone = $(
        if ([string]::IsNullOrWhiteSpace($env:RETRAINING_SCHEDULE_TIMEZONE)) {
            "Asia/Manila"
        } else {
            $env:RETRAINING_SCHEDULE_TIMEZONE
        }
    ),
    [ValidateRange(1, 60)]
    [int]$TimeoutSec = 20
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$scheduledAt = [DateTimeOffset]::UtcNow.ToString("o")

if ([string]::IsNullOrWhiteSpace($env:API_SECRET_KEY)) {
    Write-Output "scheduled_at=$scheduledAt status=FAILED code=SCHEDULE_CONFIGURATION_MISSING exit_code=20"
    exit 20
}
if (
    [string]::IsNullOrWhiteSpace($TimeZone) -or
    $TimeZone.Length -gt 64 -or
    ($TimeZone.ToCharArray() | Where-Object { [int]$_ -lt 32 }).Count -gt 0
) {
    Write-Output "scheduled_at=$scheduledAt status=FAILED code=SCHEDULE_CONFIGURATION_INVALID exit_code=20"
    exit 20
}
if (
    [string]::IsNullOrWhiteSpace($FastApiBaseUrl) -or
    ($FastApiBaseUrl.ToCharArray() | Where-Object { [int]$_ -lt 32 }).Count -gt 0
) {
    Write-Output "scheduled_at=$scheduledAt status=FAILED code=SCHEDULE_CONFIGURATION_INVALID exit_code=20"
    exit 20
}

$uri = "$($FastApiBaseUrl.TrimEnd('/'))/api/retraining/runs"
$headers = @{
    Authorization = "Bearer $($env:API_SECRET_KEY)"
    "X-Reviewer-Id" = "scheduler"
    "X-Reviewer-Role" = "ANALYST"
    "X-Requester-Timezone" = $TimeZone
    "X-Scheduled-At" = $scheduledAt
}
$body = @{ trigger = "scheduled" } | ConvertTo-Json -Compress

try {
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri $uri `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec $TimeoutSec
} catch {
    Write-Output "scheduled_at=$scheduledAt status=FAILED code=SCHEDULE_REQUEST_FAILED exit_code=30"
    exit 30
}

$requestCompletedAt = [DateTimeOffset]::UtcNow.ToString("o")
$runId = [string]$response.run_id
$state = [string]$response.state
$stage = [string]$response.stage
$created = [bool]$response.created

if ($state -eq "SKIPPED_NO_APPROVED_DATA") {
    Write-Output "run_id=$runId scheduled_at=$scheduledAt request_completed_at=$requestCompletedAt status=SKIPPED_NO_APPROVED_DATA stage=$stage created=$created timezone=$TimeZone exit_code=0"
    exit 0
}

$activeStates = @(
    "queued",
    "exporting",
    "dataset_validated",
    "training",
    "evaluating",
    "pending_approval",
    "approved",
    "deploying",
    "RETRYABLE_FAILED"
)
if (-not $created -and $activeStates -contains $state) {
    Write-Output "run_id=$runId scheduled_at=$scheduledAt request_completed_at=$requestCompletedAt status=SCHEDULE_SKIPPED_CONCURRENT_RUN stage=$stage created=$created timezone=$TimeZone exit_code=0"
    exit 0
}

Write-Output "run_id=$runId scheduled_at=$scheduledAt request_completed_at=$requestCompletedAt status=$state stage=$stage created=$created timezone=$TimeZone exit_code=0"
exit 0
