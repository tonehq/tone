import { getCallMetrics } from '@/services/callMetricsService';
import type { CallMetricsQueryParams, CallMetricsRow, CallMetricsState } from '@/types/callMetrics';
import { atom } from 'jotai';

// Same in-flight-token pattern as AgentsAtom / ServicesAtom — drops responses
// that aren't the most recent dispatch so rapid search/page changes don't
// flash stale data into the table.
function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

const callMetricsAtom = atom<CallMetricsState>({
  rows: [],
  total: 0,
  loading: false,
});

const trackCallMetrics = makeLatestTracker();

export const fetchCallMetrics = atom(null, async (_get, set, params: CallMetricsQueryParams) => {
  const isLatest = trackCallMetrics();
  set(callMetricsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const res = await getCallMetrics(params);
    if (!isLatest()) return;
    set(callMetricsAtom, {
      rows: (res.data ?? []) as CallMetricsRow[],
      total: res.total ?? 0,
      loading: false,
    });
  } catch (err) {
    if (!isLatest()) return;
    set(callMetricsAtom, (prev) => ({ ...prev, loading: false }));
    throw err;
  }
});

export default callMetricsAtom;
