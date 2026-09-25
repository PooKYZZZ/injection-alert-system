import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";

const localBaseUrl = process.env.BASE_URL || "http://localhost:3000";
const localOrigin = new URL(localBaseUrl).origin;

test.beforeAll(() => {
  const hostname = new URL(localBaseUrl).hostname;
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    throw new Error(`Workflow checks are local-only; refusing BASE_URL host ${hostname}.`);
  }
});

async function captureEvidence(page: Page, name: string) {
  const evidenceDirectory = process.env.UIUX_EVIDENCE_DIR;
  if (!evidenceDirectory) return;

  mkdirSync(evidenceDirectory, { recursive: true });
  await page.evaluate(() => {
    document.querySelectorAll("nextjs-portal").forEach((element) => {
      if (element instanceof HTMLElement) element.style.setProperty("display", "none", "important");
    });
  });
  await page.screenshot({ path: join(evidenceDirectory, name), fullPage: true });
}

async function assertSummaryLinksAndFocus(page: Page, summaryId: string) {
  const summary = page.locator(`#${summaryId}`);
  await expect(summary).toBeFocused();
  const links = summary.locator("a[href^='#']");
  const count = await links.count();
  expect(count).toBeGreaterThan(0);

  for (let index = 0; index < count; index += 1) {
    const link = links.nth(index);
    const href = await link.getAttribute("href");
    expect(href).toBeTruthy();
    const field = page.locator(href!);
    await expect(field).toHaveAttribute("aria-invalid", "true");

    const describedBy = (await field.getAttribute("aria-describedby"))?.split(/\s+/) || [];
    const inlineErrorId = describedBy.find((id) => id.endsWith("-error"));
    expect(inlineErrorId, `${href} has an inline error description`).toBeTruthy();
    await expect(page.locator(`#${inlineErrorId}`)).toContainText((await link.innerText()).trim());
  }

  await links.first().click();
  await expect(page.locator((await links.first().getAttribute("href"))!)).toBeFocused();
}

async function selectFirstValue(form: Locator, fieldName: string) {
  const select = form.locator(`[name="${fieldName}"]`);
  const value = await select.evaluate((element: HTMLSelectElement) =>
    Array.from(element.options).find((option) => option.value && !option.disabled)?.value,
  );
  expect(value, `${fieldName} has a selectable option`).toBeTruthy();
  await select.selectOption(value!);
}

async function submitAndCapturePost(page: Page, path: string, expectedFields: string[]) {
  const requestPromise = page.waitForRequest((request) => {
    const url = new URL(request.url());
    return url.origin === localOrigin && url.pathname === path && request.method() === "POST";
  });
  await Promise.all([requestPromise, page.locator("form").getByRole("button", { name: /send|request|submit/i }).click()]);
  const request = await requestPromise;
  expect(request.headers()["content-type"]).toContain("application/x-www-form-urlencoded");
  const body = new URLSearchParams(request.postData() || "");
  expect([...body.keys()].sort()).toEqual([...expectedFields].sort());
  return { request, body };
}

test("Search Records submits the query by GET and retains it in the results view", async ({ page }) => {
  const query = "Synthetic UIUX record not found";
  await page.goto("/records/search");
  const requestPromise = page.waitForRequest((request) => {
    const url = new URL(request.url());
    return url.origin === localOrigin && url.pathname === "/records/search" && request.method() === "GET" && url.searchParams.has("query");
  });
  await Promise.all([requestPromise, page.locator('[name="query"]').fill(query).then(() => page.getByRole("button", { name: "Search" }).click())]);
  const request = await requestPromise;
  const requestUrl = new URL(request.url());
  expect([...requestUrl.searchParams.keys()]).toEqual(["query"]);
  expect(requestUrl.searchParams.get("query")).toBe(query);
  await expect(page.locator('[name="query"]')).toHaveValue(query);
  await expect(page.locator("mark")).toContainText(query);
});

test("Track Status recovers clearly when a reference is not found", async ({ page }) => {
  await page.goto("/transactions/status?ref=UIUX-NOT-FOUND-20260925");
  await expect(page.getByRole("heading", { name: "Reference code not found" })).toBeVisible();
  await expect(page.locator('[name="ref"]')).toHaveValue("UIUX-NOT-FOUND-20260925");
  await expect(page.getByRole("button", { name: "Query Transaction" })).toBeVisible();
});

