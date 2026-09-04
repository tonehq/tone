import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';

// Accepted upload types — shared by the "Add sources" (DocumentUpload) and
// "Replace file" (EditDocument) flows via `useFileDropzone`. Keep the MIME list
// and the extension list in lock-step.
export const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'text/html',
  'application/json',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
export const ACCEPTED_EXTENSIONS = ['pdf', 'txt', 'csv', 'html', 'json', 'docx'];
export const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

export const contentTypeBadgeColors: Record<string, { label: string; color: string }> = {
  'application/pdf': {
    label: 'PDF',
    color: 'bg-destructive/10 text-destructive',
  },
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
    label: 'DOCX',
    color: 'bg-primary/10 text-primary',
  },
  'text/plain': {
    label: 'TXT',
    color: 'bg-muted text-muted-foreground',
  },
  'text/csv': {
    label: 'CSV',
    color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  },
  'text/html': {
    label: 'HTML',
    color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
  },
  'application/json': {
    label: 'JSON',
    color: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  },
};

type StatusKey = KnowledgeBaseDocument['status'];

export const statusDot: Record<StatusKey, string> = {
  ready: 'bg-emerald-500',
  processing: 'bg-amber-500 animate-pulse',
  failed: 'bg-destructive',
};

export const statusConfig: Record<StatusKey, { label: string; className: string }> = {
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
