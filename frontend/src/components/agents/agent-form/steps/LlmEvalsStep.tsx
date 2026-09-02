'use client';

import LlmEvalsSaveFirstEmptyState from './LlmEvalsStep/LlmEvalsSaveFirstEmptyState';
import LlmEvalsStepBody from './LlmEvalsStep/LlmEvalsStepBody';

export type { FolderScope } from './LlmEvalsStep/types';

export default function LlmEvalsStep({ agentId }: { agentId: string | null }) {
  // Create mode: agent isn't saved yet. Render an empty state instead of
  // hiding the section entirely, so users discover the feature and know
  // exactly what to do first.
  if (!agentId) {
    return <LlmEvalsSaveFirstEmptyState />;
  }
  return <LlmEvalsStepBody agentId={agentId} />;
}
