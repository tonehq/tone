'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';

import MCPToolsListPage from '@/components/mcp/MCPToolsListPage';

// Static sibling segments under /mcp/ that must never be treated as a server id
// (e.g. someone hand-types /mcp/create/tools).
const RESERVED_SEGMENTS = new Set(['create', 'edit']);

export default function MCPToolsPage() {
  const router = useRouter();
  const params = useParams<{ id: string | string[] }>();
  const raw = params?.id;
  const serverId = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw[0] : undefined;
  const invalid = !serverId || RESERVED_SEGMENTS.has(serverId);

  useEffect(() => {
    if (invalid) router.replace('/mcp');
  }, [invalid, router]);

  if (invalid || !serverId) return null;

  return <MCPToolsListPage serverId={serverId} />;
}
