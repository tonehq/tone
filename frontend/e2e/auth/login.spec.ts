import { BrowserContext, expect, Page, test as base } from '@playwright/test';

import { TEST_EMAIL, TEST_PASSWORD } from '../helpers/auth';

// ── Mock data ─────────────────────────────────────────────────────────────────
// JWT payload: {"sub":"1234567890","exp":9999999999} (year 2286 expiry)
const MOCK_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' +
  '.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjo5OTk5OTk5OTk5fQ' +
  '.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';

const MOCK_LOGIN_RESPONSE = {
  access_token: MOCK_JWT,
  user_id: 'user123',
  organizations: [{ id: 'org123', name: 'Test Org' }],
};

// ── Alert helper ──────────────────────────────────────────────────────────────
// Next.js injects an empty <div role="alert"> route announcer on every page.
// Filter it out to avoid strict-mode violations when asserting notifications.
const getAlert = (p: Page) => p.getByRole('alert').filter({ hasText: /\S+/ });

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Login page is public — no loginViaUI needed.
// One browser context per worker, one tab reused across all tests.
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
// Auth pages have no sidebar, so soft nav = skip if already on the page.
// Falls back to hard page.goto() when on a different URL (e.g., after redirect
// to /home). Test groups that need a clean form add their own nested beforeEach.
async function ensureOnLoginPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/login')) return;
  await page.goto('/auth/login');
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnLoginPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Welcome back" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(
        page.getByText('Enter your credentials to access your account'),
      ).toBeVisible();
    });

    test('shows the email input', async ({ page }) => {
      const emailInput = page.getByPlaceholder('Enter your email');
      await expect(emailInput).toBeVisible();
      await expect(emailInput).toHaveAttribute('type', 'email');
    });

    test('shows the password input', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Enter your password');
      await expect(passwordInput).toBeVisible();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('shows the Remember me checkbox checked by default', async ({ page }) => {
      await expect(page.getByRole('checkbox')).toBeVisible();
      await expect(page.getByRole('checkbox')).toBeChecked();
    });

    test('shows the "Forgot password?" link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Forgot password?' })).toBeVisible();
    });

    test('shows the Continue submit button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeVisible();
    });

    test('shows the "Continue with Google" button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Continue with Google' })).toBeVisible();
    });

    test('shows the "Don\'t have an account?" text', async ({ page }) => {
      await expect(page.getByText("Don't have an account?")).toBeVisible();
    });

    test('shows the Sign up link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Sign up' })).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to forgot password page via link', async ({ page }) => {
      await page.getByRole('link', { name: 'Forgot password?' }).click();
      await expect(page).toHaveURL(/\/auth\/forgotpassword/, { timeout: 10_000 });
    });

    test('renders the "Forgot password?" link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Forgot password?' })).toHaveAttribute(
        'href',
        '/auth/forgotpassword',
      );
    });

    test('navigates to signup page via "Sign up" link', async ({ page }) => {
      await page.getByRole('link', { name: 'Sign up' }).click();
      await expect(page).toHaveURL(/\/auth\/signup/, { timeout: 10_000 });
    });

    test('renders the "Sign up" link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Sign up' })).toHaveAttribute(
        'href',
        '/auth/signup',
      );
    });
  });

  // ── 3. Form Validation ────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    // Form validation needs a clean form — hard nav resets field values
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });

    test('stays on login page when email is empty', async ({ page }) => {
      // TextInput `isRequired` shows a visual asterisk only — the underlying input
      // does NOT have the HTML `required` attribute, so the form submits and the
      // API rejects the empty value. The page must stay on /auth/login.
      await page.getByPlaceholder('Enter your password').fill('somepassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('stays on login page when password is empty', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('prevents submit with invalid email format', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill('not-an-email');
      await page.getByPlaceholder('Enter your password').fill('somepassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      // Browser email validation blocks submit
      await expect(page).toHaveURL(/\/auth\/login/);
    });
  });

  // ── 4. Authentication Flow ────────────────────────────────────────────────
  test.describe('Authentication Flow', () => {
    // Each auth test needs a clean form to avoid stale field values
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });

    // Successful login sets cookies — clear them after each test
    test.afterEach(async ({ page }) => {
      await page.context().clearCookies();
    });

    test('successful login redirects to home', async ({ page }) => {
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

      await expect(page).toHaveURL(/\/home/, { timeout: 10_000 });
    });

    test('successful login shows success notification', async ({ page }) => {
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

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Login Successful: Welcome back!');
    });

    test('successful login sets the auth cookie', async ({ page }) => {
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

      await page.waitForURL(/\/home/, { timeout: 10_000 });

      const cookies = await page.context().cookies();
      const accessToken = cookies.find((c) => c.name === 'tone_access_token');
      expect(accessToken).toBeDefined();
      expect(accessToken!.value.length).toBeGreaterThan(0);
    });

    test('sends correct email and password to the login API', async ({ page }) => {
      let requestBody: Record<string, string> = {};
      await page.route('**/auth/login', async (route) => {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByPlaceholder('Enter your password').fill('mypassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      expect(requestBody.email).toBe('user@example.com');
      expect(requestBody.password).toBe('mypassword');
    });

    test('shows error notification on 401 invalid credentials', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('wrong@example.com');
      await page.getByPlaceholder('Enter your password').fill('wrongpassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Login Failed');
      await expect(page).toHaveURL(/\/auth\/login/);
    });

    test('stays on login page after failed login', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('wrong@example.com');
      await page.getByPlaceholder('Enter your password').fill('wrongpassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 5_000 });
      await expect(page.getByPlaceholder('Enter your email')).toBeVisible();
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Login Failed: Please try again.');
    });

    test('shows error notification on server error (500)', async ({ page }) => {
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

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Login Failed');
    });
  });

  // ── 5. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });

    test('shows loading state on the Continue button during login', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        // Delay then abort — keeps page on login (no navigation race).
        // route.abort() prevents setToken from running after the test assertion.
        await new Promise((resolve) => setTimeout(resolve, 2_000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_EMAIL);
      await page.getByPlaceholder('Enter your password').fill(TEST_PASSWORD);
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      // CustomButton keeps its "Continue" text but disables and shows Loader2 spinner.
      // (Unlike the MUI version, shadcn CustomButton does not swap text to "Loading...")
      const continueBtn = page.getByRole('button', { name: 'Continue', exact: true });
      await expect(continueBtn).toBeDisabled({ timeout: 1_000 });
      await expect(page.locator('[class*="animate-spin"]')).toBeVisible({ timeout: 1_000 });
    });

    test('re-enables the Continue button after login failure', async ({ page }) => {
      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('wrong@example.com');
      await page.getByPlaceholder('Enter your password').fill('wrongpassword');
      await page.getByRole('button', { name: 'Continue', exact: true }).click();

      // After the request resolves, button returns to enabled state
      await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeEnabled({
        timeout: 5_000,
      });
    });
  });

  // ── 6. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('allows toggling password visibility', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Enter your password');
      await expect(passwordInput).toHaveAttribute('type', 'password');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'text');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('allows unchecking and re-checking the Remember me checkbox', async ({ page }) => {
      const checkbox = page.getByRole('checkbox');
      await expect(checkbox).toBeChecked();

      await checkbox.uncheck();
      await expect(checkbox).not.toBeChecked();

      await checkbox.check();
      await expect(checkbox).toBeChecked();
    });

    test('allows form submission via Enter key', async ({ page }) => {
      await page.goto('/auth/login');

      await page.route('**/auth/login', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill('user@example.com');
      await page.getByPlaceholder('Enter your password').fill('somepassword');
      await page.getByPlaceholder('Enter your password').press('Enter');

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Login Failed');
    });

    test('allows keyboard navigation through form inputs', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').focus();
      await expect(page.getByPlaceholder('Enter your email')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Enter your password')).toBeFocused();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(page.getByRole('heading', { level: 2, name: 'Welcome back' })).toBeVisible();
    });
  });
});
