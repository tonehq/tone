import { expect, Page } from '@playwright/test';

import { test } from '../helpers/auth';

// ── Mock data ────────────────────────────────────────────────────────────────
const CUSTOM_TOOL = {
  id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  uuid: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
  name: 'check_inventory',
  description: 'Checks product inventory.',
  tool_type: 'custom',
  url: 'https://api.example.com/inventory/{product_id}',
  method: 'GET',
  auth_type: 'api_key',
  auth_config: { header_name: 'X-API-Key', api_key: 'sk-secret' },
  meta_data: null,
  parameters: {
    type: 'object',
    properties: {
      product_id: { type: 'string', description: 'Product identifier' },
    },
    required: ['product_id'],
  },
  is_active: true,
  is_template: false,
  oauth_connection_id: null,
  mcp_server_id: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-05-01T00:00:00Z',
};

const CALENDAR_TOOL = {
  id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  uuid: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
  name: 'create_calendar_event',
  description: 'Create a Google Calendar event.',
  tool_type: 'google_calendar',
  url: null,
  method: 'POST',
  auth_type: 'none',
  auth_config: null,
  meta_data: { calendar_id: 'primary', timezone: 'America/New_York' },
  parameters: {
    type: 'object',
    properties: { title: { type: 'string', description: 'Event title' } },
    required: ['title'],
  },
  is_active: true,
  is_template: false,
  oauth_connection_id: 'oauth-1',
  mcp_server_id: null,
  created_at: '2026-02-01T00:00:00Z',
  updated_at: '2026-04-01T00:00:00Z',
};

const SMS_TOOL = {
  id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
  uuid: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
  name: 'send_appointment_sms',
  description: 'Send a Twilio SMS reminder.',
  tool_type: 'send_sms',
  url: null,
  method: 'POST',
  auth_type: 'none',
  auth_config: { account_sid: 'AC123', auth_token: 'tok-secret' },
  meta_data: { from_number: '+15551234567' },
  parameters: {},
  is_active: true,
  is_template: false,
  oauth_connection_id: null,
  mcp_server_id: null,
  created_at: '2026-03-01T00:00:00Z',
  updated_at: '2026-03-15T00:00:00Z',
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

async function mockGetTool(page: Page, tool: unknown): Promise<void> {
  await page.route('**/tool/get_tool**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(tool),
    });
  });
}

async function mockGetAllTools(page: Page): Promise<void> {
  await page.route('**/tool/get_all_tools', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });
}

async function mockToolList(page: Page): Promise<void> {
  await page.route('**/tool/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20 }),
    });
  });
}

async function mockOAuthConnections(page: Page, conns: unknown[] = []): Promise<void> {
  await page.route('**/oauth/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(conns),
    });
  });
}

