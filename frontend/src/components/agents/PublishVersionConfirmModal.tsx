'use client';

import { useAtom } from 'jotai';
import { useEffect, useMemo, useState } from 'react';

import { fetchAgentReadinessSummaryAtom } from '@/atoms/ReadinessAtom';
import ReadinessBadge from '@/components/agents/readiness/ReadinessBadge';
import { CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import type { AgentVersionSummary } from '@/types/agent';
import type { ReadinessSummary } from '@/types/readiness';
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
  /** Owning agent id — required to fetch the readiness preview for the
   *  currently-selected version. */
  agentId?: string;
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
  agentId,
}: PublishVersionConfirmModalProps) {
  const [, fetchSummary] = useAtom(fetchAgentReadinessSummaryAtom);

  // Newest version first — matches the version dropdown's order.
  const ordered = useMemo(() => [...versions].sort((a, b) => b.version - a.version), [versions]);

  // Default selection = the newest draft (i.e. anything except the published
  // row). Falls back to null when only the published version exists.
  const defaultSelectionId = useMemo(() => {
    const candidate = ordered.find((v) => v.id !== publishedVersionId);
    return candidate?.id ?? null;
  }, [ordered, publishedVersionId]);

  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Readiness preview for the currently-selected version. Re-fetched every
  // time the selection or the modal-open state changes. Errors are silent —
  // the pill just shows "unavailable" rather than blocking the publish flow
  // (backend still enforces the gate at commit time).
  const [readiness, setReadiness] = useState<ReadinessSummary | null>(null);
  const [readinessLoading, setReadinessLoading] = useState(false);

  // Re-seed the default every time the modal (re-)opens, never while it's
  // open — typing/clicking shouldn't lose the user's pick mid-flow.
  useEffect(() => {
    if (open) setSelectedId(defaultSelectionId);
  }, [open, defaultSelectionId]);

  useEffect(() => {
    if (!open || !agentId || !selectedId) {
      setReadiness(null);
      return;
    }
    let cancelled = false;
    setReadinessLoading(true);
    (async () => {
      try {
        const next = await fetchSummary({
          agentId,
          configId: selectedId,
          trigger: 'publish_gate',
        });
        if (!cancelled) setReadiness(next);
      } catch {
        if (!cancelled) setReadiness(null);
      } finally {
        if (!cancelled) setReadinessLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, agentId, selectedId, fetchSummary]);

  const selected = ordered.find((v) => v.id === selectedId) ?? null;
  const publishedVersion = ordered.find((v) => v.id === publishedVersionId) ?? null;
  const hasBlockers = (readiness?.blocker_count ?? 0) > 0;
  const canConfirm =
    !loading && selected !== null && selected.id !== publishedVersionId && !hasBlockers;

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
        <div className="space-y-3">
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
                    <RadioGroupItem
                      id={rowId}
                      value={v.id}
                      disabled={isPublished || loading}
                      className={cn(!isPublished && !loading && 'cursor-pointer')}
                    />
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

          {/* Readiness preview for the currently-selected version. Rendered
              even when publishing the already-live version so users are never
              surprised by a hidden gate result. */}
          {selected && !readinessLoading && readiness && (
            <div
              className={cn(
                'flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-[12px]',
                hasBlockers
                  ? 'border-destructive/30 bg-destructive/5'
                  : readiness.warning_count > 0
                    ? 'border-amber-500/30 bg-amber-500/5'
                    : 'border-emerald-500/30 bg-emerald-500/5',
              )}
            >
              <span className="text-muted-foreground">Readiness for v{selected.version}</span>
              <ReadinessBadge
                status={readiness.overall_status}
                blockerCount={readiness.blocker_count}
                warningCount={readiness.warning_count}
                size="sm"
              />
            </div>
          )}
          {selected && readinessLoading && (
            <div className="flex items-center justify-between rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-[12px] text-muted-foreground">
              <span>Checking readiness for v{selected.version}…</span>
              <ReadinessBadge status="loading" size="sm" />
            </div>
          )}
          {hasBlockers && (
            <p className="text-[11px] text-destructive">
              Fix the {readiness?.blocker_count} blocker
              {readiness?.blocker_count === 1 ? '' : 's'} before publishing this version. Open the
              readiness drawer to see what to fix.
            </p>
          )}
        </div>
      )}
    </CustomModal>
  );
}
