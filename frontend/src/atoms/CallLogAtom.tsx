import { getCallLogs } from '@/services/callLogService';
import type { CallLogQueryParams, CallLogRow, CallLogsState } from '@/types/callLog';
import { atom } from 'jotai';

const callLogsAtom = atom<CallLogsState>({
  callLogs: [],
  total: 0,
  loading: false,
});

export const fetchCallLogs = atom(null, async (_get, set, params: CallLogQueryParams) => {
  set(callLogsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const res = await getCallLogs(params);
    set(callLogsAtom, {
      callLogs: (res.data ?? []) as CallLogRow[],
      total: res.total ?? 0,
      loading: false,
    });
  } catch (err) {
    set(callLogsAtom, (prev) => ({ ...prev, loading: false }));
    throw err;
  }
});

export default callLogsAtom;
