import isEqual from 'lodash/isEqual';

import type { AgentFormState } from '@/types/agent';
import type { ReadinessCategory } from '@/types/readiness';

/**
 * Given the previously-saved form state and the just-saved form state, return
 * the set of readiness categories whose deep probes should be re-run.
 *
 * Used by the save flow to drive a **targeted deep** readiness check — the
 * backend runs live probes only for the resources the user actually touched,
 * keeping shallow-fast save UX for prompt-only edits while catching broken
 * URLs / invalid keys / unreachable MCP servers immediately when they change.
 *
 * Categories map 1:1 to `ReadinessCategory` values on the backend. Fields the
 * form doesn't own (e.g. workflow-graph structural checks) don't participate.
 */
export function categoriesToProbeOnSave(
  prev: AgentFormState,
  next: AgentFormState,
): ReadinessCategory[] {
  const changed = new Set<ReadinessCategory>();

  const prevCfg = prev.config;
  const nextCfg = next.config;

  // Agent-level content (prompt / workflow attach / mode / language) — any of
  // these change the AGENT-category shallow checks (prompt-or-workflow,
  // workflow validity). Language changes also cascade into STT/TTS
  // model-language and TTS voice-language checks, so we add those too.
  if (
    prevCfg.mode !== nextCfg.mode ||
    prevCfg.system_prompt_template !== nextCfg.system_prompt_template ||
    prevCfg.workflow_id !== nextCfg.workflow_id
  ) {
    changed.add('agent');
  }
  if (prevCfg.language_id !== nextCfg.language_id) {
    changed.add('agent');
    changed.add('stt');
    changed.add('tts');
  }
  // KB embedding checks now read from the KB's own ingestion run (not the
  // agent's knowledge_model_id), so a change to that agent-level field
  // doesn't need to re-probe KB deep checks. The upload/attachment diff
  // below still covers real KB attach/detach changes.

  if (!isEqual(prevCfg.llm_settings, nextCfg.llm_settings)) changed.add('llm');
  if (!isEqual(prevCfg.stt_settings, nextCfg.stt_settings)) changed.add('stt');
  if (!isEqual(prevCfg.voice_settings, nextCfg.voice_settings)) changed.add('tts');

  // Attachments — set membership OR per-attachment OAuth override edits both
  // count as "tools/mcp changed" because either alters what the live probe
  // would actually authenticate against.
  if (
    !isEqual(prev.tool_ids, next.tool_ids) ||
    !isEqual(prev.tool_oauth_overrides, next.tool_oauth_overrides)
  ) {
    changed.add('tools');
  }
  if (
    !isEqual(prev.mcp_server_ids, next.mcp_server_ids) ||
    !isEqual(prev.mcp_server_oauth_overrides, next.mcp_server_oauth_overrides)
  ) {
    changed.add('mcp_servers');
  }
  if (!isEqual(prev.upload_ids, next.upload_ids)) changed.add('knowledge_bases');
  // Phone-number changes also affect telephony-account credit probe (transport).
  if (!isEqual(prev.phone_numbers, next.phone_numbers)) {
    changed.add('phone');
    changed.add('transport');
  }

  return Array.from(changed);
}
