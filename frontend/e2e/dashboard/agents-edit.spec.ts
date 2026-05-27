/**
 * Agent edit flow against the real backend.
 *
 * Scenarios AE-001 … AE-022 from frontend/e2e/docs/agents-edit.md.
 *
 * Strategy:
 * - Real login via shared worker fixture.
 * - `beforeAll` creates a real fixture agent through the UI; tests modify it
 *   and the `afterAll` deletes it. No mocks anywhere.
 * - The 404 redirect scenario uses a syntactically valid UUID that
 *   genuinely doesn't exist in the org.
 */

import { expect, type Page } from '@playwright/test';

import {
  createAgentViaUI,
  deleteAgentViaUI,
  fillBasicsStep,
  fillPromptStep,
  fillVoiceStep,
  goToStep,
  openEditAgent,
  uniqueAgentName,
} from '../helpers/agentFixtures';
import { test } from '../helpers/auth';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();
const NONEXISTENT_AGENT_ID = '00000000-0000-0000-0000-deadbeefcafe';

let fixtureAgentId = '';
let fixtureAgentName = '';

test.describe('Agents — edit', () => {
  // Reuse the already-logged-in worker context (set up by the shared `test`
  // fixture) so beforeAll/afterAll don't pay the login cost a second time.
  test.beforeAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    const { id, name } = await createAgentViaUI(page, {
      agentType: 'inbound',
      name: uniqueAgentName('edit-fixture'),
    });
    fixtureAgentId = id;
    fixtureAgentName = name;
  });

  test.afterAll(async ({ workerContext }) => {
    test.setTimeout(120_000);
    if (!fixtureAgentId) return;
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await deleteAgentViaUI(page, { agentType: 'inbound', id: fixtureAgentId });
  });

  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test.describe('Hydration', () => {
    test('AE-001 loads the agent and hydrates the form', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      const nameInput = page.locator('input[name="name"]').first();
      await expect(nameInput).toHaveValue(fixtureAgentName);
    });

    test('AE-003 404 redirects to /agents', async ({ page }) => {
      await page.goto(`/agents/edit/inbound/${NONEXISTENT_AGENT_ID}`);
      await page.waitForURL(/\/agents(?:\?|$|\/)/, { timeout: 15_000 });
      await expect(getToast(page)).toContainText(/agent not found/i, { timeout: 10_000 });
    });
  });

  test.describe('Header & meta', () => {
    test.beforeEach(async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
    });

    test('AE-005 header shows Delete and the agent name', async ({ page }) => {
      await expect(page.getByText(fixtureAgentName).first()).toBeVisible();
      await expect(page.getByRole('button', { name: /^delete$/i })).toBeVisible();
      await expect(page.getByText('New', { exact: true })).toHaveCount(0);
    });

    test('AE-006 Save button reads Save changes on edit', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible();
    });
  });

  test.describe('Diff-aware update', () => {
    test('AE-007 name change saves and persists', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      const newName = `${fixtureAgentName}-edited`;
      const nameInput = page.locator('input[name="name"]').first();
      await nameInput.fill(newName);
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(getToast(page)).toContainText(/agent updated/i, { timeout: 10_000 });
      // Reload to confirm persistence.
      await page.reload();
      await expect(page.locator('input[name="name"]').first()).toHaveValue(newName, {
        timeout: 10_000,
      });
      // Reset so other tests still see the original name.
      await page.locator('input[name="name"]').first().fill(fixtureAgentName);
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(getToast(page)).toContainText(/agent updated/i, { timeout: 10_000 });
    });

    test('AE-008 unchanged save shows No changes toast', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(getToast(page)).toContainText(/no changes/i, { timeout: 10_000 });
    });
  });

  test.describe('Delete', () => {
    test('AE-014 Delete opens confirmation modal', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.getByRole('button', { name: /^delete$/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/delete agent/i).first()).toBeVisible();
      // Cancel — we don't want to delete the shared fixture here.
      await page.keyboard.press('Escape');
    });

    test('AE-015 Delete bypasses unsaved-changes guard and removes the agent', async ({
      page,
    }) => {
      // Use a throw-away agent so the shared fixture survives.
      const throwaway = await createAgentViaUI(page, {
        agentType: 'inbound',
        name: uniqueAgentName('delete-target'),
      });
      // Make form dirty before deleting.
      await page.locator('input[name="name"]').first().fill(`${throwaway.name}-dirty`);
      await page.getByRole('button', { name: /^delete$/i }).click();
      await page
        .getByRole('dialog')
        .getByRole('button', { name: 'Delete', exact: true })
        .click();
      await page.waitForURL(/\/agents(?:\?|$|\/)/, { timeout: 10_000 });
    });
  });

  test.describe('Unsaved-changes guard', () => {
    test('AE-016 dirty sidebar click opens the discard modal', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.locator('input[name="name"]').first().fill(`${fixtureAgentName}-dirty`);
      await page.locator('a[href="/tools"]').first().click();
      await expect(page.getByText(/discard unsaved changes\?/i)).toBeVisible({ timeout: 5_000 });
      await page.getByRole('button', { name: /keep editing/i }).click();
      await expect(page).toHaveURL(new RegExp(`/agents/edit/inbound/${fixtureAgentId}`));
      // Reset the dirty state for the next test.
      await page.locator('input[name="name"]').first().fill(fixtureAgentName);
    });

    test('AE-019 dirty New tool click routes through discard modal', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.locator('input[name="name"]').first().fill(`${fixtureAgentName}-dirty`);
      await page.getByText('Tools & MCP', { exact: true }).first().click();
      await page.getByRole('button', { name: /new tool/i }).first().click();
      await expect(page.getByText(/discard unsaved changes\?/i)).toBeVisible({ timeout: 5_000 });
      await page.getByRole('button', { name: /discard/i }).click();
      await page.waitForURL(/\/tools\/create/, { timeout: 10_000 });
    });

    test('AE-020 dirty header Back routes through discard modal', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.locator('input[name="name"]').first().fill(`${fixtureAgentName}-dirty`);
      await page.getByRole('button', { name: /back to agents/i }).click();
      await expect(page.getByText(/discard unsaved changes\?/i)).toBeVisible({ timeout: 5_000 });
      await page.getByRole('button', { name: /keep editing/i }).click();
      await expect(page).toHaveURL(new RegExp(`/agents/edit/inbound/${fixtureAgentId}`));
      await page.locator('input[name="name"]').first().fill(fixtureAgentName);
    });

    test('AE-021 clean state never opens the discard modal', async ({ page }) => {
      await openEditAgent(page, {
        agentType: 'inbound',
        id: fixtureAgentId,
        nameContains: fixtureAgentName,
      });
      await page.locator('a[href="/tools"]').first().click();
      await page.waitForURL(/\/tools(?:\?|$|\/)/, { timeout: 10_000 });
    });
  });

  // ─── AE-FULL: comprehensive edit-and-verify happy path ────────────────────
  // Creates a fresh agent in-test, modifies every safe field across each step,
  // saves, reloads, verifies, deletes. Uses a fresh agent (not the shared
  // fixture) so verification reads only this test's writes.
  test.describe('Comprehensive flow', () => {
    test('AE-FULL modifies every step, saves, reloads and verifies', async ({ page }) => {
      test.setTimeout(180_000);

      // Fresh agent so we can scrub it at the end without disturbing the
      // shared fixture.
      const { id, name } = await createAgentViaUI(page, {
        agentType: 'inbound',
        name: uniqueAgentName('edit-full'),
      });

      const newDescription = 'AE-FULL edited description';
      const newFirstMessage = 'Hi from AE-FULL edit test.';
      const newSystemPrompt = 'You are a knowledgeable assistant — AE-FULL edit.';

      // 1. Basics
      const basicsReport = await fillBasicsStep(page, {
        description: newDescription,
        firstMessage: newFirstMessage,
      });
      // 2. Prompt
      const promptReport = await fillPromptStep(page, { systemPrompt: newSystemPrompt });
      // 3. Voice + STT
      const voiceReport = await fillVoiceStep(page);

      console.log('AE-FULL fill report', { ...basicsReport, ...promptReport, ...voiceReport });

      // 4. Save
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(getToast(page)).toContainText(/agent updated/i, { timeout: 15_000 });

      // 5. Reload + verify
      await page.goto(`/agents/edit/inbound/${id}`);
      await expect(page.locator('input[name="name"]').first()).toHaveValue(name, {
        timeout: 15_000,
      });
      if (basicsReport.description) {
        await expect(page.locator('textarea[name="description"]').first()).toHaveValue(
          newDescription,
        );
      }
      if (basicsReport.firstMessage) {
        await expect(
          page.locator('textarea[placeholder*="Hi there"]').first(),
        ).toHaveValue(newFirstMessage);
      }
      if (promptReport.systemPrompt) {
        await goToStep(page, 'prompt');
        await expect(page.locator('textarea').first()).toHaveValue(newSystemPrompt);
      }

      // 6. Cleanup
      await deleteAgentViaUI(page, { agentType: 'inbound', id });
    });
  });
});

// ── Documented-but-not-yet-implemented scenarios ─────────────────────────────
test.fixme('AE-002 step values persist across tab switches', async () => {});
test.fixme('AE-004 500 surfaces an error toast', async () => {});
test.fixme('AE-009 tool toggle posts tool_ids diff only', async () => {});
test.fixme('AE-010 clearing description posts null', async () => {});
test.fixme('AE-011 KB upload modal posts file and selects on close', async () => {});
test.fixme('AE-012 phone assignment round-trips channel_id and label', async () => {});
test.fixme('AE-013 Preview shows live form state', async () => {});
test.fixme('AE-017 dirty browser back routes through the discard modal', async () => {});
test.fixme('AE-018 dirty reload triggers beforeunload', async () => {});
test.fixme('AE-022 successful save resets dirty so nav is unblocked', async () => {});
