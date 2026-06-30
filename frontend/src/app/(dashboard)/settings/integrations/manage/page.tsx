'use client';

import AppIntegrationListPage from '@/components/integrations/AppIntegrationListPage';
import { Suspense } from 'react';

export default function ManageAppIntegrationsPage() {
  return (
    <Suspense>
      <AppIntegrationListPage />
    </Suspense>
  );
}
