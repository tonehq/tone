import { BrowserContext, expect, Page, test as base } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Mock data ────────────────────────────────────────────────────────────────
const MOCK_AGENT = {
  id: 1,
  uuid: 'uuid-agent-1',
  name: 'Sales Assistant',
  description: 'Handles inbound sales calls',
  agent_type: 'inbound',
  phone_number: '+1 (555) 123-4567',
  is_public: false,
  tags: {},
  total_calls: 10,
  total_minutes: 30,
  average_rating: 4.5,
  created_by: 1,
  created_at: 1708900000,
  updated_at: 1740048600000,
  llm_service_id: 1,
  tts_service_id: 1,
  stt_service_id: 1,
  llm_model_id: null,
  tts_model_id: null,
  stt_model_id: null,
  first_message: 'Hello, how can I help?',
  system_prompt: 'You are a helpful sales assistant.',
  end_call_message: 'Goodbye!',
  voicemail_message: null,
  status: 'active',
  custom_vocabulary: '["ToneHQ","Pipecat"]',
  filter_words: '["badword"]',
  realistic_filler_words: true,
  language: 'en',
  voice_speed: '70',
  patience_level: 'medium',
  speech_recognition: 'accurate',
  call_recording: true,
  call_transcription: true,
};

// ── Browser lifecycle ─────────────────────────────────────────────────────────
const test = base.extend<{ page: Page }, { workerContext: BrowserContext }>({
  workerContext: [
    async ({ browser }, provide) => {
      const context = await browser.newContext();
      const page = await context.newPage();
      await loginViaUI(page);
      await provide(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  page: async ({ workerContext }, provide) => {
    const pages = workerContext.pages();
    const page = pages.length > 0 ? pages[0] : await workerContext.newPage();
    await provide(page);
  },
});

// ── Helpers ───────────────────────────────────────────────────────────────────

const EDIT_URL = '/agents/edit/inbound/1';

async function mockGetAgentAPI(
  page: Page,
  agent: unknown = MOCK_AGENT,
): Promise<void> {
  await page.route('**/agent/get_all_agents**', async (route) => {
    const url = route.request().url();
    // The edit page fetches with ?agent_id=1 — return array with one item
    if (url.includes('agent_id')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agent ? [agent] : []),
      });
    } else {
      // List call — return full list (not needed for edit but just in case)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agent ? [agent] : []),
      });
    }
  });
}

async function ensureOnEditPage(page: Page): Promise<void> {
  if (page.url().includes(EDIT_URL)) return;
  await page.goto(EDIT_URL);
  // Wait for loading to finish
  await expect(page.getByText('Loading agent...')).not.toBeVisible({ timeout: 10_000 });
}

