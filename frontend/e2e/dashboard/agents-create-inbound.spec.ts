import { test as base, BrowserContext, expect, Page } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

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

async function ensureOnPage(page: Page): Promise<void> {
  if (page.url().includes('/agents/create/inbound')) return;
  await page.goto('/agents/create/inbound');
}

async function mockUpsertAPI(
  page: Page,
  options?: { status?: number; delay?: number },
): Promise<Record<string, unknown>[]> {
  const captured: Record<string, unknown>[] = [];
  await page.route('**/agent/upsert_agent', async (route) => {
    if (options?.delay) {
      await new Promise((r) => setTimeout(r, options.delay));
    }
    const body = route.request().postDataJSON();
    captured.push(body);
    await route.fulfill({
      status: options?.status ?? 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 99, ...body }),
    });
  });
  return captured;
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Create Inbound Agent Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnPage(page);
  });

  // ── 1. Page Rendering ───────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows agent name in sidebar', async ({ page }) => {
      await expect(page.getByText('My Inbound Assistant')).toBeVisible();
    });

    test('shows Inbound badge in sidebar', async ({ page }) => {
      // AgentTypeBadge renders a shadcn Badge with text 'Inbound' in the sidebar
      await expect(page.locator('aside').getByText('Inbound', { exact: true })).toBeVisible();
    });

    test('shows Back to Agents button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /back to agents/i })).toBeVisible();
    });

    test('shows Test Agent button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /test agent/i })).toBeVisible();
    });

    test('shows sidebar menu items Configure and Prompt', async ({ page }) => {
      // Sidebar nav items are CustomButton components (not <p> tags in new UI)
      await expect(page.getByRole('button', { name: 'Configure' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Prompt' })).toBeVisible();
    });

    test('shows status bar about receiving calls', async ({ page }) => {
      // Status bar: plain div (not MUI Alert) showing phone assignment status
      await expect(page.getByText(/can't receive calls/)).toBeVisible();
    });

    test('shows Configure heading', async ({ page }) => {
      // AgentFormPage renders <h2> for currentMenu heading (not h5)
      await expect(page.getByRole('heading', { name: 'Configure', level: 2 })).toBeVisible();
    });

    test('shows Save Changes button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible();
    });
  });

  // ── 2. Form Tabs ───────────────────────────────────────────────────────────
  test.describe('Form Tabs', () => {
    test('shows all four form tabs including Assign Number', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /voice/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /call configuration/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /assign number/i })).toBeVisible();
    });
  });

  // ── 3. General Tab ──────────────────────────────────────────────────────────
  test.describe('General Tab', () => {
    test('shows default agent name value', async ({ page }) => {
      await expect(page.locator('input[name="name"]')).toHaveValue('My Inbound Assistant');
    });

    test('shows all General tab form row labels and descriptions', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Agent Name' })).toBeVisible();
      await expect(page.getByText('What name will your agent go by.')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Agent Description' })).toBeVisible();
      await expect(
        page.getByText("Provide a brief summary explaining your agent's purpose."),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'AI Model' })).toBeVisible();
      await expect(
        page.getByText("Opt for speed or depth to suit your agent's role."),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'First Message' })).toBeVisible();
      await expect(
        page.getByText('Initial message sent when the conversation starts.'),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'End Call Message' })).toBeVisible();
      await expect(page.getByText('Message sent at the end of a conversation.')).toBeVisible();

      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      await expect(page.getByRole('heading', { name: 'Custom Vocabulary' })).toBeVisible();
      await expect(page.getByText('Add business terms to improve accuracy.')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Filter Words' })).toBeVisible();
      await expect(page.getByText('Words the agent should not speak.')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Use Realistic Filler Words' })).toBeVisible();
      await expect(
        page.getByText("Include natural filler words like 'uh' and 'um'."),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Delete Agent' })).toBeVisible();
    });

    test('shows default empty values for all text fields', async ({ page }) => {
      // Description, First Message, End Call Message textareas default to empty
      const descTextarea = page.locator('textarea[name="description"]');
      await expect(descTextarea).toHaveValue('');
      const firstMsgTextarea = page.locator('textarea[name="first_message"]');
      await expect(firstMsgTextarea).toHaveValue('');
      const endCallTextarea = page.locator('textarea[name="end_call_message"]');
      await expect(endCallTextarea).toHaveValue('');
    });

    test('shows filler words switch off by default', async ({ page }) => {
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      const switchEl = fillerRow.getByRole('switch');
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    });

    test('shows Delete Agent button', async ({ page }) => {
      await page.getByRole('button', { name: 'Delete Agent' }).scrollIntoViewIfNeeded();
      await expect(page.getByRole('button', { name: 'Delete Agent' })).toBeVisible();
    });

    test('allows editing the agent name', async ({ page }) => {
      const nameInput = page.locator('input[name="name"]');
      await expect(nameInput).toHaveValue('My Inbound Assistant');
      await nameInput.fill('Custom Agent Name');
      await expect(nameInput).toHaveValue('Custom Agent Name');
      // Sidebar should reflect the updated name
      await expect(page.locator('aside').getByText('Custom Agent Name')).toBeVisible();
    });

    test('allows editing the description field', async ({ page }) => {
      const descTextarea = page.locator('textarea[name="description"]');
      await descTextarea.fill('A helpful sales agent');
      await expect(descTextarea).toHaveValue('A helpful sales agent');
    });

    test('allows editing the first message field', async ({ page }) => {
      const firstMsgTextarea = page.locator('textarea[name="first_message"]');
      await firstMsgTextarea.fill('Hello, how can I help you today?');
      await expect(firstMsgTextarea).toHaveValue('Hello, how can I help you today?');
    });

    test('allows editing the end call message field', async ({ page }) => {
      const endCallTextarea = page.locator('textarea[name="end_call_message"]');
      await endCallTextarea.fill('Thank you for calling. Goodbye!');
      await expect(endCallTextarea).toHaveValue('Thank you for calling. Goodbye!');
    });

    test('allows adding custom vocabulary via Enter key', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');

      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();
    });

    test('allows adding multiple custom vocabulary words', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');

      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');
      await vocabInput.fill('Pipecat');
      await vocabInput.press('Enter');
      await vocabInput.fill('WebRTC');
      await vocabInput.press('Enter');

      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();
      await expect(page.getByText('Pipecat', { exact: true })).toBeVisible();
      await expect(page.getByText('WebRTC', { exact: true })).toBeVisible();
    });

    test('prevents adding duplicate vocabulary words', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');

      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');
      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');

      // Only one badge should exist
      const badges = page.locator('.flex-wrap').first().getByText('ToneHQ', { exact: true });
      await expect(badges).toHaveCount(1);
    });

    test('allows deleting custom vocabulary chips', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');
      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();

      // Delete chip — the Badge element wraps the text + X button
      await page.getByText('ToneHQ', { exact: true }).getByRole('button').click();
      await expect(page.getByText('ToneHQ', { exact: true })).not.toBeVisible();
    });

    test('allows adding custom vocabulary via Enter button', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('PipelineWord');
      // Click the paired Enter button (first "Enter" button in the form)
      await page.getByRole('button', { name: 'Enter' }).nth(0).click();
      await expect(page.getByText('PipelineWord', { exact: true })).toBeVisible();
    });

    test('allows adding and deleting filter word chips', async ({ page }) => {
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterInput = page.locator('input[name="filterWordsInput"]');
      await filterInput.fill('badword');
      await filterInput.press('Enter');

      await expect(page.getByText('badword', { exact: true })).toBeVisible();

      // Delete chip
      await page.getByText('badword', { exact: true }).getByRole('button').click();
      await expect(page.getByText('badword', { exact: true })).not.toBeVisible();
    });

    test('allows adding multiple filter words', async ({ page }) => {
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterInput = page.locator('input[name="filterWordsInput"]');

      await filterInput.fill('word1');
      await filterInput.press('Enter');
      await filterInput.fill('word2');
      await filterInput.press('Enter');

      await expect(page.getByText('word1', { exact: true })).toBeVisible();
      await expect(page.getByText('word2', { exact: true })).toBeVisible();
    });

    test('allows toggling filler words switch', async ({ page }) => {
      // Use Realistic Filler Words uses shadcn Switch (role="switch")
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      const switchEl = fillerRow.getByRole('switch');
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
    });
  });

  // ── 4. Voice Tab ────────────────────────────────────────────────────────────
  test.describe('Voice Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();
    });

    test('shows all Voice tab form row labels and descriptions', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Language' })).toBeVisible();
      await expect(page.getByText('The language your agent understands.')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Voice Provider' })).toBeVisible();
      await expect(
        page.getByText("Select the service used to generate your agent's voice."),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'STT Provider' })).toBeVisible();
      await expect(
        page.getByText('Select the service used to transcribe calls to text (Speech-to-Text).'),
      ).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Voice Speed' })).toBeVisible();
      await expect(page.getByText('Adjust how fast or slow your agent will talk.')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Patience Level' })).toBeVisible();
      await expect(page.getByText(/Adjust the response speed/)).toBeVisible();

      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('heading', { name: 'Speech Recognition' })).toBeVisible();
      await expect(
        page.getByText('Adjusts how quickly incoming speech is transcribed.'),
      ).toBeVisible();
    });

    test('defaults language to English', async ({ page }) => {
      await expect(page.getByText(/English/).first()).toBeVisible();
    });

    test('shows voice speed slider with labels', async ({ page }) => {
      await expect(page.getByRole('slider')).toBeVisible();
      await expect(page.getByText('Slow', { exact: true })).toBeVisible();
      await expect(page.getByText('Normal', { exact: true })).toBeVisible();
      await expect(page.getByText('Fast', { exact: true })).toBeVisible();
    });

    test('defaults voice speed slider to 50', async ({ page }) => {
      const slider = page.getByRole('slider');
      // shadcn Slider uses aria-valuenow
      await expect(slider).toHaveAttribute('aria-valuenow', '50');
    });

    test('defaults patience level to Low', async ({ page }) => {
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /^Medium /i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
      await expect(page.getByRole('radio', { name: /^High ~/i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });

    test('shows patience level timing labels', async ({ page }) => {
      await expect(page.getByText('~1 sec')).toBeVisible();
      await expect(page.getByText('~3 sec')).toBeVisible();
      await expect(page.getByText('~5 sec')).toBeVisible();
    });

    test('allows selecting a patience level', async ({ page }) => {
      await page.getByRole('radio', { name: /^Medium /i }).click();
      await expect(page.getByRole('radio', { name: /^Medium /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      // Previous selection should be deselected
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });

    test('defaults speech recognition to Faster', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('radio', { name: /Faster/i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /High Accuracy/i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });

    test('allows selecting High Accuracy speech recognition', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await page.getByRole('radio', { name: /High Accuracy/i }).click();
      await expect(page.getByRole('radio', { name: /High Accuracy/i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /Faster/i })).toHaveAttribute(
        'aria-checked',
        'false',
      );
    });

    test('shows speech recognition option descriptions', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByText('Lower quality, suitable for most use cases')).toBeVisible();
      await expect(page.getByText('Slower, for high accuracy use cases')).toBeVisible();
    });
  });

  // ── 5. Call Configuration Tab ───────────────────────────────────────────────
  test.describe('Call Configuration Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();
    });

    test('shows call recording label and description', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Call Recording' })).toBeVisible();
      await expect(page.getByText('Enable recording of all calls for review.')).toBeVisible();
    });

    test('shows call transcription label and description', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Call Transcription' })).toBeVisible();
      await expect(page.getByText('Automatically transcribe all calls to text.')).toBeVisible();
    });

    test('defaults call recording to off', async ({ page }) => {
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      const switchEl = recordingRow.getByRole('switch');
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    });

    test('defaults call transcription to off', async ({ page }) => {
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      const switchEl = transcriptionRow.getByRole('switch');
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    });

    test('allows enabling and disabling call recording', async ({ page }) => {
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      const switchEl = recordingRow.getByRole('switch');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    });

    test('allows enabling and disabling call transcription', async ({ page }) => {
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      const switchEl = transcriptionRow.getByRole('switch');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'false');
    });
  });

  // ── 5b. Assign Number Tab ─────────────────────────────────────────────────
  test.describe('Assign Number Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /assign number/i }).click();
    });

    test('shows save-first message in create mode', async ({ page }) => {
      await expect(page.getByText('Save the agent first to assign phone numbers.')).toBeVisible();
    });

    test('does not show Assign New Number button in create mode', async ({ page }) => {
      await expect(page.getByRole('button', { name: /assign new number/i })).not.toBeVisible();
    });
  });

  // ── 6. Prompt Editor ───────────────────────────────────────────────────────
  test.describe('Prompt Editor', () => {
    test.beforeEach(async ({ page }) => {
      // Sidebar nav items are CustomButton (not <p> in new UI)
      await page.getByRole('button', { name: 'Prompt' }).click();
    });

    test('shows TipTap editor when Prompt menu is selected', async ({ page }) => {
      await expect(page.locator('.ProseMirror')).toBeVisible();
      await expect(page.getByRole('button', { name: /clear all/i })).toBeVisible();
    });

    test('allows typing in the editor', async ({ page }) => {
      const editor = page.locator('.ProseMirror');
      await editor.click();
      await page.keyboard.type('You are a helpful assistant.');
      await expect(editor).toContainText('You are a helpful assistant.');
    });
  });

  // ── 7. Tab Navigation ──────────────────────────────────────────────────────
  test.describe('Tab Navigation', () => {
    test('switches between General, Voice, and Call Configuration tabs', async ({ page }) => {
      // Ensure we're on the Configure view with the General tab
      if (
        !(await page
          .getByRole('tab', { name: /general/i })
          .isVisible()
          .catch(() => false))
      ) {
        await page.getByRole('button', { name: 'Configure' }).click();
      }
      await page.getByRole('tab', { name: /general/i }).click();
      await expect(page.getByText('Agent Name', { exact: true })).toBeVisible();

      // Switch to Voice tab
      await page.getByRole('tab', { name: /voice/i }).click();
      await expect(page.getByText('Voice Provider')).toBeVisible();

      // Switch to Call Configuration tab
      await page.getByRole('tab', { name: /call configuration/i }).click();
      await expect(page.getByText('Call Recording')).toBeVisible();

      // Switch back to General
      await page.getByRole('tab', { name: /general/i }).click();
      await expect(page.getByText('Agent Name', { exact: true })).toBeVisible();
    });

    test('switches between Configure and Prompt menus via sidebar', async ({ page }) => {
      // Click Prompt in sidebar (CustomButton, not <p> in new UI)
      await page.getByRole('button', { name: 'Prompt' }).click();
      await expect(page.getByRole('heading', { name: 'Prompt', level: 2 })).toBeVisible();
      await expect(page.locator('.ProseMirror')).toBeVisible();

      // Click Configure in sidebar (CustomButton)
      await page.getByRole('button', { name: 'Configure' }).click();
      await expect(page.getByRole('heading', { name: 'Configure', level: 2 })).toBeVisible();
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
    });
  });

  // ── 8. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Ensure fresh form state with a hard nav
      await page.goto('/agents/create/inbound');
    });

    test('sends correct default payload and redirects to /agents on save', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        name: 'My Inbound Assistant',
        agent_type: 'inbound',
        description: null,
        first_message: null,
        end_call_message: null,
        system_prompt: null,
        custom_vocabulary: null,
        filter_words: null,
        realistic_filler_words: false,
        language: 'en',
        voice_speed: 50,
        patience_level: 'low',
        speech_recognition: 'fast',
        call_recording: false,
        call_transcription: false,
        llm_service_id: null,
        tts_service_id: null,
        stt_service_id: null,
      });
    });

    test('sends full payload with all fields filled across all tabs', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      // ── General Tab ──
      await page.locator('input[name="name"]').fill('E2E Full Agent');
      await page.locator('textarea[name="description"]').fill('Full form test agent');
      await page.locator('textarea[name="first_message"]').fill('Hello from E2E!');
      await page.locator('textarea[name="end_call_message"]').fill('Goodbye from E2E!');

      // Add custom vocabulary
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');
      await vocabInput.fill('Pipecat');
      await vocabInput.press('Enter');

      // Add filter words
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterInput = page.locator('input[name="filterWordsInput"]');
      await filterInput.fill('badword');
      await filterInput.press('Enter');

      // Enable filler words
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await fillerRow.getByRole('switch').click();

      // ── Voice Tab ──
      await page.getByRole('tab', { name: /voice/i }).click();

      // Change patience level to High
      await page.getByRole('radio', { name: /^High ~/i }).click();

      // Change speech recognition to High Accuracy
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await page.getByRole('radio', { name: /High Accuracy/i }).click();

      // ── Call Configuration Tab ──
      await page.getByRole('tab', { name: /call configuration/i }).click();
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await recordingRow.getByRole('switch').click();
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await transcriptionRow.getByRole('switch').click();

      // ── Prompt (via sidebar) ──
      await page.getByRole('button', { name: 'Prompt' }).click();
      const editor = page.locator('.ProseMirror');
      await editor.click();
      await page.keyboard.type('You are a helpful sales agent.');

      // ── Save ──
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      const payload = captured[0];
      expect(payload).toMatchObject({
        name: 'E2E Full Agent',
        agent_type: 'inbound',
        description: 'Full form test agent',
        first_message: 'Hello from E2E!',
        end_call_message: 'Goodbye from E2E!',
        realistic_filler_words: true,
        language: 'en',
        patience_level: 'high',
        speech_recognition: 'accurate',
        call_recording: true,
        call_transcription: true,
      });
      // Custom vocabulary and filter words are JSON-stringified arrays
      expect(JSON.parse(payload.custom_vocabulary as string)).toEqual(['ToneHQ', 'Pipecat']);
      expect(JSON.parse(payload.filter_words as string)).toEqual(['badword']);
      // System prompt contains the typed text (TipTap wraps in HTML)
      expect(payload.system_prompt).toContain('You are a helpful sales agent.');
    });

    test('shows Saving... and disables button during save', async ({ page }) => {
      await mockUpsertAPI(page, { delay: 2000 });

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

      await expect(page.locator('[data-sonner-toast]', { hasText: 'Server error' })).toBeVisible({
        timeout: 5_000,
      });
      expect(page.url()).toContain('/agents/create/inbound');
    });

    test('saves agent to DB and shows in list (real API)', async ({ page }) => {
      // No mocks: triggers actual save to backend/DB. Requires running backend.
      const agentName = `E2E Inbound ${Date.now()}`;
      await page.locator('input[name="name"]').fill(agentName);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 15_000 });

      // Created item should show in the list (from real get_all_agents)
      await expect(page.getByText(agentName).first()).toBeVisible({ timeout: 10_000 });
      await expect(page.locator('tbody').getByText('Inbound').first()).toBeVisible();
    });
  });

  // ── 9. Delete Agent Confirmation ──────────────────────────────────────────
  test.describe('Delete Agent Confirmation', () => {
    test('opens confirmation modal when clicking Delete Agent', async ({ page }) => {
      await page.getByRole('button', { name: 'Delete Agent' }).scrollIntoViewIfNeeded();
      await page.getByRole('button', { name: 'Delete Agent' }).click();

      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      await expect(dialog.getByText('Delete Agent')).toBeVisible();
      await expect(
        dialog.getByText(/Deleting an agent will erase personalized data/),
      ).toBeVisible();

      // Close dialog to prevent state leakage to next test
      await page.keyboard.press('Escape');
      await expect(dialog).not.toBeVisible();
    });

    test('closes delete modal when cancelled', async ({ page }) => {
      await page.getByRole('button', { name: 'Delete Agent' }).scrollIntoViewIfNeeded();
      await page.getByRole('button', { name: 'Delete Agent' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();
    });
  });

  // ── 10. Back Navigation ─────────────────────────────────────────────────
  test.describe('Back Navigation', () => {
    test('navigates to /agents when clicking Back to Agents', async ({ page }) => {
      await page.getByRole('button', { name: /back to agents/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });
  });

  // ── 11. Auth Redirect ──────────────────────────────────────────────────────
  test.describe('Auth Redirect', () => {
    let savedCookies: Awaited<ReturnType<BrowserContext['cookies']>>;

    test.beforeEach(async ({ page }) => {
      savedCookies = await page.context().cookies();
    });

    test.afterEach(async ({ page }) => {
      await page.context().addCookies(savedCookies);
    });

    test('redirects to login when no auth cookie is set', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/agents/create/inbound');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });
  });

  // ── 12. Accessibility ──────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('tab panels have tabpanel role', async ({ page }) => {
      const panels = page.locator('[role="tabpanel"]');
      await expect(panels.first()).toBeVisible();
    });

    test('tabs can be activated via keyboard', async ({ page }) => {
      const generalTab = page.getByRole('tab', { name: /general/i });
      await generalTab.focus();
      await expect(generalTab).toBeFocused();

      // Arrow right to move to Voice tab
      await page.keyboard.press('ArrowRight');
      const voiceTab = page.getByRole('tab', { name: /voice/i });
      await expect(voiceTab).toBeFocused();
    });
  });
});
