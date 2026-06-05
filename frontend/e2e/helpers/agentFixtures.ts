/**
 * Real-backend fixtures for the agent e2e specs.
 *
 * Drives the actual UI (sign in already happened in the worker fixture)
 * because the app's Axios instance injects `Authorization: Bearer …` and
 * `tenant_id` headers from cookies — re-implementing that contract in test
 * code would drift. All fixtures here use the UI.
 *
 * Names are prefixed with `__e2e__` + timestamp so a sweep can pick up
 * orphans from aborted runs.
 */

import { expect, type Page } from '@playwright/test';

export const E2E_AGENT_PREFIX = '__e2e__';

export function uniqueAgentName(label: string): string {
  return `${E2E_AGENT_PREFIX}${label}-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

/**
 * Create an agent through the UI, return the new agent's UUID parsed from the
 * post-save redirect URL `/agents/edit/{type}/{id}`.
 */
export async function createAgentViaUI(
  page: Page,
  options: { agentType: 'inbound' | 'outbound'; name?: string },
): Promise<{ id: string; name: string }> {
  const name = options.name ?? uniqueAgentName(options.agentType);
  await page.goto(`/agents/create/${options.agentType}`);
  await page.locator('input[name="name"]').first().waitFor({ state: 'visible', timeout: 15_000 });
  await page.locator('input[name="name"]').first().fill(name);
  await page.getByRole('button', { name: /create agent/i }).click();
  await page.waitForURL(new RegExp(`/agents/edit/${options.agentType}/[\\w-]+`), {
    timeout: 20_000,
  });
  const match = page.url().match(/\/agents\/edit\/[^/]+\/([\w-]+)/);
  if (!match) throw new Error(`Could not parse agent id from URL: ${page.url()}`);
  return { id: match[1], name };
}

/**
 * Best-effort delete via the UI. Swallows errors so cleanup never tanks a
 * test that already passed.
 */
export async function deleteAgentViaUI(
  page: Page,
  options: { agentType: 'inbound' | 'outbound'; id: string },
): Promise<void> {
  try {
    await page.goto(`/agents/edit/${options.agentType}/${options.id}`);
    await page.waitForLoadState('networkidle', { timeout: 10_000 });
    if (!page.url().includes(`/agents/edit/${options.agentType}/${options.id}`)) return;
    const deleteButton = page.getByRole('button', { name: /^delete$/i });
    if (!(await deleteButton.isVisible().catch(() => false))) return;
    await deleteButton.click();
    await page.getByRole('dialog').getByRole('button', { name: 'Delete', exact: true }).click();
    await page.waitForURL(/\/agents(?:\?|$|\/)/, { timeout: 10_000 });
  } catch {
    expect.soft(true, `Failed to clean up agent ${options.id}`).toBe(true);
  }
}

export async function openEditAgent(
  page: Page,
  options: { agentType: 'inbound' | 'outbound'; id: string; nameContains?: string },
): Promise<void> {
  // Opening an agent lands on its Overview; step into Basics for callers that
  // expect the editable form fields.
  await page.goto(`/agents/edit/${options.agentType}/${options.id}`);
  if (options.nameContains) {
    await expect(page.getByText(options.nameContains).first()).toBeVisible({ timeout: 15_000 });
  } else {
    await goToStep(page, 'basics');
    await page.locator('input[name="name"]').first().waitFor({ state: 'visible', timeout: 15_000 });
  }
}

// ── Step navigation ─────────────────────────────────────────────────────────

export async function goToStep(
  page: Page,
  step: 'basics' | 'prompt' | 'ai' | 'voice' | 'tools' | 'knowledge',
): Promise<void> {
  const labelMap: Record<typeof step, RegExp> = {
    basics: /^basics$/i,
    prompt: /^prompt$/i,
    ai: /^ai$/i,
    voice: /^voice$/i,
    tools: /^tools & mcp$/i,
    knowledge: /^knowledge & phone$/i,
  };
  await page.getByText(labelMap[step], { exact: false }).first().click();
}

// ── SelectInput interaction ─────────────────────────────────────────────────

/**
 * Pick the first non-placeholder option from a shadcn SelectInput, returning
 * the selected option's visible text. Returns null if the dropdown has no
 * options (renders the "No data" popover instead).
 */
export async function pickFirstSelectOption(
  page: Page,
  trigger: ReturnType<Page['getByRole']> | ReturnType<Page['locator']>,
): Promise<string | null> {
  await trigger.click();
  // shadcn renders SelectContent in a portal at body root with role=listbox.
  const listbox = page.getByRole('listbox').first();
  const firstOption = listbox.getByRole('option').first();
  if (!(await firstOption.isVisible().catch(() => false))) {
    // Maybe popper rendered the empty-state Popover instead.
    await page.keyboard.press('Escape').catch(() => undefined);
    return null;
  }
  const label = (await firstOption.textContent())?.trim() ?? null;
  await firstOption.click();
  return label;
}

// ── Comprehensive step fillers ──────────────────────────────────────────────
// Each filler is best-effort: if the catalog is empty (no providers seeded,
// no tools, etc.) it logs a console note and continues. The test still
// asserts whatever was successfully filled.

export interface FillReport {
  description: boolean;
  firstMessage: boolean;
  endCallMessage: boolean;
  isActiveToggled: boolean;
  systemPrompt: boolean;
  tokenLimit: boolean;
  temperature: boolean;
  maxTokens: boolean;
  voiceSpeed: boolean;
  llmProvider: string | null;
  llmModel: string | null;
  voiceLanguage: string | null;
  voiceProvider: string | null;
  voiceModel: string | null;
  voiceVoice: string | null;
  sttProvider: string | null;
  sttModel: string | null;
  toolsPickedCount: number;
  toolPicked: string | null;
  mcpAttached: string | null;
  kbAttached: string | null;
  phoneAssigned: string | null;
}

/**
 * Move a Radix slider to a deterministic value by pressing Home (jump to min)
 * then ArrowRight `steps` times. Use when the slider's current value is
 * unknown (e.g. fresh form). Returns true if a slider thumb was found.
 */
export async function setSliderByKeyboard(
  page: Page,
  slider: ReturnType<Page['locator']>,
  steps: number,
): Promise<boolean> {
  if (!(await slider.isVisible({ timeout: 2_000 }).catch(() => false))) return false;
  await slider.focus().catch(() => undefined);
  await page.keyboard.press('Home');
  for (let i = 0; i < steps; i += 1) {
    await page.keyboard.press('ArrowRight');
  }
  return true;
}

export async function fillBasicsStep(
  page: Page,
  values: {
    description?: string;
    firstMessage?: string;
    endCallMessage?: string;
    toggleActive?: boolean;
  },
): Promise<
  Pick<FillReport, 'description' | 'firstMessage' | 'endCallMessage' | 'isActiveToggled'>
> {
  await goToStep(page, 'basics');
  const report = {
    description: false,
    firstMessage: false,
    endCallMessage: false,
    isActiveToggled: false,
  };
  if (values.description !== undefined) {
    await page.locator('textarea[name="description"]').first().fill(values.description);
    report.description = true;
  }
  if (values.firstMessage !== undefined) {
    const firstMsg = page.locator('textarea[placeholder*="Hi there"]').first();
    if (await firstMsg.isVisible().catch(() => false)) {
      await firstMsg.fill(values.firstMessage);
      report.firstMessage = true;
    }
  }
  if (values.endCallMessage !== undefined) {
    const endMsg = page.locator('textarea[placeholder*="Thanks for calling"]').first();
    if (await endMsg.isVisible().catch(() => false)) {
      await endMsg.fill(values.endCallMessage);
      report.endCallMessage = true;
    }
  }
  if (values.toggleActive) {
    const sw = page.getByRole('switch').first();
    if (await sw.isVisible().catch(() => false)) {
      await sw.click();
      report.isActiveToggled = true;
    }
  }
  return report;
}

export async function fillPromptStep(
  page: Page,
  values: { systemPrompt?: string },
): Promise<Pick<FillReport, 'systemPrompt'>> {
  await goToStep(page, 'prompt');
  const report = { systemPrompt: false };
  if (values.systemPrompt !== undefined) {
    const promptArea = page.locator('textarea').first();
    if (await promptArea.isVisible().catch(() => false)) {
      await promptArea.fill(values.systemPrompt);
      report.systemPrompt = true;
    }
  }
  return report;
}

export async function fillAiStep(
  page: Page,
  values?: { maxTokens?: number; tokenLimit?: number; temperatureSteps?: number },
): Promise<
  Pick<FillReport, 'llmProvider' | 'llmModel' | 'temperature' | 'maxTokens' | 'tokenLimit'>
> {
  await goToStep(page, 'ai');
  const providerTrigger = page
    .locator(
      'button[id="config.llm_settings.provider_id"], button:has-text("Select an LLM provider")',
    )
    .first();
  let llmProvider: string | null = null;
  if (await providerTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    llmProvider = await pickFirstSelectOption(page, providerTrigger);
    // Give the dependent Model dropdown + LLM-settings panel a moment to mount.
    await page.waitForTimeout(500);
  } else {
    console.log('[fillAiStep] LLM provider trigger not found');
  }
  let llmModel: string | null = null;
  const modelTrigger = page
    .locator('button[id="config.llm_settings.model_id"], button:has-text("Select a model")')
    .first();
  if (await modelTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    llmModel = await pickFirstSelectOption(page, modelTrigger);
  }
  // Temperature slider is only visible once a provider is picked.
  let temperature = false;
  if (llmProvider) {
    const tempSlider = page.locator('[role="slider"]').first();
    temperature = await setSliderByKeyboard(page, tempSlider, values?.temperatureSteps ?? 7);
  }
  // Max tokens — number input next to "Max tokens per response" label.
  let maxTokens = false;
  if (values?.maxTokens !== undefined) {
    const maxTokensInput = page.locator('input[name="config.llm_settings.max_tokens"]').first();
    if (await maxTokensInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await maxTokensInput.fill(String(values.maxTokens));
      maxTokens = true;
    }
  }
  // Conversation history token limit lives on this step (not Prompt).
  let tokenLimit = false;
  if (values?.tokenLimit !== undefined) {
    const tokenInput = page
      .locator('input[name="config.conversation_history_token_limit"]')
      .first();
    if (await tokenInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await tokenInput.fill(String(values.tokenLimit));
      tokenLimit = true;
    }
  }
  return { llmProvider, llmModel, temperature, maxTokens, tokenLimit };
}

export async function fillVoiceStep(
  page: Page,
): Promise<
  Pick<
    FillReport,
    | 'voiceLanguage'
    | 'voiceProvider'
    | 'voiceModel'
    | 'voiceVoice'
    | 'sttProvider'
    | 'sttModel'
    | 'voiceSpeed'
  >
> {
  await goToStep(page, 'voice');
  const langTrigger = page
    .locator('button[id="voice_language"], button:has-text("Select a language")')
    .first();
  let voiceLanguage: string | null = null;
  if (await langTrigger.isVisible({ timeout: 5_000 }).catch(() => false)) {
    voiceLanguage = await pickFirstSelectOption(page, langTrigger);
    await page.waitForTimeout(500);
  }
  let voiceProvider: string | null = null;
  const provTrigger = page
    .locator('button[id="voice_provider"], button:has-text("Select a provider")')
    .first();
  if (await provTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    voiceProvider = await pickFirstSelectOption(page, provTrigger);
    await page.waitForTimeout(500);
  }
  let voiceModel: string | null = null;
  const modelTrigger = page.locator('button[id="voice_model"]').first();
  if (await modelTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    voiceModel = await pickFirstSelectOption(page, modelTrigger);
  }
  // Voice picker is a SearchableSelect — click it, then pick first row.
  let voiceVoice: string | null = null;
  const voiceTrigger = page.locator('button[id="voice_id"]').first();
  if (await voiceTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    voiceVoice = await pickFirstSelectOption(page, voiceTrigger);
  }
  // STT provider/model
  let sttProvider: string | null = null;
  const sttProvTrigger = page.locator('button[id="config.stt_settings.provider_id"]').first();
  if (await sttProvTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    sttProvider = await pickFirstSelectOption(page, sttProvTrigger);
    await page.waitForTimeout(500);
  }
  let sttModel: string | null = null;
  const sttModelTrigger = page.locator('button[id="config.stt_settings.model"]').first();
  if (await sttModelTrigger.isVisible({ timeout: 3_000 }).catch(() => false)) {
    sttModel = await pickFirstSelectOption(page, sttModelTrigger);
  }
  // Voice speed slider only appears once a voice is picked. min=0.5 max=2 step=0.05,
  // so 10 right-arrow presses from min lands on 1.0 (a natural-sounding default).
  let voiceSpeed = false;
  if (voiceVoice) {
    const speedSlider = page.locator('[role="slider"]').first();
    voiceSpeed = await setSliderByKeyboard(page, speedSlider, 10);
  }
  return {
    voiceLanguage,
    voiceProvider,
    voiceModel,
    voiceVoice,
    sttProvider,
    sttModel,
    voiceSpeed,
  };
}

export async function pickFirstTool(page: Page): Promise<Pick<FillReport, 'toolPicked'>> {
  await goToStep(page, 'tools');
  // Tool tiles are CustomButtons with title attribute = tool name.
  const tile = page.locator('button[title]:not([title=""]):has(svg)').first();
  if (!(await tile.isVisible({ timeout: 3_000 }).catch(() => false))) {
    return { toolPicked: null };
  }
  const toolName = await tile.getAttribute('title');
  await tile.click();
  return { toolPicked: toolName };
}

/**
 * Toggle every visible tool tile so the agent ends up bound to as many tools
 * as the catalog has available. Returns how many were clicked.
 */
export async function pickAllTools(
  page: Page,
): Promise<Pick<FillReport, 'toolsPickedCount' | 'toolPicked'>> {
  await goToStep(page, 'tools');
  const tiles = page.locator('button[title]:not([title=""]):has(svg)');
  const count = await tiles.count().catch(() => 0);
  if (count === 0) return { toolsPickedCount: 0, toolPicked: null };
  let firstName: string | null = null;
  for (let i = 0; i < count; i += 1) {
    const tile = tiles.nth(i);
    if (!(await tile.isVisible().catch(() => false))) continue;
    if (i === 0) firstName = await tile.getAttribute('title');
    await tile.click().catch(() => undefined);
  }
  return { toolsPickedCount: count, toolPicked: firstName };
}

export async function attachFirstMcpServer(page: Page): Promise<Pick<FillReport, 'mcpAttached'>> {
  await goToStep(page, 'tools');
  const addTrigger = page.locator('button[id="add_mcp_server"]').first();
  if (!(await addTrigger.isVisible({ timeout: 3_000 }).catch(() => false))) {
    return { mcpAttached: null };
  }
  const picked = await pickFirstSelectOption(page, addTrigger);
  return { mcpAttached: picked };
}

export async function pickFirstKbDoc(page: Page): Promise<Pick<FillReport, 'kbAttached'>> {
  await goToStep(page, 'knowledge');
  const tile = page.locator('button[title]:not([title=""]):has(span:has-text("KB"))').first();
  const fallback = page
    .locator('button:has(svg):has-text(".pdf"), button:has(svg):has-text(".txt")')
    .first();
  const target = (await tile.isVisible({ timeout: 2_000 }).catch(() => false)) ? tile : fallback;
  if (!(await target.isVisible({ timeout: 3_000 }).catch(() => false))) {
    return { kbAttached: null };
  }
  const name = (await target.getAttribute('title')) ?? (await target.textContent());
  await target.click();
  return { kbAttached: name?.trim() ?? null };
}

export async function assignFirstPhoneNumber(
  page: Page,
): Promise<Pick<FillReport, 'phoneAssigned'>> {
  await goToStep(page, 'knowledge');
  const openBtn = page.getByRole('button', { name: /assign number|manage numbers/i }).first();
  if (!(await openBtn.isVisible({ timeout: 3_000 }).catch(() => false))) {
    return { phoneAssigned: null };
  }
  if (await openBtn.isDisabled().catch(() => false)) {
    console.log('[assignFirstPhoneNumber] Assign Number is disabled — no channels.');
    return { phoneAssigned: null };
  }
  await openBtn.click();
  // Modal: pick first provider, first channel, first number.
  const provTrig = page.locator('button[id="assign_service_provider"]').first();
  await pickFirstSelectOption(page, provTrig).catch(() => null);
  const chTrig = page.locator('button[id="assign_channel"]').first();
  await pickFirstSelectOption(page, chTrig).catch(() => null);
  // Number list rows are <li> with a "+digits" pattern.
  const firstNumber = page.getByRole('dialog').locator('li button:not([disabled])').first();
  if (!(await firstNumber.isVisible({ timeout: 3_000 }).catch(() => false))) {
    await page.keyboard.press('Escape').catch(() => undefined);
    return { phoneAssigned: null };
  }
  const text = await firstNumber.textContent();
  await firstNumber.click();
  await page.getByRole('button', { name: /^assign/i }).click();
  return { phoneAssigned: text?.trim() ?? null };
}