async function mockUpsertAPI(
  page: Page,
): Promise<Record<string, unknown>[]> {
  const captured: Record<string, unknown>[] = [];
  await page.route('**/agent/upsert_agent', async (route) => {
    const body = route.request().postDataJSON();
    captured.push(body);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 1, ...body }),
    });
  });
  return captured;
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Edit Agent Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await mockGetAgentAPI(page);
    await ensureOnEditPage(page);
  });

  // ── 1. Loading State ───────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows loading text during API fetch', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      // Delayed API response
      await page.route('**/agent/get_all_agents**', async (route) => {
        await new Promise((r) => setTimeout(r, 3000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([MOCK_AGENT]),
        });
      });

      await page.goto(EDIT_URL);
      await expect(page.getByText('Loading agent...')).toBeVisible({ timeout: 2_000 });
    });
  });

  // ── 2. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows populated agent name in sidebar', async ({ page }) => {
      await expect(page.getByText('Sales Assistant')).toBeVisible();
    });

    test('shows correct type chip', async ({ page }) => {
      const chip = page.locator('.MuiChip-root').filter({ hasText: 'Inbound' });
      await expect(chip).toBeVisible();
    });

    test('shows edit agent info alert', async ({ page }) => {
      await expect(page.locator('.MuiAlert-root')).toContainText('Edit agent');
    });

    test('shows Save Changes button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible();
    });

    test('shows form tabs', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /voice/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /call configuration/i })).toBeVisible();
    });
  });

  // ── 3. Pre-populated Data ──────────────────────────────────────────────────
  test.describe('Pre-populated Data', () => {
    test('General tab shows API values', async ({ page }) => {
      // Agent name
      const nameInput = page.locator('input[value="Sales Assistant"]');
      await expect(nameInput).toBeVisible();

      // Description textarea
      const descTextarea = page.locator('textarea').filter({ hasText: 'Handles inbound sales calls' });
      await expect(descTextarea).toBeVisible();

      // First message textarea
      const firstMsgTextarea = page.locator('textarea').filter({ hasText: 'Hello, how can I help?' });
      await expect(firstMsgTextarea).toBeVisible();
    });

    test('Voice tab shows API values', async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();

      // Language — English
      await expect(page.getByText('English')).toBeVisible();

      // Patience level should be "medium" (from mock)
      const mediumCard = page.locator('label').filter({ hasText: 'Medium' }).filter({ hasText: '~3 sec' });
      await expect(mediumCard).toBeVisible();
    });

    test('Call Configuration tab shows API values', async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();

      // Both toggles should be on (true in mock)
      const recordingSection = page.getByText('Call Recording').locator('..').locator('..');
      const recordSwitch = recordingSection.locator('.MuiSwitch-root input');
      await expect(recordSwitch).toBeChecked();

      const transcriptionSection = page.getByText('Call Transcription').locator('..').locator('..');
      const transcriptSwitch = transcriptionSection.locator('.MuiSwitch-root input');
      await expect(transcriptSwitch).toBeChecked();
    });

    test('agent name reflects in sidebar', async ({ page }) => {
      // The sidebar should show the agent name from the API
      await expect(page.getByText('Sales Assistant').first()).toBeVisible();
    });
  });

  // ── 4. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetAgentAPI(page);
      await page.goto(EDIT_URL);
      await expect(page.getByText('Loading agent...')).not.toBeVisible({ timeout: 10_000 });
    });

    test('sends id in payload for update', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        id: 1,
        name: 'Sales Assistant',
        agent_type: 'inbound',
      });
    });

    test('shows Saving... loading state', async ({ page }) => {
      await page.route('**/agent/upsert_agent', async (route) => {
        await new Promise((r) => setTimeout(r, 2000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: 1 }),
        });
      });

      await page.getByRole('button', { name: /save changes/i }).click();
      const savingBtn = page.getByRole('button', { name: /saving/i });
      await expect(savingBtn).toBeVisible();
      await expect(savingBtn).toBeDisabled();
    });

    test('redirects to /agents on success', async ({ page }) => {
      await mockUpsertAPI(page);
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });

    test('updates agent in DB and redirects to list (real API)', async ({ page }) => {
      // No mocks: real GET agent + real POST upsert. Requires running backend and at least one agent (e.g. id=1).
      await page.unrouteAll({ behavior: 'wait' });
      await page.goto(EDIT_URL);
      await expect(page.getByText('Loading agent...')).not.toBeVisible({ timeout: 15_000 });

      // If "Agent not found" then no agent with id=1 exists — skip assertion
      if (await page.getByText('Agent not found').isVisible().catch(() => false)) return;

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 15_000 });
    });
  });

  // ── 5. Error States ────────────────────────────────────────────────────────
  test.describe('Error States', () => {
    test('shows Agent not found when API returns null', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      await page.route('**/agent/get_all_agents**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      });

      await page.goto(EDIT_URL);
      await expect(page.getByText('Agent not found')).toBeVisible({ timeout: 10_000 });
    });

    test('shows Failed to load agent when API errors', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      await page.route('**/agent/get_all_agents**', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Server error' }),
        });
      });

      await page.goto(EDIT_URL);
      await expect(page.getByText('Failed to load agent')).toBeVisible({ timeout: 10_000 });
    });
  });
});