// ── Tests: Edit Custom Tool ──────────────────────────────────────────────────
test.describe('Tools Edit — Custom Tool', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockGetTool(page, CUSTOM_TOOL);
    await mockGetAllTools(page);
    await page.goto(`/tools/edit/${CUSTOM_TOOL.id}`);
  });

  test.describe('Load Existing Values', () => {
    test('loads the name into the input', async ({ page }) => {
      await expect(page.getByPlaceholder('check_inventory')).toHaveValue('check_inventory', {
        timeout: 5_000,
      });
    });

    test('loads the description into the textarea', async ({ page }) => {
      await expect(
        page.getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        ),
      ).toHaveValue('Checks product inventory.');
    });

    test('loads the URL into the URL input', async ({ page }) => {
      await expect(
        page.getByPlaceholder('https://api.example.com/inventory/{product_id}'),
      ).toHaveValue('https://api.example.com/inventory/{product_id}');
    });

    test('loads the HTTP method', async ({ page }) => {
      const select = page.locator('button[id="tool-method"]');
      await expect(select).toContainText('GET', { timeout: 5_000 });
    });

    test('loads the API Key auth type and credential fields', async ({ page }) => {
      await expect(page.getByLabel('Authentication')).toContainText('API Key', { timeout: 5_000 });
      await expect(page.locator('input[id="tool-auth-header"]')).toHaveValue('X-API-Key');
      await expect(page.locator('input[id="tool-auth-api-key"]')).toHaveValue('sk-secret');
    });

    test('loads existing parameter rows into the parameter builder', async ({ page }) => {
      await expect(page.getByPlaceholder('parameter_name').first()).toHaveValue('product_id', {
        timeout: 5_000,
      });
      await expect(page.getByPlaceholder('Description shown to LLM').first()).toHaveValue(
        'Product identifier',
      );
      await expect(page.getByRole('checkbox', { name: 'Required' })).toBeChecked();
    });

    test('header label shows the tool name', async ({ page }) => {
      await expect(page.getByText('check_inventory', { exact: true }).first()).toBeVisible({
        timeout: 5_000,
      });
    });

    test('shows Save button (not Create) in edit mode', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible({
        timeout: 5_000,
      });
    });
  });

  test.describe('Update Flow', () => {
    test('shows success toast on successful update', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...CUSTOM_TOOL, description: 'Updated desc' }),
        });
      });

      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Updated desc');
      await page.getByRole('button', { name: 'Save', exact: true }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool updated successfully');
    });

    test('does NOT redirect away from the edit page on update', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(CUSTOM_TOOL),
        });
      });

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(getToast(page)).toContainText('Tool updated successfully', { timeout: 5_000 });
      await expect(page).toHaveURL(new RegExp(`/tools/edit/${CUSTOM_TOOL.id}`));
    });

    test('sends id in the upsert payload to indicate update', async ({ page }) => {
      let body: Record<string, unknown> | null = null;
      await page.route('**/tool/upsert_tool', async (route) => {
        body = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(CUSTOM_TOOL),
        });
      });

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect.poll(() => body, { timeout: 5_000 }).not.toBeNull();
      expect(body!.id).toBe(CUSTOM_TOOL.id);
    });

    test('shows backend error toast for 400 "Template tools cannot be edited"', async ({
      page,
    }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Template tools cannot be edited' }),
        });
      });

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Template tools cannot be edited' }),
      ).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe('Delete from Custom Edit Page', () => {
    // The custom form does not expose a Delete button (only built-in dropdown does).
    // Per-row delete is tested in tools.spec.ts. Documented here.
    test('does not show a Delete button in the custom edit header', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Delete Tool' })).not.toBeVisible();
    });
  });
});

