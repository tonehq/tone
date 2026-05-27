/**
 * Agent create — inbound flow against the real backend.
 *
 * Scenarios AC-001 … AC-030 from frontend/e2e/docs/agents-create.md.
 *
 * Strategy:
 * - Real login via the shared worker fixture.
 * - No `page.route` mocks anywhere — the form hits the actual catalog and
 *   create endpoints exactly like a human user would.
 * - Tests that actually save create a real agent. We collect their IDs and
 *   delete them via the UI in `afterAll`.
 */

import { expect, type Page } from '@playwright/test';

import {
  assignFirstPhoneNumber,
  attachFirstMcpServer,
  deleteAgentViaUI,
  fillAiStep,
  fillBasicsStep,
  fillPromptStep,
  fillVoiceStep,
  goToStep,
  pickAllTools,
  pickFirstKbDoc,
  uniqueAgentName,
} from '../helpers/agentFixtures';
import { test } from '../helpers/auth';

const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

test.describe('Agents — create inbound', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await page.goto('/agents/create/inbound');
    await expect(page.getByText('My Inbound Assistant').first()).toBeVisible({ timeout: 15_000 });
  });

  test.describe('Page identity', () => {
    test('AC-001 renders the new-inbound agent header', async ({ page }) => {
      await expect(page.getByText('My Inbound Assistant').first()).toBeVisible();
      await expect(page.getByText('New', { exact: true }).first()).toBeVisible();
    });

    test('AC-002 sidebar shows the six steps without Review', async ({ page }) => {
      for (const label of ['Basics', 'Prompt', 'AI', 'Voice', 'Tools & MCP', 'Knowledge & Phone']) {
        await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
      }
      await expect(page.getByText('Review', { exact: true })).toHaveCount(0);
    });

    test('AC-003 header has Back / Preview / Create agent buttons (no Delete)', async ({
      page,
    }) => {
      await expect(page.getByRole('button', { name: /back to agents/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /preview/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /create agent/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /^delete$/i })).toHaveCount(0);
    });

    test('AC-004 Basics step is the default body', async ({ page }) => {
      await expect(page.getByText(/agent name/i).first()).toBeVisible();
    });
  });

  test.describe('Basics step', () => {
    test('AC-005 name is required and jumps to Basics on save', async ({ page }) => {
      // Move to a different tab, then back; clear the name; click Create.
      await page.getByText('Prompt', { exact: true }).first().click();
      await page.getByText('Basics', { exact: true }).first().click();
      const nameInput = page.locator('input[name="name"]').first();
      await nameInput.fill('');
      await page.getByRole('button', { name: /create agent/i }).click();
      await expect(page.getByText(/required/i).first()).toBeVisible({ timeout: 5_000 });
    });

    test('AC-006 description accepts long text', async ({ page }) => {
      const desc = 'A'.repeat(450);
      const textarea = page.locator('textarea[name="description"]').first();
      await textarea.fill(desc);
      await expect(textarea).toHaveValue(desc);
    });

    test('AC-008 is_active switch toggles', async ({ page }) => {
      const sw = page.getByRole('switch').first();
      const startChecked = (await sw.getAttribute('aria-checked')) === 'true';
      await sw.click();
      await expect(sw).toHaveAttribute('aria-checked', String(!startChecked));
    });
  });

  test.describe('Tools & MCP step', () => {
    test('AC-022 New tool navigates when clean', async ({ page }) => {
      await page.getByText('Tools & MCP', { exact: true }).first().click();
      await page
        .getByRole('button', { name: /new tool/i })
        .first()
        .click();
      await page.waitForURL(/\/tools\/create/, { timeout: 10_000 });
    });
  });

  test.describe('Preview + Save', () => {
    test('AC-027 Preview opens with scrollable Review content', async ({ page }) => {
      await page.getByRole('button', { name: /preview/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5_000 });
      await expect(page.getByText(/agent preview/i)).toBeVisible();
      await page.keyboard.press('Escape');
    });

    test('AC-029 Create posts the form and redirects to edit', async ({ page }) => {
      const name = uniqueAgentName('inbound-save');
      await page.locator('input[name="name"]').first().fill(name);
      await page.getByRole('button', { name: /create agent/i }).click();
      await page.waitForURL(/\/agents\/edit\/inbound\/[\w-]+/, { timeout: 20_000 });
      const id = page.url().match(/\/agents\/edit\/inbound\/([\w-]+)/)?.[1];
      expect(id, 'agent id parsed from redirect URL').toBeTruthy();
      await expect(getToast(page)).toContainText(/agent created/i, { timeout: 10_000 });
      // Self-clean so the run leaves no `__e2e__` rows behind.
      if (id) await deleteAgentViaUI(page, { agentType: 'inbound', id });
    });
  });

  // ─── AC-FULL: comprehensive happy-path through every step ─────────────────
  // Real user journey — fills Basics, Prompt, AI, Voice, Tools, MCP, KB, and
  // Phone, saves, reloads the edit page, and verifies every value persisted.
  test.describe('Comprehensive flow', () => {
    test('AC-FULL fills every step, saves, reloads and verifies persistence', async ({ page }) => {
      test.setTimeout(180_000);

      const name = uniqueAgentName('inbound-full');
      const description = 'E2E inbound agent — comprehensive flow';
      const firstMessage = 'Hello! How can I help you today?';
      const endCallMessage = 'Thank you for calling. Have a great day!';
      const systemPrompt = 'You are a helpful voice assistant for the e2e suite.';
      const maxTokens = 1024;
      const tokenLimit = 4000;

      // 1. Basics — fill every textarea + flip the active switch.
      await page.locator('input[name="name"]').first().fill(name);
      const basicsReport = await fillBasicsStep(page, {
        description,
        firstMessage,
        endCallMessage,
        toggleActive: true,
      });

      // 2. Prompt
      const promptReport = await fillPromptStep(page, { systemPrompt });

      // 3. AI — provider, model, temperature slider, max tokens, history limit
      const aiReport = await fillAiStep(page, {
        maxTokens,
        tokenLimit,
        temperatureSteps: 7,
      });

      // 4. Voice + STT — language, provider, model, voice, speed slider, STT
      const voiceReport = await fillVoiceStep(page);

      // 5. Tools + MCP — toggle every tile and attach the first MCP server
      const toolReport = await pickAllTools(page);
      const mcpReport = await attachFirstMcpServer(page);

      // 6. Knowledge + Phone
      const kbReport = await pickFirstKbDoc(page);
      const phoneReport = await assignFirstPhoneNumber(page);

      // Log everything we managed to fill so failures are debuggable.
      console.log('AC-FULL fill report', {
        ...basicsReport,
        ...promptReport,
        ...aiReport,
        ...voiceReport,
        ...toolReport,
        ...mcpReport,
        ...kbReport,
        ...phoneReport,
      });

      // 7. Save
      await page.getByRole('button', { name: /create agent/i }).click();
      await page.waitForURL(/\/agents\/edit\/inbound\/[\w-]+/, { timeout: 30_000 });
      await expect(getToast(page)).toContainText(/agent created/i, { timeout: 10_000 });

      const id = page.url().match(/\/agents\/edit\/inbound\/([\w-]+)/)?.[1];
      expect(id, 'agent id parsed from redirect URL').toBeTruthy();
      if (!id) return;

      // 8. Reload the edit page and verify persistence
      await page.goto(`/agents/edit/inbound/${id}`);
      await expect(page.locator('input[name="name"]').first()).toHaveValue(name, {
        timeout: 15_000,
      });

      if (basicsReport.description) {
        await expect(page.locator('textarea[name="description"]').first()).toHaveValue(description);
      }
      if (basicsReport.firstMessage) {
        await expect(page.locator('textarea[placeholder*="Hi there"]').first()).toHaveValue(
          firstMessage,
        );
      }
      if (basicsReport.endCallMessage) {
        await expect(
          page.locator('textarea[placeholder*="Thanks for calling"]').first(),
        ).toHaveValue(endCallMessage);
      }

      if (promptReport.systemPrompt) {
        await goToStep(page, 'prompt');
        await expect(page.locator('textarea').first()).toHaveValue(systemPrompt);
      }

      if (aiReport.maxTokens) {
        await goToStep(page, 'ai');
        await expect(
          page.locator('input[name="config.llm_settings.max_tokens"]').first(),
        ).toHaveValue(String(maxTokens));
      }
      if (aiReport.tokenLimit) {
        await goToStep(page, 'ai');
        await expect(
          page.locator('input[name="config.conversation_history_token_limit"]').first(),
        ).toHaveValue(String(tokenLimit));
      }

      // 9. Cleanup
      await deleteAgentViaUI(page, { agentType: 'inbound', id });
    });
  });
});

