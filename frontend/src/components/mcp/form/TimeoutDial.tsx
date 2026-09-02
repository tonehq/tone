export default function TimeoutDial({ value }: { value: number }) {
  const min = 1;
  const max = 300;
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const size = 132;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const arcSpan = c * 0.78;
  const arc = pct * arcSpan;

  return (
    <div className="relative mx-auto flex h-[132px] w-[132px] items-center justify-center">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-[130deg]"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="mcp-dial-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.55" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="1" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="currentColor"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${arcSpan} ${c}`}
          className="text-border"
        />
        <g className="text-primary">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="url(#mcp-dial-gradient)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${arc} ${c}`}
            className="transition-all duration-300"
          />
        </g>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[30px] font-semibold leading-none tabular-nums tracking-tight text-foreground">
          {value}
        </span>
        <span className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
          seconds
        </span>
      </div>
    </div>
  );
}
