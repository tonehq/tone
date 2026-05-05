'use client';

import { CustomButton, SelectInput, TextInput } from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import type { ToolParameterProperty, ToolParameterType, ToolParametersSchema } from '@/types/tool';
import { Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

interface ParameterRow {
  id: string;
  name: string;
  type: ToolParameterType;
  description: string;
  required: boolean;
}

interface ParameterBuilderProps {
  value: ToolParametersSchema;
  onChange: (schema: ToolParametersSchema) => void;
}

const TYPE_OPTIONS = [
  { value: 'string', label: 'String' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Integer' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'array', label: 'Array' },
];

let rowIdCounter = 0;
const nextRowId = () => `param-${++rowIdCounter}`;

function schemaToRows(schema: ToolParametersSchema): ParameterRow[] {
  const properties = schema?.properties ?? {};
  const required = schema?.required ?? [];
  return Object.entries(properties).map(([name, prop]) => ({
    id: nextRowId(),
    name,
    type: (prop as ToolParameterProperty).type ?? 'string',
    description: (prop as ToolParameterProperty).description ?? '',
    required: required.includes(name),
  }));
}

function rowsToSchema(rows: ParameterRow[]): ToolParametersSchema {
  if (rows.length === 0) return {};
  const properties: Record<string, ToolParameterProperty> = {};
  const required: string[] = [];
  for (const row of rows) {
    if (!row.name.trim()) continue;
    properties[row.name.trim()] = {
      type: row.type,
      description: row.description,
    };
    if (row.required) required.push(row.name.trim());
  }
  return {
    type: 'object',
    properties,
    ...(required.length > 0 ? { required } : {}),
  };
}

export default function ParameterBuilder({ value, onChange }: ParameterBuilderProps) {
  const [rows, setRows] = useState<ParameterRow[]>(() => schemaToRows(value));

  useEffect(() => {
    const incoming = schemaToRows(value);
    if (incoming.length === 0 && rows.length === 0) return;
    if (JSON.stringify(rowsToSchema(rows)) !== JSON.stringify(value)) {
      setRows(incoming);
    }
    // Only sync from parent when value reference changes
  }, [value]);

  const emitChange = useCallback(
    (updated: ParameterRow[]) => {
      setRows(updated);
      onChange(rowsToSchema(updated));
    },
    [onChange],
  );

  const addRow = () => {
    emitChange([
      ...rows,
      { id: nextRowId(), name: '', type: 'string', description: '', required: false },
    ]);
  };

  const removeRow = (id: string) => {
    emitChange(rows.filter((r) => r.id !== id));
  };

  const updateRow = (id: string, patch: Partial<ParameterRow>) => {
    emitChange(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  if (rows.length === 0) {
    return (
      <CustomButton
        type="default"
        fullWidth
        icon={<Plus size={14} />}
        onClick={addRow}
        className="border-dashed py-3 text-[12px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
      >
        Add parameter
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
            <div className="grid min-w-0 flex-1 grid-cols-[1fr_110px] gap-2">
              <TextInput
                name={`param-name-${row.id}`}
                placeholder="parameter_name"
                value={row.name}
                onChange={(e) => updateRow(row.id, { name: e.target.value })}
                className="font-mono text-[13px]"
              />
              <SelectInput
                name={`param-type-${row.id}`}
                options={TYPE_OPTIONS}
                value={row.type}
                onValueChange={(v) => updateRow(row.id, { type: v as ToolParameterType })}
              />
              <div className="col-span-2">
                <TextInput
                  name={`param-desc-${row.id}`}
                  placeholder="Description shown to LLM"
                  value={row.description}
                  onChange={(e) => updateRow(row.id, { description: e.target.value })}
                  className="text-[13px]"
                />
              </div>
            </div>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={() => removeRow(row.id)}
              className="mt-1 text-muted-foreground opacity-0 transition-all hover:text-destructive group-hover:opacity-100"
              aria-label="Remove parameter"
            >
              <Trash2 size={13} />
            </CustomButton>
          </div>
          <div className="mt-2 border-t border-border/40 pt-2">
            <CheckboxField
              id={`param-req-${row.id}`}
              label="Required"
              checked={row.required}
              onCheckedChange={(checked) => updateRow(row.id, { required: !!checked })}
            />
          </div>
        </div>
      ))}
      <CustomButton
        type="default"
        size="sm"
        fullWidth
        icon={<Plus size={12} />}
        onClick={addRow}
        className="border-dashed text-[12px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
      >
        Add parameter
      </CustomButton>
    </div>
  );
}
