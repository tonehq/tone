'use client';

import { useMemo } from 'react';

import { SearchableSelect, type SearchableSelectOption } from '@/components/shared';
import type { OAuthConnection } from '@/types/oauth';

/** Sentinel value for "no override — fall back to the tool/MCP default". Kept
 * out of the outward-facing state, which uses ``null`` for the same intent —
 * the ``<SearchableSelect>`` primitive only accepts string values. */
const USE_DEFAULT = '__use_default__';

interface AttachmentOAuthPickerProps {
  /** OAuth connection id currently set as the version-level override (from
   * ``agent_tools`` / ``agent_mcp_servers``). ``null`` means no override. */
  overrideConnectionId: string | null;
  /** OAuth connection id set as the tool / MCP's default on its own edit page
   * (``tools.oauth_connection_id`` / ``mcp_servers.oauth_connection_id``).
   * Rendered as the "Default" option so the user can tell which connection
   * runtime will fall back to. */
  defaultConnectionId: string | null;
  /** Full connection list, loaded once by the parent. */
  connections: OAuthConnection[];
  /** Optional catalog filter (``app_integration_id``) so only connections for
   * the same provider are shown — mirrors the picker on the Tool/MCP form. */
  appIntegrationId?: string | null;
  disabled?: boolean;
  onChange: (nextConnectionId: string | null) => void;
}

/** Compact OAuth-connection picker rendered under each attached tool / MCP on
 * the agent config page. The user can:
 *  - leave it on "Use default" — no override is sent, runtime uses the entity
 *    default,
 *  - pick a specific connection — that id is sent as the version-level
 *    override.
 *
 * The parent tracks the outgoing override state as
 * ``string | null`` (id or "no override"). This component converts to/from the
 * ``__use_default__`` sentinel required by the underlying select primitive.
 */
export default function AttachmentOAuthPicker({
  overrideConnectionId,
  defaultConnectionId,
  connections,
  appIntegrationId,
  disabled,
  onChange,
}: AttachmentOAuthPickerProps) {
  const defaultLabel = useMemo(() => {
    if (!defaultConnectionId) return null;
    const match = connections.find((c) => c.id === defaultConnectionId);
    return match?.label || match?.provider_slug || 'connected account';
  }, [connections, defaultConnectionId]);

  const options: SearchableSelectOption[] = useMemo(() => {
    const scoped = appIntegrationId
      ? connections.filter(
          (c) => !c.app_integration_id || c.app_integration_id === appIntegrationId,
        )
      : connections;
    const defaultOption: SearchableSelectOption = {
      value: USE_DEFAULT,
      label: defaultLabel
        ? `Use default (${defaultLabel})`
        : 'Use default (no connection configured on the tool)',
    };
    return [
      defaultOption,
      ...scoped.map<SearchableSelectOption>((c) => ({
        value: c.id,
        label: c.label || c.provider_slug,
      })),
    ];
  }, [appIntegrationId, connections, defaultLabel]);

  return (
    <div className="mt-2">
      <SearchableSelect
        name="oauth_override"
        label="OAuth connection"
        options={options}
        value={overrideConnectionId ?? USE_DEFAULT}
        onValueChange={(next) => onChange(next === USE_DEFAULT ? null : next)}
        placeholder="Use default"
        searchPlaceholder="Search connections..."
        disabled={disabled}
      />
    </div>
  );
}
