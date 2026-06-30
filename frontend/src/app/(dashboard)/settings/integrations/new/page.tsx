'use client';

import AppIntegrationFormPage from '@/components/integrations/AppIntegrationFormPage';
import { Suspense } from 'react';

export default function NewAppIntegrationPage() {
  return (
    <Suspense>
      <AppIntegrationFormPage />
    </Suspense>
  );
}
