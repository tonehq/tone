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

export const fetchDashboardStatsAtom = atom(null, async (_get, set) => {
  set(dashboardAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const stats = await getDashboardStats();
    set(dashboardAtom, { stats, loading: false });
  } catch (error) {
    set(dashboardAtom, (prev) => ({ ...prev, loading: false }));
    handleApiError(error);
  }
});

export default dashboardAtom;
