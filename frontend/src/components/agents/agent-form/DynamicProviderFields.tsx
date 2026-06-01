'use client';

import { useFormContext, useWatch } from 'react-hook-form';

import { SelectInput, SliderField, TextInput } from '@/components/shared';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import type { MetaDataSchemaField } from '@/types/provider';

/**
 * Renders form fields dynamically from a provider's meta_data_schema.
 *
 * Each field value is stored at `{basePath}.{field.name}` in the form state.
 * For example, basePath="config.llm_settings" + field.name="temperature"
 * → form path "config.llm_settings.temperature".
 *
 * Fields that are already rendered explicitly by the parent step (like
 * temperature/max_tokens in AiStep, or speed in VoiceStep) should be passed
 * via the `exclude` prop to avoid duplication.
 */
interface DynamicProviderFieldsProps {
  fields: MetaDataSchemaField[];
  basePath: string;
  exclude?: string[];
}

export default function DynamicProviderFields({
  fields,
  basePath,
  exclude = [],
}: DynamicProviderFieldsProps) {
  const { control, setValue } = useFormContext();

  const visibleFields = fields.filter((f) => !exclude.includes(f.name));

  if (visibleFields.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {visibleFields.map((field) => (
        <FieldRenderer
          key={field.name}
          field={field}
          basePath={basePath}
          control={control}
          setValue={setValue}
        />
      ))}
    </div>
  );
}

function FieldRenderer({
  field,
  basePath,
  control,
  setValue,
}: {
  field: MetaDataSchemaField;
  basePath: string;
  control: ReturnType<typeof useFormContext>['control'];
  setValue: ReturnType<typeof useFormContext>['setValue'];
}) {
  const path = `${basePath}.${field.name}` as never;
  const currentValue = useWatch({ control, name: path });
  const isRequired = !!field.required;

  const validator =
    typeof field.validator === 'object' && field.validator !== null ? field.validator : {};
  const min = validator.min as number | undefined;
  const max = validator.max as number | undefined;
  const label = formatLabel(field.name) + (isRequired ? ' *' : '');

  // Select with predefined options
  if (field.type === 'select' && field.options) {
    return (
      <SelectInput
        name={path}
        label={label}
        options={field.options.map((o) => ({ value: o, label: o }))}
        value={String(currentValue ?? '')}
        onValueChange={(v) => setValue(path, (v || null) as never, { shouldDirty: true })}
        helperText={field.description}
      />
    );
  }

  // Boolean toggle
  if (field.data_type === 'boolean' || field.type === 'radio') {
    return (
      <div className="flex items-center justify-between gap-3 rounded-md border border-border/50 px-3 py-2.5">
        <div className="flex flex-col gap-0.5">
          <Label className="text-sm font-medium">{label}</Label>
          {field.description && (
            <span className="text-[11px] text-muted-foreground">{field.description}</span>
          )}
        </div>
        <Switch
          checked={!!currentValue}
          onCheckedChange={(checked) => setValue(path, checked as never, { shouldDirty: true })}
        />
      </div>
    );
  }

  // Float with min/max — render as slider with static min/mid/max labels
  if (field.data_type === 'float' && min !== undefined && max !== undefined) {
    const mid = Math.round(((min + max) / 2) * 10) / 10;
    return (
      <div>
        <SliderField
          name={path}
          label={label}
          control={control}
          min={min}
          max={max}
          step={0.1}
          showLabels={false}
          helperText={field.description}
        />
        <div className="mt-1 flex justify-between px-1 text-xs text-muted-foreground">
          <span>{min}</span>
          <span>{mid}</span>
          <span>{max}</span>
        </div>
      </div>
    );
  }

  // Integer / float without range — render as number input
  if (field.data_type === 'float' || field.data_type === 'integer' || field.data_type === 'int') {
    return (
      <TextInput
        name={path}
        label={label}
        control={control}
        type="number"
        placeholder={min !== undefined ? `Min: ${min}` : undefined}
        helperText={field.description}
      />
    );
  }

  // Default: string input
  return (
    <TextInput
      name={path}
      label={formatLabel(field.name)}
      control={control}
      placeholder={field.description || undefined}
      helperText={field.description}
    />
  );
}

/** Convert snake_case field name to a readable label. */
function formatLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b[a-z]/g, (c) => c.toUpperCase());
}
