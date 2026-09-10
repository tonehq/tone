'use client';

import { useMemo } from 'react';
import { PlayCircle, SlidersHorizontal } from 'lucide-react';

import { CustomLink, CustomTab, type TabItem } from '@/components/shared';

import EvalRunsPanel from './EvalRunsPanel';
import EvaluatorsPanel from './EvaluatorsPanel';

interface EvaluationConfigTabProps {
  uploadId: string;
}

// Two sub-tabs: manage the judges (Evaluators) vs run + compare (Runs). Keeps
// the KB tab bar to a single "Evaluation config" entry while splitting the two
// concerns so neither view is cramped.
export default function EvaluationConfigTab({ uploadId }: EvaluationConfigTabProps) {
  const tabs = useMemo<TabItem[]>(
    () => [
      {
        key: 'evaluators',
        label: 'Evaluators',
        icon: <SlidersHorizontal className="size-4" />,
        children: <EvaluatorsPanel />,
      },
      {
        key: 'runs',
        label: 'Runs & compare',
        icon: <PlayCircle className="size-4" />,
        children: <EvalRunsPanel uploadId={uploadId} />,
      },
    ],
    [uploadId],
  );

  return (
    <div className="flex flex-col gap-3 py-1">
      <p className="text-xs text-muted-foreground">
        Grade the eval results for this document with alternative judges, then compare them. The
        models, retrieval, and default scoring behind those results are set in{' '}
        <CustomLink href="/settings/evaluations" className="font-medium">
          Settings → Evaluations
        </CustomLink>
        .
      </p>
      <CustomTab items={tabs} defaultActiveKey="evaluators" />
    </div>
  );
}
