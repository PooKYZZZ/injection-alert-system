import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const localBaseUrl = process.env.BASE_URL || "http://localhost:3000";
const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];
const coreTaskRoutes = [
  "/records/search",
  "/transactions/status",
  "/appointments",
  "/support",
];

test.beforeAll(() => {
  const hostname = new URL(localBaseUrl).hostname;
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    throw new Error(`Homepage checks are local-only; refusing BASE_URL host ${hostname}.`);
  }
});

test("homepage keeps core destinations clear and exposes the first task CTA on mobile", async ({ page }) => {
  const evidenceDirectory = process.env.UIUX_EVIDENCE_DIR;
  if (evidenceDirectory) mkdirSync(evidenceDirectory, { recursive: true });

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");

    await expect(page.getByText("A CyberTrace test demo, not an official registry.", { exact: false })).toBeVisible();
    for (const statistic of ["427,910", "2.8M", "100%", "4 Branches"]) {
      await expect(page.getByText(statistic, { exact: true })).toHaveCount(0);
    }

    const widths = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    expect(widths.document, `${viewport.name} document width`).toBeLessThanOrEqual(widths.viewport);
    expect(widths.body, `${viewport.name} body width`).toBeLessThanOrEqual(widths.viewport);

    const taskSection = page.locator("#service-tasks");
    for (const route of coreTaskRoutes) {
      const taskLink = taskSection.locator(`a[href="${route}"]`);
      await expect(taskLink, `${viewport.name} task route ${route}`).toBeVisible();
      await expect(taskLink).toBeEnabled();
    }

    if (viewport.name === "mobile") {
      const firstTask = taskSection.locator('a[href="/records/search"]');
      const bounds = await firstTask.boundingBox();
      expect(bounds, "first task CTA has a rendered box").not.toBeNull();
      expect(bounds!.y).toBeGreaterThanOrEqual(0);
      expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(viewport.height);
    }

    if (evidenceDirectory) {
      await page.evaluate(() => {
        document.querySelectorAll("nextjs-portal").forEach((element) => {
          if (element instanceof HTMLElement) {
            element.style.setProperty("display", "none", "important");
          }
        });
      });
      await page.screenshot({
        path: join(evidenceDirectory, `m2-home-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
    }
  }
});
