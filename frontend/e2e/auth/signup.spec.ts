import { test as base, BrowserContext, expect, Page } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD } from '../helpers/auth';

// ── Alert helper ─────────────────────────────────────────────────────────────
// Next.js injects an empty <div role="alert"> route announcer on every page.
// Filter it out to avoid strict-mode violations when asserting notifications.
const getAlert = (p: Page) => p.getByRole('alert').filter({ hasText: /\S+/ });

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Auth pages are public — no loginViaUI needed.
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

// ── Soft navigation helper ───────────────────────────────────────────────────
// Auth pages have no sidebar, so soft nav = skip if already on the page.
// Falls back to hard page.goto() when on a different URL (e.g., after signup
// redirects to /auth/check-email). Test groups that need a clean form
// add their own nested beforeEach with page.goto().
async function ensureOnSignupPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/signup')) return;
  await page.goto('/auth/signup');
}

// ── Mock data ────────────────────────────────────────────────────────────────
const MOCK_SIGNUP_RESPONSE = {
  status: 200,
  message: 'User created successfully',
};

const MOCK_ORG_EXISTS_RESPONSE = {
  exists: true,
  organization: { id: 1, name: 'Existing Org', slug: 'existing-org', allow_access_requests: true },
};

const MOCK_ORG_NOT_EXISTS_RESPONSE = {
  exists: false,
};

const TEST_USER = {
  username: 'testuser',
  email: TEST_EMAIL,
  password: TEST_PASSWORD,
  orgName: 'Test Organisation',
};

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Signup Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    // Soft-navigate — skips reload if already on page, hard nav otherwise
    await ensureOnSignupPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the signup heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(page.getByText('Get started with Voice AI in minutes')).toBeVisible();
    });

    test('shows the username input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your username')).toBeVisible();
    });

    test('shows the email input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your email')).toBeVisible();
    });

    test('shows the password input', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Create a password');
      await expect(passwordInput).toBeVisible();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('shows the organisation name input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your organisation name')).toBeVisible();
    });

    test('shows the Create account button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
    });

    test('shows the Sign up with Google button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Sign up with Google' })).toBeVisible();
    });

    test('shows the "Already have an account?" text', async ({ page }) => {
      await expect(page.getByText('Already have an account?')).toBeVisible();
    });

    test('shows the Log in link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Log in' })).toBeVisible();
    });

    test('shows the Google icon in the Google button', async ({ page }) => {
      await expect(page.getByRole('img', { name: 'Google' })).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to the login page via "Log in" link', async ({ page }) => {
      await page.getByRole('link', { name: 'Log in' }).click();
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('renders the Log in link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Log in' })).toHaveAttribute(
        'href',
        '/auth/login',
      );
    });
  });

  // ── 3. Form Validation ────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    // Form validation tests need a clean form — hard nav to reset field values
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('prevents submit with empty username', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();
      // HTML5 required validation blocks submit — stays on signup page
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('prevents submit with empty email', async ({ page }) => {
      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('prevents submit with empty password', async ({ page }) => {
      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByRole('button', { name: 'Create account' }).click();
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('prevents submit with invalid email format', async ({ page }) => {
      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill('not-an-email');
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();
      // Browser email validation blocks submit
      await expect(page).toHaveURL(/\/auth\/signup/);
    });
  });

  // ── 4. User Flows — Signup Success ─────────────────────────────────────────
  test.describe('Signup Success', () => {
    test('redirects to check-email page on successful signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('shows success notification on signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Account Created');
    });

    test('passes username and email as query params to check-email page', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(
        new RegExp(`username=${encodeURIComponent(TEST_USER.username)}`),
        { timeout: 10_000 },
      );
      await expect(page).toHaveURL(new RegExp(`email=${encodeURIComponent(TEST_USER.email)}`));
    });

    test('sends correct payload to the signup API', async ({ page }) => {
      let requestBody: Record<string, unknown> = {};
      await page.route('**/auth/signup', async (route) => {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill(TEST_USER.orgName);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
      expect(requestBody.email).toBe(TEST_USER.email);
      expect(requestBody.username).toBe(TEST_USER.username);
      expect(requestBody.password).toBe(TEST_USER.password);
      expect(requestBody.org_name).toBe(TEST_USER.orgName);
    });
  });

  // ── 5. User Flows — Signup Error ───────────────────────────────────────────
  test.describe('Signup Error', () => {
    test('shows error notification on API failure', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Email already registered' }),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Sign Up Failed');
      await expect(getAlert(page)).toContainText('Email already registered');
    });

    test('stays on signup page after API error', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Sign Up Failed');
    });
  });

  // ── 6. Organization Check ──────────────────────────────────────────────────
  test.describe('Organization Check', () => {
    test('shows warning when organization name already exists', async ({ page }) => {
      await page.route('**/auth/check_organization_exists**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ORG_EXISTS_RESPONSE),
        });
      });
      // Block signup so we don't navigate away
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill('Existing Org');

      // Wait for the debounced org check to complete (500ms + network)
      await page.waitForTimeout(800);

      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getAlert(page)).toBeVisible({ timeout: 5_000 });
      await expect(getAlert(page)).toContainText('Organization Exists');
      // Should NOT navigate away — submit was blocked
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('allows submit when organization name does not exist', async ({ page }) => {
      await page.route('**/auth/check_organization_exists**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ORG_NOT_EXISTS_RESPONSE),
        });
      });
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill('New Org');

      await page.waitForTimeout(800);

      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });
  });

  // ── 7. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows loading state on the button during signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        // Delay then abort — keeps the page on signup (no navigation race).
        // Consistent with login spec's loading state pattern.
        await new Promise((resolve) => setTimeout(resolve, 2_000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      // Button should show "Loading..." and be disabled during the request
      await expect(page.getByRole('button', { name: 'Loading...' })).toBeVisible({
        timeout: 1_000,
      });
      await expect(page.getByRole('button', { name: 'Loading...' })).toBeDisabled();
    });
  });

  // ── 8. Accessibility ───────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('allows toggling password visibility', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Create a password');
      await expect(passwordInput).toHaveAttribute('type', 'password');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'text');

      await page.getByRole('button', { name: /toggle password visibility/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('allows form submission via Enter key', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your username').fill(TEST_USER.username);
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Create a password').press('Enter');

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('renders the heading at correct level', async ({ page }) => {
      await expect(
        page.getByRole('heading', { level: 4, name: 'Create your account' }),
      ).toBeVisible();
    });

    test('allows keyboard navigation through form inputs', async ({ page }) => {
      await page.getByPlaceholder('Enter your username').focus();
      await expect(page.getByPlaceholder('Enter your username')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Enter your email')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Create a password')).toBeFocused();
    });
  });
});
