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
  if (page.url().includes('/agents/create/outbound')) return;
  await page.goto('/agents/create/outbound');
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
test.describe('Create Outbound Agent Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await ensureOnPage(page);
  });

  // ── 1. Page Rendering ───────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows agent name in sidebar', async ({ page }) => {
      await expect(page.getByText('My Outbound Assistant')).toBeVisible();
    });

    test('shows Outbound badge in sidebar', async ({ page }) => {
      await expect(page.locator('aside').getByText('Outbound', { exact: true })).toBeVisible();
    });

    test('shows status bar about making calls', async ({ page }) => {
      await expect(page.getByText(/can't make calls/)).toBeVisible();
    });

    test('shows sidebar menu items Configure and Prompt', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Configure' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Prompt' })).toBeVisible();
    });

    test('shows Configure heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Configure', level: 2 })).toBeVisible();
    });

    test('shows Back to Agents button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /back to agents/i })).toBeVisible();
    });

    test('shows Test Agent button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /test agent/i })).toBeVisible();
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

  // ── 3. General Tab Defaults ─────────────────────────────────────────────────
  test.describe('General Tab Defaults', () => {
    test('shows default outbound agent name', async ({ page }) => {
      await expect(page.locator('input[name="name"]')).toHaveValue('My Outbound Assistant');
    });

    test('shows all General tab form row labels', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Agent Name' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Agent Description' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'AI Model' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'First Message' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'End Call Message' })).toBeVisible();

      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      await expect(page.getByRole('heading', { name: 'Custom Vocabulary' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Filter Words' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Use Realistic Filler Words' })).toBeVisible();
    });

    test('shows default empty values for text fields', async ({ page }) => {
      await expect(page.locator('textarea[name="description"]')).toHaveValue('');
      await expect(page.locator('textarea[name="first_message"]')).toHaveValue('');
      await expect(page.locator('textarea[name="end_call_message"]')).toHaveValue('');
    });

    test('shows filler words switch off by default', async ({ page }) => {
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await expect(fillerRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    });

    test('allows editing the agent name and reflects in sidebar', async ({ page }) => {
      const nameInput = page.locator('input[name="name"]');
      await nameInput.fill('Custom Outbound Agent');
      await expect(nameInput).toHaveValue('Custom Outbound Agent');
      await expect(page.locator('aside').getByText('Custom Outbound Agent')).toBeVisible();
    });

    test('allows editing the description field', async ({ page }) => {
      const descTextarea = page.locator('textarea[name="description"]');
      await descTextarea.fill('Outbound sales agent');
      await expect(descTextarea).toHaveValue('Outbound sales agent');
    });

    test('allows editing the first message field', async ({ page }) => {
      const firstMsgTextarea = page.locator('textarea[name="first_message"]');
      await firstMsgTextarea.fill('Hi, I am calling about your account.');
      await expect(firstMsgTextarea).toHaveValue('Hi, I am calling about your account.');
    });

    test('allows editing the end call message field', async ({ page }) => {
      const endCallTextarea = page.locator('textarea[name="end_call_message"]');
      await endCallTextarea.fill('Thank you for your time. Goodbye!');
      await expect(endCallTextarea).toHaveValue('Thank you for your time. Goodbye!');
    });

    test('allows adding and deleting custom vocabulary', async ({ page }) => {
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('ToneHQ');
      await vocabInput.press('Enter');
      await expect(page.getByText('ToneHQ', { exact: true })).toBeVisible();

      await page.getByText('ToneHQ', { exact: true }).getByRole('button').click();
      await expect(page.getByText('ToneHQ', { exact: true })).not.toBeVisible();
    });

    test('allows adding and deleting filter words', async ({ page }) => {
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterInput = page.locator('input[name="filterWordsInput"]');
      await filterInput.fill('offensive');
      await filterInput.press('Enter');
      await expect(page.getByText('offensive', { exact: true })).toBeVisible();

      await page.getByText('offensive', { exact: true }).getByRole('button').click();
      await expect(page.getByText('offensive', { exact: true })).not.toBeVisible();
    });

    test('allows toggling filler words switch', async ({ page }) => {
      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      const switchEl = fillerRow.getByRole('switch');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
    });
  });

  // ── 4. Voice Tab ────────────────────────────────────────────────────────────
  test.describe('Voice Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();
    });

    test('shows all Voice tab form row labels', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Language' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Voice Provider' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'STT Provider' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Voice Speed' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Patience Level' })).toBeVisible();

      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('heading', { name: 'Speech Recognition' })).toBeVisible();
    });

    test('defaults language to English', async ({ page }) => {
      await expect(page.getByText(/English/).first()).toBeVisible();
    });

    test('defaults voice speed slider to 50', async ({ page }) => {
      await expect(page.getByRole('slider')).toHaveAttribute('aria-valuenow', '50');
    });

    test('defaults patience level to Low', async ({ page }) => {
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
    });

    test('defaults speech recognition to Faster', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByRole('radio', { name: /Faster/i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
    });

    test('allows selecting Medium patience level', async ({ page }) => {
      await page.getByRole('radio', { name: /^Medium /i }).click();
      await expect(page.getByRole('radio', { name: /^Medium /i })).toHaveAttribute(
        'aria-checked',
        'true',
      );
      await expect(page.getByRole('radio', { name: /^Low /i })).toHaveAttribute(
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
    });
  });

  // ── 5. Call Configuration Tab ───────────────────────────────────────────────
  test.describe('Call Configuration Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();
    });

    test('defaults both toggles to off', async ({ page }) => {
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await expect(recordingRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await expect(transcriptionRow.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    });

    test('allows enabling call recording', async ({ page }) => {
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      const switchEl = recordingRow.getByRole('switch');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
    });

    test('allows enabling call transcription', async ({ page }) => {
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      const switchEl = transcriptionRow.getByRole('switch');
      await switchEl.click();
      await expect(switchEl).toHaveAttribute('aria-checked', 'true');
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
      await page.getByRole('button', { name: 'Prompt' }).click();
    });

    test('shows TipTap editor when Prompt menu is selected', async ({ page }) => {
      await expect(page.locator('.ProseMirror')).toBeVisible();
      await expect(page.getByRole('button', { name: /clear all/i })).toBeVisible();
    });

    test('allows typing in the editor', async ({ page }) => {
      const editor = page.locator('.ProseMirror');
      await editor.click();
      await page.keyboard.type('You are a helpful outbound agent.');
      await expect(editor).toContainText('You are a helpful outbound agent.');
    });
  });

  // ── 7. Tab Navigation ──────────────────────────────────────────────────────
  test.describe('Tab Navigation', () => {
    test('switches between all tabs', async ({ page }) => {
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

      await page.getByRole('tab', { name: /voice/i }).click();
      await expect(page.getByText('Voice Provider')).toBeVisible();

      await page.getByRole('tab', { name: /call configuration/i }).click();
      await expect(page.getByText('Call Recording')).toBeVisible();

      await page.getByRole('tab', { name: /assign number/i }).click();
      await expect(page.getByRole('heading', { name: 'Assign Number' })).toBeVisible();
    });

    test('switches between Configure and Prompt menus via sidebar', async ({ page }) => {
      await page.getByRole('button', { name: 'Prompt' }).click();
      await expect(page.getByRole('heading', { name: 'Prompt', level: 2 })).toBeVisible();
      await expect(page.locator('.ProseMirror')).toBeVisible();

      await page.getByRole('button', { name: 'Configure' }).click();
      await expect(page.getByRole('heading', { name: 'Configure', level: 2 })).toBeVisible();
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
    });
  });

  // ── 8. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/agents/create/outbound');
    });

    test('sends correct default payload with outbound agent_type', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        name: 'My Outbound Assistant',
        agent_type: 'outbound',
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
      await page.locator('input[name="name"]').fill('E2E Outbound Agent');
      await page.locator('textarea[name="description"]').fill('Outbound test agent');
      await page.locator('textarea[name="first_message"]').fill('Hi, this is a test call.');
      await page.locator('textarea[name="end_call_message"]').fill('Thanks for your time!');

      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      const vocabInput = page.locator('input[name="vocabularyInput"]');
      await vocabInput.fill('SalesForce');
      await vocabInput.press('Enter');

      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterInput = page.locator('input[name="filterWordsInput"]');
      await filterInput.fill('spam');
      await filterInput.press('Enter');

      const fillerRow = page.getByText('Use Realistic Filler Words').locator('..').locator('..');
      await fillerRow.getByRole('switch').click();

      // ── Voice Tab ──
      await page.getByRole('tab', { name: /voice/i }).click();
      await page.getByRole('radio', { name: /^Medium /i }).click();
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await page.getByRole('radio', { name: /High Accuracy/i }).click();

      // ── Call Configuration Tab ──
      await page.getByRole('tab', { name: /call configuration/i }).click();
      const recordingRow = page.getByText('Call Recording').locator('..').locator('..');
      await recordingRow.getByRole('switch').click();
      const transcriptionRow = page.getByText('Call Transcription').locator('..').locator('..');
      await transcriptionRow.getByRole('switch').click();

      // ── Prompt ──
      await page.getByRole('button', { name: 'Prompt' }).click();
      const editor = page.locator('.ProseMirror');
      await editor.click();
      await page.keyboard.type('You are an outbound sales agent.');

      // ── Save ──
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      const payload = captured[0];
      expect(payload).toMatchObject({
        name: 'E2E Outbound Agent',
        agent_type: 'outbound',
        description: 'Outbound test agent',
        first_message: 'Hi, this is a test call.',
        end_call_message: 'Thanks for your time!',
        realistic_filler_words: true,
        language: 'en',
        patience_level: 'medium',
        speech_recognition: 'accurate',
        call_recording: true,
        call_transcription: true,
      });
      expect(JSON.parse(payload.custom_vocabulary as string)).toEqual(['SalesForce']);
      expect(JSON.parse(payload.filter_words as string)).toEqual(['spam']);
      expect(payload.system_prompt).toContain('You are an outbound sales agent.');
    });

    test('redirects to /agents after save', async ({ page }) => {
      await mockUpsertAPI(page);
      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
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
      expect(page.url()).toContain('/agents/create/outbound');
    });

    test('saves outbound agent to DB and shows in list (real API)', async ({ page }) => {
      const agentName = `E2E Outbound ${Date.now()}`;
      await page.locator('input[name="name"]').fill(agentName);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 15_000 });

      await expect(page.getByText(agentName).first()).toBeVisible({ timeout: 10_000 });
      await expect(page.locator('tbody').getByText('Outbound').first()).toBeVisible();
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

  // ── 10. Back Navigation ─────────────────────────────────────────────────────
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
      await page.goto('/agents/create/outbound');
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

      await page.keyboard.press('ArrowRight');
      const voiceTab = page.getByRole('tab', { name: /voice/i });
      await expect(voiceTab).toBeFocused();
    });
  });
});
