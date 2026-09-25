import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

const localBaseUrl = process.env.BASE_URL || "http://localhost:3000";
const accessibilityRoutes = [
  "/",
  "/records/search",
  "/transactions/status",
  "/appointments",
  "/support",
  "/login",
  "/comments",
  "/records/LND-2026-0001/request-copy",
  "/success?type=appointment&ref=UIUX-ACCESSIBILITY",
  "/uiux-route-not-found-20260925",
];
const formRoutes = [
  "/records/search",
  "/transactions/status",
  "/appointments",
  "/support",
  "/comments",
  "/records/LND-2026-0001/request-copy",
];
const viewportCases = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];

test.beforeAll(() => {
  const hostname = new URL(localBaseUrl).hostname;
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    throw new Error(`Accessibility checks are local-only; refusing BASE_URL host ${hostname}.`);
  }
});

test("sampled routes have one main landmark and unique IDs", async ({ page }) => {
  for (const route of accessibilityRoutes) {
    await page.goto(route);
    await expect(page.locator("main"), route).toHaveCount(1);
    await expect(page.locator("main#main-content"), route).toHaveCount(1);

    const ids = await page.locator("[id]").evaluateAll((elements) =>
      elements.map((element) => element.id),
    );
    expect(new Set(ids).size, `IDs are unique on ${route}`).toBe(ids.length);
  }

  await page.goto("/comments");
  await expect(page.locator("h1")).toHaveCount(1);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Demo Comments");
});

test("skip link is first in keyboard order, visible on focus, and focuses main", async ({ page }) => {
  await page.goto("/appointments");
  await page.keyboard.press("Tab");

  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await expect(skipLink).toBeFocused();
  const focusState = await skipLink.evaluate((element) => {
    const style = getComputedStyle(element);
    const bounds = element.getBoundingClientRect();
    return {
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      left: bounds.left,
      width: bounds.width,
    };
  });
  expect(focusState.outlineStyle).not.toBe("none");
  expect(Number.parseFloat(focusState.outlineWidth)).toBeGreaterThan(0);
  expect(focusState.left).toBeGreaterThanOrEqual(0);
  expect(focusState.width).toBeGreaterThan(0);

  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("primary navigation exposes the current page", async ({ page }) => {
  const currentLinks = [
    { route: "/records/search", label: "Search Records" },
    { route: "/transactions/status", label: "Track Status" },
    { route: "/appointments", label: "Book Appointment" },
    { route: "/support", label: "Support Desk" },
    { route: "/login", label: "Demo Login" },
  ];

  for (const { route, label } of currentLinks) {
    await page.goto(route);
    const currentLink =
      label === "Demo Login"
        ? page.getByRole("link", { name: label, exact: true })
        : page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: label });
    await expect(currentLink).toHaveAttribute("aria-current", "page");
    await expect(page.locator('[aria-current="page"]')).toHaveCount(1);
  }
});

