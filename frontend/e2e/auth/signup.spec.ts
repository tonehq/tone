import { test as base, BrowserContext, expect, Page } from '@playwright/test';

// ── Toast helper ─────────────────────────────────────────────────────────────
// Sonner renders toasts as <li data-sonner-toast> elements. Use this helper
// to locate the most recent visible toast for assertions.
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Signup page is public — no loginViaUI needed.
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
// Auth pages have no sidebar. Skip navigation if already on the page,
// fall back to hard page.goto() otherwise (e.g. after redirect to check-email).
// Test groups that need a clean form add their own nested beforeEach.
async function ensureOnSignupPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/signup')) return;
  await page.goto('/auth/signup');
}

// ── Mock data ─────────────────────────────────────────────────────────────────
const MOCK_SIGNUP_RESPONSE = { message: 'User created successfully' };

const MOCK_ORG_EXISTS_RESPONSE = {
  exists: true,
  organization: {
    id: 1,
    name: 'Existing Org',
    slug: 'existing-org',
    allow_access_requests: true,
  },
};

const MOCK_ORG_NOT_EXISTS_RESPONSE = { exists: false };

const TEST_USER = {
  email: 'test@example.com',
  password: 'Test@123',
  orgName: 'Test Organisation',
};

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Signup Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnSignupPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "Create your account" heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Create your account' })).toBeVisible();
    });

    test('shows the subtitle text', async ({ page }) => {
      await expect(page.getByText('Get started with Voice AI in minutes')).toBeVisible();
    });

    test('shows the email input', async ({ page }) => {
      const emailInput = page.getByPlaceholder('Enter your email');
      await expect(emailInput).toBeVisible();
      await expect(emailInput).toHaveAttribute('type', 'email');
    });

    test('shows the password input', async ({ page }) => {
      const passwordInput = page.getByPlaceholder('Create a password');
      await expect(passwordInput).toBeVisible();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });

    test('shows the optional organisation name input', async ({ page }) => {
      await expect(page.getByPlaceholder('Enter your organisation name')).toBeVisible();
    });

    test('shows the "Create account" submit button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible();
    });

    test('shows the "Sign up with Google" button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Sign up with Google' })).toBeVisible();
    });

    test('shows the Google icon inside the Google button', async ({ page }) => {
      await expect(page.getByRole('img', { name: 'Google' })).toBeVisible();
    });

    test('shows the "Already have an account?" text', async ({ page }) => {
      await expect(page.getByText('Already have an account?')).toBeVisible();
    });

    test('shows the "Log in" link', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Welcome back' })).toBeVisible();
    });
  });

  // ── 2. Navigation ──────────────────────────────────────────────────────────
  test.describe('Navigation', () => {
    test('navigates to the login page via "Log in" link', async ({ page }) => {
      await page.getByRole('link', { name: 'Welcome back' }).click();
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });

    test('renders the "Log in" link with correct href', async ({ page }) => {
      await expect(page.getByRole('link', { name: 'Welcome back' })).toHaveAttribute(
        'href',
        '/auth/login',
      );
    });
  });

  // ── 3. Form Validation ────────────────────────────────────────────────────
  test.describe('Form Validation', () => {
    // Form validation needs a clean form — hard nav resets field values
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('stays on signup page when email is empty', async ({ page }) => {
      // TextInput `isRequired` shows a visual asterisk only — the underlying input
      // does NOT have the HTML `required` attribute, so the form submits and the
      // API rejects the empty value. The page must stay on /auth/signup.
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('stays on signup page when password is empty', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByRole('button', { name: 'Create account' }).click();
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('prevents submit with invalid email format', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').fill('not-an-email');
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();
      // Browser email input validation blocks submit for invalid format
      await expect(page).toHaveURL(/\/auth\/signup/);
    });
  });

  // ── 4. Signup Success ─────────────────────────────────────────────────────
  test.describe('Signup Success', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('redirects to check-email page on successful signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('passes email as query param to check-email page', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(new RegExp(`email=${encodeURIComponent(TEST_USER.email)}`), {
        timeout: 10_000,
      });
    });

    test('shows success notification on signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Account Created');
    });

    test('sends correct email and password payload to the signup API', async ({ page }) => {
      let requestBody: Record<string, unknown> = {};
      await page.route('**/auth/signup', async (route) => {
        requestBody = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill(TEST_USER.orgName);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
      expect(requestBody.email).toBe(TEST_USER.email);
      expect(requestBody.password).toBe(TEST_USER.password);
      expect(requestBody.org_name).toBe(TEST_USER.orgName);
    });
  });

  // ── 4b. Redirect Param ────────────────────────────────────────────────────
  test.describe('Redirect Param', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup?redirect=%2Finvited-page');
    });

    test('stores the redirect path in localStorage on successful signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });

      // The component stores the redirect value in localStorage before navigating
      const stored = await page.evaluate(() => localStorage.getItem('invite_redirect'));
      expect(stored).toBe('/invited-page');
    });

    test('still redirects to check-email when redirect param is present', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('does not store invite_redirect when no redirect param is present', async ({ page }) => {
      // Navigate to signup WITHOUT a redirect param
      await page.goto('/auth/signup');
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      // Clear any pre-existing value
      await page.evaluate(() => localStorage.removeItem('invite_redirect'));

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });

      const stored = await page.evaluate(() => localStorage.getItem('invite_redirect'));
      expect(stored).toBeNull();
    });
  });

  // ── 4c. Firebase Signup Flow ───────────────────────────────────────────────
  test.describe('Firebase Signup Flow', () => {
    // firebase_signup=true changes the post-success redirect from /auth/check-email to /home.
    // Without firebase_uid in the URL, params.get('firebase_uid') is null, so the regular
    // /auth/signup endpoint is used (not /auth/firebase_signup).
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup?firebase_signup=true');
    });

    test('redirects toward /home on successful signup when firebase_signup=true', async ({
      page,
    }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      // router.push('/home') is called; middleware may redirect unauthenticated
      // users to /auth/login?redirect=/home — both are acceptable here.
      await page.waitForURL((url) => !url.pathname.includes('/auth/signup'), {
        timeout: 10_000,
      });

      const currentUrl = page.url();
      // URL must reference /home (directly or in the redirect query param after middleware)
      expect(currentUrl.includes('/home') || currentUrl.includes('%2Fhome')).toBe(true);
    });

    test('does NOT redirect to check-email when firebase_signup=true', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await page.waitForURL((url) => !url.pathname.includes('/auth/signup'), {
        timeout: 10_000,
      });

      await expect(page).not.toHaveURL(/\/auth\/check-email/);
    });

    test('still shows success notification when firebase_signup=true', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_SIGNUP_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Account Created');
    });
  });

  // ── 5. Signup Error ────────────────────────────────────────────────────────
  test.describe('Signup Error', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('shows error notification on API 400 failure', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Email already registered' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Email already registered');
    });

    test('stays on signup page after API error', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('shows error notification on network failure', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Something went wrong');
    });
  });

  // ── 6. Organisation Check ──────────────────────────────────────────────────
  test.describe('Organisation Check', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('shows warning and blocks submit when organisation name already exists', async ({
      page,
    }) => {
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

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill('Existing Org');

      // Wait for the 500ms debounce + network round-trip to complete
      await page.waitForTimeout(800);

      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Organization Exists');
      // Submit was blocked — must stay on signup page
      await expect(page).toHaveURL(/\/auth\/signup/);
    });

    test('allows submit when organisation name does not exist', async ({ page }) => {
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

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Enter your organisation name').fill('New Org');

      await page.waitForTimeout(800);

      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('skips org check when organisation name is less than 2 characters', async ({ page }) => {
      let orgCheckCalled = false;
      await page.route('**/auth/check_organization_exists**', async (route) => {
        orgCheckCalled = true;
        await route.continue();
      });

      await page.getByPlaceholder('Enter your organisation name').fill('A');
      await page.waitForTimeout(800);

      expect(orgCheckCalled).toBe(false);
    });

    test('triggers org check when organisation name is exactly 2 characters', async ({ page }) => {
      // The guard is `orgName.trim().length < 2` — length of 2 passes the check.
      let orgCheckCalled = false;
      await page.route('**/auth/check_organization_exists**', async (route) => {
        orgCheckCalled = true;
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_ORG_NOT_EXISTS_RESPONSE),
        });
      });

      await page.getByPlaceholder('Enter your organisation name').fill('AB');
      // Wait for 500ms debounce + network
      await page.waitForTimeout(800);

      expect(orgCheckCalled).toBe(true);
    });

    test('skips org check when organisation name is only whitespace', async ({ page }) => {
      // '  '.trim().length === 0 — should not trigger
      let orgCheckCalled = false;
      await page.route('**/auth/check_organization_exists**', async (route) => {
        orgCheckCalled = true;
        await route.continue();
      });

      await page.getByPlaceholder('Enter your organisation name').fill('  ');
      await page.waitForTimeout(800);

      expect(orgCheckCalled).toBe(false);
    });
  });

  // ── 7. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/signup');
    });

    test('shows loading state on the "Create account" button during signup', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        // Delay then abort — keeps page on signup (no navigation race).
        // route.abort() prevents success handler from navigating after assertion.
        await new Promise((resolve) => setTimeout(resolve, 2_000));
        await route.abort('failed');
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      // CustomButton keeps its "Create account" text but disables and shows Loader2 spinner
      const createBtn = page.getByRole('button', { name: 'Create account' });
      await expect(createBtn).toBeDisabled({ timeout: 1_000 });
      await expect(page.locator('[class*="animate-spin"]')).toBeVisible({ timeout: 1_000 });
    });

    test('re-enables the "Create account" button after signup failure', async ({ page }) => {
      await page.route('**/auth/signup', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Email already registered' }),
        });
      });

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByRole('button', { name: 'Create account' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(page.getByRole('button', { name: 'Create account' })).toBeEnabled({
        timeout: 5_000,
      });
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

      await page.getByPlaceholder('Enter your email').fill(TEST_USER.email);
      await page.getByPlaceholder('Create a password').fill(TEST_USER.password);
      await page.getByPlaceholder('Create a password').press('Enter');

      await expect(page).toHaveURL(/\/auth\/check-email/, { timeout: 10_000 });
    });

    test('allows keyboard navigation through form inputs', async ({ page }) => {
      await page.getByPlaceholder('Enter your email').focus();
      await expect(page.getByPlaceholder('Enter your email')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByPlaceholder('Create a password')).toBeFocused();

      await page.keyboard.press('Tab');
      // Next Tab: either password visibility toggle or org name input
      // (visibility toggle has tabIndex=-1 so Tab skips it)
      await expect(page.getByPlaceholder('Enter your organisation name')).toBeFocused();
    });

    test('renders the heading at the correct level', async ({ page }) => {
      await expect(
        page.getByRole('heading', { level: 4, name: 'Create your account' }),
      ).toBeVisible();
    });
  });
});
