'use client';

import { Check, ChevronDown, History, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { CustomButton, CustomModal } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { AgentVersionSummary } from '@/types/agent';
import { cn } from '@/utils/cn';

interface AgentVersionSelectorProps {
  versions: AgentVersionSummary[];
  selectedConfigId: string | null;
  onSelect: (configId: string) => void;
  onDelete?: (configId: string) => Promise<void> | void;
  disabled?: boolean;
}

/**
 * Header dropdown that lists every saved version of an agent. The row matching
 * `selectedConfigId` is highlighted; the row with `is_live` carries a "Live"
 * badge. Non-live rows expose a small trash control that delegates to
 * `onDelete` — wrapped in a confirm modal so a misclick can't drop history.
 */
export default function AgentVersionSelector({
  versions,
  selectedConfigId,
  onSelect,
  onDelete,
  disabled,
}: AgentVersionSelectorProps) {
  const [pendingDelete, setPendingDelete] = useState<AgentVersionSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const selected = useMemo(
    () => versions.find((v) => v.id === selectedConfigId) ?? null,
    [versions, selectedConfigId],
  );

  if (versions.length === 0) return null;

  const triggerLabel = selected ? `v${selected.version}` : 'Select version';
  const triggerLive = selected?.is_live ?? false;

  const handleConfirmDelete = async () => {
    if (!pendingDelete || !onDelete) return;
    setDeleting(true);
    try {
      await onDelete(pendingDelete.id);
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <CustomButton
            type="default"
            size="sm"
            disabled={disabled}
            className="h-8 gap-1.5 rounded-full border-border/60 px-3 text-[12px] font-medium"
            icon={<History className="size-3.5" />}
          >
            <span>{triggerLabel}</span>
            {triggerLive && (
              <Badge className="ml-1 h-4 px-1.5 py-0 text-[10px] uppercase tracking-wide">
                Live
              </Badge>
            )}
            <ChevronDown className="size-3.5 opacity-60" />
          </CustomButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[200px]">
          <DropdownMenuLabel className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Versions
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {versions.map((v) => {
            const isSelected = v.id === selectedConfigId;
            return (
              <DropdownMenuItem
                key={v.id}
                onSelect={(e) => {
                  e.preventDefault();
                  onSelect(v.id);
                }}
                className={cn(
                  'flex items-center justify-between gap-2 text-[13px]',
                  isSelected && 'bg-accent/60',
                )}
              >
                <span className="flex items-center gap-2">
                  <Check className={cn('size-3.5', isSelected ? 'opacity-100' : 'opacity-0')} />
                  <span className="font-medium">v{v.version}</span>
                  {v.is_live && (
                    <Badge className="h-4 px-1.5 py-0 text-[10px] uppercase tracking-wide">
                      Live
                    </Badge>
                  )}
                </span>
                {onDelete && !v.is_live && (
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    aria-label={`Delete v${v.version}`}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setPendingDelete(v);
                    }}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="size-3.5" />
                  </CustomButton>
                )}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>

      <CustomModal
        open={pendingDelete !== null}
        onClose={() => setPendingDelete(null)}
        title={pendingDelete ? `Delete v${pendingDelete.version}?` : 'Delete version'}
        description="This version will be removed from history. The live version is not affected."
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleConfirmDelete}
      />
    </>
  );
}
