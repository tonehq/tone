/**
 * Per-CRM lookup presets for the app-integrated CRMs. When a user selects one
 * of these CRM servers in the profile-variable CRM config, the lookup tool +
 * how the caller phone is sent auto-fill (the backend mirrors this in
 * `core/services/agents/crm_lookup_presets/`). Any other/custom MCP has no
 * preset → the generic pick-tool + phone-argument flow.
 *
 * Keyed by `app_integrations.slug`.
 */
export type CrmPhonePlacement = 'single-arg' | 'filter' | 'soql';

export interface CrmLookupPreset {
  /** Lookup tool name to pre-fill (editable — the user's MCP may differ). */
  toolName: string;
  /** How the phone is sent — drives whether the "phone argument" field shows. */
  phonePlacement: CrmPhonePlacement;
  /** For `single-arg` only: which tool argument the phone goes into. */
  phoneArg?: string;
}

export type CrmPresetSlug = 'hubspot' | 'salesforce' | 'zoho_crm';

// Tool names kept in sync with the backend presets
// (core/services/agents/crm_lookup_presets/). The backend resolves the real
// tool name against the server's discovered tools at call time, so these are
// the pre-fill / display values.
export const CRM_LOOKUP_PRESETS: Record<CrmPresetSlug, CrmLookupPreset> = {
  zoho_crm: { toolName: 'search_records', phonePlacement: 'single-arg', phoneArg: 'phone' },
  hubspot: { toolName: 'hubspot-search-objects', phonePlacement: 'filter' },
  salesforce: { toolName: 'run_soql_query', phonePlacement: 'soql' },
};

export function getCrmLookupPreset(slug: string | null | undefined): CrmLookupPreset | undefined {
  if (!slug) return undefined;
  return CRM_LOOKUP_PRESETS[slug as CrmPresetSlug];
}
