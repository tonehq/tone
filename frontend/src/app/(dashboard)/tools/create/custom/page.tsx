'use client';

import { Suspense } from 'react';

import ToolFormPage from '@/components/tools/ToolFormPage';

export default function CreateCustomToolPage() {
  return (
    <Suspense>
      <ToolFormPage />
    </Suspense>
  );
}
