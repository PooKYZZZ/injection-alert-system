import assert from "node:assert/strict";
import test from "node:test";

import {
  challengeUiAction,
  removeTurnstileWidget,
} from "../lib/enforcement-challenge-ui";

test("verified and no-longer-required challenge results reload authoritatively", () => {
  assert.equal(challengeUiAction("VERIFIED"), "RELOAD");
  assert.equal(challengeUiAction("NO_LONGER_REQUIRED"), "RELOAD");
});

test("unavailable challenge remains unsatisfied", () => {
  assert.equal(challengeUiAction("UNAVAILABLE"), "RESET_UNAVAILABLE");
  assert.equal(challengeUiAction("INVALID"), "RESET_INVALID");
});

test("widget cleanup removes the rendered Turnstile instance", () => {
  const removed: string[] = [];
  removeTurnstileWidget(
    { remove: (widgetId?: string) => widgetId && removed.push(widgetId) },
    "widget-1",
  );
  assert.deepEqual(removed, ["widget-1"]);
});
