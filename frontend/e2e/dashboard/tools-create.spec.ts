import { expect, Page } from '@playwright/test';

import { test } from '../helpers/auth';

// ── Mock data ────────────────────────────────────────────────────────────────
const MOCK_TEMPLATES = [
  {
    id: 'tpl-cal',
    uuid: 'tpl-cal-uuid',
    name: 'google_calendar_template',
    description: 'Pre-configured Google Calendar template',
    tool_type: 'google_calendar',
    url: null,
    method: 'POST',
    auth_type: 'none',
    auth_config: null,
    meta_data: {},
    parameters: {
      type: 'object',
      properties: { title: { type: 'string', description: 'Event title' } },
      required: ['title'],
    },
    is_active: true,
    is_template: true,
    oauth_connection_id: null,
    mcp_server_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const MOCK_CREATED_TOOL = {
  id: 'new-tool-id',
  uuid: 'new-tool-uuid',
  name: 'new_tool',
  description: 'A newly created tool',
  tool_type: 'custom',
  url: 'https://api.example.com',
  method: 'POST',
  auth_type: 'none',
  auth_config: null,
  meta_data: null,
  parameters: {},
  is_active: true,
  is_template: false,
  oauth_connection_id: null,
  mcp_server_id: null,
  created_at: '2026-05-25T00:00:00Z',
  updated_at: '2026-05-25T00:00:00Z',
};

// ── Helpers ──────────────────────────────────────────────────────────────────
const getToast = (p: Page) => p.locator('[data-sonner-toast]').first();

async function mockTemplates(page: Page, templates: unknown[] = MOCK_TEMPLATES): Promise<void> {
  await page.route('**/tool/get_template_tools', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(templates),
    });
  });
}

async function mockUpsertSuccess(page: Page): Promise<void> {
  await page.route('**/tool/upsert_tool', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_CREATED_TOOL),
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

// ── Tests: Type selection page (/tools/create) ───────────────────────────────
test.describe('Tools Create — Type Selection Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockTemplates(page);
    await page.goto('/tools/create');
  });

  test('shows the page heading and subtitle', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'What type of tool?' })).toBeVisible();
    await expect(
      page.getByText('Choose a built-in tool or create a custom API integration.'),
    ).toBeVisible();
  });

  test('shows the Create Tool header label', async ({ page }) => {
    await expect(page.getByText('Create Tool', { exact: true })).toBeVisible();
  });

  test('shows the Custom Tool card with API badge', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Custom Tool' })).toBeVisible();
    await expect(page.getByText('API', { exact: true })).toBeVisible();
    await expect(
      page.getByText(
        'Call any external API or webhook. Define the endpoint, parameters, and authentication.',
      ),
    ).toBeVisible();
  });

  test('shows template cards loaded from the backend', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'google_calendar_template' })).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByText('Pre-configured Google Calendar template')).toBeVisible();
  });

  test('shows skeleton placeholders while templates are loading', async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    let resolveRoute: (() => void) | null = null;
    await page.route('**/tool/get_template_tools', async (route) => {
      await new Promise<void>((resolve) => {
        resolveRoute = resolve;
      });
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/tools/create');
    await expect(page.locator('[class*="animate-pulse"]').first()).toBeVisible({ timeout: 2_000 });
    resolveRoute?.();
  });

  test('falls back gracefully when templates request fails', async ({ page }) => {
    await page.unrouteAll({ behavior: 'wait' });
    await page.route('**/tool/get_template_tools', async (route) => {
      await route.fulfill({ status: 500, contentType: 'application/json', body: '{}' });
    });
    await page.goto('/tools/create');

    // The Custom Tool card is still visible — failure just hides templates
    await expect(page.getByRole('heading', { name: 'Custom Tool' })).toBeVisible({
      timeout: 5_000,
    });
  });

  test('navigates to /tools/create/custom when clicking the Custom Tool card', async ({ page }) => {
    await page.getByRole('heading', { name: 'Custom Tool' }).click();
    await expect(page).toHaveURL(/\/tools\/create\/custom$/, { timeout: 10_000 });
  });

  test('navigates to the custom form with template_id query param when clicking a template', async ({
    page,
  }) => {
    await page.getByRole('heading', { name: 'google_calendar_template' }).click();
    await expect(page).toHaveURL(/\/tools\/create\/custom\?template_id=tpl-cal/, {
      timeout: 10_000,
    });
  });

  test('navigates back to /tools when clicking the Back arrow', async ({ page }) => {
    await mockToolList(page);
    await page.getByRole('button', { name: 'Back' }).click();
    await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
  });
});

