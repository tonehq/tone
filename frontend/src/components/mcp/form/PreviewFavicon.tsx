'use client';

import { cn } from '@/utils/cn';
import { Boxes } from 'lucide-react';
import { useState } from 'react';

function getApexDomain(hostname: string): string {
  const parts = hostname.split('.');
  if (parts.length <= 2) return hostname;
  const lastTwo = parts.slice(-2).join('.');
  const dualTier = new Set(['co.uk', 'com.au', 'co.in', 'co.jp', 'com.br', 'co.nz', 'com.mx']);
  if (dualTier.has(lastTwo)) return parts.slice(-3).join('.');
  return lastTwo;
}

function getFaviconUrl(hostname: string | null): string | null {
  if (!hostname) return null;
  return `https://www.google.com/s2/favicons?domain=${getApexDomain(hostname)}&sz=64`;
}

export default function PreviewFavicon({
  hostname,
  size = 'md',
}: {
  hostname: string | null;
  size?: 'sm' | 'md';
}) {
  const [failed, setFailed] = useState(false);
  const url = getFaviconUrl(hostname);
  const show = !!url && !failed;
  const isSm = size === 'sm';
  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-border',
        isSm ? 'size-8' : 'size-9',
        show ? 'bg-white p-1 dark:border-border/60' : 'bg-primary/5 dark:bg-primary/10',
      )}
    >
      {show ? (
        <img
          src={url ?? ''}
          alt={hostname ?? 'MCP server icon'}
          width={isSm ? 18 : 20}
          height={isSm ? 18 : 20}
          className={cn('object-contain', isSm ? 'size-[18px]' : 'size-5')}
          onError={() => setFailed(true)}
        />
      ) : (
        <Boxes size={isSm ? 15 : 16} className="text-primary" />
      )}
    </div>
  );
}
