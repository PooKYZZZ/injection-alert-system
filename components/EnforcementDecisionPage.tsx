import type { EnforcementCheckResult } from "../lib/enforcement-check";

export function EnforcementDecisionPage({
  result,
  resourceLabel,
}: {
  result: Exclude<EnforcementCheckResult, { decision: "ALLOW" }>;
  resourceLabel: string;
}) {
  const throttled = result.decision === "THROTTLE";
  const challenged = result.decision === "CHALLENGE";
  const title = throttled
    ? `${resourceLabel} temporarily limited`
    : challenged
      ? "Verification required"
      : "Access temporarily blocked";
  const message = throttled
    ? `Please wait ${result.retryAfterSeconds} seconds before trying again.`
    : challenged
      ? "Complete the security verification before continuing."
      : "Access to this request is temporarily blocked.";

  return (
    <main className="mx-auto max-w-2xl px-4 py-20 text-center font-sans">
      <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
        {title}
      </h1>
      <p className="mt-3 text-sm leading-6 text-slate-600">{message}</p>
    </main>
  );
}
