import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { httpErrorPageDocument } from "../lib/http-error-page";

const localBaseUrl = process.env.BASE_URL || "http://localhost:3000";

test.beforeAll(() => {
  const hostname = new URL(localBaseUrl).hostname;
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    throw new Error(`Error-page checks are local-only; refusing BASE_URL host ${hostname}.`);
  }
});

test("shared 403 restriction template renders recovery links at desktop, tablet, and mobile", async ({ page }) => {
  await page.route("**/uiux-simulated-403", async (route) => {
    await route.fulfill({
      status: 403,
      contentType: "text/html; charset=utf-8",
      body: httpErrorPageDocument(403),
    });
  });

  const viewports = [
    { width: 1440, height: 900 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ];
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    const response = await page.goto("/uiux-simulated-403");
    expect(response?.status()).toBe(403);
    await expect(page.getByRole("heading", { name: "Access Restricted" })).toBeVisible();
    await expect(page.getByText("We couldn't complete your request because access was restricted.", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Land Records Portal home" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Contact Support" })).toBeVisible();
    await expect(page.locator("main#main-content")).toHaveCount(1);
    const widths = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
    }));
    expect(widths.document).toBeLessThanOrEqual(widths.viewport);

    const evidenceDirectory = process.env.UIUX_EVIDENCE_DIR;
    if (evidenceDirectory) {
      mkdirSync(evidenceDirectory, { recursive: true });
      await page.screenshot({
        path: join(evidenceDirectory, `m4-403-restriction-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
    }
  }
});
