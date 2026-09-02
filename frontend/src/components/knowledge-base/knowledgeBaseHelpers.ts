import { contentTypeBadgeColors } from '@/components/knowledge-base/knowledgeBaseConstants';

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
