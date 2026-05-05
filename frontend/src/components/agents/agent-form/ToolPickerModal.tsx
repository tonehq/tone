'use client';

import { CustomButton, CustomModal, TextInput } from '@/components/shared';
import { Checkbox } from '@/components/ui/checkbox';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { Search, Wrench } from 'lucide-react';
import { useMemo, useState } from 'react';

interface ToolPickerModalProps {
  open: boolean;
  onClose: () => void;
  allTools: Tool[];
  attachedToolIds: number[];
  onAttach: (toolIds: number[]) => Promise<void>;
  loading?: boolean;
}

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-500/15 text-emerald-600',
  POST: 'bg-blue-500/15 text-blue-600',
  PUT: 'bg-amber-500/15 text-amber-600',
  DELETE: 'bg-red-500/15 text-red-600',
  PATCH: 'bg-violet-500/15 text-violet-600',
};

export default function ToolPickerModal({
  open,
  onClose,
  allTools,
  attachedToolIds,
  onAttach,
  loading,
}: ToolPickerModalProps) {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [attaching, setAttaching] = useState(false);

  const availableTools = useMemo(() => {
    const attached = new Set(attachedToolIds);
    let filtered = allTools.filter((t) => !attached.has(t.id) && t.is_active);
    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q),
      );
    }
    return filtered;
  }, [allTools, attachedToolIds, search]);

  const toggleSelect = (toolId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(toolId)) next.delete(toolId);
      else next.add(toolId);
      return next;
    });
  };

  const handleAttach = async () => {
    if (selected.size === 0) return;
    setAttaching(true);
    try {
      await onAttach(Array.from(selected));
      setSelected(new Set());
      setSearch('');
      onClose();
    } catch {
      // Error handled by parent
    } finally {
      setAttaching(false);
    }
  };

  const handleClose = () => {
    setSelected(new Set());
    setSearch('');
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Add Tools"
      description="Select tools to attach to this agent."
      width="sm:max-w-lg"
      footer={
        <>
          <CustomButton type="default" onClick={handleClose} disabled={attaching}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={handleAttach}
            loading={attaching}
            disabled={selected.size === 0}
          >
            Attach {selected.size > 0 ? `(${selected.size})` : ''}
          </CustomButton>
        </>
      }
    >
      <div className="space-y-3">
        <TextInput
          name="tool-picker-search"
          placeholder="Search tools..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          leftIcon={<Search size={16} />}
        />

        <div className="max-h-[320px] space-y-1.5 overflow-y-auto">
          {loading && (
            <div className="space-y-2 py-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-muted" />
              ))}
            </div>
          )}

          {!loading && availableTools.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Wrench size={20} className="text-muted-foreground" />
              <p className="mt-2 text-[13px] text-muted-foreground">
                {search
                  ? 'No tools match your search.'
                  : attachedToolIds.length === allTools.length
                    ? 'All tools are already attached.'
                    : 'No tools available. Create one first.'}
              </p>
            </div>
          )}

          {!loading &&
            availableTools.map((tool) => {
              const isSelected = selected.has(tool.id);
              const m = tool.method?.toUpperCase() ?? 'POST';
              return (
                <div
                  key={tool.id}
                  className={cn(
                    'flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors',
                    isSelected
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-border/60 bg-background hover:bg-muted/30',
                  )}
                  onClick={() => toggleSelect(tool.id)}
                >
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => toggleSelect(tool.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[13px] font-medium text-foreground">
                        {tool.name}
                      </span>
                      <span
                        className={cn(
                          'shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-semibold',
                          METHOD_COLORS[m] ?? 'bg-muted text-muted-foreground',
                        )}
                      >
                        {m}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
                      {tool.description}
                    </p>
                  </div>
                </div>
              );
            })}
        </div>
      </div>
    </CustomModal>
  );
}
