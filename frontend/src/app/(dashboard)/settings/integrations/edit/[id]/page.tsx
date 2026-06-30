'use client';

import AppIntegrationFormPage from '@/components/integrations/AppIntegrationFormPage';
import { useParams } from 'next/navigation';
import { Suspense } from 'react';

export default function EditAppIntegrationPage() {
  const params = useParams<{ id: string }>();
  const integrationId = params?.id;

  return (
    <Suspense>
      <AppIntegrationFormPage integrationId={integrationId} />
    </Suspense>
  );
}
