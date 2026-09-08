'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import CheckboxField from '@/components/shared/CheckboxField';
import CustomButton from '@/components/shared/CustomButton';
import SelectInput from '@/components/shared/SelectInput';
import { getCrmLookupPreset } from '@/constants/crmLookupPresets';
import {
  useAgentProfileCrmConfig,
  useUpsertAgentProfileCrmConfig,
} from '@/lib/api/agentProfileCrmConfig';
import { useAppIntegrations } from '@/lib/api/appIntegrations';
import { discoverMcpTools, getMcpServersByAgent } from '@/services/mcpServerService';
import type { SelectOption } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/** Best-guess the contact-lookup tool from a server's tool names (generic MCPs). */
function suggestTool(names: string[]): string | undefined {
  const match = names.find((n) =>
    /(search|find|lookup|get|query).*(contact|person|customer|lead)|(contact|person|customer|lead)/i.test(
      n,
    ),
  );
  return match ?? names[0];
}

/** Best-guess which tool argument carries the phone number (generic MCPs). */
function suggestArg(args: string[]): string | undefined {
  return args.find((a) => /phone|mobile|tel|number|msisdn/i.test(a)) ?? args[0];
}

/**
 * Per-agent CRM lookup settings for filling EMPTY profile variables at call
 * start (edit mode only). For the three app-integrated CRMs (HubSpot /
 * Salesforce / Zoho) the lookup tool + phone request auto-fill from a preset
 * (see `@/constants/crmLookupPresets`); any other MCP keeps the generic
 * pick-tool + phone-argument flow. Server-side validation is the source of
 * truth; errors surface via `handleApiError`.
 */
