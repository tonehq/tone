import { File, FileCode, FileSpreadsheet, FileText } from 'lucide-react';

import { contentTypeBadgeColors } from '@/components/knowledge-base/knowledgeBaseConstants';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';

export function getTypeBadge(contentType?: string | null) {
  if (!contentType) return { label: 'FILE', color: 'bg-muted text-muted-foreground' };
  const config = contentTypeBadgeColors[contentType];
  if (config) return config;
  const ext = contentType.split('/').pop()?.toUpperCase() ?? 'FILE';
  return { label: ext, color: 'bg-muted text-muted-foreground' };
}

export function formatFileSize(bytes: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Visual-only truncation for long file names. Keeps the extension visible and
// shows an ellipsis in the middle: e.g. "Voice AI Testing Platfo…uation.pdf".
// The underlying value is never mutated — pair with title={fullName} for hover.
export function truncateFileName(name: string, max = 48): string {
  if (!name || name.length <= max) return name;
  const dotIdx = name.lastIndexOf('.');
  const hasExt = dotIdx > -1 && dotIdx >= name.length - 6 && dotIdx < name.length - 1;
  const ext = hasExt ? name.slice(dotIdx) : '';
  const base = hasExt ? name.slice(0, dotIdx) : name;
  const room = Math.max(max - ext.length - 1, 8); // 1 = ellipsis char
  const head = Math.ceil(room * 0.65);
  const tail = Math.max(room - head, 4);
  return `${base.slice(0, head)}…${base.slice(-tail)}${ext}`;
}

// File-type glyph for an upload row / selected file. Shared by DocumentUpload
// and EditDocument so the two pickers render identical icons.
export function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return <FileText className="size-5 text-red-500" />;
    case 'docx':
    case 'doc':
      return <FileText className="size-5 text-blue-500" />;
    case 'csv':
      return <FileSpreadsheet className="size-5 text-emerald-500" />;
    case 'json':
      return <FileCode className="size-5 text-amber-500" />;
    case 'txt':
      return <FileText className="size-5 text-gray-500" />;
    default:
      return <File className="size-5 text-muted-foreground" />;
  }
}

/** Extract the human-readable failure reason stored on a failed upload. */
export function getErrorMessage(doc: Pick<KnowledgeBaseDocument, 'meta_data'>): string | null {
  return formatIngestionError(doc.meta_data?.error);
}
