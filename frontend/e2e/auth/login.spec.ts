import { test as base, BrowserContext, expect, Page } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD } from '../helpers/auth';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// One browser context (window) per worker — stays open for the full suite.
// A single tab is reused across all tests in the worker. State isolation is
// handled by beforeEach hooks (unrouteAll, navigation) rather than opening/closing
// a new tab for every test. This eliminates tab churn visible in --headed mode.
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    // "provide" avoids ESLint react-hooks/rules-of-hooks — Playwright only cares about
    // the position of this callback, not the parameter name.
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
    // Do NOT close — the same tab is reused across all tests in this worker.
  },
});

// ── Helpers ───────────────────────────────────────────────────────────────────
// Next.js injects a <div role="alert" id="__next-route-announcer__"> on every page.
// Filter it out so getByRole('alert') only matches real MUI Snackbar/Alert elements.
const getAlert = (p: Page) => p.getByRole('alert').filter({ hasText: /\S+/ });

// ── Soft navigation helper ───────────────────────────────────────────────────
// Auth pages have no sidebar, so soft nav = skip if already on the page.
// Falls back to hard page.goto() when on a different URL (e.g., after a
// successful login redirects to /home). Test groups that need a clean form
// add their own nested beforeEach with page.goto().
async function ensureOnLoginPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/login')) return;
  await page.goto('/auth/login');
}

// ── Mock data ────────────────────────────────────────────────────────────────
// Payload: {"sub":"user123","exp":9999999999} (expires year 2286)
const MOCK_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' +
  '.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjo5OTk5OTk5OTk5fQ==' +
  '.mock-signature';

const MOCK_LOGIN_RESPONSE = {
  access_token: MOCK_JWT,
  user_id: 'user123',
  organizations: [{ id: 'org123', name: 'Test Org' }],
};

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear routes from previous tests (prevents mock bleed between tests)
    await page.unrouteAll({ behavior: 'wait' });
    // Soft-navigate — skips reload if already on page, hard nav otherwise
    await ensureOnLoginPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the login heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Log in to your account' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(
        page.getByText('Welcome back! Enter your credentials to access your account'),
      ).toBeVisible();
    });

    test('shows the email input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your email')).toBeVisible();
    });

    test('shows the password input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your password')).toBeVisible();
    });

    test('shows the remember me checkbox checked by default', async ({ page }) => {
      await expect(page.getByRole('checkbox')).toBeChecked();
    });

    test('shows the forgot password link', async ({ page }) => {
      await expect(page.getByRole('link', { name: /forgot password/i })).toBeVisible();
    });

    test('shows the continue submit button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeVisible();
    });

    test('shows the continue with google button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /continue with google/i })).toBeVisible();
    });

    test('shows the sign up link', async ({ page }) => {
      await expect(page.getByRole('link', { name: /sign up/i })).toBeVisible();
    });

    test('shows the google logo image in the google button', async ({ page }) => {
      await expect(page.getByAltText('Google')).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to the forgot password page', async ({ page }) => {
      await page.getByRole('link', { name: /forgot password/i }).click();
      await expect(page).toHaveURL(/\/auth\/forgotpassword/);
    });

    test('navigates to the signup page from the sign up link', async ({ page }) => {
      await page.getByRole('link', { name: /sign up/i }).click();
      await expect(page).toHaveURL(/\/auth\/signup/);
    });
  });

  // ── 3. Form Validation ─────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    // Form validation tests need a clean form — hard nav to reset field values
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });

    test('rejects an invalid email format via browser HTML5 validation', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill('not-an-email');
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      // Browser HTML5 email constraint prevents form submission — no notification should appear
      await expect(page).toHaveURL(/\/auth\/login/);
      await expect(getAlert(page)).not.toBeVisible();
    });

    test('submits the form with empty fields and shows an error notification', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Email and password are required' }),
        });
      });

      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5000 });
      await expect(getAlert(page)).toContainText('Login Failed');
    });
  });

  // ── 4. Password Visibility Toggle ─────────────────────────────────────────
  test.describe('Password Visibility Toggle', () => {
    test('toggles password visibility when the eye icon is clicked', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Enter your password');

      await expect(passwordInput).toHaveAttribute('type', 'password');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'text');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  // ── 5. Authentication Flow ─────────────────────────────────────────────────
  test.describe('Authentication Flow', () => {
    // Auth flow tests navigate away (to /home) and set cookies via setToken()
    // — hard nav ensures a clean login page for each test.
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });

    // Clear cookies set by successful login mocks (via setToken)
    // so they don't affect subsequent tests.
    test.afterEach(async ({ page }) => {
      await page.context().clearCookies();
    });

    test('successful login shows a success notification and redirects to home', async ({
      page,
    }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LOGIN_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toContainText('Login Successful', { timeout: 5000 });
      await expect(page).toHaveURL(/\/home/, { timeout: 10_000 });
    });

    test('successful login sends the correct credentials to the API', async ({ page }) => {
      let capturedBody: Record<string, string> = {};

      await page.route('**/auth/login', async (route) => {
        capturedBody = route.request().postDataJSON() as Record<string, string>;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_LOGIN_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5000 });
      expect(capturedBody.email).toBe(TEST_EMAIL);
      expect(capturedBody.password).toBe(TEST_PASSWORD);
    });

    test('failed login with a 401 response shows an error notification', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill('wrongpassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toContainText('Login Failed', { timeout: 5000 });
      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('failed login with a 500 response shows an error notification', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toContainText('Login Failed', { timeout: 5000 });
      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('network error during login shows an error notification', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toContainText('Login Failed', { timeout: 5000 });
      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });

  // ── 6. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows a loading button and disables submission while the API call is in-flight', async ({
      page,
    }) => {
      await page.route('**/auth/login', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(page.getByRole('button', { name: 'Loading...' })).toBeVisible({ timeout: 1000 });
      await expect(page.getByRole('button', { name: 'Loading...' })).toBeDisabled();
    });

    test('re-enables the submit button after the login attempt completes', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill('wrongpassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeEnabled({
        timeout: 5000,
      });
    });
  });

  // ── 7. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('the google logo image has an alt attribute', async ({ page }) => {
      await expect(page.getByAltText('Google')).toHaveAttribute('alt', 'Google');
    });

    test('the password visibility toggle has an accessible aria-label', async ({ page }) => {
      await expect(page.getByRole('button', { name: /toggle password visibility/i })).toBeVisible();
    });

    test('can tab through interactive form elements', async ({ page }) => {
      // Click the email input to give the window OS-level focus,
      // then Tab forward to verify keyboard navigation order.
      await page.getByPlaceholder('Enter your email').click();
      await expect(page.getByPlaceholder('Enter your email')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Enter your password')).toBeFocused();
    });
  });
});
