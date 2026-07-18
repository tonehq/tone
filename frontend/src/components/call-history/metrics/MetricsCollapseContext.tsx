'use client';

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

interface MetricsCollapseContextValue {
  expandAllSignal: number;
  collapseAllSignal: number;
  expandAll: () => void;
  collapseAll: () => void;
}

const MetricsCollapseContext = createContext<MetricsCollapseContextValue | null>(null);

interface MetricsCollapseProviderProps {
  children: React.ReactNode;
}

export function MetricsCollapseProvider({ children }: MetricsCollapseProviderProps) {
  const [expandAllSignal, setExpandAllSignal] = useState(0);
  const [collapseAllSignal, setCollapseAllSignal] = useState(0);

  const expandAll = useCallback(() => setExpandAllSignal((n) => n + 1), []);
  const collapseAll = useCallback(() => setCollapseAllSignal((n) => n + 1), []);

  const value = useMemo(
    () => ({ expandAllSignal, collapseAllSignal, expandAll, collapseAll }),
    [expandAllSignal, collapseAllSignal, expandAll, collapseAll],
  );

  return (
    <MetricsCollapseContext.Provider value={value}>{children}</MetricsCollapseContext.Provider>
  );
}

export function useMetricsCollapse(): MetricsCollapseContextValue {
  const ctx = useContext(MetricsCollapseContext);
  if (!ctx) {
    throw new Error('useMetricsCollapse must be used inside <MetricsCollapseProvider>');
  }
  return ctx;
}
