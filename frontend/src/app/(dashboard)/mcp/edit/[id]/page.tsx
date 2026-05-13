'use client';

import MCPFormPage from '@/components/mcp/MCPFormPage';
import { useParams } from 'next/navigation';
import { Suspense } from 'react';

export default function EditMCPPage() {
  const params = useParams<{ id: string }>();
  const serverId = Number(params?.id);

  return (
    <Suspense>
      <MCPFormPage serverId={Number.isFinite(serverId) ? serverId : undefined} />
    </Suspense>
  );
}
