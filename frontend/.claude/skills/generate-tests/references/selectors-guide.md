# Selector Guide — MUI + Next.js Components

## Selector priority (most resilient to least)

1. `getByRole` with accessible name — most resilient to UI changes
2. `getByLabel` — for labelled form inputs
3. `getByPlaceholder` — for unlabelled inputs with placeholder text
4. `getByText` — for static text content
5. `getByTestId` — only when no semantic option exists

---

## MUI TextField (used by TextInput component)

MUI TextField renders an `<input>` inside layers of `<div>`. The `name`, `type`, and `placeholder`
attributes are on the actual `<input>` element.

```typescript
// By placeholder (most reliable for TextInput since labels use Typography, not htmlFor)
page.getByPlaceholder('Enter your email');
page.getByPlaceholder('Enter your password');

// By name attribute (fallback)
page.locator('input[name="email"]');
page.locator('input[name="password"]');

// By type
page.locator('input[type="email"]');
page.locator('input[type="password"]');
```

> **Important**: The `TextInput` component in this project renders the label as a MUI `Typography`
> with `component="label"` but WITHOUT `htmlFor`. This means `getByLabel()` will NOT reliably
> associate with the input. Always use `getByPlaceholder()` for TextInput elements.

---

## MUI Button / CustomButton

CustomButton renders a standard MUI `<Button>` which produces a `<button>` element.

```typescript
// By accessible name (button text)
page.getByRole('button', { name: 'Continue' });
page.getByRole('button', { name: 'Continue with Google' });
page.getByRole('button', { name: 'Loading...' }); // when loading=true

// During loading state, the text becomes "Loading..." and button is disabled
page.getByRole('button', { name: 'Loading...' });
```

---

## MUI Checkbox (with FormControlLabel)

```typescript
// The checkbox role is present on the <input type="checkbox"> element
page.getByRole('checkbox'); // when only one checkbox on page
page.getByRole('checkbox', { name: /remember me/i }); // if label is associated

// Assertions
await expect(page.getByRole('checkbox')).toBeChecked();
await expect(page.getByRole('checkbox')).not.toBeChecked();
```

> **Note**: MUI `FormControlLabel` wraps the checkbox and label together. The accessible name
> may or may not be correctly associated depending on MUI version. Prefer `getByRole('checkbox')`
> when only one checkbox is on the page.

---

## MUI Link / Next.js Link

```typescript
// By role and name
page.getByRole('link', { name: /forgot password/i });
page.getByRole('link', { name: /sign up/i });

// Navigation assertion
await page.getByRole('link', { name: /forgot password/i }).click();
await expect(page).toHaveURL(/\/auth\/forgotpassword/);
```

---

## Sonner Toast (showToast function)

`showToast` from `@/utils/toast` renders Sonner toast notifications.
Sonner renders toasts as `<li data-sonner-toast>` elements with title and description
in separate child elements.

```typescript
import { Page } from '@playwright/test';

// Define this helper once at the top of every spec file
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

// Wait for and check notification (title)
await expect(getToast(page)).toBeVisible({ timeout: 5000 });
await expect(getToast(page)).toContainText('Login Successful');

// Check title and description separately
await expect(getToast(page)).toContainText('Login Successful');
await expect(getToast(page)).toContainText('Welcome back!');

// Find a toast with specific text (useful when multiple toasts may appear)
await expect(page.locator('[data-sonner-toast]', { hasText: 'Login Failed' })).toBeVisible();

// Assert no toast appeared (e.g. after HTML5 validation blocked submit)
await expect(getToast(page)).not.toBeVisible();
```

---

## MUI CircularProgress (loading spinner)

```typescript
// By CSS class (fallback when no role/text works)
page.locator('.MuiCircularProgress-root');
await expect(page.locator('.MuiCircularProgress-root')).toBeVisible();
```

---

## Next.js Image / raw img

```typescript
// By alt text
page.getByAltText('Google');
page.getByRole('img', { name: 'Google' });
```

---

## Common typography elements

```typescript
// Headings
page.getByRole('heading', { name: 'Log in to your account' });
page.getByRole('heading', { level: 4 });

// Regular text (use getByText for body copy)
page.getByText('Welcome back! Enter your credentials to access your account');
page.getByText("Don't have an account?");
```

---

## Form element

```typescript
// The Form component renders a <form> element
page.locator('form');

// Trigger submit via button
page.getByRole('button', { name: 'Continue' }).click();

// Or via keyboard
page.getByPlaceholder('Enter your password').press('Enter');
```

---

## Password visibility toggle (TextInput with type="password")

```typescript
// The eye icon button has aria-label="toggle password visibility"
page.getByRole('button', { name: /toggle password visibility/i });

// Or by aria-label exactly
page.getByLabel('toggle password visibility');
```

---

## IconButton (generic)

```typescript
// MUI IconButton renders a <button> with aria-label if provided
page.getByRole('button', { name: 'close' }); // close button
page.getByRole('button', { name: 'toggle password visibility' });
```

---

## Scoping selectors to avoid ambiguity

```typescript
// Scope to a specific section
const form = page.locator('form');
form.getByPlaceholder('Enter your email');

// Scope to a specific test id
const card = page.locator('[data-testid="login-card"]');
card.getByRole('button', { name: 'Continue' });
```

---

## Debugging selectors

```typescript
// Print all matching elements for debugging
const count = await page.getByRole('button').count();
console.log(`Found ${count} buttons`);

// Highlight element in headed mode
await page.getByPlaceholder('Enter your email').highlight();
```
