import { Page } from '@playwright/test';

// ── Test credentials ─────────────────────────────────────────────────────────
// Real credentials for the test account. The login hits the actual backend API.
// Override via environment variables if needed:
//   PLAYWRIGHT_TEST_EMAIL / PLAYWRIGHT_TEST_PASSWORD
export const TEST_EMAIL = process.env.PLAYWRIGHT_TEST_EMAIL ?? 'pegovo3694@dolofan.com';
export const TEST_PASSWORD = process.env.PLAYWRIGHT_TEST_PASSWORD ?? 'Test@123';

/**
 * Log in through the actual login page UI against the real backend.
 *
 * Flow:
 * 1. Navigate to /auth/login
 * 2. Fill email + password and click Continue
 * 3. The real backend validates credentials and returns a JWT
 * 4. The app's `login()` → `setToken()` runs, setting all 4 cookies:
 *    - tone_access_token  (JWT from backend)
 *    - org_tenant_id      (first org ID)
 *    - login_data         (full response as JSON)
 *    - user_id
 * 5. Wait for redirect to /home (confirms login succeeded)
 *
 * Requirements:
 * - The backend must be running (NEXT_PUBLIC_BACKEND_URL)
 * - The test account must exist with the given credentials
 */
export async function loginViaUI(
  page: Page,
  options?: { email?: string; password?: string },
): Promise<void> {
  const email = options?.email ?? TEST_EMAIL;
  const password = options?.password ?? TEST_PASSWORD;

  // Navigate to login page
  await page.goto('/auth/login');

  // Fill the form using the actual login page inputs
  await page.getByPlaceholder('Enter your email').fill(email);
  await page.getByPlaceholder('Enter your password').fill(password);

  // Submit — hits the real backend API, app handles the response
  await page.getByRole('button', { name: 'Continue', exact: true }).click();

  // Wait for the app to redirect after successful login
  await page.waitForURL(/\/home/, { timeout: 15_000 });
}
