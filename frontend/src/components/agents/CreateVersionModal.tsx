'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import type { AgentVersionSummary } from '@/types/agent';
import { cn } from '@/utils/cn';

export type CreateVersionMode = 'copy' | 'fresh';

export interface CreateVersionSelection {
  mode: CreateVersionMode;
  /** Populated only when `mode === 'copy'`. The version row whose fields and
   *  attachments will be cloned into the new draft. */
  sourceConfigId: string | null;
}

interface CreateVersionModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (selection: CreateVersionSelection) => void | Promise<void>;
  /** Every non-deleted version on the agent. The picker is hidden when this
   *  is empty — there's nothing to copy from. */
  versions: AgentVersionSummary[];
  /** Live version id, used to label the row. Passing null is fine (no
   *  version has been published yet). */
  publishedVersionId: string | null;
  loading?: boolean;
}

/**
 * Dialog opened by the toolbar "Create version" button.
 *
 * Two modes:
 *   1. **Copy** — radio-pick an existing version; the new draft mirrors it.
 *   2. **Fresh** — start with a blank template.
 *
 * The version picker is only rendered when "Copy" is selected so the dialog
 * stays compact and the user's focus follows their choice.
 */
export default function CreateVersionModal({
  open,
  onClose,
  onConfirm,
  versions,
  publishedVersionId,
  loading = false,
}: CreateVersionModalProps) {
  const orderedVersions = useMemo(
    () => [...versions].sort((a, b) => b.version - a.version),
    [versions],
  );
  const hasVersions = orderedVersions.length > 0;

  const [mode, setMode] = useState<CreateVersionMode>('copy');
  const [sourceConfigId, setSourceConfigId] = useState<string | null>(null);

  // Reset the dialog every time it (re-)opens so it always starts from the
  // friendliest default — copy the live version, or fall back to fresh when
  // no versions exist yet.
  useEffect(() => {
    if (!open) return;
    if (hasVersions) {
      setMode('copy');
      const preferred =
        orderedVersions.find((v) => v.id === publishedVersionId) ?? orderedVersions[0];
      setSourceConfigId(preferred.id);
    } else {
      setMode('fresh');
      setSourceConfigId(null);
    }
  }, [open, hasVersions, orderedVersions, publishedVersionId]);

  const canConfirm = !loading && (mode === 'fresh' || (mode === 'copy' && sourceConfigId !== null));

  const handleConfirm = () => {
    if (!canConfirm) return;
    void onConfirm({
      mode,
      sourceConfigId: mode === 'copy' ? sourceConfigId : null,
    });
  };

  const confirmLabel = mode === 'copy' ? 'Create copy' : 'Create from scratch';

  const footer = (
    <>
      <CustomButton type="default" onClick={onClose} disabled={loading}>
        Cancel
      </CustomButton>
      <CustomButton type="primary" onClick={handleConfirm} loading={loading} disabled={!canConfirm}>
        {confirmLabel}
      </CustomButton>
    </>
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Create a new version"
      description="Pick how the new draft should start. You can edit it after it's created."
      footer={footer}
    >
      <div className="space-y-3">
        <RadioGroup
          value={mode}
          onValueChange={(val) => setMode(val as CreateVersionMode)}
          className="space-y-2"
        >
          <ModeOption
            id="create-version-mode-copy"
            value="copy"
            selected={mode === 'copy'}
            disabled={loading || !hasVersions}
            title="Copy from an existing version"
            description={
              hasVersions
                ? 'Clone the prompt, providers, tools, MCP servers and knowledge base from a version you pick.'
                : 'No versions to copy yet — save the agent first.'
            }
          />
          <ModeOption
            id="create-version-mode-fresh"
            value="fresh"
            selected={mode === 'fresh'}
            disabled={loading}
            title="Start from scratch"
            description="Begin with an empty template — no prompt, providers, tools or knowledge attached."
          />
        </RadioGroup>

        {mode === 'copy' && hasVersions && (
          <VersionPicker
            versions={orderedVersions}
            selectedId={sourceConfigId}
            publishedVersionId={publishedVersionId}
            disabled={loading}
            onSelect={setSourceConfigId}
          />
        )}
      </div>
    </CustomModal>
  );
}

interface ModeOptionProps {
  id: string;
  value: CreateVersionMode;
  selected: boolean;
  disabled: boolean;
  title: string;
  description: string;
}

/** Small wrapper that keeps the radio + label markup DRY between the two
 *  mode options. */
function ModeOption({ id, value, selected, disabled, title, description }: ModeOptionProps) {
  return (
    <Label
      htmlFor={id}
      className={cn(
        'flex cursor-pointer items-start gap-3 rounded-md border px-3 py-2.5 text-[13px] transition',
        disabled && 'cursor-not-allowed opacity-60',
        selected && !disabled
          ? 'border-primary bg-primary/5'
          : 'border-border/60 hover:bg-accent/40',
      )}
    >
      <RadioGroupItem
        id={id}
        value={value}
        disabled={disabled}
        className={cn('mt-0.5', !disabled && 'cursor-pointer')}
      />
      <span className="flex flex-col gap-0.5">
        <span className="font-medium">{title}</span>
        <span className="text-[12px] text-muted-foreground">{description}</span>
      </span>
    </Label>
  );
}

interface VersionPickerProps {
  versions: AgentVersionSummary[];
  selectedId: string | null;
  publishedVersionId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
}

/** Scrollable radio list of versions — only rendered while "Copy" is the
 *  selected mode, so the dialog stays compact when the user picks "Fresh". */
function VersionPicker({
  versions,
  selectedId,
  publishedVersionId,
  disabled,
  onSelect,
}: VersionPickerProps) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        Source version
      </p>
      <RadioGroup
        value={selectedId ?? ''}
        onValueChange={(val) => val && onSelect(val)}
        className="max-h-60 space-y-1.5 overflow-y-auto pr-1"
      >
        {versions.map((v) => {
          const rowId = `create-version-source-${v.id}`;
          const isPublished = v.id === publishedVersionId;
          const isSelected = v.id === selectedId;
          return (
            <Label
              key={v.id}
              htmlFor={rowId}
              className={cn(
                'flex cursor-pointer items-center justify-between gap-3 rounded-md border px-3 py-2 text-[13px] transition',
                disabled && 'cursor-not-allowed opacity-60',
                isSelected && !disabled
                  ? 'border-primary bg-primary/5'
                  : 'border-border/60 hover:bg-accent/40',
              )}
            >
              <span className="flex items-center gap-2.5">
                <RadioGroupItem
                  id={rowId}
                  value={v.id}
                  disabled={disabled}
                  className={cn(!disabled && 'cursor-pointer')}
                />
                <span className="font-medium">v{v.version}</span>
                {isPublished && (
                  <Badge className="h-4 px-1.5 py-0 text-[10px] uppercase tracking-wide">
                    Live
                  </Badge>
                )}
              </span>
              {v.created_at && (
                <span className="shrink-0 text-[11px] text-muted-foreground">
                  {new Date(v.created_at).toLocaleString()}
                </span>
              )}
            </Label>
          );
        })}
      </RadioGroup>
    </div>
  );
}
