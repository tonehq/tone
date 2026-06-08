import { getCallFacets, getCallLogs } from '@/services/callLogService';
import type {
  CallFacetsParams,
  CallFacetsState,
  CallLogQueryParams,
  CallLogRow,
  CallLogsState,
} from '@/types/callLog';
import { atom } from 'jotai';

const callLogsAtom = atom<CallLogsState>({
  callLogs: [],
  total: 0,
  loading: false,
});

export const callFacetsAtom = atom<CallFacetsState>({
  facets: {},
  loading: false,
});

export const fetchCallFacets = atom(null, async (_get, set, params: CallFacetsParams) => {
  set(callFacetsAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const facets = await getCallFacets(params);
    set(callFacetsAtom, { facets: facets ?? {}, loading: false });
  } catch (err) {
    set(callFacetsAtom, (prev) => ({ ...prev, loading: false }));
    throw err;
  }
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
