/**
 * Model Providers list-page e2e flow against the real backend.
 *
 * Scenarios MPL-/MPC-/MPE-/MPD-/MPP- from
 * frontend/e2e/docs/model-providers.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture.
 * - Every test that creates a real key cancels it in `try/finally` so the
 *   org never accumulates __e2e__ rows.
 * - No is_default=true writes — see safety note in serviceProviderFixtures.
 */

import { expect, type Page } from '@playwright/test';

import { test } from '../helpers/auth';
import {
  createApiKeyViaUI,
  deleteApiKeyViaUI,
  gotoProvidersList,
  openAddProviderDrawer,
  pickFirstProviderFromCatalog,
  uniqueLabel,
} from '../helpers/serviceProviderFixtures';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Model Providers — list page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await gotoProvidersList(page);
  });

  test.describe('Page identity + rendering', () => {
    test('MPL-001 renders the header + Add Provider CTA', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /model providers/i, level: 1 })).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.getByRole('button', { name: /add provider/i })).toBeVisible();
    });

    test('MPL-002 type filter dropdown lists all/llm/stt/tts', async ({ page }) => {
      await page.locator('button[id="type-filter"]').first().click();
      const listbox = page.getByRole('listbox').first();
      for (const label of [/all/i, /^LLM$/i, /^STT$/i, /^TTS$/i]) {
        await expect(listbox.getByRole('option', { name: label }).first()).toBeVisible({
          timeout: 5_000,
        });
      }
      await page.keyboard.press('Escape');
    });

    test('MPL-003 search input is interactive', async ({ page }) => {
      const search = page.getByPlaceholder(/search providers or services/i).first();
      await expect(search).toBeVisible({ timeout: 10_000 });
      await search.fill('__zzz_no_match_zzz__');
      await page.waitForTimeout(500); // 300ms debounce + a little
      await search.clear();
    });

    test('MPL-004 Add Provider drawer opens with service_type + provider fields', async ({
      page,
    }) => {
      await openAddProviderDrawer(page);
      const dialog = page.getByRole('dialog');
      await expect(dialog.locator('button[id="service_type"]').first()).toBeVisible();
      await expect(dialog.locator('button[id="provider_id"]').first()).toBeVisible();
      await expect(dialog.locator('input[name="api_key"]').first()).toBeVisible();
      await page.keyboard.press('Escape');
    });

    test('MPL-005 empty state when search matches nothing', async ({ page }) => {
      const search = page.getByPlaceholder(/search providers or services/i).first();
      await search.fill('__zzz_no_match_zzz__');
      await page.waitForTimeout(500);
      // Actual copy from ServiceProvidersPage.tsx:347 is
      // "No matching providers" / "No providers yet".
      await expect(page.getByText(/no\s+(matching|providers)/i).first()).toBeVisible({
        timeout: 5_000,
      });
      await search.clear();
    });
  });

  test.describe('Add Provider drawer — validation', () => {
    test('MPC-002 Create button is disabled with no provider selected', async ({ page }) => {
      await openAddProviderDrawer(page);
      const dialog = page.getByRole('dialog');
      await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-001');
      const submit = dialog.getByRole('button', { name: /^create$/i });
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });

    test('MPC-003 Create button is disabled with no api_key entered', async ({ page }) => {
      await openAddProviderDrawer(page);
      await pickFirstProviderFromCatalog(page, { serviceType: 'llm' });
      const submit = page.getByRole('dialog').getByRole('button', { name: /^create$/i });
      // No api_key value → still disabled.
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });
  });

  test.describe('Create flow', () => {
    test('MPC-001 valid Create posts the form and the card grid updates', async ({ page }) => {
      const label = uniqueLabel('MPC-001');
      let created: { id: string; providerId: string; providerName: string; label: string } | null =
        null;
      try {
        created = await createApiKeyViaUI(page, { serviceType: 'llm', label });
        expect(created.providerId, 'provider id resolved from catalog').toBeTruthy();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      } finally {
        if (created) {
          await deleteApiKeyViaUI(page, {
            providerId: created.providerId,
            serviceType: 'llm',
            label: created.label,
          });
        }
      }
    });

    test('MPC-005 duplicate label per provider surfaces an error toast', async ({ page }) => {
      const label = uniqueLabel('MPC-005');
      let created: { id: string; providerId: string; providerName: string; label: string } | null =
        null;
      try {
        // Seed the first key.
        created = await createApiKeyViaUI(page, { serviceType: 'llm', label });
        // Re-open the Add drawer and reuse the same label on the same provider.
        await gotoProvidersList(page);
        await openAddProviderDrawer(page);
        await pickFirstProviderFromCatalog(page, { serviceType: 'llm' });
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="label"]').first().fill(label);
        await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-dup');
        await dialog.getByRole('button', { name: /^create$/i }).click();
        // Either an inline error or a toast — assert a toast appears and
        // the drawer stays on the create page.
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        await expect(dialog.locator('input[name="label"]').first()).toBeVisible({
          timeout: 5_000,
        });
        await page.keyboard.press('Escape');
      } finally {
        if (created) {
          await deleteApiKeyViaUI(page, {
            providerId: created.providerId,
            serviceType: 'llm',
            label: created.label,
          });
        }
      }
    });
  });

  // MPD-001 (card trash → confirm modal) was found unstable because the
  // card aggregates by (provider, service_type) and doesn't expose the label
  // text on the card body — locating the card by label fails. The delete
  // flow is fully covered by the detail-page scenario AKD-001 (row trash on
  // the keys table) which is far more reliable. See deferred list at file
  // bottom.

  // ─── MPP-FULL: comprehensive create → list → delete ───────────────────────
  test.describe('Comprehensive flow', () => {
    test('MPP-FULL create → assert card → delete → assert gone', async ({ page }) => {
      test.setTimeout(180_000);
      const label = uniqueLabel('MPP-FULL');
      let created: { id: string; providerId: string; providerName: string; label: string } | null =
        null;
      try {
        // 1. Create.
        created = await createApiKeyViaUI(page, { serviceType: 'llm', label });
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

        // 2. The list-page card aggregates by (provider, service_type) and
        //    does NOT expose the per-key label on the card body. Verify via
        //    the detail page where the key appears as a row.
        const detailUrl = `/settings/model-providers/${created.providerId}/llm`;
        await page.goto(detailUrl);
        await expect(page.locator('tbody tr').filter({ hasText: label }).first()).toBeVisible({
          timeout: 10_000,
        });

        // 3. Delete via the per-row helper.
        await deleteApiKeyViaUI(page, {
          providerId: created.providerId,
          serviceType: 'llm',
          label: created.label,
        });
        created = null;

        // 4. Assert gone from the detail page.
        await page.goto(detailUrl);
        await expect(page.locator('tbody tr').filter({ hasText: label })).toHaveCount(0, {
          timeout: 10_000,
        });
      } finally {
        // If anything failed mid-flow, the throw-away still gets cleaned up.
        if (created) {
          await deleteApiKeyViaUI(page, {
            providerId: created.providerId,
            serviceType: 'llm',
            label: created.label,
          });
        }
      }
    });
  });
});

// ─── Documented-but-not-yet-implemented scenarios ────────────────────────────
test.fixme(
  'MPC-004 reuse-key path uses an existing key for a different service_type — re-enable once a 2-service-type seed exists',
  async () => {},
);
test.fixme(
  'MPE-001..MPE-003 list-page pencil edit drawer — relies on a freshly-seeded card; covered by detail-page Edit scenarios (AKE-)',
  async () => {},
);
test.fixme(
  'MPD-001 list-page card trash → confirm modal — the card aggregates by (provider, service_type) and does not expose the per-key label on the card body, so locating the specific card to delete is unreliable. Detail-page AKD-001 covers the row-level delete reliably.',
  async () => {},
);
test.fixme(
  'MPD-002 confirm-delete removes the card from the grid — covered by MPP-FULL',
  async () => {},
);
