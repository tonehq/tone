import { useQuery } from '@tanstack/react-query';

import {
  getChannel,
  listChannelPhoneNumbers,
  listChannels,
  listTelnyxPhoneNumbers,
  listTwilioPhoneNumbers,
} from '@/services/channelService';
import type { ChannelPhoneNumber } from '@/services/channelService';
import type { Channel } from '@/types/integration';

export const channelKeys = {
  all: () => ['channels'] as const,
  detail: (id: string, includeConfig: boolean) =>
    ['channels', 'detail', id, includeConfig] as const,
  phoneNumbers: (channelId: string, providerType: string) =>
    ['channels', 'phone-numbers', channelId, providerType] as const,
};

/**
 * A single channel, optionally including its decrypted config. Only fetches
 * when an id is provided (mirrors useSipTrunk). Used by the channel form modal
 * to hydrate RHF instead of loading into local state via useEffect.
 */
export function useChannel(
  channelId: string | null | undefined,
  includeConfig = false,
  options?: { enabled?: boolean },
) {
  return useQuery<Channel>({
    queryKey: channelKeys.detail(channelId ?? '', includeConfig),
    queryFn: () => getChannel(channelId as string, includeConfig),
    enabled: (options?.enabled ?? true) && !!channelId,
  });
}

/**
 * The org's channels. A static-per-session lookup used by the agent Channels
 * step, so it lives in TanStack Query instead of a `useState` + `useEffect`
 * fetch.
 */
export function useChannels() {
  return useQuery<Channel[]>({
    queryKey: channelKeys.all(),
    queryFn: () => listChannels(),
  });
}

/**
 * Phone numbers available on a channel. The provider decides which endpoint
 * serves them (Twilio / Telnyx / generic), so the provider type is part of the
 * cache key. Only fetches once a channel is selected.
 */
export function useChannelPhoneNumbers(
  channelId: string | null | undefined,
  providerType: string | null | undefined,
  options?: { enabled?: boolean },
) {
  return useQuery<ChannelPhoneNumber[]>({
    queryKey: channelKeys.phoneNumbers(channelId ?? '', providerType ?? ''),
    queryFn: () => {
      const fetcher =
        providerType === 'twilio'
          ? listTwilioPhoneNumbers
          : providerType === 'telnyx'
            ? listTelnyxPhoneNumbers
            : listChannelPhoneNumbers;
      return fetcher(channelId as string);
    },
    enabled: (options?.enabled ?? true) && !!channelId,
  });
}
