import { useEffect } from 'react';

import { handleApiError } from '@/utils/helpers';

/**
 * Surface a TanStack Query error through the shared `handleApiError` toast —
 * the same behaviour the old imperative `.catch(handleApiError)` fetch effects
 * had. Fires once whenever the query transitions into an error state. Read-only
 * catalog queries have no error UI of their own, so the toast is the only
 * signal the user gets; keeping it here means every migrated catalog reuses one
 * implementation instead of hand-rolling an error effect per query.
 */
export function useQueryErrorToast(error: unknown) {
  useEffect(() => {
    if (error) handleApiError(error);
  }, [error]);
}
