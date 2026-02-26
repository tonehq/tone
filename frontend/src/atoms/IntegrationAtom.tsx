import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import { deleteChannel, getChannels, upsertChannel } from '@/services/channelService';
import dayjs from 'dayjs';

export interface IntegrationRow {
  id: number;
  name: string;
  auth_token: string;
  account_sid: string;
  createdAt: string;
}

interface TwilioMetaData {
  account_sid: string;
  auth_token: string;
}

const channelsRefreshAtom = atom(0);

const channelsRowsAtom = atom<Promise<IntegrationRow[]>>(async (get) => {
  get(channelsRefreshAtom);
  const apiData = await getChannels();
  return apiData.map((row: any) => ({
    id: row.id,
    name: row.name,
    auth_token: row.meta_data.auth_token ?? '••••••••',
    account_sid: row.meta_data.account_sid ?? '',
    createdAt: row.created_at ? dayjs.unix(Number(row.created_at)).format('DD-MM-YYYY HH:mm:ss') : '-',
  }));
});

const loadableChannelsAtom = loadable(channelsRowsAtom);

// Action: refresh channel list
const refetchChannelsAtom = atom(null, (_get, set) => {
  set(channelsRefreshAtom, (c) => c + 1);
});

// Action: create or update a channel, then refresh
const upsertChannelAtom = atom(
  null,
  async (
    _get,
    set,
    payload: { id?: number; name: string; type: 'TWILIO'; meta_data: TwilioMetaData },
  ) => {
    await upsertChannel(payload);
    set(channelsRefreshAtom, (c) => c + 1);
  },
);

// Action: delete a channel, then refresh
const deleteChannelAtom = atom(null, async (_get, set, channelId: number) => {
  await deleteChannel(channelId);
  set(channelsRefreshAtom, (c) => c + 1);
});

export { deleteChannelAtom, loadableChannelsAtom, refetchChannelsAtom, upsertChannelAtom };
