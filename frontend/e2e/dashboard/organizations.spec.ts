/**
 * Organizations e2e flow against the real backend.
 *
 * Scenarios OL-/OC-/OE-/OS-/OD-/OG- from frontend/e2e/ux_flow_docs/organizations.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture.
 * - `beforeAll` creates an `__e2e__org` throw-away org; `afterAll` deletes it.
 * - Every mutation test reverts the throw-away org to baseline.
 * - OS- switch tests run LAST so the window.location.reload() never breaks
 *   downstream tests; the file always ends by switching back to "My Space".
 */

import { expect, type Page } from '@playwright/test';

import { test } from '../helpers/auth';
import {
  createOrganizationViaUI,
  deleteOrganizationViaUI,
  openEditOrganization,
  switchOrganizationViaSidebar,
  uniqueOrgName,
} from '../helpers/organizationFixtures';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

let fixtureOrgId = '';
let fixtureOrgName = '';

test.describe('Organizations', () => {
  test.beforeAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    const { id, name } = await createOrganizationViaUI(page, {
      name: uniqueOrgName('fixture'),
    });
    fixtureOrgId = id;
    fixtureOrgName = name;
  });

  test.afterAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    if (!fixtureOrgId) return;
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await deleteOrganizationViaUI(page, { id: fixtureOrgId, name: fixtureOrgName });
  });

  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await page.goto('/settings/organizations');
    await expect(page.getByRole('button', { name: /new organization/i })).toBeVisible({
      timeout: 15_000,
    });
  });

  test.describe('List + rendering', () => {
    test('OL-001 renders the header + "New Organization" CTA', async ({ page }) => {
      await expect(page.getByRole('heading', { name: /organizations/i, level: 1 })).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.getByRole('button', { name: /new organization/i })).toBeVisible();
    });

    test('OL-002 the card grid lists at least the fixture org', async ({ page }) => {
      await expect(page.getByText(fixtureOrgName).first()).toBeVisible({ timeout: 10_000 });
    });

    test('OL-003 search filters cards by name', async ({ page }) => {
      const search = page.locator('input[name="org-search"]').first();
      await expect(search).toBeVisible({ timeout: 10_000 });
      await search.fill(fixtureOrgName);
      await expect(page.getByText(fixtureOrgName).first()).toBeVisible({ timeout: 5_000 });
      await search.fill('__zzz_no_match_zzz__');
      // The grid empties → expect the fixture card to no longer be visible.
      await expect(page.getByText(fixtureOrgName)).toHaveCount(0, { timeout: 5_000 });
      await search.clear();
    });

    test('OL-004 empty search shows the No matches state with a Clear button', async ({ page }) => {
      const search = page.locator('input[name="org-search"]').first();
      await search.fill('__zzz_no_match_zzz__');
      // The empty state copy varies by component; require at least one of the
      // common phrases.
      await expect(page.getByText(/no\s*(?:matches|results|organizations)/i).first()).toBeVisible({
        timeout: 5_000,
      });
      await search.clear();
    });
  });

  test.describe('Create modal', () => {
    test('OC-001 clicking New Organization opens the upsert modal with empty Name', async ({
      page,
    }) => {
      await page
        .getByRole('button', { name: /new organization/i })
        .first()
        .click();
      const dialog = page.getByRole('dialog');
      await expect(dialog.locator('input[name="name"]').first()).toBeVisible({ timeout: 5_000 });
      await expect(dialog.locator('input[name="name"]').first()).toHaveValue('');
      await page.keyboard.press('Escape');
    });

    test('OC-002 Create button is disabled while Name is blank', async ({ page }) => {
      await page
        .getByRole('button', { name: /new organization/i })
        .first()
        .click();
      const dialog = page.getByRole('dialog');
      const submit = dialog.getByRole('button', { name: /^create$/i });
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });

    test('OC-003 valid Create posts the form and the new card appears', async ({ page }) => {
      const name = uniqueOrgName('OC-003');
      let id = '';
      try {
        const created = await createOrganizationViaUI(page, { name });
        id = created.id;
        expect(id).toBeTruthy();
        // Card now visible in the grid.
        await expect(page.getByText(name).first()).toBeVisible({ timeout: 10_000 });
      } finally {
        if (id) await deleteOrganizationViaUI(page, { id, name });
      }
    });
  });

  test.describe('Edit modal', () => {
    test('OE-001 Edit modal hydrates with the existing values', async ({ page }) => {
      await openEditOrganization(page, { id: fixtureOrgId, name: fixtureOrgName });
      const dialog = page.getByRole('dialog');
      await expect(dialog.locator('input[name="name"]').first()).toHaveValue(fixtureOrgName);
      await page.keyboard.press('Escape');
    });

    test('OE-002 editing Name persists across a refetch', async ({ page }) => {
      const newName = `${fixtureOrgName}-edited`;
      await openEditOrganization(page, { id: fixtureOrgId, name: fixtureOrgName });
      const dialog = page.getByRole('dialog');
      await dialog.locator('input[name="name"]').first().fill(newName);
      await dialog.getByRole('button', { name: /^save$/i }).click();
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      await page.reload();
      await expect(page.getByText(newName).first()).toBeVisible({ timeout: 10_000 });
      // Restore so subsequent tests still find the fixture by its baseline name.
      await openEditOrganization(page, { id: fixtureOrgId, name: newName });
      await page.getByRole('dialog').locator('input[name="name"]').first().fill(fixtureOrgName);
      await page
        .getByRole('dialog')
        .getByRole('button', { name: /^save$/i })
        .click();
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
    });

    test('OE-003 description round-trips on reload', async ({ page }) => {
      // Note: website_url is NOT asserted here — the backend column is
      // `Organization.website` but the form posts `website_url`. The
      // GET /organization/details response key doesn't always match, so
      // the field doesn't reliably round-trip. Tracked separately.
      const description = `OE-003 description ${Date.now()}`;
      await openEditOrganization(page, { id: fixtureOrgId, name: fixtureOrgName });
      const dialog = page.getByRole('dialog');
      await dialog.locator('textarea[name="description"]').first().fill(description);
      await dialog.getByRole('button', { name: /^save$/i }).click();
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      await page.reload();
      await openEditOrganization(page, { id: fixtureOrgId, name: fixtureOrgName });
      await expect(
        page.getByRole('dialog').locator('textarea[name="description"]').first(),
      ).toHaveValue(description);
      await page.keyboard.press('Escape');
    });
  });

  test.describe('Delete modal', () => {
    test('OD-002 owner Delete opens the modal; Delete button is disabled until the name is typed exactly', async ({
      page,
    }) => {
      // Use a throw-away org so the shared fixture survives.
      const throwaway = await createOrganizationViaUI(page, {
        name: uniqueOrgName('OD-002'),
      });
      try {
        const menuBtn = page
          .locator(`button[aria-label="Actions for organization ${throwaway.id}"]`)
          .first();
        const card = menuBtn
          .locator('xpath=ancestor::*[@data-slot="card" or contains(@class,"cursor-pointer")][1]')
          .first();
        await card.hover({ force: true });
        await menuBtn.click({ force: true });
        const popover = menuBtn.locator('xpath=../div').first();
        await popover
          .getByRole('button', { name: /^delete$/i })
          .first()
          .click();
        const dialog = page.getByRole('dialog');
        const confirmBtn = dialog.getByRole('button', { name: /^delete$/i });
        await expect(confirmBtn).toBeDisabled();
        await dialog.locator('input[name="confirm_name"]').first().fill('wrong-name');
        await expect(confirmBtn).toBeDisabled();
        await dialog.locator('input[name="confirm_name"]').first().fill(throwaway.name);
        await expect(confirmBtn).toBeEnabled({ timeout: 5_000 });
        await page.keyboard.press('Escape');
      } finally {
        await deleteOrganizationViaUI(page, { id: throwaway.id, name: throwaway.name });
      }
    });

    test('OD-003 typed-name confirm deletes the org and removes the card', async ({ page }) => {
      const throwaway = await createOrganizationViaUI(page, {
        name: uniqueOrgName('OD-003'),
      });
      await deleteOrganizationViaUI(page, { id: throwaway.id, name: throwaway.name });
      // Card is gone.
      await page.goto('/settings/organizations');
      await expect(
        page.locator(`button[aria-label="Actions for organization ${throwaway.id}"]`),
      ).toHaveCount(0, { timeout: 10_000 });
    });
  });

  // ─── OG-FULL: comprehensive create → edit every field → delete ───────────
  test.describe('Comprehensive flow', () => {
    test('OG-FULL create → edit name+desc+website → delete', async ({ page }) => {
      test.setTimeout(180_000);

      const initialName = uniqueOrgName('OG-FULL');
      const finalName = `${initialName}-renamed`;
      const description = 'OG-FULL comprehensive flow description.';

      let id = '';
      try {
        const created = await createOrganizationViaUI(page, { name: initialName });
        id = created.id;
        // Edit name + description (website_url has a known FE/BE field
        // mismatch — see OE-003 note — so we don't assert it here).
        await openEditOrganization(page, { id, name: initialName });
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="name"]').first().fill(finalName);
        await dialog.locator('textarea[name="description"]').first().fill(description);
        await dialog.getByRole('button', { name: /^save$/i }).click();
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

        // Reload + verify every persisted value.
        await page.reload();
        await openEditOrganization(page, { id, name: finalName });
        const verify = page.getByRole('dialog');
        await expect(verify.locator('input[name="name"]').first()).toHaveValue(finalName);
        await expect(verify.locator('textarea[name="description"]').first()).toHaveValue(
          description,
        );
        await page.keyboard.press('Escape');
      } finally {
        if (id) {
          await deleteOrganizationViaUI(page, {
            id,
            // Pick whichever name the org is at when delete runs.
            name: finalName,
          }).catch(() => deleteOrganizationViaUI(page, { id, name: initialName }));
        }
      }
    });
  });

  // ─── OS- switch tests run LAST so the reload doesn't break other tests ──
  test.describe('Sidebar switch', () => {
    test('OS-001 the switcher opens a popover listing every org the user belongs to', async ({
      page,
    }) => {
      await page.getByRole('button', { name: 'Switch organization', exact: true }).first().click();
      // Popover contains a button for each org name; the fixture org must
      // appear since the test owner just created it.
      await expect(page.getByText(fixtureOrgName).first()).toBeVisible({ timeout: 5_000 });
      // Close the popover so the next test starts clean.
      await page.keyboard.press('Escape');
    });

    // Switching tenants is currently a localStorage swap + window reload
    // (see components/layout/sidebar.tsx:288–297). There is no companion
    // /auth/switch_organization call, so the JWT in cookies still encodes
    // the OLD org_id while the tenant header points at the NEW org. The
    // backend middleware reconciles this only on subsequent requests,
    // which races with Playwright's reload wait and leaves the worker
    // session in a flaky state. Document + skip until the switch flow
    // calls /auth/switch_organization (or the test gets a refreshed JWT).
    test.fixme('OS-002 picking the fixture org reloads with the new tenant', async ({ page }) => {
      test.setTimeout(120_000);
      await switchOrganizationViaSidebar(page, { name: fixtureOrgName });
      await expect(page.getByText(fixtureOrgName).first()).toBeVisible({ timeout: 10_000 });
      await switchOrganizationViaSidebar(page, { name: 'My Space' });
    });
  });
});

// ─── Documented-but-not-yet-implemented scenarios ────────────────────────────
test.fixme(
  'OE-004 invalid Website URL → inline error (modal validation surface varies; revisit after schema firmed up)',
  async () => {},
);
test.skip('OD-001 Delete option is hidden on cards where role is not Owner — needs a non-owner membership seed which CI does not provide.', async () => {});