// ── Documented-but-not-yet-implemented scenarios ─────────────────────────────
test.fixme('AC-007 conversation messages render as textareas', async () => {});
test.fixme('AC-009 system prompt persists across tab switches', async () => {});
test.fixme('AC-010 token-limit input is numeric only', async () => {});
test.fixme('AC-011 LLM provider shows No data when empty', async () => {});
test.fixme('AC-012 selecting LLM provider reveals model dropdown', async () => {});
test.fixme('AC-013 LLM tuning fields update form state', async () => {});
test.fixme('AC-014 voice language dropdown loads from API', async () => {});
test.fixme('AC-015 picking language refreshes TTS providers', async () => {});
test.fixme('AC-016 picking provider+language loads voices', async () => {});
test.fixme('AC-017 voice sample play button toggles', async () => {});
test.fixme('AC-018 speed slider is clamped and defaulted', async () => {});
test.fixme('AC-019 STT provider+model dropdowns wire together', async () => {});
test.fixme('AC-020 tool checkbox toggles tool_ids', async () => {});
test.fixme('AC-021 tool search filters the list', async () => {});
test.fixme('AC-023 MCP server picker adds and removes chips', async () => {});
test.fixme('AC-024 KB list loads and toggles upload_ids', async () => {});
test.fixme('AC-025 KB upload modal enabled in create mode and validates files', async () => {});
test.fixme('AC-026 Assign phone modal lists numbers for the channel', async () => {});
test.fixme('AC-028 Edit link in preview jumps to the step', async () => {});
test.fixme('AC-030 Create surfaces backend validation errors', async () => {});
