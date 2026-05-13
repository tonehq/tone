'use client';

import { Suspense } from 'react';

import MCPFormPage from '@/components/mcp/MCPFormPage';

export default function CreateMCPPage() {
  return (
    <Suspense>
      <MCPFormPage />
    </Suspense>
  );
}
