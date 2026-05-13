'use client';

import { CustomButton, TextInput } from '@/components/shared';
import { Plus, Trash2 } from 'lucide-react';

export interface HttpHeaderRow {
  id: string;
  key: string;
  value: string;
}

interface HttpHeadersBuilderProps {
  rows: HttpHeaderRow[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  onChange: (id: string, patch: Partial<Pick<HttpHeaderRow, 'key' | 'value'>>) => void;
}

export default function HttpHeadersBuilder({
  rows,
  onAdd,
  onRemove,
  onChange,
}: HttpHeadersBuilderProps) {
  if (rows.length === 0) {
    return (
      <CustomButton
        type="default"
        fullWidth
        icon={<Plus size={14} />}
        onClick={onAdd}
        className="border-dashed py-3 text-[12px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
      >
        Add header
      </CustomButton>
    );
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div
          key={row.id}
          className="group rounded-lg border border-border/60 bg-card p-3 transition-colors hover:border-border"
        >
          <div className="flex items-start gap-2">
            <div className="grid min-w-0 flex-1 grid-cols-2 gap-2">
              <TextInput
                name={`header-key-${row.id}`}
                placeholder="Header name"
                value={row.key}
                onChange={(e) => onChange(row.id, { key: e.target.value })}
                className="font-mono text-[13px]"
              />
              <TextInput
                name={`header-value-${row.id}`}
                placeholder="Header value"
                value={row.value}
                onChange={(e) => onChange(row.id, { value: e.target.value })}
                className="font-mono text-[13px]"
              />
            </div>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={() => onRemove(row.id)}
              className="mt-1 text-muted-foreground opacity-0 transition-all hover:text-destructive group-hover:opacity-100"
              aria-label="Remove header"
            >
              <Trash2 size={13} />
            </CustomButton>
          </div>
        </div>
      ))}
      <CustomButton
        type="default"
        size="sm"
        fullWidth
        icon={<Plus size={12} />}
        onClick={onAdd}
        className="border-dashed text-[12px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
      >
        Add header
      </CustomButton>
    </div>
  );
}
