'use client';

import { useRouter } from 'next/navigation';
import { createContext, useContext } from 'react';

interface AgentFormNavValue {
  /** Navigate to `href` while honouring the parent form's unsaved-changes
   * guard. Steps must use this instead of `router.push` for any outbound
   * navigation (e.g. "New tool", "New MCP server"). */
  safeNavigate: (href: string) => void;
}

const AgentFormNavContext = createContext<AgentFormNavValue | null>(null);

export const AgentFormNavProvider = AgentFormNavContext.Provider;

/**
 * Returns `safeNavigate`. When called outside the agent form (e.g. for unit
 * tests), it falls back to plain `router.push` so the caller still works.
 */
export function useAgentFormNav(): AgentFormNavValue {
  const ctx = useContext(AgentFormNavContext);
  const router = useRouter();
  if (ctx) return ctx;
  return { safeNavigate: (href: string) => router.push(href) };
}
