/**
 * Tools create flow against the real backend.
 *
 * Scenarios TC-001 … TC-FULL from frontend/e2e/docs/tools-create.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture.
 * - No `page.route` mocks — the form posts to /tool/upsert_tool exactly like
 *   a human user.
 * - Tests that save create a real tool. We collect their ids and delete
 *   them via the UI in the same test or in an afterAll hook.
 */

import { expect, type Page } from '@playwright/test';

import { test } from '../helpers/auth';
import {
  addParameter,
  createCustomToolViaUI,
  deleteToolViaUI,
  gotoCreateCustom,
  gotoCreatePicker,
  setAuthType,
  setHttpMethod,
  uniqueToolName,
} from '../helpers/toolFixtures';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Tools — create', () => {
  test.describe('Type picker', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await gotoCreatePicker(page);
    });

    test('TC-001 picker renders the Custom tile and built-in templates', async ({ page }) => {
      await expect(page.getByText('Custom Tool').first()).toBeVisible();
      // Built-in templates load from /tool/get_template_tools — we don't
      // assert specific tiles because the seed list can vary, but the
      // section heading must always render.
      await expect(page.getByText(/choose a built-in tool/i)).toBeVisible({ timeout: 5_000 });
    });

    test('TC-002 clicking Custom Tool navigates to /tools/create/custom', async ({ page }) => {
      await page.getByText('Custom Tool').first().click();
      await page.waitForURL(/\/tools\/create\/custom/, { timeout: 10_000 });
      await expect(page.locator('input[name="name"]').first()).toBeVisible({ timeout: 10_000 });
    });
  });

  test.describe('Form identity', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await gotoCreateCustom(page);
    });

    test('TC-004 header shows Cancel + Create (no Delete in create mode)', async ({ page }) => {
      await expect(page.getByRole('button', { name: /^cancel$/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /^create$/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /^delete$/i })).toHaveCount(0);
    });
  });

  test.describe('Validation', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await gotoCreateCustom(page);
    });

    test('TC-005 blank name + Create surfaces an inline error', async ({ page }) => {
      // Description and URL stay blank too; Zod resolver reports the first
      // missing field via inline helperText.
      await page.getByRole('button', { name: /^create$/i }).click();
      // Inline error text differs by field; "required" is shared.
      await expect(page.getByText(/required/i).first()).toBeVisible({ timeout: 5_000 });
    });

    test('TC-006 blank description + Create surfaces an inline error', async ({ page }) => {
      await page.locator('input[name="name"]').first().fill(uniqueToolName('desc-test'));
      await page.locator('input[name="url"]').first().fill('https://api.example.com/x');
      await page.getByRole('button', { name: /^create$/i }).click();
      await expect(page.getByText(/required/i).first()).toBeVisible({ timeout: 5_000 });
    });

    test('TC-007 invalid URL + Create surfaces an inline error', async ({ page }) => {
      await page.locator('input[name="name"]').first().fill(uniqueToolName('url-test'));
      await page.locator('textarea[name="description"]').first().fill('Invalid URL probe.');
      await page.locator('input[name="url"]').first().fill('not-a-url');
      await page.getByRole('button', { name: /^create$/i }).click();
      // Zod's URL schema returns "Invalid url" — accept any mention of url.
      await expect(page.getByText(/url|required/i).first()).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe('Form controls', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await gotoCreateCustom(page);
    });

    test('TC-008 HTTP method dropdown exposes all five verbs', async ({ page }) => {
      await page.locator('button[name="tool-method"]').first().click();
      const listbox = page.getByRole('listbox').first();
      for (const verb of ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']) {
        await expect(listbox.getByRole('option', { name: verb, exact: true })).toBeVisible();
      }
      await page.keyboard.press('Escape');
    });

    test('TC-009 Active checkbox toggles', async ({ page }) => {
      const cb = page.locator('#tool-is-active');
      const startChecked = await cb.isChecked();
      await cb.click();
      expect(await cb.isChecked()).toBe(!startChecked);
    });

    test('TC-010 adding a parameter renders its row controls', async ({ page }) => {
      await page
        .getByRole('button', { name: /add parameter/i })
        .first()
        .click();
      await expect(page.locator('input[name^="param-name-"]').first()).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.locator('button[name^="param-type-"]').first()).toBeVisible();
      await expect(page.locator('input[name^="param-desc-"]').first()).toBeVisible();
    });

    test('TC-011 removing a parameter clears its row', async ({ page }) => {
      await addParameter(page, { name: 'tmp_param', type: 'string', description: 'tmp' });
      const removeBtn = page.getByRole('button', { name: /remove parameter/i }).first();
      // Trash icon is hover-only — force a click so we don't depend on hover.
      await removeBtn.click({ force: true });
      await expect(page.locator('input[name^="param-name-"]')).toHaveCount(0, { timeout: 5_000 });
    });

    test('TC-012 selecting API Key reveals header + value', async ({ page }) => {
      await setAuthType(page, 'api_key');
      await expect(page.locator('input[name="tool-auth-header"]').first()).toBeVisible();
      await expect(page.locator('input[name="tool-auth-api-key"]').first()).toBeVisible();
    });

    test('TC-013 selecting Bearer reveals only the token field', async ({ page }) => {
      await setAuthType(page, 'bearer');
      await expect(page.locator('input[name="tool-auth-bearer"]').first()).toBeVisible();
      await expect(page.locator('input[name="tool-auth-username"]')).toHaveCount(0);
    });

    test('TC-014 selecting Basic reveals username + password', async ({ page }) => {
      await setAuthType(page, 'basic');
      await expect(page.locator('input[name="tool-auth-username"]').first()).toBeVisible();
      await expect(page.locator('input[name="tool-auth-password"]').first()).toBeVisible();
    });

    test('TC-015 switching back to No Authentication hides conditional fields', async ({
      page,
    }) => {
      await setAuthType(page, 'api_key');
      await expect(page.locator('input[name="tool-auth-api-key"]').first()).toBeVisible();
      await setAuthType(page, 'none');
      await expect(page.locator('input[name="tool-auth-api-key"]')).toHaveCount(0);
      await expect(page.locator('input[name="tool-auth-bearer"]')).toHaveCount(0);
      await expect(page.locator('input[name="tool-auth-username"]')).toHaveCount(0);
    });
  });

  test.describe('Save + redirect', () => {
    test('TC-016 minimum-required create posts the form and redirects to /tools', async ({
      page,
    }) => {
      const created = await createCustomToolViaUI(page);
      expect(created.id, 'tool id resolved from /tools row click').toBeTruthy();
      // Self-clean so the run doesn't leave __e2e__ rows behind.
      await deleteToolViaUI(page, { id: created.id, name: created.name });
    });

    test('TC-017 duplicate-name create surfaces an error toast', async ({ page }) => {
      // Create the first tool, then attempt to create a second with the
      // same name and assert the form stays put (no /tools redirect) and
      // an error toast appears. The backend returns 409 on the unique
      // constraint and the frontend pipes it through `handleApiError`,
      // which surfaces the detail as an error toast.
      const first = await createCustomToolViaUI(page);
      try {
        await gotoCreateCustom(page);
        await page.locator('input[name="name"]').first().fill(first.name);
        await page.locator('textarea[name="description"]').first().fill('Duplicate-name probe.');
        await page.locator('input[name="url"]').first().fill('https://api.example.com/dup');
        await page.getByRole('button', { name: /^create$/i }).click();
        // We expect the form to stay on /tools/create/custom — the error
        // surfaces as a toast, not a redirect.
        await expect.poll(() => page.url(), { timeout: 10_000 }).toMatch(/\/tools\/create\/custom/);
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      } finally {
        await deleteToolViaUI(page, { id: first.id, name: first.name });
      }
    });
  });

  // ─── TC-FULL: every writable Custom-tool field ────────────────────────────
  test.describe('Comprehensive flow', () => {
    test('TC-FULL fills every field + 2 parameters, saves, reloads, and verifies persistence', async ({
      page,
    }) => {
      test.setTimeout(180_000);

      const name = uniqueToolName('full');
      const description = 'TC-FULL e2e tool — comprehensive coverage.';
      const url = 'https://api.example.com/full/{resource_id}';
      const apiKeyHeader = 'X-Test-Api-Key';
      const apiKeyValue = 'sk-tc-full-secret';

      // 1. Fill the form.
      await gotoCreateCustom(page);
      await page.locator('input[name="name"]').first().fill(name);
      await page.locator('textarea[name="description"]').first().fill(description);
      await page.locator('input[name="url"]').first().fill(url);
      await setHttpMethod(page, 'PUT');

      // Toggle Active off so we can verify it round-trips as `false`.
      await page.locator('#tool-is-active').click();

      // Cycle auth_type through every variant so the conditional sections
      // all render at least once, then settle on api_key for the save.
      await setAuthType(page, 'bearer');
      await page.locator('input[name="tool-auth-bearer"]').first().fill('discarded-bearer');
      await setAuthType(page, 'basic');
      await page.locator('input[name="tool-auth-username"]').first().fill('discarded-user');
      await page.locator('input[name="tool-auth-password"]').first().fill('discarded-pass');
      await setAuthType(page, 'api_key');
      await page.locator('input[name="tool-auth-header"]').first().fill(apiKeyHeader);
      await page.locator('input[name="tool-auth-api-key"]').first().fill(apiKeyValue);

      // Two parameters covering string + number.
      await addParameter(page, {
        name: 'resource_id',
        type: 'string',
        description: 'Resource path id',
        required: true,
      });
      await addParameter(page, {
        name: 'limit',
        type: 'number',
        description: 'Result cap',
        required: false,
      });

      // 2. Save.
      await page.getByRole('button', { name: /^create$/i }).click();
      await page.waitForURL(/\/tools(?:\?|$|\/)/, { timeout: 30_000 });
      await expect(getToast(page)).toContainText(/tool created successfully/i, {
        timeout: 10_000,
      });

      // 3. Resolve the id from the list row.
      await page.goto('/tools');
      const row = page.locator('tbody tr').filter({ hasText: name }).first();
      await expect(row).toBeVisible({ timeout: 15_000 });
      await row.click();
      await page.waitForURL(/\/tools\/edit\/[\w-]+/, { timeout: 10_000 });
      const id = page.url().match(/\/tools\/edit\/([\w-]+)/)?.[1] ?? '';
      expect(id, 'tool id parsed from edit URL').toBeTruthy();

      // 4. Verify each persisted value.
      await expect(page.locator('input[name="name"]').first()).toHaveValue(name);
      await expect(page.locator('textarea[name="description"]').first()).toHaveValue(description);
      await expect(page.locator('input[name="url"]').first()).toHaveValue(url);
      // is_active should be off after our toggle.
      expect(await page.locator('#tool-is-active').isChecked()).toBe(false);
      // Auth: the form re-renders the api_key section with the decrypted
      // values from the GET response.
      await expect(page.locator('input[name="tool-auth-header"]').first()).toHaveValue(
        apiKeyHeader,
      );
      await expect(page.locator('input[name="tool-auth-api-key"]').first()).toHaveValue(
        apiKeyValue,
      );
      // Parameters: both rows should reload.
      await expect(page.locator('input[name^="param-name-"]')).toHaveCount(2, { timeout: 5_000 });

      // 5. Cleanup.
      await deleteToolViaUI(page, { id, name });
    });
  });
});

// ─── Documented-but-not-yet-implemented scenarios ────────────────────────────
test.fixme('TC-003 template tile pre-fills the form with template_id query', async () => {});
test.fixme('TC-CAL-001 Google Calendar built-in flow (needs OAuth seed)', async () => {});
test.fixme('TC-SMS-001 SMS built-in flow (needs Twilio seed creds)', async () => {});
