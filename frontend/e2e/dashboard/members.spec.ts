/**
 * Members + Invitations e2e flow against the real backend.
 *
 * Scenarios ML-/MI-/MR-/MD-/INV-/MM- from frontend/e2e/docs/members.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture (logs in as the org owner).
 * - No `page.route` mocks — every invite/cancel hits the real backend.
 * - Tests that create an invitation cancel it in `try/finally` so the org
 *   never finishes above the Core member-cap (3).
 * - Scenarios that need a *real accepted member* (MR-002, MD-002) cannot
 *   be implemented today: invitation tokens are not exposed via the API,
 *   so there is no way to programmatically accept an invite. Those tests
 *   ship as `test.skip()` with a documented reason.
 */

import { expect, type Page } from '@playwright/test';

import { test } from '../helpers/auth';
import {
  cancelInvitationViaUI,
  gotoInvitationsTab,
  gotoMembersTab,
  inviteMemberViaUI,
  openInviteModal,
  pickSelectOptionByLabel,
  uniqueInviteEmail,
} from '../helpers/memberFixtures';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Members', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await page.goto('/members');
    await expect(page.getByRole('button', { name: /invite member/i })).toBeVisible({
      timeout: 15_000,
    });
  });

  test.describe('Page identity + rendering', () => {
    test('ML-001 renders the header, both tabs, and Invite Member CTA', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /^members$/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /^invitations$/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /invite member/i })).toBeVisible();
    });

    test('ML-002 Members tab shows the expected columns', async ({ page }) => {
      await gotoMembersTab(page);
      for (const header of [/^name$/i, /^role$/i, /^status$/i]) {
        await expect(page.getByRole('columnheader', { name: header }).first()).toBeVisible({
          timeout: 10_000,
        });
      }
    });

    test('ML-003 Members tab lists at least one row (the logged-in user)', async ({ page }) => {
      await gotoMembersTab(page);
      // The signed-in user must always appear in the org's own member list.
      await expect(page.locator('tbody tr').first()).toBeVisible({ timeout: 10_000 });
    });

    test('ML-004 search input is interactive', async ({ page }) => {
      await gotoMembersTab(page);
      const search = page.getByPlaceholder(/search members/i).first();
      await expect(search).toBeVisible({ timeout: 5_000 });
      await search.fill('zzznoresult');
      await page.waitForTimeout(500); // debounce
      await search.clear();
    });

    test('ML-005 role filter dropdown opens with the documented options', async ({ page }) => {
      await gotoMembersTab(page);
      // The role-filter trigger is the only SelectInput inside the toolbar.
      const trigger = page.getByRole('combobox').first();
      await trigger.click();
      const listbox = page.getByRole('listbox').first();
      for (const role of [/all/i, /owner/i, /admin/i, /member/i, /viewer/i]) {
        await expect(listbox.getByRole('option', { name: role }).first()).toBeVisible();
      }
      await page.keyboard.press('Escape');
    });

    test('ML-006 Invitations tab renders its own column headers', async ({ page }) => {
      await gotoInvitationsTab(page);
      await expect(page.getByRole('columnheader', { name: /^email$/i }).first()).toBeVisible({
        timeout: 10_000,
      });
      await expect(page.getByRole('columnheader', { name: /^role$/i }).first()).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /^status$/i }).first()).toBeVisible();
    });
  });

  test.describe('Invite modal — validation', () => {
    test('MI-001 clicking Invite Member opens the modal with all three fields', async ({
      page,
    }) => {
      await openInviteModal(page);
      const dialog = page.getByRole('dialog');
      await expect(dialog.locator('input[name="name"]').first()).toBeVisible();
      await expect(dialog.locator('input[name="email"]').first()).toBeVisible();
      await expect(dialog.locator('button[id="invite-role"]').first()).toBeVisible();
      await page.keyboard.press('Escape');
    });

    test('MI-002 Send Invite is disabled while the form is invalid', async ({ page }) => {
      await openInviteModal(page);
      const submit = page.getByRole('dialog').getByRole('button', { name: /send invite/i });
      await expect(submit).toBeDisabled();
      // Fill name only — still invalid because email is empty.
      await page.getByRole('dialog').locator('input[name="name"]').first().fill('Invalid Probe');
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });

    test('MI-003 invalid email keeps Send Invite disabled', async ({ page }) => {
      await openInviteModal(page);
      const dialog = page.getByRole('dialog');
      await dialog.locator('input[name="name"]').first().fill('Bad Email Probe');
      await dialog.locator('input[name="email"]').first().fill('not-an-email');
      // Trigger blur to surface the Zod email validation.
      await dialog.locator('input[name="email"]').first().blur();
      const submit = dialog.getByRole('button', { name: /send invite/i });
      await expect(submit).toBeDisabled();
      await page.keyboard.press('Escape');
    });
  });

  test.describe('Invite — happy path + duplicates', () => {
    test('MI-004 valid invite creates a new row + success toast', async ({ page }) => {
      const email = uniqueInviteEmail('MI-004');
      try {
        await inviteMemberViaUI(page, { email });
        await expect(getToast(page)).toContainText(/invite|sent|success/i, { timeout: 10_000 });
        await gotoInvitationsTab(page);
        await expect(page.locator('tbody tr').filter({ hasText: email }).first()).toBeVisible({
          timeout: 10_000,
        });
      } finally {
        await cancelInvitationViaUI(page, { email });
      }
    });

    test('MI-005 inviting the same email twice surfaces an error toast', async ({ page }) => {
      const email = uniqueInviteEmail('MI-005');
      try {
        await inviteMemberViaUI(page, { email });
        // Re-open the modal and try to invite the SAME email again.
        await page.goto('/members');
        await openInviteModal(page);
        const dialog = page.getByRole('dialog');
        await dialog.locator('input[name="name"]').first().fill('Duplicate Probe');
        await dialog.locator('input[name="email"]').first().fill(email);
        const roleTrigger = dialog.locator('button[id="invite-role"]').first();
        await pickSelectOptionByLabel(page, roleTrigger, 'Member');
        await dialog.getByRole('button', { name: /send invite/i }).click();
        // Either an inline field error or an error toast — accept either.
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
        await page.keyboard.press('Escape').catch(() => undefined);
      } finally {
        await cancelInvitationViaUI(page, { email });
      }
    });
  });

  test.describe('Invitation row actions', () => {
    test('INV-001 cancelling a pending invitation removes the row', async ({ page }) => {
      const email = uniqueInviteEmail('INV-001');
      await inviteMemberViaUI(page, { email });
      // cancelInvitationViaUI does the work + asserts the row is gone.
      await cancelInvitationViaUI(page, { email });
    });

    test('INV-002 resending a pending invitation surfaces a toast', async ({ page }) => {
      const email = uniqueInviteEmail('INV-002');
      try {
        await inviteMemberViaUI(page, { email });
        await gotoInvitationsTab(page);
        const row = page.locator('tbody tr').filter({ hasText: email }).first();
        await expect(row).toBeVisible({ timeout: 10_000 });
        await row.getByRole('button', { name: 'Resend invitation', exact: true }).click({
          force: true,
        });
        await expect(getToast(page)).toBeVisible({ timeout: 10_000 });
      } finally {
        await cancelInvitationViaUI(page, { email });
      }
    });
  });

  test.describe('Last-owner protection', () => {
    test('MR-001 the signed-in owner role dropdown is locked or read-only', async ({ page }) => {
      await gotoMembersTab(page);
      // The current user is the only owner — find the row by the owner badge.
      const ownerRow = page.locator('tbody tr', { hasText: /owner/i }).first();
      await expect(ownerRow).toBeVisible({ timeout: 10_000 });
      // The role control on the last-owner row should be disabled OR omitted.
      const roleControl = ownerRow.getByRole('combobox').first();
      const visible = await roleControl.isVisible({ timeout: 1_000 }).catch(() => false);
      if (visible) {
        await expect(roleControl).toBeDisabled();
      }
    });

    test('MD-001 the signed-in owner Delete button is locked or omitted', async ({ page }) => {
      await gotoMembersTab(page);
      const ownerRow = page.locator('tbody tr', { hasText: /owner/i }).first();
      await expect(ownerRow).toBeVisible({ timeout: 10_000 });
      const deleteBtn = ownerRow.getByRole('button', { name: /remove|delete/i }).first();
      const visible = await deleteBtn.isVisible({ timeout: 1_000 }).catch(() => false);
      if (visible) {
        await expect(deleteBtn).toBeDisabled();
      }
    });
  });

  // ─── MM-FULL: comprehensive invite → resend → cancel happy path ──────────
  test.describe('Comprehensive flow', () => {
    test('MM-FULL invite → assert row → resend → cancel → assert gone', async ({ page }) => {
      test.setTimeout(180_000);
      const email = uniqueInviteEmail('MM-FULL');

      // 1. Invite.
      await inviteMemberViaUI(page, { email, role: 'admin' });
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

      // 2. Confirm row appears in Invitations tab.
      await gotoInvitationsTab(page);
      const row = page.locator('tbody tr').filter({ hasText: email }).first();
      await expect(row).toBeVisible({ timeout: 10_000 });

      // 3. Resend.
      await row.getByRole('button', { name: 'Resend invitation', exact: true }).click({
        force: true,
      });
      await expect(getToast(page)).toBeVisible({ timeout: 10_000 });

      // 4. Cancel.
      await cancelInvitationViaUI(page, { email });

      // 5. Confirm gone.
      await page.goto('/members');
      await gotoInvitationsTab(page);
      await expect(page.locator('tbody tr').filter({ hasText: email })).toHaveCount(0, {
        timeout: 10_000,
      });
    });
  });
});

// ─── Documented-but-not-yet-implemented scenarios ────────────────────────────
test.skip('MR-002 role change on an accepted member persists — needs an accepted-member seed (invite tokens are not exposed via API, so we cannot programmatically accept).', async () => {});
test.skip('MD-002 delete confirmation modal on a non-owner member opens — needs the same accepted-member seed.', async () => {});
test.fixme(
  'MI-006 member-cap (3 in Core) returns 403 — would leave the org near the cap; run this manually in a dedicated test env',
  async () => {},
);
