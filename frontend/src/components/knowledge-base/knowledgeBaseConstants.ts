import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';

export const contentTypeBadgeColors: Record<string, { label: string; color: string }> = {
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
