'use client';

import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

/**
 * Returns a stable callback that navigates one step back in history,
 * falling back to a given URL when there's no history entry to return to
 * (e.g. deep-link, page opened in a new tab).
 */
export function useGoBack(fallbackHref: string): () => void {
  const router = useRouter();
  return useCallback(() => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
    } else {
      router.push(fallbackHref);
    }
  }, [router, fallbackHref]);
}
