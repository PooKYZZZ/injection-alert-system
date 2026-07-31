import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { recordPr7PortalStage } from "../lib/pr7-portal-sentinel";

test("appends only the bounded portal evidence contract", async () => {
  const directory = await mkdtemp(join(tmpdir(), "pr7-sentinel-"));
  const path = join(directory, "events.jsonl");
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.PR7_PORTAL_SENTINEL_PATH = path;
  process.env.APP_ENV = "testing";

  try {
    await recordPr7PortalStage({
      evidenceId: "evidence_123",
      stage: "request_received",
    });

    const record = JSON.parse((await readFile(path, "utf8")).trim());
    assert.deepEqual(Object.keys(record).sort(), [
      "evidence_id",
      "method",
      "path",
      "stage",
      "timestamp",
    ]);
    assert.equal(record.evidence_id, "evidence_123");
    assert.equal(record.stage, "request_received");
    assert.equal(record.method, "GET");
    assert.equal(record.path, "/records/search");
    assert.match(record.timestamp, /^\d{4}-\d{2}-\d{2}T/);
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
    await rm(directory, { recursive: true });
  }
});

test("is inert without a configured path or valid evidence id", async () => {
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.APP_ENV = "testing";
  delete process.env.PR7_PORTAL_SENTINEL_PATH;
  await recordPr7PortalStage({
    evidenceId: "valid",
    stage: "request_received",
  });

  const directory = await mkdtemp(join(tmpdir(), "pr7-sentinel-"));
  const path = join(directory, "events.jsonl");
  process.env.PR7_PORTAL_SENTINEL_PATH = path;
  try {
    for (const evidenceId of ["", "line\nbreak", "../escape", "a".repeat(81)]) {
      await recordPr7PortalStage({
        evidenceId,
        stage: "protected_work_started",
      });
    }
    await assert.rejects(readFile(path, "utf8"), { code: "ENOENT" });
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
    await rm(directory, { recursive: true });
  }
});

test("write failures never escape into the enforcement flow", async () => {
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.PR7_PORTAL_SENTINEL_PATH = tmpdir();
  process.env.APP_ENV = "testing";
  try {
    await recordPr7PortalStage({
      evidenceId: "write_failure",
      stage: "request_received",
    });
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
  }
});

test("rejects an invalid runtime stage without writing evidence", async () => {
  const directory = await mkdtemp(join(tmpdir(), "pr7-sentinel-"));
  const path = join(directory, "events.jsonl");
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.PR7_PORTAL_SENTINEL_PATH = path;
  process.env.APP_ENV = "testing";
  try {
    await recordPr7PortalStage({
      evidenceId: "safe",
      stage: "unexpected" as "request_received",
    });
    await recordPr7PortalStage({
      evidenceId: { untrusted: true } as unknown as string,
      stage: "request_received",
    });
    await assert.rejects(readFile(path, "utf8"), { code: "ENOENT" });
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
    await rm(directory, { recursive: true });
  }
});

test("rejects a relative or traversal sentinel path", async () => {
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.APP_ENV = "testing";
  try {
    for (const sentinelPath of ["events.jsonl", "/tmp/../events.jsonl"]) {
      process.env.PR7_PORTAL_SENTINEL_PATH = sentinelPath;
      await recordPr7PortalStage({
        evidenceId: "safe",
        stage: "request_received",
      });
    }
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
  }
});

test("bounds concurrent sentinel output", async () => {
  const directory = await mkdtemp(join(tmpdir(), "pr7-sentinel-"));
  const path = join(directory, "events.jsonl");
  const previous = process.env.PR7_PORTAL_SENTINEL_PATH;
  const previousAppEnv = process.env.APP_ENV;
  process.env.PR7_PORTAL_SENTINEL_PATH = path;
  process.env.APP_ENV = "testing";
  try {
    await Promise.all(
      Array.from({ length: 2500 }, (_, index) =>
        recordPr7PortalStage({
          evidenceId: `request_${index}`,
          stage: "request_received",
        }),
      ),
    );
    assert.ok((await stat(path)).size <= 256 * 1024);
  } finally {
    if (previous === undefined) delete process.env.PR7_PORTAL_SENTINEL_PATH;
    else process.env.PR7_PORTAL_SENTINEL_PATH = previous;
    if (previousAppEnv === undefined) delete process.env.APP_ENV;
    else process.env.APP_ENV = previousAppEnv;
    await rm(directory, { recursive: true });
  }
});
