import { test as base, BrowserContext, expect, Page } from '@playwright/test';

// ── Toast helper ─────────────────────────────────────────────────────────────
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

// ── Browser lifecycle ─────────────────────────────────────────────────────────
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      await context.newPage();
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

const VERIFY_URL = '/auth/verify_signup?email=test%40example.com&code=abc123&user_id=1';

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Email Verification Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await page.goto(VERIFY_URL);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Email Verification" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Email Verification' })).toBeVisible();
    });

    test('shows the verification instruction text', async ({ page }) => {
      await expect(
        page.getByText('To complete the verification process, please click the button below'),
      ).toBeVisible();
    });

    test('shows the "Verify Email" button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Verify Email' })).toBeVisible();
    });

    test('shows the check circle icon', async ({ page }) => {
      await expect(page.locator('svg').first()).toBeVisible();
    });

    test('shows the theme toggle button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Toggle theme' })).toBeVisible();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(
        page.getByRole('heading', { level: 2, name: 'Email Verification' }),
      ).toBeVisible();
    });
  });

  // ── 2. Verification Flow ──────────────────────────────────────────────────
  test.describe('Verification Flow', () => {
    test('shows success notification and redirects to login on success', async ({ page }) => {
      await page.route('**/auth/verify_user_email**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Email verified' }),
        });
      });

      await page.getByRole('button', { name: 'Verify Email' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Email Verified');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('redirects to invite URL if stored in localStorage', async ({ page }) => {
      await page.evaluate(() => localStorage.setItem('invite_redirect', '/invited-page'));

      await page.route('**/auth/verify_user_email**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Email verified' }),
        });
      });

      await page.getByRole('button', { name: 'Verify Email' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Email Verified');
    });

    test('shows error notification on API failure', async ({ page }) => {
      await page.route('**/auth/verify_user_email**', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid verification code' }),
        });
      });

      await page.getByRole('button', { name: 'Verify Email' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Invalid verification code');
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/verify_user_email**', async (route) => {
        await route.abort('failed');
      });

      await page.getByRole('button', { name: 'Verify Email' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Something went wrong');
    });
  });

  // ── 3. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows loading state on the "Verify Email" button', async ({ page }) => {
      // Clear any previously registered routes to avoid conflicts
      await page.unrouteAll({ behavior: 'wait' });

      let resolveRoute: (() => void) | null = null;
      await page.route('**/auth/verify_user_email**', async (route) => {
        await new Promise<void>((resolve) => {
          resolveRoute = resolve;
        });
        await route.abort('failed');
      });

      await page.getByRole('button', { name: 'Verify Email' }).click();

      const verifyBtn = page.getByRole('button', { name: 'Verify Email' });
      await expect(verifyBtn).toBeDisabled({ timeout: 3_000 });
      await expect(page.locator('[class*="animate-spin"]')).toBeVisible({ timeout: 3_000 });

      // Release the pending route so cleanup doesn't hang
      resolveRoute?.();
    });
  });
});
