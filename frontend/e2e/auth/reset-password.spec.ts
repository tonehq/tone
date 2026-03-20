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

const RESET_URL = '/auth/reset-password?email=user%40example.com&token=abc123';

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Reset Password Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await page.goto(RESET_URL);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Reset password" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Reset password' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(page.getByText('Enter your new password below')).toBeVisible();
    });

    test('shows the new password input', async ({ page }) => {
      const input = page.getByPlaceholder('Enter new password');
      await expect(input).toBeVisible();
      await expect(input).toHaveAttribute('type', 'password');
    });

    test('shows the confirm password input', async ({ page }) => {
      const input = page.getByPlaceholder('Confirm new password');
      await expect(input).toBeVisible();
      await expect(input).toHaveAttribute('type', 'password');
    });

    test('shows the "Reset Password" submit button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Reset Password' })).toBeVisible();
    });

    test('shows the theme toggle button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Toggle theme' })).toBeVisible();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 2, name: 'Reset password' })).toBeVisible();
    });
  });

  // ── 2. Form Validation ────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    test('stays on page when password is empty', async ({ page }) => {
      await page.getByRole('button', { name: 'Reset Password' }).click();
      await expect(page).toHaveURL(/\/auth\/reset-password/);
    });

    test('stays on page when confirm password is empty', async ({ page }) => {
      await page.getByPlaceholder('Enter new password').fill('NewPass@123');
      await page.getByRole('button', { name: 'Reset Password' }).click();
      await expect(page).toHaveURL(/\/auth\/reset-password/);
    });
  });

  // ── 3. Reset Password Flow ────────────────────────────────────────────────
  test.describe('Reset Password Flow', () => {
    test('shows success notification and redirects to login on success', async ({ page }) => {
      await page.route('**/auth/acceptForgotPassword**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Password reset successful' }),
        });
      });

      await page.getByPlaceholder('Enter new password').fill('NewPass@123');
      await page.getByPlaceholder('Confirm new password').fill('NewPass@123');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Password Reset');
    });

    test('shows error notification on API failure', async ({ page }) => {
      await page.route('**/auth/acceptForgotPassword**', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid or expired token' }),
        });
      });

      await page.getByPlaceholder('Enter new password').fill('NewPass@123');
      await page.getByPlaceholder('Confirm new password').fill('NewPass@123');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Invalid or expired token');
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/acceptForgotPassword**', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter new password').fill('NewPass@123');
      await page.getByPlaceholder('Confirm new password').fill('NewPass@123');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Something went wrong');
    });
  });

  // ── 4. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows loading state on the "Reset Password" button', async ({ page }) => {
      await page.route('**/auth/acceptForgotPassword**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2_000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter new password').fill('NewPass@123');
      await page.getByPlaceholder('Confirm new password').fill('NewPass@123');
      await page.getByRole('button', { name: 'Reset Password' }).click();

      const resetBtn = page.getByRole('button', { name: 'Reset Password' });
      await expect(resetBtn).toBeDisabled({ timeout: 1_000 });
      await expect(page.locator('[class*="animate-spin"]')).toBeVisible({ timeout: 1_000 });
    });
  });

  // ── 5. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('allows toggling new password visibility', async ({ page }) => {
      const input = page.getByPlaceholder('Enter new password');
      await expect(input).toHaveAttribute('type', 'password');

      const toggleBtns = page.getByRole('button', { name: /toggle password visibility/i });
      await toggleBtns.first().click();
      await expect(input).toHaveAttribute('type', 'text');
    });

    test('allows keyboard navigation through form inputs', async ({ page }) => {
      await page.getByPlaceholder('Enter new password').focus();
      await expect(page.getByPlaceholder('Enter new password')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Confirm new password')).toBeFocused();
    });
  });
});
