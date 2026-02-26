import { test as base, BrowserContext, expect, Page } from '@playwright/test';

import { loginViaUI } from '../helpers/auth';

// ── Mock data ────────────────────────────────────────────────────────────────
const MOCK_AGENTS = [
  {
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
    system_prompt: '',
    end_call_message: 'Goodbye!',
    voicemail_message: null,
    status: 'active',
    custom_vocabulary: null,
    filter_words: null,
    realistic_filler_words: null,
    language: 'en',
    voice_speed: '50',
    patience_level: 'low',
    speech_recognition: 'fast',
    call_recording: null,
    call_transcription: null,
  },
  {
    id: 2,
    uuid: 'uuid-agent-2',
    name: 'Support Bot',
    description: 'Handles outbound support calls',
    agent_type: 'outbound',
    phone_number: null,
    is_public: false,
    tags: {},
    total_calls: 5,
    total_minutes: 15,
    average_rating: 3.8,
    created_by: 1,
    created_at: 1708700000,
    updated_at: 1739875800000,
    llm_service_id: 1,
    tts_service_id: 1,
    stt_service_id: 1,
    llm_model_id: null,
    tts_model_id: null,
    stt_model_id: null,
    first_message: 'Hi there!',
    system_prompt: '',
    end_call_message: 'Thanks!',
    voicemail_message: null,
    status: 'active',
    custom_vocabulary: null,
    filter_words: null,
    realistic_filler_words: null,
    language: 'en',
    voice_speed: '50',
    patience_level: 'medium',
    speech_recognition: 'fast',
    call_recording: null,
    call_transcription: null,
  },
];

// ── Browser lifecycle ─────────────────────────────────────────────────────────
// Worker-scoped context = one browser window shared across all tests in this worker.
// Login happens ONCE during worker setup, not before every test.
// Single tab = reused across all tests; beforeEach uses soft navigation.
// IMPORTANT: name the Playwright fixture callback "provide", NOT "use".
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

// Soft navigation helper — exact match for /agents (not /agents/create/...).
// Uses sidebar link when on another dashboard page, falls back to page.goto().
async function ensureOnAgentsPage(page: Page): Promise<void> {
  if (/\/agents(?:\?|$)/.test(page.url())) return;

  const sidebarLink = page.locator('a[href="/agents"]').first();
  if (await sidebarLink.isVisible().catch(() => false)) {
    await sidebarLink.click();
    await page.waitForURL(/\/agents(?:\?|$)/, { timeout: 5_000 });
    return;
  }

  await page.goto('/agents');
}

