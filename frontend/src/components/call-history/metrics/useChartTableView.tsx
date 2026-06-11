'use client';

import React, { useState } from 'react';

import { ChartTableToggle, type MetricView } from './ChartTableToggle';

interface UseChartTableViewResult {
  view: MetricView;
  setView: (next: MetricView) => void;
  /** Pre-rendered toggle bound to this hook's state — drop into any header. */
  toggle: React.ReactNode;
}

/**
 * State + UI bundle for a chart/table toggle. Each section uses this hook so
 * the local view-state and toggle JSX are written in one line, keeping the
 * call-site free of repeated `useState` + `<ChartTableToggle>` boilerplate.
 */
export function useChartTableView(
  defaultView: MetricView = 'chart',
  label?: string,
): UseChartTableViewResult {
  const [view, setView] = useState<MetricView>(defaultView);
  const toggle = <ChartTableToggle view={view} onChange={setView} label={label} />;
  return { view, setView, toggle };
}
