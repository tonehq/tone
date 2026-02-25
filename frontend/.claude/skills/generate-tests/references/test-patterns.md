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

## Mock JWT for auth tests

The app uses `decodeJWT` which does `Buffer.from(payload, 'base64').toString()` then `JSON.parse`.
Use this pre-computed mock JWT with `exp: 9999999999` (expires year 2286):

```typescript
// Payload: {"sub":"user123","exp":9999999999}
export const MOCK_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' +
  '.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjo5OTk5OTk5OTk5fQ==' +
  '.mock-signature';

export const MOCK_LOGIN_RESPONSE = {
  access_token: MOCK_JWT,
  user_id: 'user123',
  organizations: [{ id: 'org123', name: 'Test Org' }],
};
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
suite. A **single tab is reused** across all tests in the worker. This avoids the visual
churn of tabs opening and closing in `--headed` mode and reduces per-test overhead.
State isolation is handled by `beforeEach` hooks (cookies, navigation, route cleanup)
rather than by creating fresh tabs.

```typescript
import { BrowserContext, expect, Page, test as base } from '@playwright/test';

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Worker-scoped context = one browser window shared across all tests in this worker.
// Single tab = reused across all tests; beforeEach resets state between tests.
// IMPORTANT: name the Playwright fixture callback "provide", NOT "use".
// ESLint's react-hooks/rules-of-hooks treats any call to a function named "use"
// inside a lowercase function (e.g. "page") as an illegal React Hook call.
// Playwright only cares about the callback's position, not its name.
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
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

// ── Mock data ────────────────────────────────────────────────────────────────
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
test.describe('<PageName> Page', () => {
  test.beforeEach(async ({ page }) => {
    // Clear routes from previous tests (prevents bleed between tests)
    await page.unrouteAll({ behavior: 'wait' });
    await page.goto('/route');
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
expect(accessToken?.value).toBe(MOCK_JWT);
```

---

## Keyboard navigation

```typescript
await page.keyboard.press('Tab');        // move focus
await page.keyboard.press('Enter');      // activate focused element
await page.keyboard.press('Escape');     // close dialog/menu
await page.keyboard.press('Space');      // check checkbox
```
