'use client';

import { useEffect, useState } from 'react';

import { listMcpServers } from '@/services/mcpServerService';
import { getAllTools } from '@/services/toolService';
import { pagedGetAllUsersForOrganization } from '@/services/userService';
import type { AuditLogResourceType } from '@/types/settings/auditLog';

// One shared shape for every lookup category. Kept intentionally minimal so
// the same Map type works whether the row came from tools, mcp, kb, etc.
export interface AuditLookups {
  loading: boolean;
  users: Map<string, string>;
  targets: Record<AuditLogResourceType, Map<string, string>>;
}

const EMPTY_TARGETS: Record<AuditLogResourceType, Map<string, string>> = {
  tool: new Map(),
  mcp_server: new Map(),
  knowledge_base: new Map(),
  phone_number: new Map(),
  web_channel: new Map(),
  agent_config: new Map(),
};

// Members endpoint is paginated — pull one large page so the audit page's
// actor column can hydrate names without a second fetch per row. 500 is
// generous enough for any real org; if we ever cross that we'll add cursoring.
const MEMBERS_PAGE_SIZE = 500;

function memberDisplayName(m: {
  first_name?: string | null;
  last_name?: string | null;
  username?: string | null;
  email?: string | null;
}): string {
  const full = `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim();
  if (full) return full;
  return m.username || m.email || '';
}

/**
 * Fetches every lookup list the audit-log renderer needs, once, and returns
 * hydration Maps keyed by resource UUID.
 *
 * A single hook (rather than N atoms) keeps the audit-log page self-contained
 * — nothing else in the app cares about "all users + all tools + all mcp in
 * one bundle". Uses local state, no atoms, no cache-busting: the page mounts,
 * fetches, and lives with what it got. If a resource is created mid-view its
 * name won't hydrate until the user reloads — an acceptable trade for the
 * simplicity, since the audit log is a review surface not a live console.
 */
export function useAuditLookups(): AuditLookups {
  const [state, setState] = useState<AuditLookups>({
    loading: true,
    users: new Map(),
    targets: EMPTY_TARGETS,
  });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      // Fire everything in parallel — none depends on the others. Each
      // sub-fetch is defensively wrapped so one 500 doesn't blank the page:
      // audit rows still render, just with UUIDs where the failed category
      // should have hydrated names.
      const [membersRes, toolsRes, mcpRes] = await Promise.allSettled([
        pagedGetAllUsersForOrganization({ page: 1, page_size: MEMBERS_PAGE_SIZE }),
        getAllTools(),
        listMcpServers({ page: 1, page_size: 500 }),
      ]);

      if (cancelled) return;

      const users = new Map<string, string>();
      if (membersRes.status === 'fulfilled') {
        for (const m of membersRes.value.rows) {
          if (m.user_id) users.set(m.user_id, memberDisplayName(m));
        }
      }

      const targets: Record<AuditLogResourceType, Map<string, string>> = {
        tool: new Map(),
        mcp_server: new Map(),
        knowledge_base: new Map(),
        phone_number: new Map(),
        web_channel: new Map(),
        agent_config: new Map(),
      };

      if (toolsRes.status === 'fulfilled') {
        for (const t of toolsRes.value) targets.tool.set(t.id, t.name);
      }
      if (mcpRes.status === 'fulfilled') {
        for (const s of mcpRes.value) targets.mcp_server.set(s.id, s.name);
      }

      setState({ loading: false, users, targets });
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
