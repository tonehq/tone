'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import CheckboxField from '@/components/shared/CheckboxField';
import CustomButton from '@/components/shared/CustomButton';
import SelectInput from '@/components/shared/SelectInput';
import {
  useAgentProfileCrmConfig,
  useUpsertAgentProfileCrmConfig,
} from '@/lib/api/agentProfileCrmConfig';
import { discoverMcpTools, getMcpServersByAgent } from '@/services/mcpServerService';
import type { SelectOption } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/** Best-guess the contact-lookup tool from a server's tool names. */
function suggestTool(names: string[]): string | undefined {
  const match = names.find((n) =>
    /(search|find|lookup|get|query).*(contact|person|customer|lead)|(contact|person|customer|lead)/i.test(
      n,
    ),
  );
  return match ?? names[0];
}

/** Best-guess which tool argument carries the phone number. */
function suggestArg(args: string[]): string | undefined {
  return args.find((a) => /phone|mobile|tel|number|msisdn/i.test(a)) ?? args[0];
}

/**
 * Per-agent CRM lookup settings for filling EMPTY profile variables at call
 * start. Only meaningful once the agent exists (edit mode), so the drawer
 * renders it only when `agentId` is present. The chosen server, tool, and
 * phone argument are auto-suggested from the server's discovered tools and the
 * user confirms. Save enforcement (all fields required when enabled) is done
 * server-side; the error surfaces via `handleApiError`.
 */
export default function ProfileCrmConfigForm({ agentId }: { agentId: string }) {
  const { data: config, isLoading: configLoading } = useAgentProfileCrmConfig(agentId);
  const upsert = useUpsertAgentProfileCrmConfig(agentId);

  const { data: servers = [], isLoading: serversLoading } = useQuery({
    queryKey: ['agent-attached-mcp-servers', agentId],
    queryFn: () => getMcpServersByAgent(agentId),
    staleTime: 60_000,
  });

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
  const toolOptions: SelectOption[] = tools.map((t) => ({ value: t.name, label: t.name }));
  const argOptions: SelectOption[] = selectedTool
    ? Object.keys(selectedTool.parameters ?? {}).map((k) => ({ value: k, label: k }))
    : [];

  // Auto-suggest the lookup tool once the server's tools arrive.
  useEffect(() => {
    if (!tools.length || toolName) return;
    const s = suggestTool(tools.map((t) => t.name));
    if (s) setToolName(s);
  }, [tools, toolName]);

  // Auto-suggest the phone argument once a tool is selected.
  useEffect(() => {
    if (!selectedTool || phoneArg) return;
    const s = suggestArg(Object.keys(selectedTool.parameters ?? {}));
    if (s) setPhoneArg(s);
  }, [selectedTool, phoneArg]);

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
    try {
      await upsert.mutateAsync({
        mcp_server_id: serverId || null,
        lookup_tool_name: toolName || null,
        phone_argument: phoneArg || null,
        is_enabled: enabled,
      });
      showToast.success('CRM lookup settings saved.');
    } catch (err) {
      handleApiError(err);
    }
  };

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
              toolsError
                ? "Couldn't load this server's tools — check its connection."
                : 'Auto-suggested from the server; change if needed.'
            }
          />
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
