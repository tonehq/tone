'use client';

import { Plus } from 'lucide-react';
import { useMemo, useState } from 'react';

import CustomCredentialModal from '@/components/integrations/custom-credential-modal';
import { CustomButton, SearchableSelect, type SearchableSelectOption } from '@/components/shared';
import type { OAuthConnection } from '@/types/oauth';

/** Sentinel value for "no connection — the entity uses its own inline
 * credentials". Kept out of the outward-facing state, which uses ``null`` —
 * the ``<SearchableSelect>`` primitive only accepts string values. */
const NO_CONNECTION = '__no_connection__';

interface AttachmentOAuthPickerProps {
  /** Connection id currently set as the version-level override (from
   * ``agent_tools`` / ``agent_mcp_servers``). ``null`` means no override. */
  overrideConnectionId: string | null;
  /** Connection id set as the tool / MCP's default on its own edit page
   * (``tools.oauth_connection_id`` / ``mcp_servers.oauth_connection_id``).
   * Selecting it maps back to "no override" so untouched rows stay clean. */
  defaultConnectionId: string | null;
  /** Full connection list, loaded once by the parent. */
  connections: OAuthConnection[];
  disabled?: boolean;
  onChange: (nextConnectionId: string | null) => void;
  /** Called when a credential is created inline (via "Add credential") so the
   * parent can add it to the shared connection list — the picker then selects
   * it as this attachment's override. */
  onConnectionCreated?: (created: OAuthConnection) => void;
}

/** Compact connection picker rendered under each attached tool / MCP on the
 * agent config page. Lists **every** connection in the org — not just OAuth,
 * and not scoped to the entity's provider — so any stored credential (catalog
 * OAuth, custom bearer, OAuth2 client-credentials, generic MCP) can be swapped
 * onto this attachment for the current agent version. The list is shown once —
 * no separate "Use default" row — with the *effective* connection (override →
 * entity default) preselected. Picking the entity's default connection is
 * stored as ``null`` (no override), so runtime keeps following the Tool/MCP
 * page's default; picking any other connection is sent as the version-level
 * override.
 *
 * Entities without a default connection (e.g. bearer / api-key tools with
 * inline secrets) get an explicit "No connection" row so an override can be
 * cleared back to the inline credentials.
 */
export default function AttachmentOAuthPicker({
  overrideConnectionId,
  defaultConnectionId,
  connections,
  disabled,
  onChange,
  onConnectionCreated,
}: AttachmentOAuthPickerProps) {
  const [addOpen, setAddOpen] = useState(false);
  /** Human-readable label for one connection. Prefers the authorized account's
   * email (from ``public_metadata.user_email``) so the user can tell "which
   * account" at a glance, then falls back to the admin-set label or provider
   * slug. Mirrors the picker on the MCP / Tool edit pages so labels are
   * consistent across every OAuth surface. */
  const labelForConnection = (c: OAuthConnection): string =>
    `${c.public_metadata?.user_email || c.label || c.provider_slug} (${c.provider_slug})`;

  const options: SearchableSelectOption[] = useMemo(() => {
    // List every connection in the org, regardless of provider or auth type —
    // the user chooses which credential this attachment should use for the
    // current agent version. An in-flight OAuth handshake (``status ===
    // 'pending'``) isn't usable yet, so it's excluded, but the connection
    // currently in effect (override or default) is always kept visible below so
    // an existing selection can never silently disappear.
    let scoped = connections.filter((c) => c.public_metadata?.status !== 'pending');
    for (const id of [overrideConnectionId, defaultConnectionId]) {
      if (id && !scoped.some((c) => c.id === id)) {
        const current = connections.find((c) => c.id === id);
        if (current) scoped = [current, ...scoped];
      }
    }
    const rows = scoped.map<SearchableSelectOption>((c) => ({
      value: c.id,
      label: labelForConnection(c),
    }));
    if (!defaultConnectionId) {
      rows.unshift({ value: NO_CONNECTION, label: 'No connection (its own credentials)' });
    }
    return rows;
  }, [connections, defaultConnectionId, overrideConnectionId]);

  const effectiveId = overrideConnectionId ?? defaultConnectionId ?? null;

  // Only the "No connection" sentinel and no real connections yet — the select
  // would be noise, but the user can still create one inline, so we drop the
  // dropdown and keep just the "Add credential" action below.
  const hasRealOptions = options.some((o) => o.value !== NO_CONNECTION);

  return (
    <div className="mt-2 flex flex-col gap-1.5">
      {hasRealOptions && (
        <SearchableSelect
          name="oauth_override"
          label="Connection"
          options={options}
          value={effectiveId ?? NO_CONNECTION}
          onValueChange={(next) => {
            const id = next === NO_CONNECTION ? null : next;
            // Re-selecting the entity default = "no override" — keeps untouched
            // attachments following the Tool/MCP page's connection.
            onChange(id === defaultConnectionId ? null : id);
          }}
          placeholder="Select a connection"
          searchPlaceholder="Search connections..."
          disabled={disabled}
        />
      )}
      <CustomButton
        type="text"
        size="sm"
        icon={<Plus className="size-3.5" />}
        onClick={() => setAddOpen(true)}
        disabled={disabled}
        className="w-fit px-0 text-xs text-muted-foreground hover:text-foreground"
      >
        Add credential (API key / bearer token)
      </CustomButton>
      <CustomCredentialModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={(created) => {
          if (!created) return;
          // Surface the new credential to the shared list, then select it as
          // this attachment's override.
          onConnectionCreated?.(created);
          onChange(created.id);
        }}
      />
    </div>
  );
}
