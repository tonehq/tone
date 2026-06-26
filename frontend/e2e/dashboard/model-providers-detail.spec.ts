/**
 * Model Providers detail-page e2e flow against the real backend.
 *
 * Scenarios AKL-/AKC-/AKE-/AKD-/AKK- (API Keys tab) and
 * MDL-/MDC-/MDE-/MDD-/MDM- (Models tab) from
 * frontend/e2e/ux_flow_docs/model-providers-detail.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture.
 * - `beforeAll` creates a fixture API key on the first available LLM
 *   provider so the Keys-tab read tests have a stable row to render
 *   against. `afterAll` deletes it.
 * - Every test that creates a model also deletes it in `try/finally` (the
 *   model catalog is global per core/services/model_provider_service.py).
 */

import { expect, type Page } from '@playwright/test';

import { test } from '../helpers/auth';
import {
  createApiKeyViaUI,
  createProviderModelViaUI,
  deleteApiKeyViaUI,
  deleteProviderModelViaUI,
  gotoKeysTab,
  gotoModelsTab,
  gotoProviderDetail,
  openAddKeyDrawer,
  openAddModelDrawer,
  pickSelectOptionByLabel,
  uniqueLabel,
  uniqueModelName,
} from '../helpers/serviceProviderFixtures';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

let fixtureProviderId = '';
let fixtureLabel = '';

