import { BrowserContext, Page, test as base } from '@playwright/test';

// ── Test credentials ─────────────────────────────────────────────────────────
// Real credentials for the test account. Login hits the actual backend API.
// Override via environment variables if needed:
//   PLAYWRIGHT_TEST_EMAIL / PLAYWRIGHT_TEST_PASSWORD
export const TEST_EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL ?? 'kishok.k@productfusion.co';
export const TEST_PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD ?? 'Pass@123';

/**
 * Log in through the actual login page UI against the real backend.
 *
 * The login page lives at `/login` (the legacy `/auth/login` redirects here).
 * Submitting the form hits the real backend, the app's `setLoginResponse` stores
 * the JWT and tenant info, and the router pushes to `/home`.
 *
 * Requirements:
 *   - The dev server is running (`yarn dev`)
 *   - The backend (NEXT_PUBLIC_BACKEND_URL) is reachable
 *   - A user with TEST_EMAIL / TEST_PASSWORD exists
 */
export async function loginViaUI(
  page: Page,
  options?: { email?: string; password?: string },
): Promise<void> {
  const email = options?.email ?? TEST_EMAIL;
  const password = options?.password ?? TEST_PASSWORD;

  await page.goto('/login');

  // Wait for the form to be interactive (loaded under <Suspense>)
  await page.getByRole('button', { name: 'Sign In', exact: true }).waitFor({
    state: 'visible',
    timeout: 15_000,
  });

  // Fill the form. Email TextInput exposes a proper label; password label is
  // a sibling <label htmlFor="password">, so getByLabel works for both.
  await page.getByLabel('Email', { exact: false }).fill(email);
  await page.locator('input[name="password"]').fill(password);

  // Submit the form (button + Enter both work; Enter avoids any overlay issues)
  await page.locator('input[name="password"]').press('Enter');

  // Wait for the app to redirect after successful login
  await page.waitForURL(/\/home/, { timeout: 20_000 });
}

// ── Shared worker fixture (login once per worker) ────────────────────────────
// Dashboard specs should import `test` from this file instead of redefining the
// browser lifecycle in each spec. One browser window per worker, one tab reused
// across all tests, login happens ONCE during worker setup.
export const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      const page = await context.newPage();
      await loginViaUI(page);
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
  },
});

// ── Soft navigation helper ───────────────────────────────────────────────────
// Avoids hard page reloads between tests. Three cases:
//   1. Already on target page → skip navigation (0ms)
//   2. On another dashboard page → click sidebar link for client-side nav
//   3. Outside dashboard (e.g., /login) → fall back to page.goto()
export async function ensureOnPage(page: Page, targetPath: string): Promise<void> {
  if (page.url().includes(targetPath)) return;

  const sidebarLink = page.locator(`a[href="${targetPath}"]`).first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(new RegExp(targetPath.replace('/', '\\/')), { timeout: 5_000 });
    return;
  }

  await page.goto(targetPath);
}
