'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';

import AppLoader from '@/components/shared/AppLoader';

// React Flow measures the DOM, so the editor must be client-only.
const WorkflowBuilder = dynamic(() => import('@/components/workflows/WorkflowBuilder'), {
  ssr: false,
  loading: () => <AppLoader />,
});

// Workflows live under their owning agent, so the builder is a nested route of
// the agent editor. It shares the editor's layout (form state is preserved and
// navigating here counts as internal — no "discard changes?" prompt), and the
// dashboard chrome is already hidden for /agents/edit/*.
export default function AgentWorkflowBuilderPage() {
  const params = useParams<{ type: string; id: string; workflowId: string }>();
  const { type, id, workflowId } = params ?? {};
  if (!workflowId || !type || !id) return <AppLoader />;
  return <WorkflowBuilder workflowId={workflowId} backHref={`/agents/edit/${type}/${id}/prompt`} />;
}
