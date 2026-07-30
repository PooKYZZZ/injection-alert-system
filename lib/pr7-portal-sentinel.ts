import { appendFile } from "node:fs/promises";

const EVIDENCE_ID_PATTERN = /^[A-Za-z0-9_-]{1,80}$/;
const TEST_ENVIRONMENTS = new Set(["development", "test", "testing"]);

export type Pr7PortalStage =
  | "request_received"
  | "protected_work_started";

export async function recordPr7PortalStage(input: {
  evidenceId: string | null | undefined;
  stage: Pr7PortalStage;
}): Promise<void> {
  const sentinelPath = process.env.PR7_PORTAL_SENTINEL_PATH;
  if (!sentinelPath || !input.evidenceId) return;

  const environment = (process.env.APP_ENV || process.env.NODE_ENV || "").toLowerCase();
  if (!TEST_ENVIRONMENTS.has(environment) || !EVIDENCE_ID_PATTERN.test(input.evidenceId)) {
    console.warn(JSON.stringify({
      event: "pr7_portal_sentinel_rejected",
      reason: !TEST_ENVIRONMENTS.has(environment)
        ? "environment_not_test_only"
        : "invalid_evidence_id",
      stage: input.stage,
    }));
    return;
  }

  try {
    await appendFile(
      sentinelPath,
      `${JSON.stringify({
        evidence_id: input.evidenceId,
        stage: input.stage,
        method: "GET",
        path: "/records/search",
        timestamp: new Date().toISOString(),
      })}\n`,
      { encoding: "utf8", flag: "a" },
    );
  } catch (error) {
    console.warn(JSON.stringify({
      event: "pr7_portal_sentinel_write_failed",
      reason: error instanceof Error ? error.name : "unknown_error",
      stage: input.stage,
    }));
  }
}
