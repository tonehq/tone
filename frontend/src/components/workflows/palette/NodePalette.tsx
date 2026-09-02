'use client';

import React, { useMemo, useState } from 'react';
import { GripVertical } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import SearchBar from '@/components/shared/SearchBar';
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
    <aside className="flex h-full w-72 shrink-0 flex-col border-l border-border bg-card/60 backdrop-blur">
      <div className="border-b border-border px-4 py-3.5">
        <div className="text-sm font-semibold text-foreground">Add node</div>
        <p className="mt-0.5 text-xs text-muted-foreground">Drag onto the canvas or click to add</p>
        <SearchBar
          value={query}
          onChange={setQuery}
          debounceMs={0}
          placeholder="Search nodes…"
          aria-label="Search node types"
          containerClassName="mt-3 max-w-none"
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
                  <CustomButton
                    key={meta.type}
                    type="text"
                    fullWidth
                    draggable
                    onDragStart={(e: React.DragEvent) => onDragStart(e, meta.type)}
                    onClick={() => onAdd(meta.type)}
                    className="group !h-auto cursor-grab !justify-start gap-3 rounded-xl border border-border bg-card px-2.5 py-2 text-left shadow-sm transition-all hover:-translate-y-px hover:border-primary/30 hover:bg-card active:scale-[.99] active:cursor-grabbing"
                  >
                    <span
                      className={cn(
                        'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                        meta.accent.chip,
                      )}
                    >
                      <Icon className="h-[18px] w-[18px]" strokeWidth={2} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-foreground">
                        {meta.label}
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">
                        {meta.description}
                      </span>
                    </span>
                    <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground/40" />
                  </CustomButton>
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
