import { cn } from '@/utils/cn';

export default function ProtocolDiagram({
  type,
  active,
}: {
  type: 'shttp' | 'sse';
  active: boolean;
}) {
  const gradientId = `mcp-proto-${type}`;
  return (
    <div
      className={cn(
        'rounded-md border bg-muted/30 px-3 py-2 transition-colors',
        active ? 'border-primary/30 text-primary' : 'border-border text-muted-foreground',
      )}
    >
      <svg viewBox="0 0 200 48" className="h-10 w-full" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.4" />
            <stop offset="50%" stopColor="currentColor" stopOpacity="1" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        <circle cx="20" cy="24" r="4" fill="currentColor" />
        <text
          x="20"
          y="44"
          textAnchor="middle"
          className="fill-current text-[8px] uppercase tracking-wider opacity-60"
        >
          srv
        </text>
        <circle cx="180" cy="24" r="4" fill="currentColor" />
        <text
          x="180"
          y="44"
          textAnchor="middle"
          className="fill-current text-[8px] uppercase tracking-wider opacity-60"
        >
          tone
        </text>

        {type === 'shttp' ? (
          <>
            <path
              d="M 28 24 Q 50 10 72 24 T 116 24 T 160 24 L 172 24"
              fill="none"
              stroke={active ? `url(#${gradientId})` : 'currentColor'}
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            <path
              d="M 28 24 Q 50 38 72 24 T 116 24 T 160 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              opacity="0.45"
              strokeDasharray="2,3"
            />
            <polygon points="172,24 168,21 168,27" fill="currentColor" />
            <polygon points="28,24 32,21 32,27" fill="currentColor" opacity="0.45" />
          </>
        ) : (
          <>
            <line
              x1="28"
              y1="24"
              x2="172"
              y2="24"
              stroke={active ? `url(#${gradientId})` : 'currentColor'}
              strokeWidth="1.5"
              strokeDasharray="6,5"
              strokeLinecap="round"
            />
            <circle cx="60" cy="24" r="2.5" fill="currentColor" />
            <circle cx="100" cy="24" r="2.5" fill="currentColor" />
            <circle cx="140" cy="24" r="2.5" fill="currentColor" />
            <polygon points="172,24 167,21 167,27" fill="currentColor" />
          </>
        )}
      </svg>
    </div>
  );
}