test("Appointment validation links to matching inline errors and focuses the summary", async ({ page }) => {
  await page.goto("/appointments");
  await page.getByRole("button", { name: "Send demo request" }).click();
  await assertSummaryLinksAndFocus(page, "appointment-errors-summary");
  await captureEvidence(page, "m3-appointment-errors-desktop.png");
});

test("Support validation links to matching inline errors and focuses the summary", async ({ page }) => {
  await page.goto("/support");
  await page.getByRole("button", { name: "Send demo request" }).click();
  await assertSummaryLinksAndFocus(page, "support-errors-summary");
  await captureEvidence(page, "m3-support-errors-desktop.png");
});

test("Comments validation links to matching inline errors and focuses the summary", async ({ page }) => {
  await page.goto("/comments");
  await page.locator("#citizen-comments-form").getByRole("button", { name: "Post comment" }).click();
  await assertSummaryLinksAndFocus(page, "comments-errors-summary");
  await captureEvidence(page, "m3-comments-errors-desktop.png");
});

test("Appointment accepts synthetic input and confirms only a test request", async ({ page }) => {
  await page.goto("/appointments");
  const form = page.locator("#registrar-appointment-form");
  await form.locator('[name="fullName"]').fill("Synthetic UIUX Appointment Alpha");
  await form.locator('[name="email"]').fill("uiux-appointment@example.test");
  await selectFirstValue(form, "branch");
  await selectFirstValue(form, "serviceType");
  await form.locator('[name="preferredDate"]').fill(new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10));
  await form.locator('[name="notes"]').fill("Synthetic workflow verification note");

  const { request } = await submitAndCapturePost(page, "/appointments/submit", [
    "fullName", "email", "branch", "serviceType", "preferredDate", "notes",
  ]);
  const body = new URLSearchParams(request.postData() || "");
  expect(body.get("fullName")).toBe("Synthetic UIUX Appointment Alpha");
  await expect(page).toHaveURL((url) => url.pathname === "/success" && url.searchParams.get("type") === "appointment");
  await expect(page.getByRole("heading", { name: "Demo appointment request received" })).toBeVisible();
  await expect(page.getByText("It does not book a real appointment or send email.", { exact: false })).toBeVisible();
  await expect(page.getByText("Synthetic UIUX Appointment Alpha", { exact: true })).toHaveCount(0);
  await expect(page.getByText("uiux-appointment@example.test", { exact: true })).toHaveCount(0);
  await captureEvidence(page, "m3-appointment-confirmation-desktop.png");
});

test("Support accepts synthetic input and confirms no email reply is sent", async ({ page }) => {
  await page.goto("/support");
  const form = page.locator("#system-support-form");
  await form.locator('[name="email"]').fill("uiux-support@example.test");
  await selectFirstValue(form, "category");
  await form.locator('[name="subject"]').fill("Synthetic UIUX support check");
  await form.locator('[name="referenceNo"]').fill("LND-2026-0001");
  await form.locator('[name="message"]').fill("Synthetic local workflow verification only.");

  const { request } = await submitAndCapturePost(page, "/support/submit", [
    "email", "category", "subject", "referenceNo", "message",
  ]);
  const body = new URLSearchParams(request.postData() || "");
  expect(body.get("subject")).toBe("Synthetic UIUX support check");
  await expect(page).toHaveURL((url) => url.pathname === "/success" && url.searchParams.get("type") === "support");
  await expect(page.getByRole("heading", { name: "Demo support request received" })).toBeVisible();
  await expect(page.getByText("No email reply is sent.", { exact: false })).toBeVisible();
  await expect(page.getByText("uiux-support@example.test", { exact: true })).toHaveCount(0);
  await captureEvidence(page, "m3-support-confirmation-desktop.png");
});

