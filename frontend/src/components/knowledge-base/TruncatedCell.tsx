'use client';

import { CustomTooltip } from '@/components/shared';

interface TruncatedCellProps {
  text: string | null | undefined;
  // Tailwind max-width utility for the clamped line (columns vary in width).
  maxWidthClassName?: string;
}

// A table cell that shows a single truncated line and reveals the full text in
// a hover tooltip. Reused by the question / expected / actual answer columns.
export default function TruncatedCell({
  text,
  maxWidthClassName = 'max-w-[240px]',
}: TruncatedCellProps) {
  const value = text?.trim();
  if (!value) return <span className="text-muted-foreground">—</span>;
  return (
    <CustomTooltip
      content={
        <div className="max-h-60 max-w-sm overflow-auto whitespace-pre-wrap break-words text-xs leading-snug">
          {value}
        </div>
      }
    >
      <span className={`line-clamp-1 ${maxWidthClassName} text-sm text-foreground`}>{value}</span>
    </CustomTooltip>
  );
}
