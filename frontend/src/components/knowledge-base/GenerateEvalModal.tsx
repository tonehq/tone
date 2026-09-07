'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomModal, RadioGroupField, SelectInput, TextAreaField } from '@/components/shared';
import type { EvalVersion, GenerateEvalVersionPayload } from '@/types/eval';

interface GenerateEvalModalProps {
  open: boolean;
  onClose: () => void;
  versions: EvalVersion[];
  generating: boolean;
  onGenerate: (payload: GenerateEvalVersionPayload) => void;
}

const MODE_OPTIONS = [
  { value: 'new', label: 'New version' },
  { value: 'overwrite', label: 'Overwrite an existing version' },
];

// Modal to generate an LLM eval set — a fresh version or an overwrite of an
// un-run one — with an optional custom instruction prompt.
export default function GenerateEvalModal({
  open,
  onClose,
  versions,
  generating,
  onGenerate,
}: GenerateEvalModalProps) {
  const [mode, setMode] = useState<'new' | 'overwrite'>('new');
  const [versionId, setVersionId] = useState<string | null>(null);
  const [instructions, setInstructions] = useState('');

  // Only un-run versions can be overwritten (a run version is locked).
  const overwritableOptions = useMemo(
    () =>
      versions
        .filter((v) => !v.has_results && v.status !== 'generating')
        .map((v) => ({ value: v.id, label: `v${v.version_number}` })),
    [versions],
  );

  useEffect(() => {
    if (!open) {
      setMode('new');
      setVersionId(null);
      setInstructions('');
    }
  }, [open]);

  const canGenerate = !generating && (mode === 'new' || (mode === 'overwrite' && !!versionId));

  const handleGenerate = () => {
    if (!canGenerate) return;
    onGenerate({
      mode,
      version_id: mode === 'overwrite' ? versionId : null,
      instructions: instructions.trim() || null,
    });
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Generate evals"
      description="An LLM drafts a question set you can review, then approve or reject."
      confirmText="Generate"
      onConfirm={handleGenerate}
      confirmLoading={generating}
      confirmDisabled={!canGenerate}
    >
      <div className="flex flex-col gap-4">
        <RadioGroupField
          name="generate-mode"
          label="Mode"
          options={MODE_OPTIONS}
          value={mode}
          onValueChange={(v) => setMode(v as 'new' | 'overwrite')}
        />
        {mode === 'overwrite' &&
          (overwritableOptions.length > 0 ? (
            <SelectInput
              name="overwrite-version"
              label="Version to overwrite"
              value={versionId ?? undefined}
              onValueChange={(v) => setVersionId(v || null)}
              options={overwritableOptions}
              placeholder="Select a version"
              isRequired
            />
          ) : (
            <p className="rounded-md border border-dashed border-border/60 p-3 text-xs text-muted-foreground">
              No un-run versions to overwrite — a version that has been scored is locked. Choose
              &ldquo;New version&rdquo; instead.
            </p>
          ))}
        <TextAreaField
          name="generate-instructions"
          label="Instructions (optional)"
          placeholder="e.g. focus on refund & cancellation policies; ask tricky edge cases"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          rows={3}
        />
      </div>
    </CustomModal>
  );
}
