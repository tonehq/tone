'use client';

import Integrations from '@/components/settings/Integrations';
import { showToast } from '@/utils/toast';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';

function IntegrationsWithCallback() {
  const searchParams = useSearchParams();
  const [callbackProvider, setCallbackProvider] = useState<string | null>(null);

  useEffect(() => {
    const provider = searchParams.get('provider');
    const status = searchParams.get('status');
    if (provider && status === 'success') {
      setCallbackProvider(provider);
      showToast.success(`${provider.replaceAll('_', ' ')} connected successfully`);
      window.history.replaceState({}, '', '/integrations');
    }
  }, [searchParams]);

  return <Integrations refreshKey={callbackProvider} />;
}

export default function IntegrationsPage() {
  return (
    <div className="animate-page flex h-full flex-col">
      <Suspense>
        <IntegrationsWithCallback />
      </Suspense>
    </div>
  );
}
