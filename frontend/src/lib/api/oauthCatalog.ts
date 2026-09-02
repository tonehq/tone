import { useQuery } from '@tanstack/react-query';

import { getOAuthCatalog } from '@/services/oauthService';
import type { OAuthCatalogProvider } from '@/types/oauth';

export const oauthCatalogKeys = {
  all: () => ['oauth-catalog'] as const,
};

/**
 * The OAuth/API provider catalog shown in the "Available providers" grid.
 * Server data in the TanStack cache instead of per-component useState; refresh
 * after admin actions by invalidating {@link oauthCatalogKeys.all}.
 */
export function useOAuthCatalog() {
  return useQuery<OAuthCatalogProvider[]>({
    queryKey: oauthCatalogKeys.all(),
    queryFn: getOAuthCatalog,
  });
}
