# Playwright Test Patterns — Next.js + MUI

## playwright.config.ts template

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'yarn dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

---

## API Mocking with page.route()

Always use `**/path` pattern so tests are backend-URL-agnostic:

```typescript
// Successful API response
await page.route('**/auth/login', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access_token: MOCK_JWT, user_id: 'user123' }),
  });
});

// Error response (4xx/5xx)
await page.route('**/auth/login', async (route) => {
  await route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Invalid credentials' }),
  });
});

// Network failure
await page.route('**/auth/login', async (route) => {
  await route.abort('failed');
});

// Delayed response (to test loading state)
await page.route('**/auth/login', async (route) => {
  await new Promise((resolve) => setTimeout(resolve, 2000));
  await route.abort('failed');
});

// Remove a route after use
await page.unroute('**/auth/login');
```

---

## Authentication for dashboard pages — loginViaUI (login once per worker)

Dashboard pages (under `(dashboard)/`) require a `tone_access_token` cookie. Instead of
manually injecting cookies, use the **shared auth helper** that logs in through the actual
login page UI against the real backend. The app's `setToken()` function sets all 4 cookies naturally.

**Critical rules**:
- Login happens **once per worker** in the worker-scoped fixture, NOT in `beforeEach`
- `beforeEach` uses **soft navigation** — skips reload if already on the target page, uses
  sidebar links for client-side navigation when on another dashboard page, and only falls
  back to hard `page.goto()` when outside the dashboard layout (e.g., after Auth Redirect)
- This combination reduces test run time dramatically (e.g., 43 tests: 2.9 min → 18 sec)

**Helper location**: `e2e/helpers/auth.ts`

**Exports**:
- `loginViaUI(page, options?)` — logs in via the login page against the real backend
- `TEST_EMAIL`, `TEST_PASSWORD` — default test credentials (overridable via env vars)

**Usage in dashboard spec files** (login-once pattern):

```typescript
import { loginViaUI, TEST_EMAIL } from '../helpers/auth';

const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      // Login once per worker — sets all auth cookies on the context
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

// Soft navigation helper — avoids hard reloads between tests.
// Skips navigation if already on the target page, uses sidebar link for
// client-side routing when on another dashboard page, and only falls back
// to page.goto() when outside the dashboard layout (e.g., /auth/login).
async function ensureOnPage(page: Page, targetPath: string): Promise<void> {
  if (page.url().includes(targetPath)) return;

  const sidebarLink = page.locator(`a[href="${targetPath}"]`).first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(new RegExp(targetPath.replace('/', '\\/')), { timeout: 5_000 });
    return;
  }

  await page.goto(targetPath);
}

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    // Soft-navigate — skips reload if already there, uses sidebar link otherwise
    await ensureOnPage(page, '/your-dashboard-route');
  });
});
```

**What loginViaUI does**:
1. Navigates to `/auth/login`
2. Fills email + password and clicks Continue
3. The real backend validates credentials, returns a JWT
4. The app's `login()` → `setToken()` runs, which:
   - Decodes the JWT to get the `exp` claim
   - Sets `tone_access_token` cookie (JWT)
   - Sets `org_tenant_id` cookie (first org ID)
   - Sets `login_data` cookie (full response JSON)
   - Sets `user_id` cookie
5. Waits for redirect to `/home`

**Cookies set by loginViaUI** (all via the app, not manually):

| Cookie | Value | Source |
|--------|-------|--------|
| `tone_access_token` | JWT from backend | Real backend response |
| `org_tenant_id` | Org ID or empty | `organizations[0].id` |
| `login_data` | JSON string | Full login response |
| `user_id` | User ID | Backend response |

**Tests that clear cookies (e.g., Auth Redirect)** must save and restore them:

```typescript
test.describe('Auth Redirect', () => {
  let savedCookies: Awaited<ReturnType<BrowserContext['cookies']>>;

  test.beforeEach(async ({ page }) => {
    savedCookies = await page.context().cookies();
  });

  test.afterEach(async ({ page }) => {
    await page.context().addCookies(savedCookies);
  });

  test('redirects to login when no auth cookie is set', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/home');
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
  });
});
```

> **IMPORTANT**: For dashboard pages, always use `loginViaUI` in the worker-scoped
> fixture (login once), NOT in `beforeEach`. This exercises the real login flow,
> ensures all cookies are set correctly, and keeps test runs fast.

