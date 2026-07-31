import { appendFile, stat } from "node:fs/promises";
import { basename, isAbsolute } from "node:path";

const EVIDENCE_ID_PATTERN = /^[A-Za-z0-9_-]{1,80}$/;
const TEST_ENVIRONMENTS = new Set(["development", "test", "testing"]);
const MAX_SENTINEL_BYTES = 256 * 1024;
const ALLOWED_STAGES = new Set<Pr7PortalStage>([
  "request_received",
  "protected_work_started",
]);

function isSafeSentinelPath(value: string): boolean {
  return (
    isAbsolute(value) &&
    !value.includes("\0") &&
    !value.split(/[\\/]+/).includes("..") &&
    /^[A-Za-z0-9._-]{1,100}\.jsonl$/i.test(basename(value))
  );
}

let sentinelWriteQueue: Promise<void> = Promise.resolve();
const sentinelSizeWarningPaths = new Set<string>();
const sentinelWarningKeys = new Set<string>();

function warnSentinelOnce(key: string, payload: Record<string, string>): void {
  if (sentinelWarningKeys.has(key)) return;
  sentinelWarningKeys.add(key);
  console.warn(JSON.stringify(payload));
}

async function appendBoundedSentinel(
  path: string,
  content: string,
): Promise<boolean> {
  let written = false;
  const operation = sentinelWriteQueue.then(async () => {
    let currentBytes = 0;
    try {
      currentBytes = (await stat(path)).size;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
    if (currentBytes + Buffer.byteLength(content, "utf8") > MAX_SENTINEL_BYTES) {
      return;
    }
    await appendFile(path, content, { encoding: "utf8", flag: "a" });
    written = true;
  });
  sentinelWriteQueue = operation.catch(() => undefined);
  await operation;
  return written;
}

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
  const validEvidenceId =
    typeof input.evidenceId === "string" && EVIDENCE_ID_PATTERN.test(input.evidenceId);
  const validStage =
    typeof input.stage === "string" && ALLOWED_STAGES.has(input.stage);
  if (
    !TEST_ENVIRONMENTS.has(environment) ||
    !validEvidenceId ||
    !validStage ||
    !isSafeSentinelPath(sentinelPath)
  ) {
    const safeStage = validStage ? input.stage : "unknown";
    const reason = !TEST_ENVIRONMENTS.has(environment)
      ? "environment_not_test_only"
      : !validEvidenceId
        ? "invalid_evidence_id"
        : !validStage
          ? "invalid_stage"
          : "invalid_path";
    warnSentinelOnce(`${sentinelPath}:${reason}`, {
      event: "pr7_portal_sentinel_rejected",
      reason,
      stage: safeStage,
    });
    return;
  }

  try {
    const written = await appendBoundedSentinel(
      sentinelPath,
      `${JSON.stringify({
        evidence_id: input.evidenceId,
        stage: input.stage,
        method: "GET",
        path: "/records/search",
        timestamp: new Date().toISOString(),
      })}\n`,
    );
    if (!written) {
      if (!sentinelSizeWarningPaths.has(sentinelPath)) {
        sentinelSizeWarningPaths.add(sentinelPath);
        warnSentinelOnce(`${sentinelPath}:size_limit`, {
          event: "pr7_portal_sentinel_rejected",
          reason: "size_limit",
          stage: input.stage,
        });
      }
    }
  } catch (error) {
    warnSentinelOnce(`${sentinelPath}:write_failed`, {
      event: "pr7_portal_sentinel_write_failed",
      reason: error instanceof Error ? error.name : "unknown_error",
      stage: input.stage,
    });
  }
}
