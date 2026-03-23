const { chromium } = require('playwright');
const path = require('path');

(async() => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1600, height: 2200 } });
  const page = await context.newPage();
  const base = 'http://127.0.0.1:3000';

  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.getByLabel('Password').fill('demo1234');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL('**/dashboard', { timeout: 30000 });
  await page.waitForLoadState('networkidle');

  const shots = [
    { name: 'dashboard-full-real.png', url: '/dashboard' },
    { name: 'dashboard-alerts-real.png', url: '/alerts' },
    { name: 'dashboard-ml-health-real.png', url: '/ml-health' },
  ];

  for (const shot of shots) {
    await page.goto(`${base}${shot.url}`, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join('..', 'screenshots', shot.name), fullPage: true });
  }

  await browser.close();
})();
