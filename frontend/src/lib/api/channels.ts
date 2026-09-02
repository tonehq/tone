import { useQuery } from '@tanstack/react-query';

import { getChannel } from '@/services/channelService';
import type { Channel } from '@/types/integration';

export const channelKeys = {
  all: () => ['channels'] as const,
  detail: (id: string, includeConfig: boolean) =>
    ['channels', 'detail', id, includeConfig] as const,
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
