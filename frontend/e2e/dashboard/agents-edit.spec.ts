import { test as base, BrowserContext, expect, Page } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Mock data ────────────────────────────────────────────────────────────────
const MOCK_AGENT = {
  id: 1,
  uuid: 'uuid-agent-1',
  name: 'Sales Assistant',
  description: 'Handles inbound sales calls',
  agent_type: 'inbound',
  phone_number: null,
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

// Minimal mock: only required fields set, all optional fields null/empty/default
const MOCK_AGENT_MINIMAL = {
  id: 2,
  uuid: 'uuid-agent-2',
  name: 'Minimal Agent',
  description: null,
  agent_type: 'outbound',
  phone_number: null,
  is_public: false,
  tags: {},
  total_calls: 0,
  total_minutes: 0,
  average_rating: null,
  created_by: 1,
  created_at: 1708900000,
  updated_at: 1740048600000,
  llm_service_id: null,
  tts_service_id: null,
  stt_service_id: null,
  llm_model_id: null,
  tts_model_id: null,
  stt_model_id: null,
  first_message: null,
  system_prompt: null,
  end_call_message: null,
  voicemail_message: null,
  status: 'active',
  custom_vocabulary: null,
  filter_words: null,
  realistic_filler_words: false,
  language: 'en',
  voice_speed: '50',
  patience_level: 'low',
  speech_recognition: 'fast',
  call_recording: false,
  call_transcription: false,
};

// Mock with phone numbers assigned
const MOCK_AGENT_WITH_PHONE = {
  ...MOCK_AGENT,
  id: 3,
  uuid: 'uuid-agent-3',
  phone_number: [
    { type: 'twilio', no: '+1 (555) 123-4567' },
    { type: 'twilio', no: '+1 (555) 987-6543' },
  ],
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

async function mockGetAgentAPI(page: Page, agent: unknown = MOCK_AGENT): Promise<void> {
  await page.route('**/agent/get_all_agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agent ? [agent] : []),
    });
  });
}

async function ensureOnEditPage(page: Page): Promise<void> {
  if (page.url().includes(EDIT_URL)) return;
  await page.goto(EDIT_URL);
  await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 10_000 });
}