---

## Real backend login (no mocks)

Tests authenticate against the **real backend** — no mock JWT or mock API responses.
The `loginViaUI` helper fills and submits the actual login form. Credentials default to
env vars `PLAYWRIGHT_TEST_EMAIL` / `PLAYWRIGHT_TEST_PASSWORD` or hardcoded test account values.

```typescript
import { loginViaUI, TEST_EMAIL } from '../helpers/auth';
```

---

## Page navigation

```typescript
// Always use relative paths — baseURL is set in playwright.config.ts
await page.goto('/auth/login');
await page.goto('/auth/signup?redirect=/home');
```

---

## Waiting for navigation

```typescript
// Wait for URL change
await expect(page).toHaveURL('/home', { timeout: 10_000 });
await expect(page).toHaveURL(/\/home/);

// Wait for network idle after navigation
await Promise.all([
  page.waitForURL('/home'),
  page.getByRole('button', { name: 'Continue' }).click(),
]);
```

---

## Waiting for notifications (MUI Snackbar + Alert)

MUI Alert renders with `role="alert"`. The notification message format in this project is:
`"${title}: ${message}"` (e.g., "Login Successful: Welcome back!")

```typescript
await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
await expect(page.getByRole('alert')).toContainText('Login Successful');
await expect(page.getByRole('alert')).toContainText('Login Failed');
```

---

## Form submission

```typescript
// Fill and submit
await page.getByPlaceholder('Enter your email').fill('test@example.com');
await page.getByPlaceholder('Enter your password').fill('password123');
await page.getByRole('button', { name: 'Continue' }).click();

// Alternatively, press Enter to submit
await page.getByPlaceholder('Enter your password').press('Enter');
```

---

## Test structure template

**Browser lifecycle**: one browser window (context) per worker — stays open for the full
suite. **Login happens once** in the worker fixture. A **single tab is reused** across all
tests in the worker. **Soft navigation** avoids hard reloads — tests that stay on the same
page skip navigation entirely, and tests that need to return from another page use sidebar
links for client-side routing. This eliminates visual churn in `--headed` mode and makes
tests blazing fast.

```typescript
import { BrowserContext, expect, Page, test as base } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Worker-scoped context = one browser window shared across all tests in this worker.
// Login happens ONCE during worker setup, not before every test.
// Single tab = reused across all tests; beforeEach uses soft navigation.
// IMPORTANT: name the Playwright fixture callback "provide", NOT "use".
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      // Login once per worker — all auth cookies are set on the context
      const page = await context.newPage();
      await loginViaUI(page);
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    // Reuse the first existing tab, or create one if none exist yet.
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
    // Do NOT close — the same tab is reused across all tests in this worker.
  },
});

// ── Soft navigation helper ───────────────────────────────────────────────────
// Avoids hard page reloads between tests. Three cases:
// 1. Already on target page → skip navigation (0ms)
// 2. On another dashboard page → click sidebar link for client-side nav (~200ms)
// 3. Outside dashboard (e.g., /auth/login) → fall back to page.goto() (~400ms)
async function ensureOnPage(page: Page, targetPath: string): Promise<void> {
  if (page.url().includes(targetPath)) return;

  const sidebarLink = page.locator(`a[href="${targetPath}"]`).first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(new RegExp(targetPath.replace('/', '\\/')), { timeout: 5_000 });
    return;
  }

  await page.goto(targetPath);
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('<PageName> Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear routes from previous tests (prevents bleed between tests)
    await page.unrouteAll({ behavior: 'wait' });
    // Soft-navigate — skips reload if already there
    await ensureOnPage(page, '/route');
  });

  test.describe('Page Rendering', () => {
    test('shows <element>', async ({ page }) => { ... });
  });

  test.describe('Navigation', () => {
    test('navigates to <page>', async ({ page }) => { ... });
  });

  test.describe('Form Validation', () => {
    test('rejects <invalid input>', async ({ page }) => { ... });
  });

  test.describe('Authentication Flow', () => {
    test('successful <action> redirects to <route>', async ({ page }) => { ... });
    test('failed <action> shows error notification', async ({ page }) => { ... });
    test('network error shows error notification', async ({ page }) => { ... });
  });

  test.describe('Loading State', () => {
    test('shows loading indicator during <action>', async ({ page }) => { ... });
  });
});
```

