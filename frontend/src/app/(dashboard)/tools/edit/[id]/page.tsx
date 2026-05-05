'use client';

import ToolFormPage from '@/components/tools/ToolFormPage';
import { useParams } from 'next/navigation';

export default function EditToolPage() {
  const params = useParams();
  const id = params?.id as string;

  return <ToolFormPage toolId={id} />;
}
