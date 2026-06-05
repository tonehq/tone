'use client';

import { createContext, useContext } from 'react';

import type { AgentDetail, AgentDirection } from '@/types/agent';

interface AgentEditorContextValue {
  /** Full saved agent (null in create mode or before the first load). */
  detail: AgentDetail | null;
  agentId: string | null;
  agentType: AgentDirection;
  /** Persist the active flag immediately (Overview toggle). */
  setActive: (active: boolean) => Promise<void>;
}

const AgentEditorContext = createContext<AgentEditorContextValue | null>(null);

export const AgentEditorProvider = AgentEditorContext.Provider;

export function useAgentEditor(): AgentEditorContextValue {
  const ctx = useContext(AgentEditorContext);
  if (!ctx) {
    throw new Error('useAgentEditor must be used within an AgentEditorProvider');
  }
  return ctx;
}