async function mockAgentsAPI(page: Page, agents: unknown[] = MOCK_AGENTS): Promise<void> {
  await page.route('**/agent/get_all_agents**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(agents),
    });
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────
test.describe('Agents List Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await mockAgentsAPI(page);
    await ensureOnAgentsPage(page);
  });

  // ── 1. Page Rendering ──────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the agents heading', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Agents' })).toBeVisible();
    });

    test('shows the search input with placeholder', async ({ page }) => {
      await expect(page.getByPlaceholder('Search...')).toBeVisible();
    });

    test('shows the create agent button', async ({ page }) => {
      await expect(page.getByRole('button', { name: /create agent/i })).toBeVisible();
    });

    test('shows agent names in the data grid', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.getByText('Sales Assistant')).toBeVisible({ timeout: 5_000 });
      await expect(grid.getByText('Support Bot')).toBeVisible();
    });

    test('shows inbound agent type chip', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      const inboundChip = grid.locator('.MuiChip-root').filter({ hasText: 'Inbound' });
      await expect(inboundChip).toBeVisible({ timeout: 5_000 });
    });

    test('shows outbound agent type chip', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      const outboundChip = grid.locator('.MuiChip-root').filter({ hasText: 'Outbound' });
      await expect(outboundChip).toBeVisible({ timeout: 5_000 });
    });

    test('shows phone number for agents that have one', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      const salesRow = grid.locator('.MuiDataGrid-row').filter({ hasText: 'Sales Assistant' });
      await expect(salesRow).toBeVisible({ timeout: 5_000 });
      await expect(salesRow.getByText('+1 (555) 123-4567')).toBeVisible();
    });

    test('shows dash for agents without a phone number', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      const supportRow = grid.locator('.MuiDataGrid-row').filter({ hasText: 'Support Bot' });
      await expect(supportRow).toBeVisible({ timeout: 5_000 });
      await expect(supportRow.locator('[data-field="phone_number"]').getByText('-')).toBeVisible();
    });

    test('shows pagination controls', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.locator('.MuiTablePagination-root')).toBeVisible({ timeout: 5_000 });
    });
  });

  // ── 2. DataGrid Columns & Interaction ─────────────────────────────────────
  test.describe('DataGrid Columns & Interaction', () => {
    test('shows all column headers', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.getByText('AGENT NAME')).toBeVisible({ timeout: 5_000 });
      await expect(grid.getByText('PHONE NUMBER')).toBeVisible();
      await expect(grid.getByText('LAST EDITED')).toBeVisible();
      await expect(grid.getByText('AGENT TYPE')).toBeVisible();
      await expect(grid.getByText('ACTION')).toBeVisible();
    });

    test('shows action menu with Edit and Delete options', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.getByText('Sales Assistant')).toBeVisible({ timeout: 5_000 });

      // Click the action menu button (three-dot icon) in the first row
      const firstRow = grid.locator('.MuiDataGrid-row').first();
      await firstRow.locator('button').click();

      await expect(page.getByRole('menuitem', { name: 'Edit' })).toBeVisible();
      await expect(page.getByRole('menuitem', { name: 'Delete' })).toBeVisible();

      // Close the menu by pressing Escape
      await page.keyboard.press('Escape');
    });

    test('navigates to edit page when clicking Edit in action menu', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.getByText('Sales Assistant')).toBeVisible({ timeout: 5_000 });

      // Open action menu on the first row (Sales Assistant, inbound, id=1)
      const firstRow = grid.locator('.MuiDataGrid-row').first();
      await firstRow.locator('button').click();
      await page.getByRole('menuitem', { name: 'Edit' }).click();

      await expect(page).toHaveURL(/\/agents\/edit\/inbound\/1/, { timeout: 10_000 });
    });
  });

  // ── 3. Create Agent Modal ─────────────────────────────────────────────────
  test.describe('Create Agent Modal', () => {
    // Dismiss any dialog left open by a previous test (e.g., test 13 opens modal
    // but doesn't close it; without cleanup test 14 can't click behind the backdrop).
    test.beforeEach(async ({ page }) => {
      if (
        await page
          .getByRole('dialog')
          .isVisible()
          .catch(() => false)
      ) {
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).not.toBeVisible();
      }
    });

    test('opens the create agent modal when clicking Create Agent', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByText('Choose type of agent')).toBeVisible();
    });

    test('shows Outbound and Inbound agent type options', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      const dialog = page.getByRole('dialog');

      await expect(dialog.getByText('Outbound')).toBeVisible();
      await expect(
        dialog.getByText('Automate calls within workflows using Zapier, REST API, or HighLevel'),
      ).toBeVisible();
      await expect(dialog.getByText('Inbound')).toBeVisible();
      await expect(
        dialog.getByText('Manage incoming calls via phone, Zapier, REST API, or HighLevel'),
      ).toBeVisible();
    });

    test('closes the modal when pressing Escape', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible();

      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();
    });

    test('navigates to inbound create page when clicking Inbound card', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByText('Inbound').click();

      await expect(page).toHaveURL(/\/agents\/create\/inbound/, { timeout: 10_000 });
    });

    test('navigates to outbound create page when clicking Outbound card', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      const dialog = page.getByRole('dialog');
      await dialog.getByText('Outbound').click();

      await expect(page).toHaveURL(/\/agents\/create\/outbound/, { timeout: 10_000 });
    });
  });

  // ── 4. Empty State ────────────────────────────────────────────────────────
  test.describe('Empty State', () => {
    test.beforeEach(async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockAgentsAPI(page, []);
      await page.goto('/agents');
    });

    test('shows empty data grid when no agents exist', async ({ page }) => {
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.getByText(/no rows/i)).toBeVisible({ timeout: 5_000 });
    });
  });

  // ── 5. Loading State ──────────────────────────────────────────────────────
  test.describe('Loading State', () => {
    test('shows loading indicator while agents are being fetched', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });

      // Delayed API response — use route.abort() to prevent success handler side effects
      await page.route('**/agent/get_all_agents**', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await route.abort('failed');
      });

      await page.goto('/agents');

      // MUI DataGrid v6 shows skeleton placeholder rows when loading={true}
      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid.locator('.MuiSkeleton-root').first()).toBeVisible({
        timeout: 2_000,
      });
    });
  });

  // ── 6. Error State ────────────────────────────────────────────────────────
  test.describe('Error State', () => {
    test('shows empty grid when API returns an error', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await page.route('**/agent/get_all_agents**', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      });
      await page.goto('/agents');

      const grid = page.locator('.MuiDataGrid-root');
      // After API error, atom sets agentList to [] — grid shows "No rows"
      await expect(grid.getByText(/no rows/i)).toBeVisible({ timeout: 5_000 });
    });
  });

  // ── 7. Auth Redirect ──────────────────────────────────────────────────────
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
      await page.goto('/agents');
      await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10_000 });
    });
  });

  // ── 8. Real API (list from backend/DB) ─────────────────────────────────────
  test.describe('Real API', () => {
    test('loads agents list from API (no mocks)', async ({ page }) => {
      await page.unrouteAll({ behavior: 'wait' });
      // No mock: real GET /agent/get_all_agents. Requires running backend.
      await ensureOnAgentsPage(page);

      const grid = page.locator('.MuiDataGrid-root');
      await expect(grid).toBeVisible({ timeout: 10_000 });
      // List may be empty or have rows; grid is visible when API has responded
    });
  });

  // ── 9. Accessibility ──────────────────────────────────────────────────────
  test.describe('Accessibility', () => {
    test('shows proper heading level for the page title', async ({ page }) => {
      const heading = page.getByRole('heading', { name: 'Agents', level: 4 });
      await expect(heading).toBeVisible();
    });

    test('allows Create Agent button to be activated via keyboard', async ({ page }) => {
      const createBtn = page.getByRole('button', { name: /create agent/i });
      await createBtn.focus();
      await expect(createBtn).toBeFocused();

      await page.keyboard.press('Enter');
      await expect(page.getByRole('dialog')).toBeVisible();

      // Close modal to clean up
      await page.keyboard.press('Escape');
    });

    test('traps focus within the create agent modal', async ({ page }) => {
      await page.getByRole('button', { name: /create agent/i }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();

      // MUI Dialog traps focus — Tab should cycle within the dialog
      await page.keyboard.press('Tab');
      const focusedInDialog = await dialog.locator(':focus').count();
      expect(focusedInDialog).toBeGreaterThan(0);

      await page.keyboard.press('Escape');
    });
  });
});
