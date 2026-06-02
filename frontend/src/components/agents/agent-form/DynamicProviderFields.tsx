'use client';

import type { RegisterOptions } from 'react-hook-form';
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
  /** Model-level meta_data — overrides provider schema validator limits per field. */
  modelMetaData?: Record<string, unknown> | null;
}

export default function DynamicProviderFields({
  fields,
  basePath,
  exclude = [],
  modelMetaData,
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
          modelMetaData={modelMetaData}
        />
      ))}
    </div>
  );
}

/** Safely extract min/max from a field's validator + optional model override. */
function getFieldRange(field: MetaDataSchemaField, modelMetaData?: Record<string, unknown> | null) {
  const validatorObj =
    typeof field.validator === 'object' && field.validator !== null ? field.validator : {};
  const min = validatorObj.min as number | undefined;
  const modelMax =
    modelMetaData && field.name in modelMetaData
      ? (modelMetaData[field.name] as number)
      : undefined;
  const max = modelMax ?? (validatorObj.max as number | undefined);
  return { min, max };
}

function FieldRenderer({
  field,
  basePath,
  control,
  setValue,
  modelMetaData,
}: {
  field: MetaDataSchemaField;
  basePath: string;
  control: ReturnType<typeof useFormContext>['control'];
  setValue: ReturnType<typeof useFormContext>['setValue'];
  modelMetaData?: Record<string, unknown> | null;
}) {
  const path = `${basePath}.${field.name}` as never;
  const currentValue = useWatch({ control, name: path });
  const isRequired = !!field.required;

  const { min, max } = getFieldRange(field, modelMetaData);
  const label = formatLabel(field.name) + (isRequired ? ' *' : '');
  const rules = buildValidationRules(field, min, max);

  // Select with predefined options
  if (field.type === 'select' && field.options) {
    return (
      <SelectInput
        name={path}
        label={label}
        control={control}
        rules={rules}
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

  // Float with min/max — render as slider (UI enforces range, no rules needed)
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

  // Integer / float without full range — render as number input
  if (field.data_type === 'float' || field.data_type === 'integer' || field.data_type === 'int') {
    return (
      <TextInput
        name={path}
        label={label}
        control={control}
        rules={rules}
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
      label={label}
      control={control}
      rules={rules}
      placeholder={field.description || undefined}
      helperText={field.description}
    />
  );
}

/** Build React Hook Form validation rules from a meta_data_schema field. */
function buildValidationRules(
  field: MetaDataSchemaField,
  min?: number,
  max?: number,
): RegisterOptions {
  const rules: RegisterOptions = {};
  const label = formatLabel(field.name);

  if (field.required) {
    rules.required = `${label} is required`;
  }

  const isNumeric =
    field.data_type === 'float' || field.data_type === 'integer' || field.data_type === 'int';
  const hasOptions = field.options && field.options.length > 0;
  const isArray = field.data_type === 'array' || field.data_type === 'list';

  if (isNumeric || hasOptions || isArray) {
    rules.validate = (value: unknown) => {
      if (value === null || value === undefined || value === '') return true;

      if (isNumeric) {
        const num = Number(value);
        if (isNaN(num)) return `${label} must be a valid number`;
        if (field.data_type !== 'float' && !Number.isInteger(num))
          return `${label} must be a whole number`;
        if (min !== undefined && num < min) return `${label} must be at least ${min}`;
        if (max !== undefined && num > max) return `${label} must be at most ${max}`;
      }

      if (hasOptions && !field.options!.includes(String(value))) {
        return `${label} must be one of: ${field.options!.join(', ')}`;
      }

      if (isArray && !Array.isArray(value)) {
        return `${label} must be a list`;
      }

      return true;
    };
  }

  return rules;
}

/** Convert snake_case field name to a readable label. */
function formatLabel(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b[a-z]/g, (c) => c.toUpperCase());
}
