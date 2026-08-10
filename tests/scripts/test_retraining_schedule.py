from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "retraining" / "run_daily_retraining.ps1"


def test_daily_retraining_wrapper_is_bounded_and_never_promotes():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'trigger = "scheduled"' in source
    assert "/api/retraining/runs" in source
    assert "TimeoutSec" in source
    assert "X-Scheduled-At" in source
    assert "scheduled_at=" in source
    assert "request_completed_at=" in source
    assert "exit_code=" in source
    assert "SCHEDULE_SKIPPED_CONCURRENT_RUN" in source
    assert "SKIPPED_NO_APPROVED_DATA" in source
    assert "API_SECRET_KEY" in source
    assert "Write-Output $env:API_SECRET_KEY" not in source
    assert "/deploy" not in source.lower()
    assert "deploy_retraining" not in source.lower()
    assert "rollback_retraining" not in source.lower()
    assert "Start-Sleep" not in source