export default function ProfileCrmConfigForm({ agentId }: { agentId: string }) {
  const { data: config, isLoading: configLoading } = useAgentProfileCrmConfig(agentId);
  const upsert = useUpsertAgentProfileCrmConfig(agentId);

  const { data: servers = [], isLoading: serversLoading } = useQuery({
    queryKey: ['agent-attached-mcp-servers', agentId],
    queryFn: () => getMcpServersByAgent(agentId),
    staleTime: 60_000,
  });
  const { data: integrations = [] } = useAppIntegrations({ page_size: 200 });

  const [enabled, setEnabled] = useState(false);
  const [serverId, setServerId] = useState('');
  const [toolName, setToolName] = useState('');
  const [phoneArg, setPhoneArg] = useState('');
  const [seeded, setSeeded] = useState(false);

  // Seed local state from the saved config once it loads.
  useEffect(() => {
    if (seeded || configLoading) return;
    setEnabled(config?.is_enabled ?? false);
    setServerId(config?.mcp_server_id ?? '');
    setToolName(config?.lookup_tool_name ?? '');
    setPhoneArg(config?.phone_argument ?? '');
    setSeeded(true);
  }, [seeded, configLoading, config]);

  // Which app-integrated CRM (if any) the selected server maps to → its preset.
  const slugById = useMemo(
    () => Object.fromEntries(integrations.map((i) => [i.id, i.slug])),
    [integrations],
  );
  const selectedServer = servers.find((s) => s.id === serverId);
  const selectedSlug = selectedServer?.app_integration_id
    ? slugById[selectedServer.app_integration_id]
    : undefined;
  const preset = getCrmLookupPreset(selectedSlug);

  const {
    data: toolsResp,
    isLoading: toolsLoading,
    isError: toolsError,
  } = useQuery({
    queryKey: ['mcp-discover-tools', serverId],
    queryFn: () => discoverMcpTools(serverId),
    enabled: !!serverId,
    staleTime: 60_000,
    retry: false,
  });
  const tools = toolsResp?.tools ?? [];
  const selectedTool = tools.find((t) => t.name === toolName);

  const serverOptions: SelectOption[] = servers.map((s) => ({ value: s.id, label: s.name }));
  // Ensure a preset's tool is selectable even if discovery hasn't surfaced that
  // exact name (the tool stays editable per the design).
  const toolOptions: SelectOption[] = useMemo(() => {
    const opts = tools.map((t) => ({ value: t.name, label: t.name }));
    if (preset && !opts.some((o) => o.value === preset.toolName)) {
      return [{ value: preset.toolName, label: preset.toolName }, ...opts];
    }
    return opts;
  }, [tools, preset]);
  const argOptions: SelectOption[] = selectedTool
    ? Object.keys(selectedTool.parameters ?? {}).map((k) => ({ value: k, label: k }))
    : [];

  // Preset CRM → pre-fill the tool. Generic MCP → regex-suggest the tool.
  useEffect(() => {
    if (toolName) return;
    if (preset) {
      setToolName(preset.toolName);
      return;
    }
    if (!tools.length) return;
    const s = suggestTool(tools.map((t) => t.name));
    if (s) setToolName(s);
  }, [preset, tools, toolName]);

  // Generic MCP only → suggest the phone argument (preset CRMs handle phone via
  // the preset, no per-arg pick).
  useEffect(() => {
    if (preset || !selectedTool || phoneArg) return;
    const s = suggestArg(Object.keys(selectedTool.parameters ?? {}));
    if (s) setPhoneArg(s);
  }, [preset, selectedTool, phoneArg]);

  const onServerChange = (v: string) => {
    setServerId(v);
    setToolName('');
    setPhoneArg('');
  };
  const onToolChange = (v: string) => {
    setToolName(v);
    setPhoneArg('');
  };
  const save = async () => {
    // For a preset CRM the phone is placed by the backend preset; store the
    // single-arg name for Zoho, nothing for filter/SOQL CRMs.
    const savedPhoneArg = preset
      ? preset.phonePlacement === 'single-arg'
        ? (preset.phoneArg ?? null)
        : null
      : phoneArg || null;
    try {
      await upsert.mutateAsync({
        mcp_server_id: serverId || null,
        lookup_tool_name: toolName || null,
        phone_argument: savedPhoneArg,
        is_enabled: enabled,
      });
      showToast.success('CRM lookup settings saved.');
    } catch (err) {
      handleApiError(err);
    }
  };

  const presetPhoneNote = preset
    ? preset.phonePlacement === 'single-arg'
      ? `Phone is sent automatically as the "${preset.phoneArg}" argument for this CRM.`
      : 'Phone is sent automatically in this CRM’s required request shape.'
    : null;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border p-3">
      <div>
        <p className="text-sm font-medium">Fill empty variables from a CRM</p>
        <p className="text-xs text-muted-foreground">
          When on, any variable left empty that has a CRM field is filled from the caller&apos;s CRM
          record at call start (matched by phone). Unmatched callers fall back to the default/blank.
        </p>
      </div>

      <CheckboxField
        id="crm_enabled"
        label="Enable CRM enrichment"
        checked={enabled}
        onCheckedChange={(c) => setEnabled(!!c)}
        disabled={upsert.isPending || !seeded}
      />

      {enabled && (
        <>
          <SelectInput
            name="crm_server"
            label="CRM server"
            placeholder={serversLoading ? 'Loading…' : 'Select a connected CRM'}
            options={serverOptions}
            value={serverId}
            onValueChange={onServerChange}
            loading={serversLoading}
            disabled={upsert.isPending}
            helperText={
              !serversLoading && serverOptions.length === 0
                ? 'No MCP servers are attached to this agent — attach one in the Tools / MCP step first.'
                : undefined
            }
          />
          <SelectInput
            name="crm_tool"
            label="Lookup tool"
            placeholder={toolsLoading ? 'Discovering tools…' : 'Select the contact-lookup tool'}
            options={toolOptions}
            value={toolName}
            onValueChange={onToolChange}
            loading={toolsLoading}
            disabled={!serverId || upsert.isPending}
            error={toolsError}
            helperText={
              preset
                ? 'Auto-selected for this CRM; change only if your server differs.'
                : toolsError
                  ? "Couldn't load this server's tools — check its connection."
                  : 'Auto-suggested from the server; change if needed.'
            }
          />
          {preset ? (
            <p className="text-xs text-muted-foreground">{presetPhoneNote}</p>
          ) : (
            <SelectInput
              name="crm_phone_arg"
              label="Phone argument"
              placeholder="Which tool input receives the phone"
              options={argOptions}
              value={phoneArg}
              onValueChange={setPhoneArg}
              disabled={!selectedTool || upsert.isPending}
              helperText="The caller's phone number is passed to the tool as this argument."
            />
          )}
        </>
      )}

      <div className="flex justify-end">
        <CustomButton
          type="primary"
          size="sm"
          onClick={save}
          loading={upsert.isPending}
          disabled={upsert.isPending || !seeded}
        >
          Save CRM settings
        </CustomButton>
      </div>
    </div>
  );
}
