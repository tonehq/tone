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

// ── Soft navigation helper ────────────────────────────────────────────────────
async function ensureOnForgotPasswordPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/forgotpassword')) return;
  await page.goto('/auth/forgotpassword');
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Forgot Password Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnForgotPasswordPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Reset password" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Reset password' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(page.getByText('we will send you a link to reset your password')).toBeVisible();
    });

    test('shows the email input', async ({ page }) => {
      const emailInput = page.getByPlaceholder('Enter your email');
      await expect(emailInput).toBeVisible();
      await expect(emailInput).toHaveAttribute('type', 'email');
    });

    test('shows the "Reset Password" submit button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Reset Password' })).toBeVisible();
    });

    test('shows the "Cancel" button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
    });

    test('shows the "Log in" link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Log in' })).toBeVisible();
    });

    test('shows the theme toggle button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Toggle theme' })).toBeVisible();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 2, name: 'Reset password' })).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to login page via "Log in" link', async ({ page }) => {
      await page.getByRole('link', { name: 'Log in' }).click();
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('renders the "Log in" link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Log in' })).toHaveAttribute(
        'href',
        '/auth/login',
      );
    });
  });

  // ── 3. Form Validation ────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/forgotpassword');
    });

    test('stays on page when email is empty', async ({ page }) => {
      await page.getByRole('button', { name: 'Reset Password' }).click();
      await expect(page).toHaveURL(/\/auth\/forgotpassword/);
    });

    test('prevents submit with invalid email format', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill('not-an-email');
      await page.getByRole('button', { name: 'Reset Password' }).click();
      await expect(page).toHaveURL(/\/auth\/forgotpassword/);
    });
  });

  // ── 4. Reset Password Flow ────────────────────────────────────────────────
  test.describe('Reset Password Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/forgotpassword');
    });

    test('shows success notification on successful reset request', async ({ page }) => {
      await page.route('**/auth/forget-password**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Email sent' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Email Sent');
    });

    test('shows error notification on API failure', async ({ page }) => {
      await page.route('**/auth/forget-password**', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Internal server error');
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/forget-password**', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Something went wrong');
    });
  });

  // ── 5. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/forgotpassword');
    });

    test('shows loading state on the "Reset Password" button', async ({ page }) => {
      await page.route('**/auth/forget-password**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2_000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      const resetBtn = page.getByRole('button', { name: 'Reset Password' });
      await expect(resetBtn).toBeDisabled({ timeout: 1_000 });
      await expect(page.locator('[class*="animate-spin"]')).toBeVisible({ timeout: 1_000 });
    });
  });

  // ── 6. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('allows form submission via Enter key', async ({ page }) => {
      await page.goto('/auth/forgotpassword');

      await page.route('**/auth/forget-password**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Email sent' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByPlaceholder('Enter your email').press('Enter');

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Email Sent');
    });
  });
});
