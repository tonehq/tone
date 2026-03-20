import { test as base, BrowserContext, expect, Page } from '@playwright/test';

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

const CHECK_EMAIL_URL = '/auth/check-email?email=test%40example.com';

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Check Email Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(CHECK_EMAIL_URL);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Check your email" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
    });

    test('shows the email icon', async ({ page }) => {
      // The Mail icon is inside a styled container
      await expect(page.locator('svg').first()).toBeVisible();
    });

    test('displays the user email from query params', async ({ page }) => {
      await expect(page.getByText('test@example.com')).toBeVisible();
    });

    test('shows the "sent an email" instruction text', async ({ page }) => {
      await expect(page.getByText("We've sent an email to")).toBeVisible();
    });

    test('shows the verification instruction', async ({ page }) => {
      await expect(
        page.getByText('Click the link in the email to verify your account'),
      ).toBeVisible();
    });

    test('shows the spam folder tip with "try again" link', async ({ page }) => {
      await expect(page.getByText('Check your spam folder')).toBeVisible();
      await expect(page.getByRole('link', { name: 'try again' })).toBeVisible();
    });

    test('shows the theme toggle button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Toggle theme' })).toBeVisible();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 2, name: 'Check your email' })).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('renders the "try again" link pointing to login', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'try again' })).toHaveAttribute(
        'href',
        '/auth/login',
      );
    });

    test('navigates to login page via "try again" link', async ({ page }) => {
      await page.getByRole('link', { name: 'try again' }).click();
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });
  });

  // ── 3. Fallback Email ─────────────────────────────────────────────────────
  test.describe('Fallback Email', () => {
    test('shows "your email" when no email query param is provided', async ({ page }) => {
      await page.goto('/auth/check-email');
      await expect(page.getByText('your email', { exact: true })).toBeVisible();
    });
  });
});
