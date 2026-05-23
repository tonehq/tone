import { getDashboardStats } from '@/services/dashboardService';
import type { DashboardStats } from '@/services/dashboardService';
import { handleApiError } from '@/utils/helpers';
import { atom } from 'jotai';

interface DashboardState {
  stats: DashboardStats | null;
  loading: boolean;
}

const dashboardAtom = atom<DashboardState>({
  stats: null,
  loading: false,
});

// Module-scoped in-flight de-dupe: every caller of fetchDashboardStatsAtom
// (Strict Mode double-mount, re-renders that re-invoke the setter, sibling
// components subscribed to the atom) shares the same promise while a request
// is in flight, and a fresh request only fires once the previous one settles.
let inFlight: Promise<void> | null = null;

export const fetchDashboardStatsAtom = atom(null, (_get, set) => {
  if (inFlight) return inFlight;
  set(dashboardAtom, (prev) => ({ ...prev, loading: true }));
  inFlight = (async () => {
    try {
      const stats = await getDashboardStats();
      set(dashboardAtom, { stats, loading: false });
    } catch (error) {
      set(dashboardAtom, (prev) => ({ ...prev, loading: false }));
      handleApiError(error);
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
});

export default dashboardAtom;
