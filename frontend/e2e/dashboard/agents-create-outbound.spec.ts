/**
 * Agent create — outbound variant against the real backend.
 *
 * Scenarios ACO-001 … ACO-003 from frontend/e2e/ux_flow_docs/agents-create.md.
 */

import { expect, type Page } from '@playwright/test';

import { deleteAgentViaUI, uniqueAgentName } from '../helpers/agentFixtures';
import { test } from '../helpers/auth';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Agents — create outbound', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await page.goto('/agents/create/outbound');
    await expect(page.getByText('My Outbound Assistant').first()).toBeVisible({ timeout: 15_000 });
  });

  test('ACO-001 renders the new-outbound agent header', async ({ page }) => {
    await expect(page.getByText('My Outbound Assistant').first()).toBeVisible();
    await expect(page.getByText('New', { exact: true }).first()).toBeVisible();
  });

  test('ACO-002 outbound create persists and redirects to edit', async ({ page }) => {
    const name = uniqueAgentName('outbound-save');
    await page.locator('input[name="name"]').first().fill(name);
    await page.getByRole('button', { name: /create agent/i }).click();
    await page.waitForURL(/\/agents\/edit\/outbound\/[\w-]+/, { timeout: 20_000 });
    const id = page.url().match(/\/agents\/edit\/outbound\/([\w-]+)/)?.[1];
    expect(id, 'agent id parsed from redirect URL').toBeTruthy();
    await expect(getToast(page)).toContainText(/agent created/i, { timeout: 10_000 });
    // Self-clean.
    if (id) await deleteAgentViaUI(page, { agentType: 'outbound', id });
  });

  test('ACO-003 outbound exposes the same six steps', async ({ page }) => {
    for (const label of ['Basics', 'Prompt', 'AI', 'Voice', 'Tools & MCP', 'Knowledge & Phone']) {
      await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText('Review', { exact: true })).toHaveCount(0);
  });
});
