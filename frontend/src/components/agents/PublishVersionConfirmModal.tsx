'use client';

import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import type { AgentVersionSummary } from '@/types/agent';
import { cn } from '@/utils/cn';

interface PublishVersionConfirmModalProps {
  open: boolean;
  onClose: () => void;
  /** Fires with the config id of the version the user picked. */
  onConfirm: (configId: string) => void | Promise<void>;
  /** All non-deleted versions. The currently-published one is rendered
   *  disabled — re-publishing it would be a no-op. */
  versions: AgentVersionSummary[];
  /** Id of the version currently serving calls, or null when there isn't one
   *  yet (fresh agent before the first publish). */
  publishedVersionId: string | null;
  loading?: boolean;
}

/**
 * Self-contained Publish flow. Click Publish → this opens → user picks a
 * version → confirm. Decoupled from the version-preview dropdown in the
 * toolbar, so picking a row here doesn't change what the form is currently
 * rendering.
 */
export default function PublishVersionConfirmModal({
  open,
  onClose,
  onConfirm,
  versions,
  publishedVersionId,
  loading = false,
}: PublishVersionConfirmModalProps) {
  // Newest version first — matches the version dropdown's order.
  const ordered = useMemo(() => [...versions].sort((a, b) => b.version - a.version), [versions]);

  // Default selection = the newest draft (i.e. anything except the published
  // row). Falls back to null when only the published version exists.
  const defaultSelectionId = useMemo(() => {
    const candidate = ordered.find((v) => v.id !== publishedVersionId);
    return candidate?.id ?? null;
  }, [ordered, publishedVersionId]);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Re-seed the default every time the modal (re-)opens, never while it's
  // open — typing/clicking shouldn't lose the user's pick mid-flow.
  useEffect(() => {
    if (open) setSelectedId(defaultSelectionId);
  }, [open, defaultSelectionId]);

  const selected = ordered.find((v) => v.id === selectedId) ?? null;
  const publishedVersion = ordered.find((v) => v.id === publishedVersionId) ?? null;
  const canConfirm = !loading && selected !== null && selected.id !== publishedVersionId;

  const handleConfirm = () => {
    if (!canConfirm || !selected) return;
    void onConfirm(selected.id);
  };

  const description = publishedVersion
    ? `Pick a version to publish. The selected version will replace v${publishedVersion.version} and start serving calls immediately.`
    : 'Pick a version to publish. The selected version will start serving calls immediately.';

  const footer = (
    <>
      <CustomButton type="default" onClick={onClose} disabled={loading}>
        Cancel
      </CustomButton>
      <CustomButton type="primary" onClick={handleConfirm} loading={loading} disabled={!canConfirm}>
        {selected ? `Publish v${selected.version}` : 'Publish'}
      </CustomButton>
    </>
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Publish a version"
      description={description}
      footer={footer}
    >
      {ordered.length === 0 ? (
        <p className="text-sm text-muted-foreground">No saved versions yet.</p>
      ) : (
        <RadioGroup
          value={selectedId ?? ''}
          onValueChange={(val) => setSelectedId(val || null)}
          className="max-h-72 overflow-y-auto pr-1"
        >
          {ordered.map((v) => {
            const isPublished = v.id === publishedVersionId;
            const isSelected = v.id === selectedId;
            const rowId = `publish-version-${v.id}`;
            return (
              <Label
                key={v.id}
                htmlFor={rowId}
                className={cn(
                  'flex cursor-pointer items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-[13px] transition',
                  isSelected && !isPublished && 'border-primary bg-primary/5',
                  !isSelected && !isPublished && 'border-border/60 hover:bg-accent/40',
                  isPublished && 'cursor-not-allowed border-border/60 bg-muted/30 opacity-70',
                )}
              >
                <span className="flex items-center gap-2.5">
                  <RadioGroupItem id={rowId} value={v.id} disabled={isPublished || loading} />
                  <span className="font-medium">v{v.version}</span>
                  {isPublished && (
                    <Badge className="h-4 px-1.5 py-0 text-[10px] uppercase tracking-wide">
                      Currently published
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
      )}
    </CustomModal>
  );
}