> **Route isolation with single-tab reuse**: Since the tab is shared, `page.route()` mocks
> from one test persist into the next. Always call `page.unrouteAll({ behavior: 'wait' })`
> in `beforeEach` to clear stale routes. For test files that do NOT use `page.route()`,
> this call can be omitted.

> **Login-once rule**: Dashboard specs must login in the worker fixture, NOT in `beforeEach`.
> Tests that need to clear cookies (e.g., Auth Redirect) must save/restore them using
> `beforeEach`/`afterEach` within their own `test.describe` block.

> **Soft navigation rule**: Use `ensureOnPage(page, '/route')` in `beforeEach` instead of
> `page.goto()`. This skips navigation when already on the target page (most tests),
> uses sidebar links for client-side navigation from other dashboard pages, and only
> falls back to hard reload when outside the dashboard layout.

---

## Auth page soft navigation (login, signup, etc.)

Auth pages are public — no `loginViaUI` needed. The soft navigation strategy is simpler:
skip if already on the page, hard `page.goto()` if not. **No form clearing in the helper** —
`fill('')` triggers React re-renders that can cause element detachment and race conditions.

```typescript
// ── Soft navigation helper ───────────────────────────────────────────────────
// Auth pages have no sidebar, so soft nav = skip if already on the page.
// Falls back to hard page.goto() when on a different URL.
// Test groups that need a clean form add their own nested beforeEach with page.goto().
async function ensureOnLoginPage(page: Page): Promise<void> {
  if (page.url().includes('/auth/login')) return;
  await page.goto('/auth/login');
}

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnLoginPage(page);
  });

  // Read-only groups — soft nav skips reload (Page Rendering, Accessibility)
  test.describe('Page Rendering', () => {
    test('shows the heading', async ({ page }) => { ... });
  });

  // Form groups — nested beforeEach forces clean form
  test.describe('Form Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login'); // needs clean form state
    });
    test('rejects invalid email', async ({ page }) => { ... });
  });

  // Auth flow — hard nav + clear cookies after (setToken sets cookies)
  test.describe('Authentication Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/auth/login');
    });
    test.afterEach(async ({ page }) => {
      await page.context().clearCookies();
    });
    test('successful login redirects to home', async ({ page }) => { ... });
  });
});
```

**Key rules for auth page soft nav**:
- **No form clearing in the helper** — `fill('')` causes React re-renders and element detachment. Skip-or-goto only.
- **Form Validation groups** need a nested `beforeEach` with `page.goto()` to reset field values.
- **Auth Flow groups** (that mock login API with 200) must `clearCookies()` in `afterEach` — the mock triggers `setToken()` which sets real auth cookies that persist and can interfere with subsequent tests.
- **Loading state mocks** should use `route.abort()` not `route.fulfill()` to prevent the success handler from navigating after the test ends.

---

## CustomButton loading state

`CustomButton` with `loading={true}` renders:
- Button text changes from `text` prop to `"Loading..."`
- Button gets `disabled` attribute
- `CircularProgress` spinner appears as start icon

```typescript
// Check loading state
await expect(page.getByRole('button', { name: 'Loading...' })).toBeVisible();
await expect(page.getByRole('button', { name: 'Loading...' })).toBeDisabled();
```

---

## TextInput password toggle

TextInput with `type="password"` renders an eye icon button with `aria-label="toggle password visibility"`.

```typescript
const passwordInput = page.getByPlaceholder('Enter your password');
await expect(passwordInput).toHaveAttribute('type', 'password');

await page.getByRole('button', { name: /toggle password visibility/i }).click();
await expect(passwordInput).toHaveAttribute('type', 'text');
```

---

## Checking cookies (for auth tests)

```typescript
const cookies = await page.context().cookies();
const accessToken = cookies.find((c) => c.name === 'tone_access_token');
expect(accessToken).toBeDefined();
expect(accessToken!.value.length).toBeGreaterThan(0);
```

---

## Keyboard navigation

```typescript
await page.keyboard.press('Tab');        // move focus
await page.keyboard.press('Enter');      // activate focused element
await page.keyboard.press('Escape');     // close dialog/menu
await page.keyboard.press('Space');      // check checkbox
```
