import {
  deleteChannel as deleteChannelApi,
  listChannelPhoneNumbers,
  listChannels,
  upsertChannel as upsertChannelApi,
  type ChannelPhoneNumber,
} from '@/services/channelService';
import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import { atom } from 'jotai';

interface ChannelsState {
  items: Channel[];
  status: 'idle' | 'loading' | 'error';
  error: string | null;
  initialized: boolean;
}

const initialState: ChannelsState = {
  items: [],
  status: 'idle',
  error: null,
  initialized: false,
};

const channelsStateAtom = atom<ChannelsState>(initialState);

const channelsAtom = atom((get) => get(channelsStateAtom));

const fetchChannelsAtom = atom(null, async (get, set): Promise<void> => {
  const current = get(channelsStateAtom);
  if (current.status === 'loading') return;
  set(channelsStateAtom, { ...current, status: 'loading', error: null });
  try {
    const items = await listChannels();
    set(channelsStateAtom, {
      items,
      status: 'idle',
      error: null,
      initialized: true,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load channels';
    set(channelsStateAtom, { ...current, status: 'error', error: message });
    throw err;
  }
});

const upsertChannelAtom = atom(null, async (_get, set, payload: ChannelUpsertPayload) => {
  const result = await upsertChannelApi(payload);
  await set(fetchChannelsAtom);
  return result;
});

const deleteChannelAtom = atom(null, async (_get, set, channelId: string) => {
  await deleteChannelApi(channelId);
  await set(fetchChannelsAtom);
});

const resetChannelsAtom = atom(null, (_get, set) => {
  set(channelsStateAtom, initialState);
});

// ─── per-channel phone numbers (used by the agent form) ────────────────────

interface ChannelPhoneNumbersState {
  byChannelId: Record<string, ChannelPhoneNumber[]>;
  loadingChannelId: string | null;
}

const channelPhoneNumbersStateAtom = atom<ChannelPhoneNumbersState>({
  byChannelId: {},
  loadingChannelId: null,
});

const fetchChannelPhoneNumbersAtom = atom(
  null,
  async (_get, set, channelId: string): Promise<ChannelPhoneNumber[]> => {
    set(channelPhoneNumbersStateAtom, (prev) => ({ ...prev, loadingChannelId: channelId }));
    try {
      const items = await listChannelPhoneNumbers(channelId);
      set(channelPhoneNumbersStateAtom, (prev) => ({
        byChannelId: { ...prev.byChannelId, [channelId]: items },
        loadingChannelId: prev.loadingChannelId === channelId ? null : prev.loadingChannelId,
      }));
      return items;
    } catch (err) {
      set(channelPhoneNumbersStateAtom, (prev) => ({
        ...prev,
        loadingChannelId: prev.loadingChannelId === channelId ? null : prev.loadingChannelId,
      }));
      throw err;
    }
  },
);

export {
  channelPhoneNumbersStateAtom,
  channelsAtom,
  channelsStateAtom,
  deleteChannelAtom,
  fetchChannelPhoneNumbersAtom,
  fetchChannelsAtom,
  resetChannelsAtom,
  upsertChannelAtom,
};
export type { ChannelsState };