test("Request a Copy preserves its payload and reaches the local status result", async ({ page }) => {
  await page.goto("/records/LND-2026-0001/request-copy");
  const form = page.locator("form");
  await expect(page.getByText("Test submissions may be visible to other visitors. Use synthetic values only.", { exact: true })).toBeVisible();
  await expect(form.getByText("Delivery choices are test inputs only; no document is produced or delivered.", { exact: true })).toBeVisible();
  await form.getByLabel("Printed copy (sample test value)").check();
  await expect(form.locator('[name="deliveryOption"]:checked')).toHaveValue("Printed certified copy");
  await form.locator('[name="fullName"]').fill("Synthetic UIUX Copy Requester");
  await form.locator('[name="email"]').fill("uiux-copy@example.test");
  await selectFirstValue(form, "purpose");
  await form.locator('[name="remarks"]').fill("Synthetic local copy request verification.");

  const { request } = await submitAndCapturePost(page, "/records/LND-2026-0001/request-copy/submit", [
    "fullName", "email", "purpose", "deliveryOption", "remarks",
  ]);
  const body = new URLSearchParams(request.postData() || "");
  expect(body.get("fullName")).toBe("Synthetic UIUX Copy Requester");
  expect(body.get("deliveryOption")).toBe("Printed certified copy");
  await expect(page).toHaveURL((url) => url.pathname === "/transactions/status" && Boolean(url.searchParams.get("ref")));
  const reference = new URL(page.url()).searchParams.get("ref");
  await expect(page.getByRole("heading", { name: reference!, exact: true })).toBeVisible();
  await expect(page.getByText("All records, submissions, and reference numbers are mock data for local testing only.", { exact: false })).toBeVisible();
  await expect(page.getByText(/Recipient: Synthetic UIUX Copy Requester/)).toBeVisible();
  await expect(page.getByText("uiux-copy@example.test", { exact: true })).toHaveCount(0);
});

test("Demo Login empty-field errors focus the linked summary without sending a request", async ({ page }) => {
  await page.goto("/login");
  let postSeen = false;
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin === localOrigin && url.pathname === "/login/submit" && request.method() === "POST") {
      postSeen = true;
    }
  });

  await page.getByRole("button", { name: "Submit demo attempt" }).click();
  await assertSummaryLinksAndFocus(page, "login-errors-summary");
  expect(postSeen).toBe(false);
});

test("Demo Login maps the existing JSON failure to recovery guidance inside the portal", async ({ page }) => {
  const directResponse = await page.request.post(`${localOrigin}/login/submit`, {
    form: { username: "", password: "synthetic-invalid-test" },
  });
  expect(directResponse.status()).toBe(400);
  expect(await directResponse.json()).toEqual({ error: "Invalid input" });

  await page.goto("/login");
  await page.route("**/login/submit", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ error: "Invalid input" }),
    });
  });
  const form = page.locator("form");
  await form.locator('[name="username"]').fill("synthetic-invalid-test");
  await form.locator('[name="password"]').fill("synthetic-only-password");
  await form.getByRole("button", { name: "Submit demo attempt" }).click();
  const summary = page.locator("#login-errors-summary");
  await expect(summary).toBeFocused();
  await expect(summary).toContainText("The demo rejected those values. Check the username and password, then try again.");
  await expect(form.locator('[name="password"]')).toHaveValue("");
  await captureEvidence(page, "m3-login-error-desktop.png");
});

test("Demo Login records a synthetic attempt without creating an authenticated session", async ({ page }) => {
  await page.goto("/login");
  const beforeCookies = await page.context().cookies(localOrigin);
  const form = page.locator("form");
  await form.locator('[name="username"]').fill(" synthetic-uiux-login-check ");
  await form.locator('[name="password"]').fill("synthetic-only-password");

  const requestPromise = page.waitForRequest((request) => {
    const url = new URL(request.url());
    return url.origin === localOrigin && url.pathname === "/login/submit" && request.method() === "POST";
  });
  await Promise.all([requestPromise, form.getByRole("button", { name: "Submit demo attempt" }).click()]);
  const request = await requestPromise;
  expect(request.headers()["content-type"]).toContain("application/x-www-form-urlencoded");
  const body = new URLSearchParams(request.postData() || "");
  expect([...body.keys()].sort()).toEqual(["password", "username"]);
  expect(body.get("username")).toBe(" synthetic-uiux-login-check ");

  await expect(page).toHaveURL((url) => url.pathname === "/login");
  await expect(page.locator("#login-success-feedback")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Demo login attempt recorded" })).toBeVisible();
  await expect(page.getByText("No account or session was created.", { exact: false })).toBeVisible();
  const afterCookies = await page.context().cookies(localOrigin);
  expect(afterCookies.filter((cookie) => /auth|session/i.test(cookie.name))).toEqual(
    beforeCookies.filter((cookie) => /auth|session/i.test(cookie.name)),
  );
  await captureEvidence(page, "m3-login-confirmation-desktop.png");
});