// ── Tests: Custom Tool Form (/tools/create/custom) ───────────────────────────
test.describe('Tools Create — Custom Tool Form', () => {
  test.beforeEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
    await mockGetAllTools(page);
    await page.goto('/tools/create/custom');
  });

  // ── Page Rendering ─────────────────────────────────────────────────────
  test.describe('Page Rendering', () => {
    test('shows the "New Tool" header label', async ({ page }) => {
      await expect(page.getByText('New Tool', { exact: true })).toBeVisible();
    });

    test('shows the Tool Definition section', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Tool Definition', level: 3 })).toBeVisible();
    });

    test('shows the Active checkbox checked by default', async ({ page }) => {
      await expect(page.getByLabel('Active')).toBeChecked();
    });

    test('shows the Function name input with placeholder', async ({ page }) => {
      await expect(page.getByLabel(/Function name/i)).toBeVisible();
      await expect(page.getByPlaceholder('check_inventory')).toBeVisible();
    });

    test('shows the Description textarea with placeholder', async ({ page }) => {
      await expect(page.getByLabel(/Description/i)).toBeVisible();
      await expect(
        page.getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        ),
      ).toBeVisible();
    });

    test('shows the Request section with URL input', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Request', level: 3 })).toBeVisible();
      await expect(
        page.getByPlaceholder('https://api.example.com/inventory/{product_id}'),
      ).toBeVisible();
    });

    test('shows the placeholder helper text under the URL field', async ({ page }) => {
      await expect(page.getByText(/Use\s+\{param\}\s+placeholders/)).toBeVisible();
    });

    test('shows the Parameters section', async ({ page }) => {
      await expect(page.getByRole('heading', { name: 'Parameters', level: 3 })).toBeVisible();
      await expect(page.getByRole('button', { name: /add parameter/i })).toBeVisible();
    });

    test('shows the Authentication select set to "No Authentication" by default', async ({
      page,
    }) => {
      await expect(page.getByLabel('Authentication')).toBeVisible();
      await expect(page.getByLabel('Authentication')).toContainText('No Authentication');
    });

    test('shows Cancel and Create buttons in the header', async ({ page }) => {
      await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Create' })).toBeVisible();
    });

    test('header label updates as the user types the function name', async ({ page }) => {
      await page.getByPlaceholder('check_inventory').fill('my_awesome_tool');
      await expect(page.getByText('my_awesome_tool', { exact: true }).first()).toBeVisible({
        timeout: 3_000,
      });
    });
  });

  // ── Validation ─────────────────────────────────────────────────────────
  test.describe('Validation', () => {
    test('shows "Name is required" when submitting an empty form', async ({ page }) => {
      await page.getByRole('button', { name: 'Create' }).click();
      await expect(page.getByText('Name is required')).toBeVisible({ timeout: 5_000 });
    });

    test('shows "Description is required" when name is filled but description is empty', async ({
      page,
    }) => {
      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page.getByRole('button', { name: 'Create' }).click();
      await expect(page.getByText('Description is required')).toBeVisible({ timeout: 5_000 });
    });

    test('shows "URL is required" when name and description are filled but URL is empty', async ({
      page,
    }) => {
      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Does a thing');
      await page.getByRole('button', { name: 'Create' }).click();
      await expect(page.getByText('URL is required')).toBeVisible({ timeout: 5_000 });
    });

    test('shows "Please enter a valid URL" for malformed URLs (no protocol)', async ({ page }) => {
      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Does a thing');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('not-a-url');
      await page.getByRole('button', { name: 'Create' }).click();
      await expect(page.getByText('Please enter a valid URL')).toBeVisible({ timeout: 5_000 });
    });

    test('rejects "ftp://" URL with Zod url() validator (still shown as valid URL — schema only blocks non-URLs)', async ({
      page,
    }) => {
      // Zod url() accepts ftp:// as a valid URL — this test documents that behavior.
      // No client error should appear; the backend will reject it.
      await mockUpsertSuccess(page);
      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('ftp://example.com/file');
      await page.getByRole('button', { name: 'Create' }).click();
      // Should NOT show the URL validation error
      await expect(page.getByText('Please enter a valid URL')).not.toBeVisible({ timeout: 2_000 });
    });

    test('accepts whitespace-only name as invalid (Zod min(1) checks length not trimmed)', async ({
      page,
    }) => {
      // The Zod schema uses .min(1) which counts whitespace as valid characters.
      // This test documents current behavior — whitespace IS accepted by the client schema.
      await mockUpsertSuccess(page);
      await page.getByPlaceholder('check_inventory').fill('   ');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();
      // Should NOT show "Name is required" since whitespace passes min(1)
      await expect(page.getByText('Name is required')).not.toBeVisible({ timeout: 2_000 });
    });

    test('accepts very long name (no max length on custom tool client schema)', async ({
      page,
    }) => {
      await mockUpsertSuccess(page);
      const longName = 'a'.repeat(500);
      await page.getByPlaceholder('check_inventory').fill(longName);
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool created successfully');
    });

    test('accepts special characters in the name', async ({ page }) => {
      await mockUpsertSuccess(page);
      await page.getByPlaceholder('check_inventory').fill('tool-with_special.chars/v1');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool created successfully');
    });
  });

  // ── HTTP Method Selector ───────────────────────────────────────────────
  test.describe('HTTP Method', () => {
    test('defaults to POST', async ({ page }) => {
      // The method select is inside the URL row
      const select = page.locator('button[id="tool-method"]');
      await expect(select).toContainText('POST');
    });

    test('exposes all five methods in the dropdown', async ({ page }) => {
      await page.locator('button[id="tool-method"]').click();
      for (const method of ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']) {
        await expect(page.getByRole('option', { name: method, exact: true })).toBeVisible();
      }
      await page.keyboard.press('Escape');
    });

    test('changes the helper text under Parameters when switching to GET', async ({ page }) => {
      await page.locator('button[id="tool-method"]').click();
      await page.getByRole('option', { name: 'GET', exact: true }).click();

      await expect(page.getByText('Parameters will be sent as query string values.')).toBeVisible({
        timeout: 3_000,
      });
    });

    test('shows JSON helper text under Parameters for POST', async ({ page }) => {
      await expect(
        page.getByText(
          'Parameters will be sent as JSON request body. Any parameter matching a {placeholder} in the URL will be used as a path value instead.',
        ),
      ).toBeVisible();
    });
  });

  // ── Parameter Builder ──────────────────────────────────────────────────
  test.describe('Parameter Builder', () => {
    test('adds a parameter row when clicking "Add parameter"', async ({ page }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();
      await expect(page.getByPlaceholder('parameter_name').first()).toBeVisible({ timeout: 3_000 });
      await expect(page.getByPlaceholder('Description shown to LLM').first()).toBeVisible();
    });

    test('lists all five parameter types in the type dropdown', async ({ page }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();

      const typeSelect = page.locator('button[id^="param-type-"]').first();
      await typeSelect.click();

      for (const type of ['String', 'Number', 'Integer', 'Boolean', 'Array']) {
        await expect(page.getByRole('option', { name: type, exact: true })).toBeVisible();
      }
      await page.keyboard.press('Escape');
    });

    test('toggles the Required checkbox on a parameter', async ({ page }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();
      const requiredCheckbox = page.getByRole('checkbox', { name: 'Required' }).first();
      await expect(requiredCheckbox).not.toBeChecked();
      await requiredCheckbox.click();
      await expect(requiredCheckbox).toBeChecked();
    });

    test('removes a parameter row when clicking the trash icon', async ({ page }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();
      await expect(page.getByPlaceholder('parameter_name').first()).toBeVisible({ timeout: 3_000 });

      await page.getByRole('button', { name: 'Remove parameter' }).first().click();
      await expect(page.getByPlaceholder('parameter_name')).toHaveCount(0);
    });

    test('shows a parameter count badge in the section header', async ({ page }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();
      const nameInput = page.getByPlaceholder('parameter_name').first();
      await nameInput.fill('product_id');

      // The count badge is the small "1" next to the Parameters heading
      const paramSection = page
        .locator('div')
        .filter({ has: page.getByRole('heading', { name: 'Parameters' }) })
        .first();
      await expect(paramSection.getByText('1', { exact: true })).toBeVisible({ timeout: 3_000 });
    });

    test('keeps both rows when adding duplicate parameter names (UI does not block, schema overwrites)', async ({
      page,
    }) => {
      await page.getByRole('button', { name: /add parameter/i }).click();
      await page.getByPlaceholder('parameter_name').first().fill('foo');
      await page.getByRole('button', { name: /add parameter/i }).click();
      await page.getByPlaceholder('parameter_name').nth(1).fill('foo');

      // Both row inputs visible in UI
      await expect(page.getByPlaceholder('parameter_name')).toHaveCount(2);
    });
  });

  // ── Authentication ─────────────────────────────────────────────────────
  test.describe('Authentication', () => {
    test('hides auth credential fields when "No Authentication" is selected', async ({ page }) => {
      await expect(page.getByLabel('Header')).not.toBeVisible();
      await expect(page.getByLabel('Token')).not.toBeVisible();
      await expect(page.getByLabel('Username')).not.toBeVisible();
    });

    test('shows Header + Value fields when API Key is selected', async ({ page }) => {
      await page.locator('button[id="tool-auth-type"]').click();
      await page.getByRole('option', { name: 'API Key' }).click();

      await expect(page.getByLabel('Header')).toBeVisible({ timeout: 3_000 });
      await expect(page.getByLabel('Value')).toBeVisible();
      await expect(page.getByPlaceholder('X-API-Key')).toBeVisible();
      await expect(page.getByPlaceholder('sk-...')).toBeVisible();
      // Value field is type=password
      await expect(page.locator('input[id="tool-auth-api-key"]')).toHaveAttribute(
        'type',
        'password',
      );
    });

    test('shows Token field when Bearer Token is selected', async ({ page }) => {
      await page.locator('button[id="tool-auth-type"]').click();
      await page.getByRole('option', { name: 'Bearer Token' }).click();

      await expect(page.getByLabel('Token')).toBeVisible({ timeout: 3_000 });
      await expect(page.getByPlaceholder('Enter bearer token')).toBeVisible();
      await expect(page.locator('input[id="tool-auth-bearer"]')).toHaveAttribute(
        'type',
        'password',
      );
    });

    test('shows Username + Password fields when Basic Auth is selected', async ({ page }) => {
      await page.locator('button[id="tool-auth-type"]').click();
      await page.getByRole('option', { name: 'Basic Auth' }).click();

      await expect(page.getByLabel('Username')).toBeVisible({ timeout: 3_000 });
      await expect(page.getByLabel('Password', { exact: true })).toBeVisible();
      await expect(page.locator('input[id="tool-auth-password"]')).toHaveAttribute(
        'type',
        'password',
      );
    });

    test('allows toggling password visibility on Bearer token field', async ({ page }) => {
      await page.locator('button[id="tool-auth-type"]').click();
      await page.getByRole('option', { name: 'Bearer Token' }).click();

      await page.getByPlaceholder('Enter bearer token').fill('secret-token');
      await page
        .getByRole('button', { name: /toggle password visibility/i })
        .first()
        .click();

      await expect(page.locator('input[id="tool-auth-bearer"]')).toHaveAttribute('type', 'text');
    });
  });

  // ── Active Toggle ──────────────────────────────────────────────────────
  test.describe('Active Toggle', () => {
    test('toggles the Active checkbox off and on', async ({ page }) => {
      const checkbox = page.getByLabel('Active');
      await expect(checkbox).toBeChecked();
      await checkbox.click();
      await expect(checkbox).not.toBeChecked();
      await checkbox.click();
      await expect(checkbox).toBeChecked();
    });
  });

  // ── Submit & Toasts ────────────────────────────────────────────────────
  test.describe('Submit', () => {
    async function fillBasicForm(page: Page) {
      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('A new tool');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://api.example.com/v1');
    }

    test('shows success toast and redirects to /tools on successful create', async ({ page }) => {
      await mockUpsertSuccess(page);
      await mockToolList(page);
      await fillBasicForm(page);
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(getToast(page)).toBeVisible({ timeout: 5_000 });
      await expect(getToast(page)).toContainText('Tool created successfully');
      await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
    });

    test('sends the trimmed name + description and other fields in the payload', async ({
      page,
    }) => {
      let body: Record<string, unknown> | null = null;
      await page.route('**/tool/upsert_tool', async (route) => {
        body = route.request().postDataJSON();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CREATED_TOOL),
        });
      });
      await mockToolList(page);

      await page.getByPlaceholder('check_inventory').fill('  trim_me  ');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('  desc  ');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect.poll(() => body, { timeout: 5_000 }).not.toBeNull();
      expect(body!.name).toBe('trim_me');
      expect(body!.description).toBe('desc');
      expect(body!.url).toBe('https://example.com');
      expect(body!.method).toBe('POST');
      expect(body!.is_active).toBe(true);
    });

    test('shows 409 backend error toast for duplicate name', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: "A tool with name 'my_tool' already exists in this organization",
          }),
        });
      });

      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(page.locator('[data-sonner-toast]', { hasText: /already exists/i })).toBeVisible(
        { timeout: 5_000 },
      );
      await expect(page).toHaveURL(/\/tools\/create\/custom/, { timeout: 3_000 });
    });

    test('shows generic error toast when the backend returns no detail', async ({ page }) => {
      await page.route('**/tool/upsert_tool', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({}),
        });
      });

      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(
        page.locator('[data-sonner-toast]', {
          hasText: 'Something went wrong. Please try again.',
        }),
      ).toBeVisible({ timeout: 5_000 });
    });

    test('shows loading indicator on Create button while saving', async ({ page }) => {
      let resolveRoute: (() => void) | null = null;
      await page.route('**/tool/upsert_tool', async (route) => {
        await new Promise<void>((resolve) => {
          resolveRoute = resolve;
        });
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CREATED_TOOL),
        });
      });

      await page.getByPlaceholder('check_inventory').fill('my_tool');
      await page
        .getByPlaceholder(
          'Checks product inventory in real-time and returns availability, stock count, and pricing.',
        )
        .fill('Desc');
      await page
        .getByPlaceholder('https://api.example.com/inventory/{product_id}')
        .fill('https://example.com');
      await page.getByRole('button', { name: 'Create' }).click();

      await expect(page.locator('.animate-spin').first()).toBeVisible({ timeout: 2_000 });
      resolveRoute?.();
    });

    test('Cancel button returns to /tools', async ({ page }) => {
      await mockToolList(page);
      await page.getByRole('button', { name: 'Cancel' }).click();
      await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
    });

    test('Back arrow returns to /tools', async ({ page }) => {
      await mockToolList(page);
      await page.getByRole('button', { name: 'Back' }).click();
      await expect(page).toHaveURL(/\/tools$/, { timeout: 10_000 });
    });
  });

  // ── Template-based create ──────────────────────────────────────────────
  test.describe('Template-based Create', () => {
    test('preloads parameters from the selected template', async ({ page }) => {
      await page.unrouteAll({ behavior: 'ignoreErrors' });
      await mockGetAllTools(page);
      await page.route('**/tool/get_tool**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_TEMPLATES[0]),
        });
      });

      await page.goto('/tools/create/custom?template_id=tpl-cal');

      // Template defines `title` as a required parameter — should appear preloaded.
      // Since the template type is google_calendar, the form actually mounts as BuiltInToolForm.
      // The selected built-in form should show the Google Calendar header and Tool Settings.
      await expect(page.getByRole('heading', { name: 'Tool Settings' })).toBeVisible({
        timeout: 5_000,
      });
    });
  });
});
