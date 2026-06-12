'use client';

import React, { useMemo, useState } from 'react';

import { cn } from '@/utils/cn';
import { NODE_CATEGORIES, type NodeTypeMeta } from '@/components/workflows/nodeRegistry';
import type { WorkflowNodeType } from '@/types/workflow';

interface NodePaletteProps {
  onAdd: (type: WorkflowNodeType) => void;
}

const NodePalette: React.FC<NodePaletteProps> = ({ onAdd }) => {
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return NODE_CATEGORIES;
    return NODE_CATEGORIES.map((g) => ({
      ...g,
      items: g.items.filter(
        (i) => i.label.toLowerCase().includes(q) || i.description.toLowerCase().includes(q),
      ),
    })).filter((g) => g.items.length > 0);
  }, [query]);

  const onDragStart = (e: React.DragEvent, type: WorkflowNodeType) => {
    e.dataTransfer.setData('application/tone-node', type);
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-card/80 backdrop-blur">
      <div className="border-b border-border p-3">
        <div className="text-sm font-semibold text-foreground">Add node</div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search nodes…"
          className="mt-2 w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm outline-none ring-primary/40 placeholder:text-muted-foreground focus:ring-2"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {groups.map((group) => (
          <div key={group.heading} className="mb-4 last:mb-0">
            <div className="mb-1.5 px-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              {group.heading}
            </div>
            <div className="flex flex-col gap-1">
              {group.items.map((meta: NodeTypeMeta) => {
                const Icon = meta.icon;
                return (
                  <button
                    key={meta.type}
                    type="button"
                    draggable
                    onDragStart={(e) => onDragStart(e, meta.type)}
                    onClick={() => onAdd(meta.type)}
                    className="flex w-full cursor-grab items-center gap-2.5 rounded-lg border border-transparent px-2 py-2 text-left transition-colors hover:bg-accent active:scale-[.99] active:cursor-grabbing"
                  >
                    <span
                      className={cn(
                        'inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md',
                        meta.accent.chip,
                      )}
                    >
                      <Icon className="h-4 w-4" strokeWidth={2} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-foreground">
                        {meta.label}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {meta.description}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        {groups.length === 0 && (
          <div className="px-1 py-6 text-center text-sm text-muted-foreground">
            No matching nodes
          </div>
        )}
      </div>
    </aside>
  );
};

export default NodePalette;