async function mockUpsertAPI(page: Page): Promise<Record<string, unknown>[]> {
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
    test('shows loading spinner during API fetch', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      await page.route('**/agent/get_all_agents**', async (route) => {
        await new Promise((r) => setTimeout(r, 3000));
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([MOCK_AGENT]),
        });
      });

      await page.goto(EDIT_URL);
      await expect(page.locator('[class*="animate-spin"]').first()).toBeVisible({
        timeout: 2_000,
      });
    });
  });

  // ── 2. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows populated agent name in sidebar', async ({ page }) => {
      await expect(page.locator('aside').getByText('Sales Assistant')).toBeVisible();
    });

    test('shows correct type badge in sidebar', async ({ page }) => {
      await expect(page.locator('aside').getByText('Inbound')).toBeVisible();
    });

    test('shows status bar about receiving calls', async ({ page }) => {
      await expect(page.getByText(/can't receive calls/)).toBeVisible();
    });

    test('shows Save Changes button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible();
    });

    test('shows all four form tabs including Assign Number', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /voice/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /call configuration/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /assign number/i })).toBeVisible();
    });

    test('shows Back to Agents button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /back to agents/i })).toBeVisible();
    });

    test('shows Test Agent button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /test agent/i })).toBeVisible();
    });
  });

  // ── 3. Pre-populated Data — General Tab ────────────────────────────────────
  test.describe('Pre-populated Data — General Tab', () => {
    test('shows agent name from API', async ({ page }) => {
      await expect(page.locator('input[name="name"]')).toHaveValue('Sales Assistant');
    });

    test('shows description from API', async ({ page }) => {
      const descTextarea = page.locator('textarea[name="description"]');
      await expect(descTextarea).toHaveValue('Handles inbound sales calls');
    });

    test('shows first message from API', async ({ page }) => {
      const firstMsgTextarea = page.locator('textarea[name="first_message"]');
      await expect(firstMsgTextarea).toHaveValue('Hello, how can I help?');
    });

    test('shows end call message from API', async ({ page }) => {
      const endCallTextarea = page.locator('textarea[name="end_call_message"]');
      await expect(endCallTextarea).toHaveValue('Goodbye!');
    });

    test('shows custom vocabulary chips from API', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();
      await expect(page.getByText('Pipecat', { exact: true })).toBeVisible();
    });

    test('shows filter word chips from API', async ({ page }) => {
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      await expect(page.getByText('badword', { exact: true })).toBeVisible();
    });

    test('shows filler words switch on from API', async ({ page }) => {
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await expect(fillerRow.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    });

    test('agent name reflects in sidebar', async ({ page }) => {
      await expect(page.locator('aside').getByText('Sales Assistant')).toBeVisible();
    });
  });

  // ── 4. Pre-populated Data — Voice Tab ──────────────────────────────────────
  test.describe('Pre-populated Data — Voice Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();
    });

    test('shows language as English from API', async ({ page }) => {
      await expect(page.getByText(/English/).first()).toBeVisible();
    });

    test('shows voice speed at 70 from API', async ({ page }) => {
      const slider = page.getByRole('slider');
      await expect(slider).toHaveAttribute('aria-valuenow', '70');
    });

    test('shows patience level as Medium from API', async ({ page }) => {
      await expect(page.getByRole('radio', { name: /^Medium /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
      await expect(page.getByRole('radio', { name: /^High ~/i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });

    test('shows speech recognition as High Accuracy from API', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('radio', { name: /High Accuracy/i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /Faster/i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });
  });

  // ── 5. Pre-populated Data — Call Configuration Tab ─────────────────────────
  test.describe('Pre-populated Data — Call Configuration Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();
    });

    test('shows call recording enabled from API', async ({ page }) => {
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await expect(recordingRow.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    });

    test('shows call transcription enabled from API', async ({ page }) => {
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await expect(transcriptionRow.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    });
  });

  // ── 6. Pre-populated Data — Prompt ─────────────────────────────────────────
  test.describe('Pre-populated Data — Prompt', () => {
    test('shows system prompt from API in editor', async ({ page }) => {
      await page.getByRole('button', { name: 'Prompt' }).click();
      const editor = page.locator('.ProseMirror');
      await expect(editor).toContainText('You are a helpful sales assistant.');
    });
  });

  // ── 7. Pre-populated Data — Assign Number Tab (edit mode) ──────────────────
  test.describe('Assign Number Tab — Edit Mode', () => {
    test('shows Assign New Number button in edit mode', async ({ page }) => {
      await page.getByRole('tab', { name: /assign number/i }).click();
      await expect(page.getByRole('button', { name: /assign new number/i })).toBeVisible();
    });

    test('shows no-numbers message when no phone assigned', async ({ page }) => {
      await page.getByRole('tab', { name: /assign number/i }).click();
      await expect(page.getByText('No phone numbers assigned yet.')).toBeVisible();
    });
  });

  // ── 7b. Assign Number Tab — With Phone Numbers ─────────────────────────────
  test.describe('Assign Number Tab — With Phone Numbers', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetAgentAPI(page, MOCK_AGENT_WITH_PHONE);
      await page.goto('/agents/edit/inbound/3');
      await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 10_000 });
    });

    test('shows phone assigned status bar', async ({ page }) => {
      await expect(page.getByText('Phone assigned:')).toBeVisible();
      await expect(page.getByText('+1 (555) 123-4567')).toBeVisible();
      await expect(page.getByText('+1 (555) 987-6543')).toBeVisible();
    });

    test('shows phone numbers in sidebar', async ({ page }) => {
      await expect(page.locator('aside').getByText('+1 (555) 123-4567')).toBeVisible();
      await expect(page.locator('aside').getByText('+1 (555) 987-6543')).toBeVisible();
    });

    test('shows assigned phone numbers in Assign Number tab', async ({ page }) => {
      await page.getByRole('tab', { name: /assign number/i }).click();
      await expect(page.getByText('+1 (555) 123-4567')).toBeVisible();
      await expect(page.getByText('+1 (555) 987-6543')).toBeVisible();
    });

    test('shows Unassign button for each phone number', async ({ page }) => {
      await page.getByRole('tab', { name: /assign number/i }).click();
      const unassignButtons = page.getByRole('button', { name: 'Unassign' });
      await expect(unassignButtons).toHaveCount(2);
    });
  });

  // ── 8. Minimal Agent — Default Values for Null Fields ──────────────────────
  test.describe('Minimal Agent — Default Values', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetAgentAPI(page, MOCK_AGENT_MINIMAL);
      await page.goto('/agents/edit/outbound/2');
      await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 10_000 });
    });

    test('shows agent name and Outbound badge', async ({ page }) => {
      await expect(page.locator('input[name="name"]')).toHaveValue('Minimal Agent');
      await expect(page.locator('aside').getByText('Outbound')).toBeVisible();
    });

    test('shows empty description for null value', async ({ page }) => {
      await expect(page.locator('textarea[name="description"]')).toHaveValue('');
    });

    test('shows empty first message for null value', async ({ page }) => {
      await expect(page.locator('textarea[name="first_message"]')).toHaveValue('');
    });

    test('shows empty end call message for null value', async ({ page }) => {
      await expect(page.locator('textarea[name="end_call_message"]')).toHaveValue('');
    });

    test('shows no custom vocabulary chips for null value', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      // The badges container should be empty (no Badge components)
      const badges = page.locator('.flex-wrap').first().locator('[class*="badge"]');
      await expect(badges).toHaveCount(0);
    });

    test('shows filler words switch off for false value', async ({ page }) => {
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await expect(fillerRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    });

    test('shows Voice tab defaults for null providers and default values', async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();

      // Voice speed at 50 (default)
      await expect(page.getByRole('slider')).toHaveAttribute('aria-valuenow', '50');

      // Patience level: Low (default)
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );

      // Speech recognition: Faster (default)
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('radio', { name: /Faster/i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
    });

    test('shows Call Configuration both off for false values', async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();

      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await expect(recordingRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');

      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await expect(transcriptionRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    });

    test("shows can't make calls status for outbound with no phone", async ({ page }) => {
      await expect(page.getByText(/can't make calls/)).toBeVisible();
    });
  });

  // ── 9. Edit Fields & Save Updated Payload ──────────────────────────────────
  test.describe('Edit Fields & Save Updated Payload', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetAgentAPI(page);
      await page.goto(EDIT_URL);
      await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 10_000 });
    });

    test('modifies all fields and sends correct updated payload', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      // ── General Tab: modify all fields ──
      await page.locator('input[name="name"]').fill('Updated Sales Agent');
      await page.locator('textarea[name="description"]').fill('Updated description');
      await page.locator('textarea[name="first_message"]').fill('Updated first message');
      await page.locator('textarea[name="end_call_message"]').fill('Updated goodbye');

      // Remove existing vocabulary chip "ToneHQ" and add a new one
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      await page.getByText('ToneHQ', { exact: true }).getByRole('button').click();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('NewWord');
      await vocabInput.press('Enter');

      // Remove existing filter word and add new ones
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      await page.getByText('badword', { exact: true }).getByRole('button').click();
      const filterInput = page.locator('input[name="filterWordsInput"]');
      await filterInput.fill('newbad');
      await filterInput.press('Enter');

      // Toggle filler words off (was true)
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await fillerRow.getByRole('switch').click();

      // ── Voice Tab: change options ──
      await page.getByRole('tab', { name: /voice/i }).click();
      // Change patience from Medium to High
      await page.getByRole('radio', { name: /^High ~/i }).click();
      // Change speech recognition from Accurate to Faster
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await page.getByRole('radio', { name: /Faster/i }).click();

      // ── Call Configuration Tab: toggle both off ──
      await page.getByRole('tab', { name: /call configuration/i }).click();
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await recordingRow.getByRole('switch').click();
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await transcriptionRow.getByRole('switch').click();

      // ── Prompt: update prompt text ──
      await page.getByRole('button', { name: 'Prompt' }).click();
      const editor = page.locator('.ProseMirror');
      // Select all existing text and replace
      await editor.click();
      await page.keyboard.press('Meta+a');
      await page.keyboard.type('Updated system prompt.');

      // ── Save ──
      await page.getByRole('button', { name: /save changes/i }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Agent saved successfully' }),
      ).toBeVisible({ timeout: 5_000 });

      expect(captured.length).toBe(1);
      const payload = captured[0];
      expect(payload).toMatchObject({
        id: 1,
        name: 'Updated Sales Agent',
        agent_type: 'inbound',
        description: 'Updated description',
        first_message: 'Updated first message',
        end_call_message: 'Updated goodbye',
        realistic_filler_words: false,
        language: 'en',
        patience_level: 'high',
        speech_recognition: 'fast',
        call_recording: false,
        call_transcription: false,
      });
      // Vocabulary: "ToneHQ" removed, "NewWord" added, "Pipecat" retained
      expect(JSON.parse(payload.custom_vocabulary as string)).toEqual(['Pipecat', 'NewWord']);
      expect(JSON.parse(payload.filter_words as string)).toEqual(['newbad']);
      expect(payload.system_prompt).toContain('Updated system prompt.');
    });

    test('sidebar reflects name change in real time', async ({ page }) => {
      await page.locator('input[name="name"]').fill('Renamed Agent');
      await expect(page.locator('aside').getByText('Renamed Agent')).toBeVisible();
    });

    test('can add new vocabulary word alongside existing ones', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('NewTerm');
      await vocabInput.press('Enter');

      // All three should be visible: ToneHQ, Pipecat (from API), NewTerm (added)
      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();
      await expect(page.getByText('Pipecat', { exact: true })).toBeVisible();
      await expect(page.getByText('NewTerm', { exact: true })).toBeVisible();
    });
  });

  // ── 10. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetAgentAPI(page);
      await page.goto(EDIT_URL);
      await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 10_000 });
    });

    test('sends id in payload and stays on edit page after save', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Agent saved successfully' }),
      ).toBeVisible({ timeout: 5_000 });
      expect(page.url()).toContain(EDIT_URL);

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        id: 1,
        name: 'Sales Assistant',
        agent_type: 'inbound',
      });
    });

    test('sends complete payload with all pre-populated values on save', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Agent saved successfully' }),
      ).toBeVisible({ timeout: 5_000 });

      expect(captured.length).toBe(1);
      const payload = captured[0];
      expect(payload).toMatchObject({
        id: 1,
        name: 'Sales Assistant',
        agent_type: 'inbound',
        description: 'Handles inbound sales calls',
        first_message: 'Hello, how can I help?',
        end_call_message: 'Goodbye!',
        realistic_filler_words: true,
        language: 'en',
        voice_speed: 70,
        patience_level: 'medium',
        speech_recognition: 'accurate',
        call_recording: true,
        call_transcription: true,
        llm_service_id: 1,
        tts_service_id: 1,
        stt_service_id: 1,
      });
      expect(JSON.parse(payload.custom_vocabulary as string)).toEqual(['ToneHQ', 'Pipecat']);
      expect(JSON.parse(payload.filter_words as string)).toEqual(['badword']);
      expect(payload.system_prompt).toContain('You are a helpful sales assistant.');
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

    test('shows error notification when save fails', async ({ page }) => {
      await page.route('**/agent/upsert_agent', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Server error' }),
        });
      });

      await page.getByRole('button', { name: /save changes/i }).click();

      await expect(page.locator('[data-sonner-toast]', { hasText: 'Failed to save agent' })).toBeVisible(
        { timeout: 5_000 },
      );
      expect(page.url()).toContain(EDIT_URL);
    });

    test('updates agent in DB and shows success notification (real API)', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await page.goto(EDIT_URL);
      await expect(page.locator('[class*="animate-spin"]')).not.toBeVisible({ timeout: 15_000 });

      const hasError = await page
        .locator('[data-sonner-toast]', { hasText: 'Agent not found' })
        .isVisible()
        .catch(() => false);
      if (hasError) return;

      await page.getByRole('button', { name: /save changes/i }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Agent saved successfully' }),
      ).toBeVisible({ timeout: 15_000 });
      expect(page.url()).toContain(EDIT_URL);
    });
  });

  // ── 11. Delete Agent ───────────────────────────────────────────────────────
  test.describe('Delete Agent', () => {
    test('opens delete confirmation modal from General tab', async ({ page }) => {
      await page.getByText('Delete Agent').scrollIntoViewIfNeeded();
      await page.getByRole('button', { name: 'Delete Agent' }).click();

      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog.getByText('Delete Agent')).toBeVisible();
      await expect(
        dialog.getByText(/Deleting an agent will erase personalized data/),
      ).toBeVisible();
    });

    test('closes delete modal when cancelled', async ({ page }) => {
      await page.getByText('Delete Agent').scrollIntoViewIfNeeded();
      await page.getByRole('button', { name: 'Delete Agent' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });

  // ── 12. Error States ────────────────────────────────────────────────────────
  test.describe('Error States', () => {
    test('shows error notification when agent is not found', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      await page.route('**/agent/get_all_agents**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      });

      await page.goto(EDIT_URL);
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Agent not found' }),
      ).toBeVisible({ timeout: 10_000 });
    });

    test('shows error notification when API errors', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      await page.route('**/agent/get_all_agents**', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Server error' }),
        });
      });

      await page.goto(EDIT_URL);
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Failed to load agent' }),
      ).toBeVisible({ timeout: 10_000 });
    });
  });

  // ── 13. Back Navigation ─────────────────────────────────────────────────────
  test.describe('Back Navigation', () => {
    test('navigates to /agents when clicking Back to Agents', async ({ page }) => {
      await page.getByRole('button', { name: /back to agents/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });
  });

  // ── 14. Tab Navigation ─────────────────────────────────────────────────────
  test.describe('Tab Navigation', () => {
    test('switches between all tabs preserving data', async ({ page }) => {
      // Verify General tab data
      await expect(page.locator('input[name="name"]')).toHaveValue('Sales Assistant');

      // Switch to Voice tab and verify data
      await page.getByRole('tab', { name: /voice/i }).click();
      await expect(page.getByRole('radio', { name: /^Medium /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );

      // Switch to Call Configuration tab and verify data
      await page.getByRole('tab', { name: /call configuration/i }).click();
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await expect(recordingRow.getByRole('switch')).toHaveAttribute('aria-checked', 'true');

      // Switch back to General tab and verify data is still there
      await page.getByRole('tab', { name: /general/i }).click();
      await expect(page.locator('input[name="name"]')).toHaveValue('Sales Assistant');
    });

    test('switches between Configure and Prompt preserving data', async ({ page }) => {
      // Check prompt
      await page.getByRole('button', { name: 'Prompt' }).click();
      await expect(page.locator('.ProseMirror')).toContainText(
        'You are a helpful sales assistant.',
      );

      // Switch back to Configure and verify data preserved
      await page.getByRole('button', { name: 'Configure' }).click();
      await expect(page.locator('input[name="name"]')).toHaveValue('Sales Assistant');
    });
  });

  // ── 15. Accessibility ──────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('tab panels have tabpanel role', async ({ page }) => {
      await expect(page.locator('[role="tabpanel"]').first()).toBeVisible();
    });

    test('tabs can be activated via keyboard', async ({ page }) => {
      const generalTab = page.getByRole('tab', { name: /general/i });
      await generalTab.focus();
      await expect(generalTab).toBeFocused();

      await page.keyboard.press('ArrowRight');
      const voiceTab = page.getByRole('tab', { name: /voice/i });
      await expect(voiceTab).toBeFocused();
    });
  });
});
