'use client';

// Two-line clamped cell for long text (prompt / expected / actual answer) in the
// Eval Results table; full text on hover via the native title tooltip.
export default function AgentEvalTruncatedCell({ text }: { text: string | null }) {
  return (
    <span className="line-clamp-2 block max-w-[240px] text-muted-foreground" title={text ?? ''}>
      {text || '—'}
    </span>
  );
}
