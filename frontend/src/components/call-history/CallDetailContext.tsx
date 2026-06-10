'use client';

import type { CallLogRow } from '@/types/callLog';
import { createContext, useContext } from 'react';

interface CallDetailContextValue {
  callLog: CallLogRow | null;
  loading: boolean;
}

const CallDetailContext = createContext<CallDetailContextValue | null>(null);

export function CallDetailProvider({
  value,
  children,
}: {
  value: CallDetailContextValue;
  children: React.ReactNode;
}) {
  return <CallDetailContext.Provider value={value}>{children}</CallDetailContext.Provider>;
}

export function useCallDetail() {
  const ctx = useContext(CallDetailContext);
  if (!ctx) throw new Error('useCallDetail must be used within CallDetailProvider');
  return ctx;
}
