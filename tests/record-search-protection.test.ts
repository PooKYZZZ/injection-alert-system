import assert from "node:assert/strict";
import test from "node:test";

import { runRecordSearchProtectedWork } from "../app/records/search/record-search-protection";

test("BLOCK does not execute protected record-search work", async () => {
  let invocations = 0;

  const result = await runRecordSearchProtectedWork(
    { decision: "BLOCK", status: "checked" },
    async () => {
      invocations += 1;
      return ["protected-record"];
    },
  );

  assert.equal(invocations, 0);
  assert.equal(result, null);
});

test("ALLOW executes protected record-search work exactly once", async () => {
  let invocations = 0;

  const result = await runRecordSearchProtectedWork(
    { decision: "ALLOW", status: "checked" },
    async () => {
      invocations += 1;
      return ["public-index"];
    },
  );

  assert.equal(invocations, 1);
  assert.deepEqual(result, ["public-index"]);
});
