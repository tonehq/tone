/**
 * Real-backend fixtures for the Members + Invitations e2e specs.
 *
 * Mirrors the shape of `agentFixtures.ts` / `toolFixtures.ts`: drives the real
 * UI, namespaces every fixture with the `__e2e__` prefix so an orphan-sweep
 * can pick up leftovers from aborted runs, and exposes one helper per major
 * interaction (open modal, invite, cancel, switch tab).
 *
 * NOTE on seeded members: the backend's `accept-invitation` endpoint exists
 * but invite tokens are NOT exposed via `/user/get_all_invited_users_for_organization`
 * (Invite.to_dict drops the token). So tests that need a *real accepted
 * member* (MR-002, MD-002, OD-001) `test.skip()` with a documented message.
 */

import { expect, type Page } from '@playwright/test';

import { pickSelectOptionByLabel } from './toolFixtures';

export const E2E_INVITE_PREFIX = '__e2e__';

export function uniqueInviteEmail(label: string): string {
  const safe = label.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase();
  return `${E2E_INVITE_PREFIX}invite_${safe}_${Date.now()}_${Math.floor(
    Math.random() * 10_000,
  )}@e2e.tonehq.test`;
}

// ── Tab navigation ─────────────────────────────────────────────────────────

export async function gotoMembersTab(page: Page): Promise<void> {
  await page
    .getByRole('tab', { name: /^members$/i })
    .first()
    .click();
}

export async function gotoInvitationsTab(page: Page): Promise<void> {
  await page
    .getByRole('tab', { name: /^invitations$/i })
    .first()
    .click();
}

// ── Invite modal ──────────────────────────────────────────────────────────

export async function openInviteModal(page: Page): Promise<void> {
  await page
    .getByRole('button', { name: /invite member/i })
    .first()
    .click();
  await page
    .getByRole('dialog')
    .locator('input[name="name"]')
    .first()
    .waitFor({ state: 'visible', timeout: 5_000 });
}

const ROLE_LABEL: Record<'admin' | 'member' | 'viewer', string> = {
  admin: 'Admin',
  member: 'Member',
  viewer: 'Viewer',
};

/**
 * Fill + submit the Invite modal. Returns the invited email so the caller
 * can clean it up. Waits for the success toast — caller is responsible for
 * any subsequent UI assertions.
 */
export async function inviteMemberViaUI(
  page: Page,
  options: { name?: string; email?: string; role?: 'admin' | 'member' | 'viewer' } = {},
): Promise<{ name: string; email: string; role: 'admin' | 'member' | 'viewer' }> {
  const name = options.name ?? 'E2E Invitee';
  const email = options.email ?? uniqueInviteEmail('invite');
  const role = options.role ?? 'member';

  await openInviteModal(page);
  const dialog = page.getByRole('dialog');
  await dialog.locator('input[name="name"]').first().fill(name);
  await dialog.locator('input[name="email"]').first().fill(email);
  const roleTrigger = dialog.locator('button[id="invite-role"]').first();
  await pickSelectOptionByLabel(page, roleTrigger, ROLE_LABEL[role]);

  await dialog.getByRole('button', { name: /send invite/i }).click();
  await expect(page.locator('[data-sonner-toast]').first()).toBeVisible({ timeout: 10_000 });
  return { name, email, role };
}

/**
 * Best-effort cancel an invitation via the Invitations tab's X icon. The
 * tab is identified by email row text. Swallows errors so a teardown failure
 * never fails a test that already passed.
 */
export async function cancelInvitationViaUI(page: Page, options: { email: string }): Promise<void> {
  try {
    await page.goto('/members');
    await page.waitForLoadState('networkidle', { timeout: 10_000 });
    await gotoInvitationsTab(page);
    const row = page.locator('tbody tr').filter({ hasText: options.email }).first();
    if (!(await row.isVisible({ timeout: 5_000 }).catch(() => false))) return;
    await row
      .getByRole('button', { name: 'Cancel invitation', exact: true })
      .click({ force: true });
    // Confirm modal: title "Cancel Invitation", confirm button labelled the same.
    const confirm = page
      .getByRole('dialog')
      .getByRole('button', { name: 'Cancel Invitation', exact: true });
    if (await confirm.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await confirm.click();
    }
    await expect(row).toHaveCount(0, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to cancel invitation for ${options.email}`).toBe(true);
  }
}

// ── Re-exports for convenience ─────────────────────────────────────────────
export { pickSelectOptionByLabel };
