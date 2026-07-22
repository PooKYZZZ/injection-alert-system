import type { EnforcementCheckResult } from "../../../lib/enforcement-check";

export async function runRecordSearchProtectedWork<T>(
  enforcement: EnforcementCheckResult,
  protectedWork: () => Promise<T>,
): Promise<T | null> {
  if (enforcement.decision !== "ALLOW") return null;
  return protectedWork();
}
