import { useEffect, useLayoutEffect, useRef, useState } from 'react';

interface AdaptiveScrollOptions {
  reservedHeightPx?: number;
  minScrollYPx?: number;
}

// Calculates and returns a vertical scroll height only when the table content overflows
// the available viewport height (window.innerHeight - reservedHeightPx). Returns undefined otherwise.
export const useAdaptiveTableScrollY = (options: AdaptiveScrollOptions = {}) => {
  const { reservedHeightPx = 420, minScrollYPx = 180 } = options;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [scrollY, setScrollY] = useState<number | undefined>(undefined);

  const recompute = () => {
    if (typeof window === 'undefined') return;
    const available = Math.max(minScrollYPx, window.innerHeight - reservedHeightPx);

    // Find the table body inside the container
    const body = containerRef.current?.querySelector<HTMLElement>('.ant-table-body');
    if (!body) {
      // If body not yet rendered, set tentative value; a later layout effect will refine it
      setScrollY(undefined);
      return;
    }

    const hasOverflow = body.scrollHeight > available;
    setScrollY(hasOverflow ? available : undefined);
  };

  useLayoutEffect(() => {
    recompute();
  }, []);

  useEffect(() => {
    const onResize = () => recompute();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  // Recompute when the table content size changes.
  useEffect(() => {
    if (!containerRef.current) return;
    const body = containerRef.current.querySelector('.ant-table-body');
    if (!body) return;
    const ro = new ResizeObserver(() => recompute());
    ro.observe(body);
    return () => ro.disconnect();
  }, [containerRef.current]);

  return { scrollY, containerRef } as const;
};
