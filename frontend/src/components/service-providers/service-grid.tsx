'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { useEffect, useRef } from 'react';

import type { ProviderUsage } from '@/types/service';

import ServiceCard from './service-card';

interface ServiceGridProps {
  items: ProviderUsage[];
  total: number;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSelect: (usage: ProviderUsage) => void;
  onEdit: (usage: ProviderUsage) => void;
  onDelete: (usage: ProviderUsage) => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.04, delayChildren: 0.02 } },
};

export default function ServiceGrid({
  items,
  total,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  onSelect,
  onEdit,
  onDelete,
}: ServiceGridProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!hasNextPage) return;
    const node = sentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: '200px' },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  return (
    <div className="flex flex-col gap-4">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
      >
        <AnimatePresence mode="popLayout">
          {items.map((u) => (
            <ServiceCard
              key={u.id}
              usage={u}
              onClick={onSelect}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </AnimatePresence>
      </motion.div>

      <div className="flex items-center justify-center pb-4 pt-2 text-xs text-muted-foreground">
        {hasNextPage ? (
          <div ref={sentinelRef} className="flex items-center gap-2">
            {isFetchingNextPage && <Loader2 className="size-3.5 animate-spin" />}
            <span>{isFetchingNextPage ? 'Loading more…' : 'Scroll to load more'}</span>
          </div>
        ) : items.length > 0 ? (
          <span>Showing all {total} providers</span>
        ) : null}
      </div>
    </div>
  );
}
