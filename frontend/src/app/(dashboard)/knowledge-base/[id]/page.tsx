'use client';

import { use } from 'react';

import KnowledgeBaseDetailPage from '@/components/knowledge-base/KnowledgeBaseDetailPage';

interface Params {
  id: string;
}

export default function KnowledgeBaseDetailRoute({ params }: { params: Promise<Params> }) {
  const { id } = use(params);
  return <KnowledgeBaseDetailPage uploadId={id} />;
}
