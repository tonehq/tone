import { CHIP_TONES } from '@/components/mcp/mcpConstants';

export default function CountChip({
  count,
  label,
  tone,
  noun = false,
}: {
  count: number;
  label: string;
  tone: keyof typeof CHIP_TONES;
  noun?: boolean;
}) {
  if (count === 0) {
    return <span className="text-[12px] text-muted-foreground/50">—</span>;
  }
  const suffix = noun ? label : count === 1 ? label : `${label}s`;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={`inline-flex h-5 min-w-[20px] items-center justify-center rounded-md px-1.5 text-[11px] font-semibold tabular-nums ring-1 ring-inset ${CHIP_TONES[tone]}`}
      >
        {count}
      </span>
      <span className="text-[12px] text-muted-foreground">{suffix}</span>
    </span>
  );
}
