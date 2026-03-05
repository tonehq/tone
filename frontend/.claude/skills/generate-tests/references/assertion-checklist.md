# Assertion Checklist — Playwright Tests

## Required assertions per test category

For every test group, apply the assertions listed. No group should be skipped.

---

## 1. Page Rendering

Every interactive and visible element must have at least one visibility assertion.

```typescript
// Element is visible
await expect(locator).toBeVisible();

// Element contains expected text
await expect(locator).toContainText('...');
await expect(locator).toHaveText('...');

// Element has expected attribute
await expect(locator).toHaveAttribute('type', 'email');
await expect(locator).toHaveAttribute('placeholder', '...');

// Checkbox default state
await expect(page.getByRole('checkbox')).toBeChecked();
await expect(page.getByRole('checkbox')).not.toBeChecked();
```

---

## 2. Navigation

```typescript
// URL changed to exact path
await expect(page).toHaveURL('/auth/forgotpassword');

// URL matches pattern
await expect(page).toHaveURL(/\/auth\/forgotpassword/);

// Still on same page (navigation did NOT happen)
await expect(page).toHaveURL(/\/auth\/login/);

// Title changed
await expect(page).toHaveTitle('...');
```

---

## 3. Form Validation

```typescript
// Page did not navigate away (validation blocked submit)
await expect(page).toHaveURL(/\/auth\/login/);

// Error message appeared
await expect(page.getByRole('alert')).toBeVisible();
await expect(page.getByRole('alert')).toContainText('...');

// Input is in error state (MUI TextField error prop)
await expect(page.locator('input[name="email"]')).toHaveAttribute('aria-invalid', 'true');

// Browser native validation message is shown
// (Playwright does not assert native tooltips — check URL did not change instead)
```

---

## 4. API Mocking — Verify request was made

```typescript
// Capture and assert request body
let requestBody: Record<string, string> = {};
await page.route('**/auth/login', async (route) => {
  requestBody = route.request().postDataJSON();
  await route.fulfill({ status: 200, body: JSON.stringify(MOCK_RESPONSE) });
});
// ... interact ...
expect(requestBody.email).toBe('test@example.com');
expect(requestBody.password).toBe('password123');
```

---

## 5. User Flows — Success path

```typescript
// Success toast visible (Sonner)
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();
await expect(getToast(page)).toBeVisible({ timeout: 5000 });
await expect(getToast(page)).toContainText('Login Successful');

// Redirected to correct page
await expect(page).toHaveURL(/\/home/, { timeout: 10_000 });

// Cookie was set (auth flows)
const cookies = await page.context().cookies();
const token = cookies.find((c) => c.name === 'tone_access_token');
expect(token).toBeDefined();
```

---

## 6. User Flows — Error path

```typescript
// Error toast visible (Sonner)
await expect(page.locator('[data-sonner-toast]', { hasText: 'Login Failed' })).toBeVisible({ timeout: 5000 });

// Did NOT navigate away
await expect(page).toHaveURL(/\/auth\/login/);

// Form inputs are still present (not cleared)
await expect(page.getByPlaceholder('Enter your email')).toBeVisible();
```

---

## 7. Loading State

```typescript
// CustomButton shows "Loading..." text when loading=true
await expect(page.getByRole('button', { name: 'Loading...' })).toBeVisible({ timeout: 1000 });

// Button is disabled during loading
await expect(page.getByRole('button', { name: 'Loading...' })).toBeDisabled();

// Spinner is visible
await expect(page.locator('.MuiCircularProgress-root')).toBeVisible();

// After operation completes, button returns to normal
await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled({ timeout: 5000 });
```

---

## 8. Element State Assertions

```typescript
// Enabled / disabled
await expect(locator).toBeEnabled();
await expect(locator).toBeDisabled();

// Checked / unchecked
await expect(locator).toBeChecked();
await expect(locator).not.toBeChecked();

// Focused
await expect(locator).toBeFocused();

// Empty / has value
await expect(locator).toBeEmpty();
await expect(locator).toHaveValue('expected@email.com');

// Count
await expect(page.getByRole('button')).toHaveCount(2);
```

---

## 9. Accessibility Assertions

```typescript
// Element has accessible name
await expect(page.getByRole('img')).toHaveAttribute('alt', 'Google');

// Form inputs are keyboard accessible
await page.keyboard.press('Tab');
await expect(page.getByPlaceholder('Enter your email')).toBeFocused();

// Interactive elements are not divs with click handlers
// (verified during code review, not directly assertable in Playwright)

// Toast is visible (Sonner)
await expect(page.locator('[data-sonner-toast]').first()).toBeVisible();
```

---

## Sonner toast helper — avoid selector issues

Sonner renders toasts as `<li data-sonner-toast>` elements. Use the locator helper:

```typescript
import { Page } from '@playwright/test';

// Declare once per spec file, above the test.describe block
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

// Usage
await expect(getToast(page)).toBeVisible({ timeout: 5000 });
await expect(getToast(page)).toContainText('Login Failed');
await expect(getToast(page)).not.toBeVisible(); // no toast shown

// Find toast with specific text
await expect(page.locator('[data-sonner-toast]', { hasText: 'Error' })).toBeVisible();
```

---

## Notification format reference

`showToast` from `@/utils/toast` renders title (and optional description) in the toast element.
`handleApiError` from `@/utils/helpers` extracts `error.response.data.detail` and shows it as the toast title.

| Scenario                            | Toast text                                    |
| ----------------------------------- | --------------------------------------------- |
| Login success                       | Title: `Login Successful`, Desc: `Welcome back!` |
| Login failed (empty/falsy response) | Title: `Login Failed`, Desc: `Please enter email and password` |
| API error with detail               | Title: the `detail` value from the API response |
| API error / network failure         | Title: `Something went wrong. Please try again.` |

---

## Timeout guide

| Scenario                      | Recommended timeout |
| ----------------------------- | ------------------- |
| Element visible on page load  | `default (5s)`      |
| API response and notification | `5_000` ms          |
| Redirect after login          | `10_000` ms         |
| Loading state appears         | `1_000` ms          |
| Loading state disappears      | `5_000` ms          |

---

## Anti-patterns to avoid

```typescript
// ❌ Hard-coded sleep — use expect with timeout instead
await page.waitForTimeout(2000);

// ✅ Wait for condition
await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 5000 });

// ❌ XPath selectors — fragile and unreadable
page.locator('//div[@class="MuiAlert-message"]');

// ✅ Data attribute selectors for toast
page.locator('[data-sonner-toast]');

// ❌ Depending on CSS classes for logic — breaks on library updates
page.locator('.MuiButton-contained');

// ✅ Role + name
page.getByRole('button', { name: 'Continue' });

// ❌ No timeout on async assertions — can give false positives
await expect(page.locator('[data-sonner-toast]').first()).toBeVisible();

// ✅ Explicit timeout for async events
await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 5000 });
```
