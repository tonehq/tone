'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect } from 'react';

// Moved into the dedicated Settings area. OAuth callbacks land here with
// ?provider=...&status=success (target is backend-controlled), so forward the
// query string when redirecting to keep the success toast working.
function IntegrationsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const query = searchParams.toString();
    router.replace(`/settings/integrations${query ? `?${query}` : ''}`);
  }, [router, searchParams]);

  return null;
}

export default function IntegrationsRedirectPage() {
  return (
    <Suspense>
      <IntegrationsRedirect />
    </Suspense>
  );
}
