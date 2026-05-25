import {
  deleteChannel as deleteChannelApi,
  listChannels,
  upsertChannel as upsertChannelApi,
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

export {
  channelsAtom,
  channelsStateAtom,
  deleteChannelAtom,
  fetchChannelsAtom,
  resetChannelsAtom,
  upsertChannelAtom,
};
export type { ChannelsState };
