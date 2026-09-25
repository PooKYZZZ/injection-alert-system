import { expect, test, type Locator, type Page, type Request } from "@playwright/test";

const localBaseUrl = process.env.BASE_URL || "http://localhost:3000";
const localOrigin = new URL(localBaseUrl).origin;

type WorkflowContract = {
  path: string;
  method: "GET" | "POST";
  fields: string[];
};

test.beforeAll(() => {
  const host = new URL(localBaseUrl).hostname;
  if (host !== "localhost" && host !== "127.0.0.1") {
    throw new Error(`Request-contract checks are local-only; refusing BASE_URL host ${host}.`);
  }
});

async function fillSelect(form: Locator, name: string) {
  const select = form.locator(`[name="${name}"]`);
  const value = await select.evaluate((element: HTMLSelectElement) =>
    Array.from(element.options).find((option) => option.value)?.value,
  );
  expect(value, `${name} has a non-placeholder option`).toBeTruthy();
  await select.selectOption(value!);
}

async function captureSubmit(
  page: Page,
  contract: WorkflowContract,
  fill: (form: Locator) => Promise<void>,
  queryValues: Record<string, string> = {},
) {
  const forms = page.locator("form");
  await expect(forms).toHaveCount(1);
  const form = forms.first();

  const domContract = await form.evaluate((element: HTMLFormElement) => ({
    path: new URL(element.action).pathname,
    method: element.method.toUpperCase(),
  }));
  expect(domContract).toEqual({ path: contract.path, method: contract.method });

  await fill(form);
  let matchedRequest: Request | undefined;
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      url.origin === localOrigin &&
      url.pathname === contract.path &&
      request.method() === contract.method
    ) {
      matchedRequest = request;
      await route.fulfill({
        status: 200,
        contentType: "text/html; charset=utf-8",
        body: "<!doctype html><html><body><main>Local request contract captured.</main></body></html>",
      });
      return;
    }
    await route.continue();
  });

  const requestPromise = page.waitForRequest(
    (request) =>
      new URL(request.url()).origin === localOrigin &&
      new URL(request.url()).pathname === contract.path &&
      request.method() === contract.method,
  );
  await Promise.all([requestPromise, form.locator("button").last().click()]);
  const request = matchedRequest;
  expect(request, `${contract.method} ${contract.path} was intercepted`).toBeTruthy();
  const submittedUrl = new URL(request!.url());

  if (contract.method === "GET") {
    expect([...submittedUrl.searchParams.keys()].sort()).toEqual([...contract.fields].sort());
    for (const [name, value] of Object.entries(queryValues)) {
      expect(submittedUrl.searchParams.get(name)).toBe(value);
    }
  } else {
    expect(request!.headers()["content-type"]).toContain("application/x-www-form-urlencoded");
    const body = new URLSearchParams(request!.postData() || "");
    expect([...body.keys()].sort()).toEqual([...contract.fields].sort());
  }

  await page.unrouteAll({ behavior: "wait" });
  return request!;
}

test("Search Records sends the entered test string to its GET route unchanged", async ({ page }) => {
  const query = "uiux ' OR 1=1 --";
  await page.goto("/records/search");
  await captureSubmit(
    page,
    { path: "/records/search", method: "GET", fields: ["query"] },
    async (form) => form.locator('[name="query"]').fill(query),
    { query },
  );
});

test("Track Status keeps its GET reference contract", async ({ page }) => {
  const ref = "UIUX-NOT-FOUND-20260925";
  await page.goto("/transactions/status");
  await captureSubmit(
    page,
    { path: "/transactions/status", method: "GET", fields: ["ref"] },
    async (form) => form.locator('[name="ref"]').fill(ref),
    { ref },
  );
});

test("Appointment keeps its URL-encoded POST contract", async ({ page }) => {
  await page.goto("/appointments");
  await captureSubmit(page, {
    path: "/appointments/submit",
    method: "POST",
    fields: ["fullName", "email", "branch", "serviceType", "preferredDate", "notes"],
  }, async (form) => {
    await form.locator('[name="fullName"]').fill("Synthetic UI Test");
    await form.locator('[name="email"]').fill("uiux-contract@example.test");
    await fillSelect(form, "branch");
    await fillSelect(form, "serviceType");
    await form.locator('[name="preferredDate"]').fill("2035-02-03");
    await form.locator('[name="notes"]').fill("Synthetic local request contract check");
  });
});

test("Support keeps its URL-encoded POST contract", async ({ page }) => {
  await page.goto("/support");
  await captureSubmit(page, {
    path: "/support/submit",
    method: "POST",
    fields: ["email", "category", "subject", "referenceNo", "message"],
  }, async (form) => {
    await form.locator('[name="email"]').fill("uiux-contract@example.test");
    await fillSelect(form, "category");
    await form.locator('[name="subject"]').fill("Synthetic local request");
    await form.locator('[name="referenceNo"]').fill("LND-2026-0001");
    await form.locator('[name="message"]').fill("Synthetic local request contract check");
  });
});

test("Request a Copy keeps its dynamic URL-encoded POST contract", async ({ page }) => {
  await page.goto("/records/LND-2026-0001/request-copy");
  await captureSubmit(page, {
    path: "/records/LND-2026-0001/request-copy/submit",
    method: "POST",
    fields: ["fullName", "email", "purpose", "deliveryOption", "remarks"],
  }, async (form) => {
    await form.locator('[name="fullName"]').fill("Synthetic UI Test");
    await form.locator('[name="email"]').fill("uiux-contract@example.test");
    await fillSelect(form, "purpose");
    await form.locator('[name="remarks"]').fill("Synthetic local request contract check");
  });
});

test("Demo Login remains a placeholder POST with username and password fields", async ({ page }) => {
  await page.goto("/login");
  await captureSubmit(page, {
    path: "/login/submit",
    method: "POST",
    fields: ["username", "password"],
  }, async (form) => {
    await form.locator('[name="username"]').fill("synthetic-uiux-check");
    await form.locator('[name="password"]').fill("synthetic-only");
  });
});

test("Comments keeps its URL-encoded POST contract", async ({ page }) => {
  await page.goto("/comments");
  await captureSubmit(page, {
    path: "/comments/submit",
    method: "POST",
    fields: ["displayName", "message"],
  }, async (form) => {
    await form.locator('[name="displayName"]').fill("Synthetic UI Test");
    await form.locator('[name="message"]').fill("Synthetic local request contract check");
  });
});
