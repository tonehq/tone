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

    test('shows Inbound chip in sidebar', async ({ page }) => {
      const chip = page.locator('.MuiChip-root').filter({ hasText: 'Inbound' });
      await expect(chip).toBeVisible();
    });

    test('shows Back to Agents button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /back to agents/i })).toBeVisible();
    });

    test('shows Test Agent button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /test agent/i })).toBeVisible();
    });

    test('shows sidebar menu items', async ({ page }) => {
      // Sidebar menu items are body2 Typography (renders as <p>)
      await expect(page.locator('p').filter({ hasText: /^Configure$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Prompt$/ })).toBeVisible();
      await expect(page.locator('p').filter({ hasText: /^Deployments$/ })).toBeVisible();
    });

    test('shows info alert about receiving calls', async ({ page }) => {
      await expect(page.locator('.MuiAlert-root')).toContainText("can't receive calls");
    });

    test('shows Configure heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Configure', level: 5 })).toBeVisible();
    });

    test('shows Save Changes button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible();
    });
  });

  // ── 2. Form Tabs ───────────────────────────────────────────────────────────
  test.describe('Form Tabs', () => {
    test('shows three form tabs', async ({ page }) => {
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /voice/i })).toBeVisible();
      await expect(page.getByRole('tab', { name: /call configuration/i })).toBeVisible();
    });
  });

  // ── 3. General Tab ──────────────────────────────────────────────────────────
  test.describe('General Tab', () => {
    test('shows default agent name value', async ({ page }) => {
      const nameInput = page.locator('input[value="My Inbound Assistant"]');
      await expect(nameInput).toBeVisible();
    });

    test('shows default AI model value', async ({ page }) => {
      // The Select renderValue shows "GPT-4.1"
      await expect(page.getByText('GPT-4.1')).toBeVisible();
    });

    test('allows editing the agent name', async ({ page }) => {
      // The Agent Name row: label on the left, TextField on the right.
      // Locate the input inside the Agent Name form row by finding the
      // TextField closest to the "Agent Name" label.
      const agentNameRow = page
        .getByText('What name will your agent go by.')
        .locator('..')
        .locator('..');
      const nameInput = agentNameRow.locator('input');
      await expect(nameInput).toHaveValue('My Inbound Assistant');
      await nameInput.fill('Custom Agent Name');
      await expect(nameInput).toHaveValue('Custom Agent Name');
      // Sidebar should reflect the updated name
      await expect(page.getByText('Custom Agent Name')).toBeVisible();
    });

    test('allows editing the description field', async ({ page }) => {
      const descField = page
        .locator('.MuiTextField-root')
        .filter({ has: page.locator('textarea') })
        .first();
      const textarea = descField.locator('textarea').first();
      await textarea.fill('A helpful sales agent');
      await expect(textarea).toHaveValue('A helpful sales agent');
    });

    test('allows adding and deleting custom vocabulary chips', async ({ page }) => {
      // The first text input after agent name might not be right — find the one near "Custom Vocabulary"
      await page.getByText('Custom Vocabulary').scrollIntoViewIfNeeded();
      // The text inputs in the chip sections come after the main form fields
      // Custom Vocabulary has a text input + Enter button pair
      const vocabContainer = page.getByText('Add business terms').locator('..').locator('..');
      const input = vocabContainer.locator('input');
      const enterBtn = vocabContainer.getByRole('button', { name: 'Enter' });

      await input.fill('ToneHQ');
      await enterBtn.click();

      const chip = page.locator('.MuiChip-root').filter({ hasText: 'ToneHQ' });
      await expect(chip).toBeVisible();

      // Delete the chip
      await chip.locator('[data-testid="CancelIcon"]').click();
      await expect(chip).not.toBeVisible();
    });

    test('allows adding and deleting filter words chips', async ({ page }) => {
      await page.getByText('Filter Words').scrollIntoViewIfNeeded();
      const filterContainer = page
        .getByText('Words the agent should not speak')
        .locator('..')
        .locator('..');
      const input = filterContainer.locator('input');
      const enterBtn = filterContainer.getByRole('button', { name: 'Enter' });

      await input.fill('badword');
      await enterBtn.click();

      const chip = page.locator('.MuiChip-root').filter({ hasText: 'badword' });
      await expect(chip).toBeVisible();

      // Delete
      await chip.locator('[data-testid="CancelIcon"]').click();
      await expect(chip).not.toBeVisible();
    });

    test('allows toggling filler words switch', async ({ page }) => {
      const fillerSection = page
        .getByText('Use Realistic Filler Words')
        .locator('..')
        .locator('..');
      const switchEl = fillerSection.locator('.MuiSwitch-root input');
      await expect(switchEl).not.toBeChecked();
      await switchEl.click({ force: true });
      await expect(switchEl).toBeChecked();
    });
  });

  // ── 4. Voice Tab ────────────────────────────────────────────────────────────
  test.describe('Voice Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /voice/i }).click();
    });

    test('shows default language, voice provider, and STT provider', async ({ page }) => {
      // Language select shows English flag + label
      await expect(page.getByText('English')).toBeVisible();
      // Voice provider
      await expect(page.getByText('ElevenLabs')).toBeVisible();
      // STT provider
      await expect(page.getByText('Deepgram')).toBeVisible();
    });

    test('shows voice speed slider', async ({ page }) => {
      await expect(page.getByText('Voice Speed')).toBeVisible();
      await expect(page.locator('.MuiSlider-root')).toBeVisible();
    });

    test('shows patience level options', async ({ page }) => {
      await expect(page.getByText('Patience Level')).toBeVisible();
      // Low is selected by default (has highlighted border)
      await expect(page.getByText('Low').first()).toBeVisible();
      await expect(page.getByText('Medium').first()).toBeVisible();
      await expect(page.getByText('High').first()).toBeVisible();
    });

    test('allows selecting a patience level', async ({ page }) => {
      const mediumLabel = page.getByText('Medium').first();
      await mediumLabel.click();
      // After clicking Medium, the ~3 sec card should have the active border color
      const mediumCard = page
        .locator('label')
        .filter({ hasText: 'Medium' })
        .filter({ hasText: '~3 sec' });
      await expect(mediumCard).toBeVisible();
    });

    test('shows speech recognition options', async ({ page }) => {
      await page.getByText('Speech Recognition').first().scrollIntoViewIfNeeded();
      await expect(page.getByText('Speech Recognition').first()).toBeVisible();
      await expect(page.getByText('Faster')).toBeVisible();
      await expect(page.getByText('High Accuracy', { exact: true })).toBeVisible();
    });
  });

  // ── 5. Call Configuration Tab ───────────────────────────────────────────────
  test.describe('Call Configuration Tab', () => {
    test.beforeEach(async ({ page }) => {
      await page.getByRole('tab', { name: /call configuration/i }).click();
    });

    test('shows call recording toggle', async ({ page }) => {
      await expect(page.getByText('Call Recording')).toBeVisible();
      const section = page.getByText('Call Recording').locator('..').locator('..');
      const switchEl = section.locator('.MuiSwitch-root input');
      await expect(switchEl).not.toBeChecked();
      await switchEl.click({ force: true });
      await expect(switchEl).toBeChecked();
    });

    test('shows call transcription toggle', async ({ page }) => {
      await expect(page.getByText('Call Transcription')).toBeVisible();
      const section = page.getByText('Call Transcription').locator('..').locator('..');
      const switchEl = section.locator('.MuiSwitch-root input');
      await expect(switchEl).not.toBeChecked();
      await switchEl.click({ force: true });
      await expect(switchEl).toBeChecked();
    });
  });

  // ── 6. Prompt Editor ───────────────────────────────────────────────────────
  test.describe('Prompt Editor', () => {
    test.beforeEach(async ({ page }) => {
      // Use the sidebar Prompt menu item (body2 text), not the h5 heading
      await page
        .locator('p')
        .filter({ hasText: /^Prompt$/ })
        .click();
    });

    test('shows TipTap editor when Prompt menu is selected', async ({ page }) => {
      await expect(page.locator('.ProseMirror')).toBeVisible();
      await expect(page.getByText('Clear all')).toBeVisible();
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
      // Ensure we're on Configure view with General tab selected
      if (
        !(await page
          .getByRole('tab', { name: /general/i })
          .isVisible()
          .catch(() => false))
      ) {
        await page
          .locator('p')
          .filter({ hasText: /^Configure$/ })
          .click();
      }
      await page.getByRole('tab', { name: /general/i }).click();

      // General tab should show the agent name label
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

    test('switches between Configure and Prompt menus', async ({ page }) => {
      // Click Prompt in sidebar
      await page
        .locator('p')
        .filter({ hasText: /^Prompt$/ })
        .click();
      await expect(page.getByRole('heading', { name: 'Prompt', level: 5 })).toBeVisible();
      await expect(page.locator('.ProseMirror')).toBeVisible();

      // Click Configure in sidebar
      await page
        .locator('p')
        .filter({ hasText: /^Configure$/ })
        .click();
      await expect(page.getByRole('heading', { name: 'Configure', level: 5 })).toBeVisible();
      await expect(page.getByRole('tab', { name: /general/i })).toBeVisible();
    });
  });

  // ── 8. Save Flow ───────────────────────────────────────────────────────────
  test.describe('Save Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Ensure fresh form state with a hard nav
      await page.goto('/agents/create/inbound');
    });

    test('sends correct payload and redirects to /agents on save', async ({ page }) => {
      const captured = await mockUpsertAPI(page);

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });

      expect(captured.length).toBe(1);
      expect(captured[0]).toMatchObject({
        name: 'My Inbound Assistant',
        agent_type: 'inbound',
      });
    });

    test('shows Saving... and disables button during save', async ({ page }) => {
      await mockUpsertAPI(page, { delay: 2000 });

      await page.getByRole('button', { name: /save changes/i }).click();

      const savingBtn = page.getByRole('button', { name: /saving/i });
      await expect(savingBtn).toBeVisible();
      await expect(savingBtn).toBeDisabled();
    });

    test('stays on page when save fails', async ({ page }) => {
      await page.route('**/agent/upsert_agent', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Server error' }),
        });
      });

      await page.getByRole('button', { name: /save changes/i }).click();

      // Should stay on the create page
      await page.waitForTimeout(1000);
      expect(page.url()).toContain('/agents/create/inbound');
    });

    test('saves agent to DB and shows in list (real API)', async ({ page }) => {
      // No mocks: triggers actual save to backend/DB. Requires running backend (NEXT_PUBLIC_BACKEND_URL).
      const agentName = 'My Inbound Assistant';

      await page.getByRole('button', { name: /save changes/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 15_000 });

      // Created item should show in the list (from real get_all_agents)
      await expect(page.getByText(agentName).first()).toBeVisible({ timeout: 10_000 });
      await expect(page.getByText('Inbound').first()).toBeVisible();

      // Do not delete the created item for now — uncomment below when cleanup is needed:
      // await page.getByRole('button', { name: /delete|remove/i }).first().click();
      // await page.getByRole('button', { name: /confirm|yes/i }).click();
      // await expect(page.getByText(agentName)).not.toBeVisible();
    });
  });

  // ── 9. Back Navigation ─────────────────────────────────────────────────────
  test.describe('Back Navigation', () => {
    test('navigates to /agents when clicking Back to Agents', async ({ page }) => {
      await page.getByRole('button', { name: /back to agents/i }).click();
      await expect(page).toHaveURL(/\/agents(?:\?|$)/, { timeout: 10_000 });
    });
  });

  // ── 10. Auth Redirect ──────────────────────────────────────────────────────
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

  // ── 11. Accessibility ──────────────────────────────────────────────────────
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
