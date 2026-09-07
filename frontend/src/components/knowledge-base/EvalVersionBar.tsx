'use client';

import { useMemo } from 'react';
import { CheckCheck, Sparkles, XCircle } from 'lucide-react';

import { versionLabel } from '@/components/knowledge-base/evalsConstants';
import { CustomButton, CustomTooltip, SelectInput } from '@/components/shared';
import type { EvalVersion } from '@/types/eval';

interface EvalVersionBarProps {
  versions: EvalVersion[];
  selectedVersion: EvalVersion | null;
  onSelectVersion: (versionId: string) => void;
  onOpenGenerate: () => void;
  onApproveAll: () => void;
  onRejectAll: () => void;
  approvingAll: boolean;
  rejectingAll: boolean;
}

// The manage-evals toolbar: pick a version, generate a new one, and bulk
// approve / reject the selected version's questions.
export default function EvalVersionBar({
  versions,
  selectedVersion,
  onSelectVersion,
  onOpenGenerate,
  onApproveAll,
  onRejectAll,
  approvingAll,
  rejectingAll,
}: EvalVersionBarProps) {
  const options = useMemo(
    () => versions.map((v) => ({ value: v.id, label: versionLabel(v) })),
    [versions],
  );

  const total = selectedVersion?.counts.total ?? 0;
  const busy = approvingAll || rejectingAll;
  const bulkDisabled = !selectedVersion || total === 0 || busy;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/95 px-4 py-3">
      <div className="flex items-center gap-2">
        <label className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground">
          Version
        </label>
        <div className="min-w-[260px]">
          {versions.length > 0 ? (
            <SelectInput
              name="eval-version"
              value={selectedVersion?.id ?? undefined}
              onValueChange={(v) => v && onSelectVersion(v)}
              options={options}
              placeholder="Select a version"
            />
          ) : (
            <span className="text-sm text-muted-foreground">No versions yet</span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-end gap-2">
        {selectedVersion && total > 0 && (
          <>
            <CustomTooltip content="Approve all questions in this version">
              <CustomButton
                type="default"
                size="sm"
                onClick={onApproveAll}
                disabled={bulkDisabled}
                loading={approvingAll}
              >
                <CheckCheck className="mr-1 size-4" />
                Approve all
              </CustomButton>
            </CustomTooltip>
            <CustomTooltip content="Reject (delete) all questions in this version">
              <CustomButton
                type="default"
                size="sm"
                onClick={onRejectAll}
                disabled={bulkDisabled}
                loading={rejectingAll}
                className="text-destructive"
              >
                <XCircle className="mr-1 size-4" />
                Reject all
              </CustomButton>
            </CustomTooltip>
          </>
        )}
        <CustomButton type="primary" size="sm" onClick={onOpenGenerate}>
          <Sparkles className="mr-1 size-4" />
          Generate
        </CustomButton>
      </div>
    </div>
  );
}