test("form helper text and placeholders meet 4.5:1 contrast", async ({ page }) => {
  for (const route of formRoutes) {
    await page.goto(route);
    const samples = await page.evaluate(() => {
      type Rgb = [number, number, number, number];
      const parse = (value: string): Rgb | null => {
        const parts = value.match(/[\d.]+/g)?.map(Number);
        if (!parts || parts.length < 3) return null;
        return [parts[0], parts[1], parts[2], parts[3] ?? 1];
      };
      const blend = (foreground: Rgb, background: Rgb): Rgb => {
        const alpha = foreground[3];
        return [
          foreground[0] * alpha + background[0] * (1 - alpha),
          foreground[1] * alpha + background[1] * (1 - alpha),
          foreground[2] * alpha + background[2] * (1 - alpha),
          1,
        ];
      };
      const backgroundFor = (element: Element): Rgb => {
        const ancestors: Element[] = [];
        for (let current: Element | null = element; current; current = current.parentElement) {
          ancestors.unshift(current);
        }
        return ancestors.reduce<Rgb>((background, ancestor) => {
          const color = parse(getComputedStyle(ancestor).backgroundColor);
          return color ? blend(color, background) : background;
        }, [255, 255, 255, 1]);
      };
      const luminance = (color: Rgb) => {
        const channels = color.slice(0, 3).map((channel) => {
          const normalized = channel / 255;
          return normalized <= 0.04045
            ? normalized / 12.92
            : ((normalized + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
      };
      const contrast = (foreground: Rgb, background: Rgb) => {
        const foregroundLuminance = luminance(foreground);
        const backgroundLuminance = luminance(background);
        return (
          (Math.max(foregroundLuminance, backgroundLuminance) + 0.05) /
          (Math.min(foregroundLuminance, backgroundLuminance) + 0.05)
        );
      };

      const result: Array<{ label: string; ratio: number }> = [];
      for (const element of document.querySelectorAll<HTMLParagraphElement | HTMLSpanElement>(
        "form p.text-gray-400, form span.text-gray-400",
      )) {
        const foreground = parse(getComputedStyle(element).color);
        if (foreground) {
          result.push({
            label: element.textContent?.trim() || "helper text",
            ratio: contrast(foreground, backgroundFor(element)),
          });
        }
      }
      for (const element of document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
        "form input[placeholder], form textarea[placeholder]",
      )) {
        const style = getComputedStyle(element, "::placeholder");
        const foreground = parse(style.color);
        if (foreground) {
          foreground[3] *= Number.parseFloat(style.opacity || "1");
          result.push({
            label: element.placeholder,
            ratio: contrast(foreground, backgroundFor(element)),
          });
        }
      }
      return result;
    });

    expect(samples.length, `${route} has measured form text`).toBeGreaterThan(0);
    for (const sample of samples) {
      expect(sample.ratio, `${route}: ${sample.label}`).toBeGreaterThanOrEqual(4.5);
    }
  }
});

test("core routes have no horizontal overflow at desktop, tablet, or mobile widths", async ({ page }) => {
  const evidenceDirectory = process.env.UIUX_EVIDENCE_DIR;
  if (evidenceDirectory) mkdirSync(evidenceDirectory, { recursive: true });

  for (const viewport of viewportCases) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/appointments");
    const homeWidth = await page.evaluate(() => ({
      viewport: document.documentElement.clientWidth,
      document: document.documentElement.scrollWidth,
      body: document.body.scrollWidth,
    }));
    expect(homeWidth.document, `${viewport.name} shared-shell document width`).toBeLessThanOrEqual(
      homeWidth.viewport,
    );
    expect(homeWidth.body, `${viewport.name} shared-shell body width`).toBeLessThanOrEqual(
      homeWidth.viewport,
    );
    if (evidenceDirectory) {
      await page.evaluate(() => {
        document.querySelectorAll("nextjs-portal").forEach((element) => {
          if (element instanceof HTMLElement) {
            element.style.setProperty("display", "none", "important");
          }
        });
      });
      await page.screenshot({
        path: join(evidenceDirectory, `m1-appointments-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
      await page.screenshot({
        path: join(evidenceDirectory, `m4-appointments-${viewport.width}x${viewport.height}.png`),
        fullPage: true,
      });
    }

    for (const route of accessibilityRoutes.slice(1)) {
      await page.goto(route);
      const widths = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        document: document.documentElement.scrollWidth,
        body: document.body.scrollWidth,
      }));
      expect(widths.document, `${route} ${viewport.name} document width`).toBeLessThanOrEqual(
        widths.viewport,
      );
      expect(widths.body, `${route} ${viewport.name} body width`).toBeLessThanOrEqual(
        widths.viewport,
      );
      if (evidenceDirectory) {
        const routeName = route.split("?")[0].replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "home";
        await page.evaluate(() => {
          document.querySelectorAll("nextjs-portal").forEach((element) => {
            if (element instanceof HTMLElement) {
              element.style.setProperty("display", "none", "important");
            }
          });
        });
        await page.screenshot({
          path: join(evidenceDirectory, `m4-${routeName}-${viewport.width}x${viewport.height}.png`),
          fullPage: true,
        });
      }
    }
  }
});