// ── Tests: Edit Google Calendar Tool ─────────────────────────────────────────
test.describe('Tools Edit — Built-In (Google Calendar)', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockGetTool(page, CALENDAR_TOOL);
    await mockGetAllTools(page);
    await mockOAuthConnections(page, [
      {
        id: 'oauth-1',
        label: 'work-calendar',
        public_metadata: { user_email: 'user@example.com' },
      },
    ]);
    await page.goto(`/tools/edit/${CALENDAR_TOOL.id}`);
  });

  test.describe('Page Rendering', () => {
    test('shows the Tool Settings section', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Tool Settings' })).toBeVisible({
        timeout: 5_000,
      });
    });

    test('loads the name into the Tool Name input', async ({ page }) => {
      await expect(page.getByLabel('Tool Name')).toHaveValue('create_calendar_event', {
        timeout: 5_000,
      });
    });

    test('loads the description and shows live character counter', async ({ page }) => {
      await expect(page.getByLabel('Description')).toHaveValue('Create a Google Calendar event.', {
        timeout: 5_000,
      });
      // "31/1000" appears in the counter
      await expect(page.getByText('/1000', { exact: false })).toBeVisible();
    });

    test('shows the Google Account connection section', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Google Account' })).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.getByLabel('Connected Account')).toBeVisible();
    });

    test('lists OAuth connections in the dropdown', async ({ page }) => {
      await page.locator('button[id="oauth-connection"]').click();
      await expect(page.getByRole('option', { name: 'user@example.com' })).toBeVisible({
        timeout: 5_000,
      });
      await page.keyboard.press('Escape');
    });

    test('shows the Calendar Settings meta section', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Calendar Settings' })).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.getByLabel('Calendar ID')).toHaveValue('primary');
      await expect(page.getByLabel('Timezone')).toHaveValue('America/New_York');
    });

    test('shows helper text under Calendar ID and Timezone fields', async ({ page }) => {
      await expect(
        page.getByText(/Defaults to "primary" if not specified\./),
      ).toBeVisible();
      await expect(page.getByText(/Defaults to UTC if not specified\./)).toBeVisible();
    });

    test('shows the truncated UUID in the header with copy button', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Copy UUID' })).toBeVisible({ timeout: 5_000 });
      await expect(
        page.getByText(CALENDAR_TOOL.uuid.slice(0, 13) + '...', { exact: false }),
      ).toBeVisible();
    });
  });

  test.describe('No OAuth Connections', () => {
    test('shows a helper link to Integrations when no Google accounts are connected', async ({
      page,
    }) => {
      await page.unrouteAll({ behavior: 'wait' });
      await mockGetTool(page, { ...CALENDAR_TOOL, oauth_connection_id: null });
      await mockGetAllTools(page);
      await mockOAuthConnections(page, []);

      await page.goto(`/tools/edit/${CALENDAR_TOOL.id}`);
      await expect(page.getByText(/No Google accounts connected\./)).toBeVisible({
        timeout: 5_000,
      });
      await expect(page.getByRole('link', { name: /Connect one in Integrations/i })).toBeVisible();
    });
  });

  test.describe('Validation', () => {
    test('shows "Name is required" when name is cleared', async ({ page }) => {
      await page.getByLabel('Tool Name').fill('');
      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(page.getByText('Name is required')).toBeVisible({ timeout: 5_000 });
    });

    test('shows "Description is required" when description is cleared', async ({ page }) => {
      await page.getByLabel('Description').fill('');
      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(page.getByText('Description is required')).toBeVisible({ timeout: 5_000 });
    });

    test('shows "Description is too long" when description exceeds 1000 characters', async ({
      page,
    }) => {
      const longDesc = 'a'.repeat(1001);
      // The textarea has maxLength=1000 enforced by the browser, so we have to set the value
      // directly via JavaScript to bypass it and verify the Zod schema error message.
      await page.getByLabel('Description').evaluate((el, value) => {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype,
          'value',
        )?.set;
        setter?.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }, longDesc);

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(page.getByText('Description is too long')).toBeVisible({ timeout: 5_000 });
    });

    test('character counter displays current length over 1000', async ({ page }) => {
      await page.getByLabel('Description').fill('hello');
      await expect(page.getByText('5/1000', { exact: true })).toBeVisible({ timeout: 3_000 });
    });
  });

  test.describe('OAuth Error Mapping', () => {
    // Built-in form loads in "Saved" state — dirty a field so Save button appears.
    test.beforeEach(async ({ page }) => {
      await page.getByLabel('Tool Name').fill('renamed_for_test');
      await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible({
        timeout: 3_000,
      });
    });

    test('shows backend error toast when OAuth connection is not found (400)', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'OAuth connection oauth-1 not found' }),
        });
      });

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'OAuth connection oauth-1 not found' }),
      ).toBeVisible({ timeout: 5_000 });
    });

    test('shows backend error toast when OAuth connection is inactive (400)', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'OAuth connection oauth-1 is not active' }),
        });
      });

      await page.getByRole('button', { name: 'Save', exact: true }).click();
      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'OAuth connection oauth-1 is not active' }),
      ).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe('Delete from Built-In Edit Page', () => {
    test('opens the kebab menu and shows Delete Tool + Copy Tool ID', async ({ page }) => {
      // The MoreVertical icon button is unnamed — locate via its sibling Save button
      // Kebab is the sibling button next to the Save/Saved button in the form header.
      const savedBtn = page.getByRole('button', { name: /^Saved?$/ }).first();
      const moreBtn = savedBtn.locator('xpath=following-sibling::button[1]');
      await moreBtn.click();

      await expect(page.getByRole('menuitem', { name: /Copy Tool ID/i })).toBeVisible({
        timeout: 3_000,
      });
      await expect(page.getByRole('menuitem', { name: /Delete Tool/i })).toBeVisible();
    });

    test('copies the tool UUID and shows "Tool ID copied" toast', async ({ page, context }) => {
      await context.grantPermissions(['clipboard-read', 'clipboard-write']);

      // Kebab is the sibling button next to the Save/Saved button in the form header.
      const savedBtn = page.getByRole('button', { name: /^Saved?$/ }).first();
      const moreBtn = savedBtn.locator('xpath=following-sibling::button[1]');
      await moreBtn.click();
      await page.getByRole('menuitem', { name: /Copy Tool ID/i }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool ID copied');
    });

    test('deletes the tool and redirects to /tools', async ({ page }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ message: 'Tool deleted successfully' }),
        });
      });
      await mockToolList(page);

      // Kebab is the sibling button next to the Save/Saved button in the form header.
      const savedBtn = page.getByRole('button', { name: /^Saved?$/ }).first();
      const moreBtn = savedBtn.locator('xpath=following-sibling::button[1]');
      await moreBtn.click();
      await page.getByRole('menuitem', { name: /Delete Tool/i }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool deleted successfully');
      await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
    });

    test('shows backend error toast for delete failure (e.g. template tool)', async ({ page }) => {
      await page.route('**/tool/delete_tool**', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Template tools cannot be deleted' }),
        });
      });

      // Kebab is the sibling button next to the Save/Saved button in the form header.
      const savedBtn = page.getByRole('button', { name: /^Saved?$/ }).first();
      const moreBtn = savedBtn.locator('xpath=following-sibling::button[1]');
      await moreBtn.click();
      await page.getByRole('menuitem', { name: /Delete Tool/i }).click();

      await expect(
        page.locator('[data-sonner-toast]', { hasText: 'Template tools cannot be deleted' }),
      ).toBeVisible({ timeout: 5_000 });
    });
  });

  test.describe('Save State Indicator', () => {
    test('shows Saved state immediately after page load (existing tool is clean)', async ({
      page,
    }) => {
      await expect(page.getByRole('button', { name: 'Saved', exact: true })).toBeVisible({
        timeout: 5_000,
      });
    });

    test('switches from Saved back to Save when a field is modified', async ({ page }) => {
      await page.getByLabel('Tool Name').fill('renamed_calendar_event');
      await expect(page.getByRole('button', { name: 'Save', exact: true })).toBeVisible({
        timeout: 3_000,
      });
    });
  });
});

