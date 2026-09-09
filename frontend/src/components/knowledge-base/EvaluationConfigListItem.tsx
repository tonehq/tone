'use client';

import { Pencil, Star, Trash2 } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import type { EvaluationConfig } from '@/types/evaluationConfig';

interface EvaluationConfigListItemProps {
  config: EvaluationConfig;
  busy: boolean;
  onEdit: (config: EvaluationConfig) => void;
  onDelete: (config: EvaluationConfig) => void;
  onSetDefault: (config: EvaluationConfig) => void;
}

export default function EvaluationConfigListItem({
  config,
  busy,
  onEdit,
  onDelete,
  onSetDefault,
}: EvaluationConfigListItemProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-foreground">{config.name}</span>
          {config.is_default && (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              Default
            </span>
          )}
        </div>
        <div className="mt-0.5 truncate text-xs text-muted-foreground">
          {config.judge_model} · {config.metrics_enabled.length} metric
          {config.metrics_enabled.length === 1 ? '' : 's'}
          {config.judge_prompt ? ' · custom prompt' : ''}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {!config.is_default && (
          <CustomButton
            type="text"
            size="icon-xs"
            aria-label="Set as default"
            disabled={busy}
            onClick={() => onSetDefault(config)}
          >
            <Star className="size-4" />
          </CustomButton>
        )}
        <CustomButton
          type="text"
          size="icon-xs"
          aria-label="Edit config"
          disabled={busy}
          onClick={() => onEdit(config)}
        >
          <Pencil className="size-4" />
        </CustomButton>
        <CustomButton
          type="text"
          size="icon-xs"
          aria-label="Delete config"
          disabled={busy}
          onClick={() => onDelete(config)}
        >
          <Trash2 className="size-4" />
        </CustomButton>
      </div>
    </div>
  );
}
