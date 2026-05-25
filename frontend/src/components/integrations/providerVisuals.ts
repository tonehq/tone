import {
  API_KEY_PROVIDERS,
  OAUTH_PROVIDERS,
  type ProviderCardConfig,
} from '@/constants/integrations';

const byKey = (list: ProviderCardConfig[]) =>
  list.reduce<Record<string, ProviderCardConfig>>((acc, item) => {
    acc[item.key] = item;
    return acc;
  }, {});

const OAUTH_BY_KEY = byKey(OAUTH_PROVIDERS);
const CHANNEL_BY_KEY = byKey(API_KEY_PROVIDERS);

export const getOAuthProviderVisual = (slug: string): ProviderCardConfig | undefined =>
  OAUTH_BY_KEY[slug];

export const getChannelProviderVisual = (slug: string): ProviderCardConfig | undefined =>
  CHANNEL_BY_KEY[slug];

export const humanizeSlug = (slug: string): string =>
  slug
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