// ── Tests: Edit SMS Tool ─────────────────────────────────────────────────────
test.describe('Tools Edit — Built-In (Send SMS)', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockGetTool(page, SMS_TOOL);
    await mockGetAllTools(page);
    await page.goto(`/tools/edit/${SMS_TOOL.id}`);
  });

  test('shows the SMS Credentials section with Account SID + Auth Token fields', async ({
    page,
  }) => {
    await expect(page.getByRole('heading', { name: 'SMS Credentials' })).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByLabel('Account SID')).toHaveValue('AC123');
    await expect(page.getByLabel('Auth Token')).toHaveValue('tok-secret');
    await expect(page.locator('input[id="tool-auth-auth_token"]')).toHaveAttribute(
      'type',
      'password',
    );
  });

  test('shows the SMS Settings meta section with From Number field', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'SMS Settings' })).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByLabel('From Number')).toHaveValue('+15551234567');
  });

  test('does NOT show the Google Account connection section for SMS', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Google Account' })).not.toBeVisible();
  });
});

// ── Tests: Edit error paths ──────────────────────────────────────────────────
test.describe('Tools Edit — Error Paths', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('redirects to /tools and shows error toast on 404 tool not found', async ({ page }) => {
    await page.route('**/tool/get_tool**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Tool not found' }),
      });
    });
    await mockToolList(page);

    await page.goto('/tools/edit/nonexistent-id');
    // React StrictMode in dev fires the effect twice → two toasts may appear; assert at least one.
    await expect(
      page.locator('[data-sonner-toast]', { hasText: 'Tool not found' }).first(),
    ).toBeVisible({ timeout: 5_000 });
    await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
  });

  test('shows loading state while fetching the tool', async ({ page }) => {
    let resolveRoute: (() => void) | null = null;
    await page.route('**/tool/get_tool**', async (route) => {
      await new Promise<void>((resolve) => {
        resolveRoute = resolve;
      });
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(CUSTOM_TOOL),
      });
    });
    await mockGetAllTools(page);

    await page.goto(`/tools/edit/${CUSTOM_TOOL.id}`);
    await expect(page.getByText('Loading tool...')).toBeVisible({ timeout: 3_000 });
    resolveRoute?.();
  });

  test('refresh during edit reloads via GET /tool/get_tool', async ({ page }) => {
    let getToolCalls = 0;
    await page.route('**/tool/get_tool**', async (route) => {
      getToolCalls += 1;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(CUSTOM_TOOL),
      });
    });
    await mockGetAllTools(page);

    await page.goto(`/tools/edit/${CUSTOM_TOOL.id}`);
    await expect(page.getByPlaceholder('check_inventory')).toHaveValue('check_inventory', {
      timeout: 5_000,
    });

    const callsBefore = getToolCalls;
    await page.reload();
    await expect(page.getByPlaceholder('check_inventory')).toHaveValue('check_inventory', {
      timeout: 5_000,
    });
    expect(getToolCalls).toBeGreaterThan(callsBefore);
  });
});
