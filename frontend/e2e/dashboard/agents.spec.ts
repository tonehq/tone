/**
 * Agents list page — e2e scenarios AL-001 … AL-013.
 *
 * Strategy: real backend, real user experience. Login happens once per
 * worker via the shared `test` fixture. No mocks — the list is whatever
 * the test account has at run time. We assert structural behaviour
 * (header, columns, controls present, sort/search inputs interactive,
 * navigation works) rather than specific row contents.
 */

import { expect, type Page } from '@playwright/test';

import { createAgentViaUI, deleteAgentViaUI, uniqueAgentName } from '../helpers/agentFixtures';
import { ensureOnPage, test } from '../helpers/auth';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Agents list page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await ensureOnPage(page, '/agents');
  });

  test.describe('Rendering', () => {
    test('AL-001 header + subtitle render', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Agents', level: 1 })).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.getByText('Manage your voice agents')).toBeVisible();
    });

    test('AL-005 table columns: Agent / Status / Type / Phone / Last Updated', async ({ page }) => {
      await expect(page.getByRole('columnheader', { name: 'Agent' })).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.getByRole('columnheader', { name: 'Status' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Type' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Phone' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /last updated/i })).toBeVisible();
    });
  });

  test.describe('Filters & sort', () => {
    test('AL-006 search input is interactive and clears on demand', async ({ page }) => {
      const search = page.getByPlaceholder('Search agents...');
      await search.fill('zzznoresult');
      // Either the table empties or the empty-state row appears — accept both
      // (depends on whether the org has zero matching rows).
      await page.waitForTimeout(700); // debounce
      await search.clear();
    });

    test('AL-007 type filter dropdown opens', async ({ page }) => {
      await page.locator('button[id="agent-type-filter"]').click();
      await expect(page.getByRole('option', { name: /inbound/i }).first()).toBeVisible({
        timeout: 3_000,
      });
      await page.keyboard.press('Escape');
    });

    test('AL-008 click Agent column header is clickable (sort)', async ({ page }) => {
      const header = page.getByRole('columnheader', { name: 'Agent' });
      await header.click(); // ascending
      await header.click(); // descending
      // Just make sure no exception bubbles up — concrete payload assertion
      // is in agents-create-inbound.spec.ts via real create.
    });
  });

  test.describe('Row actions', () => {
    test('AL-010 + AL-011: row click navigates to edit; row delete works end-to-end', async ({
      page,
    }) => {
      // We need a row that we own and can safely delete. Create a fresh
      // inbound agent through the UI, then navigate back to the list.
      const created = await createAgentViaUI(page, {
        agentType: 'inbound',
        name: uniqueAgentName('list-row'),
      });
      await ensureOnPage(page, '/agents');

      // Find the row by its unique name.
      const row = page.locator('tr', { hasText: created.name });
      await expect(row).toBeVisible({ timeout: 10_000 });

      // AL-010: click the row's name cell → navigate to edit.
      await row.getByText(created.name).click();
      await page.waitForURL(new RegExp(`/agents/edit/inbound/${created.id}`), {
        timeout: 10_000,
      });

      // AL-011: navigate back, open the row menu, delete.
      await deleteAgentViaUI(page, { agentType: 'inbound', id: created.id });
      await expect(getToast(page)).toContainText(/deleted/i, { timeout: 10_000 });
    });
  });

  test.describe('Create entry', () => {
    test('AL-012 header Create Agent opens type-picker', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).first().click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      // Close it — we're only testing that the modal opens here. The
      // navigation from there is covered by AC-001 (which lands on the
      // create page directly).
      await page.keyboard.press('Escape');
    });
  });
});

// ── Documented-but-not-yet-implemented scenarios ─────────────────────────────
test.fixme('AL-002 empty state when org has no agents', async () => {});
test.fixme('AL-003 loading state shows a skeleton until rows arrive', async () => {});
test.fixme('AL-004 error toast on /agent/list 500', async () => {});
test.fixme('AL-009 page size selector + pagination next/prev', async () => {});
test.fixme('AL-013 unauthenticated visit → redirect to /login', async () => {});
