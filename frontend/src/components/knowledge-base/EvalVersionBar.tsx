'use client';

import { useMemo } from 'react';
import { Loader2, Sparkles } from 'lucide-react';

import { versionLabel } from '@/components/knowledge-base/evalsConstants';
import { CustomButton, SelectInput } from '@/components/shared';
import type { EvalVersion } from '@/types/eval';

interface EvalVersionBarProps {
  versions: EvalVersion[];
  selectedVersion: EvalVersion | null;
  onSelectVersion: (versionId: string) => void;
  onOpenGenerate: () => void;
}

// The anchor row: pick the version being reviewed, see its pending/approved
// summary, and generate a new one. Bulk approve/reject live in the review
// toolbar (next to the question list they act on).
export default function EvalVersionBar({
  versions,
  selectedVersion,
  onSelectVersion,
  onOpenGenerate,
}: EvalVersionBarProps) {
  const options = useMemo(
    () => versions.map((v) => ({ value: v.id, label: versionLabel(v) })),
    [versions],
  );

  const counts = selectedVersion?.counts;
  const isGenerating = selectedVersion?.status === 'generating';

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/95 px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
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
        {isGenerating ? (
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Generating…
          </span>
        ) : (
          counts && (
            <span className="text-xs text-muted-foreground">
              <span className="font-medium text-amber-600 dark:text-amber-400">
                {counts.pending} pending
              </span>
              {' · '}
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                {counts.approved} approved
              </span>
            </span>
          )
        )}
      </div>

      <CustomButton type="primary" size="sm" onClick={onOpenGenerate} disabled={isGenerating}>
        <Sparkles className="mr-1 size-4" />
        Generate
      </CustomButton>
    </div>
  );
}
