'use client';

import dynamic from 'next/dynamic';
import { useParams } from 'next/navigation';

import AppLoader from '@/components/shared/AppLoader';

// React Flow measures the DOM, so the editor must be client-only.
const WorkflowBuilder = dynamic(() => import('@/components/workflows/WorkflowBuilder'), {
  ssr: false,
  loading: () => <AppLoader />,
});

const WorkflowEditorPage = () => {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  if (!id) return <AppLoader />;
  return <WorkflowBuilder workflowId={id} />;
};

export default WorkflowEditorPage;
