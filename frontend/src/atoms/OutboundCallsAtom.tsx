import {
  cancelScheduledCall,
  cancelScheduledCalls,
  createOutboundCall,
  createOutboundCallFromFile,
  getScheduledCalls,
} from '@/services/outboundCallService';
import type {
  CreateOutboundCallPayload,
  ScheduledCallRow,
  ScheduledCallsQueryParams,
  ScheduledCallsState,
} from '@/types/outboundCall';
import { atom } from 'jotai';

const scheduledCallsAtom = atom<ScheduledCallsState>({
  rows: [],
  total: 0,
  loading: false,
});

export const fetchScheduledCalls = atom(
  null,
  async (_get, set, payload: { params: ScheduledCallsQueryParams; silent?: boolean }) => {
    const { params, silent } = payload;
    // Background polls pass silent=true so the table updates in place without
    // flashing the loading skeleton on every refresh.
    if (!silent) set(scheduledCallsAtom, (prev) => ({ ...prev, loading: true }));
    try {
      const res = await getScheduledCalls(params);
      set(scheduledCallsAtom, {
        rows: (res.data ?? []) as ScheduledCallRow[],
        total: res.total ?? 0,
        loading: false,
      });
    } catch (err) {
      set(scheduledCallsAtom, (prev) => ({ ...prev, loading: false }));
      throw err;
    }
  },
);

// Placing a call (immediate or scheduled). Components go through this atom.
export const createOutboundCallAtom = atom(
  null,
  async (_get, _set, payload: CreateOutboundCallPayload) => createOutboundCall(payload),
);

// Placing calls from an uploaded CSV/Excel — the file is parsed server-side.
export const createOutboundCallFromFileAtom = atom(null, async (_get, _set, formData: FormData) =>
  createOutboundCallFromFile(formData),
);

export const cancelScheduledCallAtom = atom(null, async (_get, _set, id: string) =>
  cancelScheduledCall(id),
);

export const cancelScheduledCallsAtom = atom(null, async (_get, _set, ids: string[]) =>
  cancelScheduledCalls(ids),
);

export default scheduledCallsAtom;
