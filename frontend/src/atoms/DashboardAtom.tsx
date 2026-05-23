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

// In-flight de-dupe — guards against React 19 Strict Mode's intentional
// double-mount (and any parent re-render that calls the setter twice) so we
// only fire one network request per mount cycle. The shared promise is
// awaited by any concurrent callers so they all observe the same result.
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
