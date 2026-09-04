'use client';

import { AlertTriangle, Calendar, FileText, HardDrive, RotateCcw, User } from 'lucide-react';

import DetailRow from '@/components/knowledge-base/DetailRow';
import { statusConfig } from '@/components/knowledge-base/knowledgeBaseConstants';
import {
  formatFileSize,
  getErrorMessage,
  getTypeBadge,
  truncateFileName,
} from '@/components/knowledge-base/knowledgeBaseHelpers';
import { CustomButton, IconChip } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';

interface KnowledgeBaseOverviewProps {
  doc: KnowledgeBaseDocument;
  agentName?: string | null;
  onRetry?: (doc: KnowledgeBaseDocument) => void;
  retrying?: boolean;
}

// Detail block for a single upload. Rendered inside the KB list modal AND on
// the standalone KB detail page's Overview tab — no divergence between the
// two views.
export default function KnowledgeBaseOverview({
  doc,
  agentName,
  onRetry,
  retrying,
}: KnowledgeBaseOverviewProps) {
  const badge = getTypeBadge(doc.file_type);
  const statusInfo = statusConfig[doc.status] ?? statusConfig.processing;
  const errorMsg = doc.status === 'failed' ? getErrorMessage(doc) : null;

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <IconChip icon={<FileText strokeWidth={1.75} />} tone="primary" size="lg" />
        <div className="min-w-0 flex-1">
          <p className="break-all text-sm font-semibold text-foreground" title={doc.file_name}>
            {truncateFileName(doc.file_name, 72)}
          </p>
          <div className="mt-1 flex items-center gap-2">
            <span
              className={cn(
                'inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider leading-none',
                badge.color,
              )}
            >
              {badge.label}
            </span>
            <Badge className={statusInfo.className}>{statusInfo.label}</Badge>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/10 px-3.5 py-3"
        >
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium text-destructive">Processing failed</p>
            <p className="mt-0.5 break-words text-[13px] text-destructive/90">{errorMsg}</p>
            {onRetry && (
              <CustomButton
                type="default"
                size="sm"
                icon={<RotateCcw className={cn('size-4', retrying && 'animate-spin')} />}
                disabled={retrying}
                onClick={() => onRetry(doc)}
                className="mt-2.5"
              >
                Retry processing
              </CustomButton>
            )}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-muted/20">
        <DetailRow icon={<User className="size-4" />} label="Agent" value={agentName ?? '—'} />
        <DetailRow
          icon={<HardDrive className="size-4" />}
          label="File size"
          value={formatFileSize(doc.size_bytes)}
        />
        <DetailRow
          icon={<Calendar className="size-4" />}
          label="Uploaded"
          value={formatDate(doc.created_at)}
        />
        <DetailRow
          icon={<Calendar className="size-4" />}
          label="Last updated"
          value={formatDate(doc.updated_at)}
          last
        />
      </div>
    </div>
  );
}
