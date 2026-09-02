export const formatPercent = (v: number) => `${Math.round(v * 100)}%`;
export const formatDecimal = (v: number) => (Number.isFinite(v) ? v.toFixed(2) : '—');
