'use client';

import { AlertTriangle, Calendar, FileText, HardDrive, RotateCcw, User } from 'lucide-react';

import { CustomButton, IconChip } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';

// ─── shared visual helpers (mirror KnowledgeBasePage but rendered here so
// the detail page and modal can share the same overview block) ─────────────

const contentTypeBadgeColors: Record<string, { label: string; color: string }> = {
  'application/pdf': {
    label: 'PDF',
    color: 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400',
  },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'DOCX',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400',
  },
  'text/plain': {
    label: 'TXT',
    color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  },
  'text/csv': {
    label: 'CSV',
    color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  },
  'text/html': {
    label: 'HTML',
    color: 'bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400',
  },
  'application/json': {
    label: 'JSON',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  },
};

function getTypeBadge(contentType?: string | null) {
  if (!contentType) return { label: 'FILE', color: 'bg-muted text-muted-foreground' };
  const config = contentTypeBadgeColors[contentType];
  if (config) return config;
  const ext = contentType.split('/').pop()?.toUpperCase() ?? 'FILE';
  return { label: ext, color: 'bg-muted text-muted-foreground' };
}

const statusConfig: Record<KnowledgeBaseDocument['status'], { label: string; className: string }> =
  {
    ready: {
      label: 'Active',
      className:
        'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    },
    processing: {
      label: 'Processing',
      className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    },
    failed: {
      label: 'Failed',
      className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    },
  };

function formatFileSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function truncateFileName(name: string, max = 72): string {
  if (!name || name.length <= max) return name;
  const dotIdx = name.lastIndexOf('.');
  const hasExt = dotIdx > -1 && dotIdx >= name.length - 6 && dotIdx < name.length - 1;
  const ext = hasExt ? name.slice(dotIdx) : '';
  const base = hasExt ? name.slice(0, dotIdx) : name;
  const room = Math.max(max - ext.length - 1, 8);
  const head = Math.ceil(room * 0.65);
  const tail = Math.max(room - head, 4);
  return `${base.slice(0, head)}…${base.slice(-tail)}${ext}`;
}

function getErrorMessage(doc: Pick<KnowledgeBaseDocument, 'meta_data'>): string | null {
  return formatIngestionError(doc.meta_data?.error);
}

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
            {truncateFileName(doc.file_name)}
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

function DetailRow({
  icon,
  label,
  value,
  last,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div className={cn('flex items-center gap-3 px-4 py-3', !last && 'border-b border-border/60')}>
      <span className="text-muted-foreground">{icon}</span>
      <span className="text-[13px] text-muted-foreground">{label}</span>
      <span className="ml-auto truncate text-[13px] font-medium text-foreground">{value}</span>
    </div>
  );
}
