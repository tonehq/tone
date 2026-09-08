'use client';

import { CheckCheck, Sparkles, XCircle } from 'lucide-react';
import { useMemo } from 'react';

import { CustomButton, CustomTooltip, SelectInput } from '@/components/shared';
import type { AgentLlmEvalScenarioVersion } from '@/types/agentLlmEval';

import { versionLabel } from './constants';
import VersionStatusChip from './VersionStatusChip';

interface AgentEvalVersionBarProps {
  versions: AgentLlmEvalScenarioVersion[];
  selectedVersion: AgentLlmEvalScenarioVersion | null;
  onSelectVersion: (versionId: string) => void;
  onOpenGenerate: () => void;
  onApproveAll: () => void;
  onRejectAll: () => void;
  approvingAll: boolean;
  rejectingAll: boolean;
}

// The Manage-Evals toolbar: pick a version, generate a new one, and bulk
// approve / reject the selected version's pending scenarios. Mirrors the KB
// ``EvalVersionBar`` so the two eval surfaces feel like siblings.
export default function AgentEvalVersionBar({
  versions,
  selectedVersion,
  onSelectVersion,
  onOpenGenerate,
  onApproveAll,
  onRejectAll,
  approvingAll,
  rejectingAll,
}: AgentEvalVersionBarProps) {
  const options = useMemo(
    () => versions.map((v) => ({ value: v.id, label: versionLabel(v) })),
    [versions],
  );

  const total = selectedVersion?.counts.total ?? 0;
  const pending = selectedVersion?.counts.pending ?? 0;
  const busy = approvingAll || rejectingAll;
  // While a version is generating its scenarios are in flux — block bulk
  // approve/reject on it (the backend also refuses a concurrent regenerate).
  const isGenerating = selectedVersion?.status === 'generating';
  const bulkDisabled = !selectedVersion || total === 0 || busy || isGenerating;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/95 px-4 py-3">
      <div className="flex items-center gap-2">
        <label className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground">
          Version
        </label>
        <div className="min-w-[260px]">
          {versions.length > 0 ? (
            <SelectInput
              name="agent-eval-version"
              value={selectedVersion?.id ?? undefined}
              onValueChange={(v) => v && onSelectVersion(v)}
              options={options}
              placeholder="Select a version"
            />
          ) : (
            <span className="text-sm text-muted-foreground">No versions yet</span>
          )}
        </div>
        {selectedVersion && <VersionStatusChip status={selectedVersion.status} />}
        {selectedVersion?.status === 'failed' && selectedVersion.generation_error && (
          <span className="text-xs text-destructive">{selectedVersion.generation_error}</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <CustomButton
          type="default"
          size="sm"
          onClick={onOpenGenerate}
          icon={<Sparkles className="size-3.5" />}
        >
          Generate
        </CustomButton>
        <CustomTooltip content={pending === 0 ? 'No pending scenarios to approve' : 'Approve all'}>
          <span>
            <CustomButton
              type="default"
              size="sm"
              onClick={onApproveAll}
              loading={approvingAll}
              disabled={bulkDisabled}
              icon={<CheckCheck className="size-3.5" />}
            >
              Approve all
            </CustomButton>
          </span>
        </CustomTooltip>
        <CustomTooltip content={pending === 0 ? 'No pending scenarios to reject' : 'Reject all'}>
          <span>
            <CustomButton
              type="danger"
              size="sm"
              onClick={onRejectAll}
              loading={rejectingAll}
              disabled={bulkDisabled}
              icon={<XCircle className="size-3.5" />}
            >
              Reject all
            </CustomButton>
          </span>
        </CustomTooltip>
      </div>
    </div>
  );
}
