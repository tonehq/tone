/**
 * Real-backend fixtures for the Organizations e2e specs.
 *
 * Mirrors the shape of `agentFixtures.ts` / `toolFixtures.ts`: drives the real
 * UI, namespaces every fixture with the `__e2e__` prefix so leftovers from
 * aborted runs can be swept, and exposes one helper per major interaction.
 *
 * Org id resolution: `OrganizationCard` renders a `<OrganizationCardMenu>`
 * whose trigger carries `aria-label="Actions for organization {id}"`. We
 * extract the id from that aria-label after finding the card by name.
 */

import { expect, type Page } from '@playwright/test';

export const E2E_ORG_PREFIX = '__e2e__';

export function uniqueOrgName(label: string): string {
  const safe = label.replace(/[^a-zA-Z0-9]+/g, '_');
  return `${E2E_ORG_PREFIX}org_${safe}_${Date.now()}_${Math.floor(Math.random() * 10_000)}`;
}

// ── Org-card resolution ────────────────────────────────────────────────────

/**
 * Find the card matching the given name and return its id from the
 * adjacent `Actions for organization {id}` menu trigger's aria-label.
 */
async function resolveOrgIdByName(page: Page, name: string): Promise<string | null> {
  const card = page.locator('div', { hasText: name }).first();
  // The menu button sits next to the name within the same card subtree.
  const menuButton = card.locator('button[aria-label^="Actions for organization "]').first();
  if (!(await menuButton.isVisible({ timeout: 5_000 }).catch(() => false))) return null;
  const aria = (await menuButton.getAttribute('aria-label')) ?? '';
  return aria.replace(/^Actions for organization\s+/, '').trim() || null;
}

// ── Create ─────────────────────────────────────────────────────────────────

export interface CreateOrgValues {
  name?: string;
}

/**
 * Open the New Organization modal, fill the name, save, wait for the
 * success toast, and resolve the new id from the resulting card.
 */
export async function createOrganizationViaUI(
  page: Page,
  values: CreateOrgValues = {},
): Promise<{ id: string; name: string }> {
  const name = values.name ?? uniqueOrgName('fixture');

  await page.goto('/settings/organizations');
  await page
    .getByRole('button', { name: /new organization/i })
    .first()
    .click();
  const dialog = page.getByRole('dialog');
  await dialog.locator('input[name="name"]').first().fill(name);
  await dialog.getByRole('button', { name: /^create$/i }).click();
  await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10_000 });

  // Narrow the card grid via search so a busy environment with leftover
  // `__e2e__org` cards doesn't make the new card hard to find by text.
  await page.locator('input[name="org-search"]').first().fill(name);
  await expect(page.getByText(name).first()).toBeVisible({ timeout: 10_000 });
  const id = await resolveOrgIdByName(page, name);
  if (!id) throw new Error(`Could not resolve org id for "${name}" from the card grid`);
  return { id, name };
}

// ── Edit modal ─────────────────────────────────────────────────────────────

/**
 * Open the Edit modal for the named org. Waits for the GET /organization/details
 * response so the modal hydrates before fills run.
 */
export async function openEditOrganization(
  page: Page,
  options: { id: string; name: string },
): Promise<void> {
  await page.goto('/settings/organizations');
  // Narrow the grid to a single card by typing the name into the search box
  // — works around stale `__e2e__org` cards from previous runs cluttering
  // the layout and making xpath ancestors ambiguous.
  await page.locator('input[name="org-search"]').first().fill(options.name);
  // OrganizationCard's onClick handler opens Edit directly for admin/owner
  // (see OrganizationCard.tsx:31). Click the card body via its menu-button
  // ancestor to dodge the hover-only opacity-0 trigger.
  const menuButton = page
    .locator(`button[aria-label="Actions for organization ${options.id}"]`)
    .first();
  await menuButton.waitFor({ state: 'attached', timeout: 10_000 });
  const card = menuButton
    .locator('xpath=ancestor::*[@data-slot="card" or contains(@class,"cursor-pointer")][1]')
    .first();
  await card.scrollIntoViewIfNeeded();
  const detailsGet = page
    .waitForResponse(
      (r) => r.url().includes('/organization/details') && r.request().method() === 'GET',
      { timeout: 10_000 },
    )
    .catch(() => null);
  await card.click({ force: true });
  await detailsGet;
  await page
    .getByRole('dialog')
    .locator('input[name="name"]')
    .first()
    .waitFor({ state: 'visible', timeout: 10_000 });
}

// ── Delete ─────────────────────────────────────────────────────────────────

/**
 * Best-effort delete via the per-card menu + typed-name confirm modal.
 * Swallows errors so a teardown failure never fails a test that already passed.
 */
export async function deleteOrganizationViaUI(
  page: Page,
  options: { id: string; name: string },
): Promise<void> {
  try {
    await page.goto('/settings/organizations');
    await page.waitForLoadState('networkidle', { timeout: 10_000 });
    // Narrow the grid to a single card (see openEditOrganization).
    await page.locator('input[name="org-search"]').first().fill(options.name);
    const menuButton = page
      .locator(`button[aria-label="Actions for organization ${options.id}"]`)
      .first();
    if ((await menuButton.count()) === 0) return;
    // The menu trigger is `opacity-0 group-hover:opacity-100` — hover first
    // so React updates the popover state cleanly, then click.
    const card = menuButton
      .locator('xpath=ancestor::*[@data-slot="card" or contains(@class,"cursor-pointer")][1]')
      .first();
    await card.scrollIntoViewIfNeeded();
    await card.hover({ force: true });
    await menuButton.click({ force: true });
    const popover = menuButton.locator('xpath=../div').first();
    const deleteItem = popover.getByRole('button', { name: /^delete$/i }).first();
    if (!(await deleteItem.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await deleteItem.click();
    const dialog = page.getByRole('dialog');
    await dialog.locator('input[name="confirm_name"]').first().fill(options.name);
    await dialog.getByRole('button', { name: /^delete$/i }).click();
    // Card should be gone from the grid.
    await expect(
      page.locator(`button[aria-label="Actions for organization ${options.id}"]`),
    ).toHaveCount(0, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to delete organization ${options.id}`).toBe(true);
  }
}

// ── Sidebar switch ─────────────────────────────────────────────────────────

/**
 * Pick a different org from the sidebar switcher. The current implementation
 * (`components/layout/sidebar.tsx:288–297`) is a localStorage swap + window
 * reload — there is no /auth/switch_organization round-trip. We click the
 * switcher trigger (aria-label "Switch organization"), click the item button
 * matching the org name inside the popover, then wait for the full reload.
 */
export async function switchOrganizationViaSidebar(
  page: Page,
  options: { name: string },
): Promise<void> {
  await page.getByRole('button', { name: 'Switch organization', exact: true }).first().click();
  // Radix Popover renders with data-slot="popover-content"; items are plain
  // <button> elements (NOT `role="menuitem"`).
  const popover = page.locator('[data-slot="popover-content"]').first();
  await popover.waitFor({ state: 'visible', timeout: 5_000 });
  const item = popover.getByRole('button', { name: options.name }).first();
  // Wait for the reload event the click triggers.
  const navPromise = page.waitForLoadState('load', { timeout: 15_000 });
  await item.click();
  await navPromise;
}