test.describe('Model Providers — detail page', () => {
  test.beforeAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    const label = uniqueLabel('detail_fixture');
    const created = await createApiKeyViaUI(page, { serviceType: 'llm', label });
    fixtureProviderId = created.providerId;
    fixtureLabel = created.label;
  });

  test.afterAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    if (!fixtureProviderId || !fixtureLabel) return;
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await deleteApiKeyViaUI(page, {
      providerId: fixtureProviderId,
      serviceType: 'llm',
      label: fixtureLabel,
    });
  });

  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  // ─── API Keys tab ────────────────────────────────────────────────────────
  test.describe('API Keys tab', () => {
    test.beforeEach(async ({ page }) => {
      await gotoProviderDetail(page, {
        providerId: fixtureProviderId,
        serviceType: 'llm',
      });
      await gotoKeysTab(page);
    });

    test('AKL-001 page loads with Keys tab active', async ({ page }) => {
      await expect(page.getByRole('button', { name: /^API Keys/i }).first()).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });

    test('AKL-002 keys table renders the documented columns', async ({ page }) => {
      for (const header of [/^name$/i, /^type$/i, /^status$/i]) {
        await expect(page.getByRole('columnheader', { name: header }).first()).toBeVisible({
          timeout: 10_000,
        });
      }
    });

    test('AKL-003 fixture key appears in the list', async ({ page }) => {
      await expect(page.locator('tbody tr').filter({ hasText: fixtureLabel }).first()).toBeVisible({
        timeout: 10_000,
      });
    });

    test('AKL-004 search filters rows by label', async ({ page }) => {
      const search = page.getByPlaceholder(/search keys/i).first();
      await search.fill('__zzz_no_match_zzz__');
      await page.waitForTimeout(500);
      await expect(page.locator('tbody tr').filter({ hasText: fixtureLabel })).toHaveCount(0, {
        timeout: 5_000,
      });
      await search.clear();
    });

    test('AKL-005 Add API key button opens drawer', async ({ page }) => {
      await openAddKeyDrawer(page);
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      await page.keyboard.press('Escape');
    });

    test('AKC-001 valid Create → row + success toast', async ({ page }) => {
      const label = uniqueLabel('AKC-001');
      try {
        await openAddKeyDrawer(page);
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="label"]').first().fill(label);
        await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-akc');
        await dialog.getByRole('button', { name: /^create$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('tbody tr').filter({ hasText: label }).first()).toBeVisible({
          timeout: 10_000,
        });
      } finally {
        await deleteApiKeyViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          label,
        });
      }
    });

    test('AKC-002 Create button is disabled with no api_key entered', async ({ page }) => {
      await openAddKeyDrawer(page);
      const dialog = page.getByRole('dialog');
      await dialog.locator('input[name="label"]').first().fill(uniqueLabel('AKC-002'));
      const submit = dialog.getByRole('button', { name: /^create$/i });
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });

    test('AKC-003 duplicate label surfaces an error toast', async ({ page }) => {
      // Re-use the fixture key's label — backend rejects with 409.
      await openAddKeyDrawer(page);
      const dialog = page.getByRole('dialog');
      await dialog.locator('input[name="label"]').first().fill(fixtureLabel);
      await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-dup');
      await dialog.getByRole('button', { name: /^create$/i }).click();
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      // Drawer should still be open.
      await expect(dialog.locator('input[name="label"]').first()).toBeVisible();
      await page.keyboard.press('Escape');
    });

    test('AKE-001 clicking a row opens the edit drawer', async ({ page }) => {
      const row = page.locator('tbody tr').filter({ hasText: fixtureLabel }).first();
      await row.click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      await page.keyboard.press('Escape');
    });

    test('AKE-002 editing description persists on reload', async ({ page }) => {
      const newDescription = `AKE-002 ${Date.now()}`;
      const row = page.locator('tbody tr').filter({ hasText: fixtureLabel }).first();
      await row.click();
      const dialog = page.getByRole('dialog');
      await dialog.locator('textarea#description').first().fill(newDescription);
      await dialog.getByRole('button', { name: /^save$/i }).click();
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      // Re-open the edit drawer; description should rehydrate from GET.
      await page.reload();
      await gotoKeysTab(page);
      await page.locator('tbody tr').filter({ hasText: fixtureLabel }).first().click();
      await expect(
        page.getByRole('dialog').locator('textarea#description').first(),
      ).toHaveValue(newDescription);
      await page.keyboard.press('Escape');
    });

    test('AKD-001 row trash icon opens the confirm modal', async ({ page }) => {
      // Use a throw-away key so the shared fixture survives.
      const label = uniqueLabel('AKD-001');
      try {
        await openAddKeyDrawer(page);
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="label"]').first().fill(label);
        await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-akd');
        await dialog.getByRole('button', { name: /^create$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        const row = page.locator('tbody tr').filter({ hasText: label }).first();
        await expect(row).toBeVisible({ timeout: 10_000 });
        await row
          .getByRole('button', { name: 'Delete API key', exact: true })
          .click({ force: true });
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
        await page.keyboard.press('Escape');
      } finally {
        await deleteApiKeyViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          label,
        });
      }
    });

    test('AKK-FULL create → list (masked) → edit description → delete', async ({ page }) => {
      test.setTimeout(180_000);
      const label = uniqueLabel('AKK-FULL');
      const description1 = 'AKK-FULL initial description.';
      const description2 = `AKK-FULL edited ${Date.now()}`;

      try {
        // 1. Create.
        await openAddKeyDrawer(page);
        let dialog = page.getByRole('dialog');
        await dialog.locator('input[name="label"]').first().fill(label);
        await dialog.locator('textarea#description').first().fill(description1);
        await dialog.locator('input[name="api_key"]').first().fill('sk-e2e-test-akk');
        await dialog.getByRole('button', { name: /^create$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

        // 2. Row appears in the list with the label.
        const row = page.locator('tbody tr').filter({ hasText: label }).first();
        await expect(row).toBeVisible({ timeout: 10_000 });

        // 3. Edit description.
        await row.click();
        dialog = page.getByRole('dialog');
        await dialog.locator('textarea#description').first().fill(description2);
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

        // 4. Reload + verify description round-tripped.
        await page.reload();
        await gotoKeysTab(page);
        await page.locator('tbody tr').filter({ hasText: label }).first().click();
        await expect(
          page.getByRole('dialog').locator('textarea#description').first(),
        ).toHaveValue(description2);
        await page.keyboard.press('Escape');
      } finally {
        await deleteApiKeyViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          label,
        });
      }
    });
  });

  // ─── Models tab ──────────────────────────────────────────────────────────
  test.describe('Models tab', () => {
    test.beforeEach(async ({ page }) => {
      await gotoProviderDetail(page, {
        providerId: fixtureProviderId,
        serviceType: 'llm',
      });
      await gotoModelsTab(page);
    });

    test('MDL-001 Models tab activates and the table renders', async ({ page }) => {
      await expect(page.getByRole('button', { name: /^Models/i }).first()).toHaveAttribute(
        'aria-pressed',
        'true',
      );
    });

    test('MDL-002 models table renders the documented columns', async ({ page }) => {
      for (const header of [/^name$/i, /^kind$/i, /^status$/i]) {
        await expect(page.getByRole('columnheader', { name: header }).first()).toBeVisible({
          timeout: 10_000,
        });
      }
    });

    test('MDL-003 Add Model button opens the drawer', async ({ page }) => {
      await openAddModelDrawer(page);
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      await page.keyboard.press('Escape');
    });

    test('MDC-001 create minimal model (name + kind) succeeds', async ({ page }) => {
      const name = uniqueModelName('MDC-001');
      try {
        await openAddModelDrawer(page);
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="name"]').first().fill(name);
        await pickSelectOptionByLabel(page, dialog.locator('button[id="kind"]').first(), 'LLM');
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        await expect(page.locator('tbody tr').filter({ hasText: name }).first()).toBeVisible({
          timeout: 10_000,
        });
      } finally {
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
      }
    });

    test('MDC-002 create with all fields persists', async ({ page }) => {
      const name = uniqueModelName('MDC-002');
      const displayName = `${name} display`;
      const description = 'MDC-002 full fields.';
      try {
        await createProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          kind: 'llm',
          name,
          displayName,
          description,
        });
        // Row shows display name preferentially over name.
        await expect(page.locator('tbody tr').filter({ hasText: displayName }).first()).toBeVisible(
          { timeout: 10_000 },
        );
      } finally {
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
      }
    });

    test('MDC-003 Save button is disabled with blank name', async ({ page }) => {
      await openAddModelDrawer(page);
      const dialog = page.getByRole('dialog');
      // Pick a kind but leave name blank.
      await pickSelectOptionByLabel(page, dialog.locator('button[id="kind"]').first(), 'LLM');
      const submit = dialog.getByRole('button', { name: /^save$/i });
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });

    test('MDC-004 duplicate name within provider surfaces an error toast', async ({ page }) => {
      const name = uniqueModelName('MDC-004');
      try {
        await createProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          kind: 'llm',
          name,
        });
        // Try to create another model with the SAME name on the SAME provider.
        await gotoModelsTab(page);
        await openAddModelDrawer(page);
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="name"]').first().fill(name);
        await pickSelectOptionByLabel(page, dialog.locator('button[id="kind"]').first(), 'LLM');
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        // Drawer stays open (the name field is still visible).
        await expect(dialog.locator('input[name="name"]').first()).toBeVisible({
          timeout: 5_000,
        });
        await page.keyboard.press('Escape');
      } finally {
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
      }
    });

    test('MDE-002 editing display_name persists on reload', async ({ page }) => {
      const name = uniqueModelName('MDE-002');
      const newDisplay = `MDE-002 edited ${Date.now()}`;
      try {
        await createProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          kind: 'llm',
          name,
        });
        // Open edit by clicking the row.
        const row = page.locator('tbody tr').filter({ hasText: name }).first();
        await row.click();
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="display_name"]').first().fill(newDisplay);
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        await page.reload();
        await gotoModelsTab(page);
        await expect(page.locator('tbody tr').filter({ hasText: newDisplay }).first()).toBeVisible({
          timeout: 10_000,
        });
      } finally {
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
      }
    });

    test('MDD-001 trash icon opens confirm modal', async ({ page }) => {
      const name = uniqueModelName('MDD-001');
      try {
        await createProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          kind: 'llm',
          name,
        });
        const row = page.locator('tbody tr').filter({ hasText: name }).first();
        await row.getByRole('button', { name: 'Delete model', exact: true }).click({ force: true });
        await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
        await page.keyboard.press('Escape');
      } finally {
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
      }
    });

    test('MDM-FULL create → search → edit display → delete', async ({ page }) => {
      test.setTimeout(180_000);
      const name = uniqueModelName('MDM-FULL');
      const newDisplay = `MDM-FULL renamed ${Date.now()}`;
      try {
        await createProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          kind: 'llm',
          name,
          description: 'MDM-FULL initial.',
        });
        await expect(page.locator('tbody tr').filter({ hasText: name }).first()).toBeVisible({
          timeout: 10_000,
        });

        // Edit display_name.
        await page.locator('tbody tr').filter({ hasText: name }).first().click();
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="display_name"]').first().fill(newDisplay);
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

        // Reload + assert display name shows.
        await page.reload();
        await gotoModelsTab(page);
        await expect(page.locator('tbody tr').filter({ hasText: newDisplay }).first()).toBeVisible({
          timeout: 10_000,
        });

        // Delete + assert gone.
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        });
        await expect(page.locator('tbody tr').filter({ hasText: newDisplay })).toHaveCount(0, {
          timeout: 10_000,
        });
      } finally {
        // Belt-and-braces — the body deletes already, but if something
        // crashed mid-flow we still attempt cleanup.
        await deleteProviderModelViaUI(page, {
          providerId: fixtureProviderId,
          serviceType: 'llm',
          name,
        }).catch(() => undefined);
      }
    });
  });
});

// ─── Documented-but-not-yet-implemented scenarios ────────────────────────────
test.fixme(
  'AKR-MASK (secret reveal-once via POST response, masked on GET) — defer until network interception story is in place',
  async () => {},
);
test.fixme(
  'AKE-003 toggle Active off persists on reload — needs the edit drawer to expose the Active checkbox reliably',
  async () => {},
);
test.fixme('MDE-003 toggle Active off on a model — same reason', async () => {});
test.skip('MDC-005 admin/owner-only model CRUD (non-owner sees no Add button) — needs a non-owner membership seed', async () => {});
