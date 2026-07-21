export type BrowserChallengeStatus =
  | "VERIFIED"
  | "INVALID"
  | "UNAVAILABLE"
  | "NO_LONGER_REQUIRED";

export type ChallengeUiAction =
  | "RELOAD"
  | "RESET_INVALID"
  | "RESET_UNAVAILABLE";

export function challengeUiAction(
  status: BrowserChallengeStatus,
): ChallengeUiAction {
  if (status === "VERIFIED" || status === "NO_LONGER_REQUIRED") {
    return "RELOAD";
  }
  return status === "UNAVAILABLE" ? "RESET_UNAVAILABLE" : "RESET_INVALID";
}

export function removeTurnstileWidget(
  turnstile: { remove: (widgetId?: string) => void } | undefined,
  widgetId: string | undefined,
): void {
  if (turnstile && widgetId) turnstile.remove(widgetId);
}
