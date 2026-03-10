'use client';

import {
  MultiSelectField,
  RadioGroupField,
  SelectInput,
  SliderField,
  TextInput,
} from '@/components/shared';
import type { MetaDataSchemaField } from '@/types/provider';
import { toSelectOptions } from '@/utils/selectUtils';
import { buildFieldRules, getDefaultValue } from '@/utils/validators';
import { type ReactNode, useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';

export interface DynamicProviderFieldsHandle {
  trigger: () => Promise<boolean>;
}

interface DynamicProviderFieldsProps {
  schema: MetaDataSchemaField[];
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
  onValidityChange?: (handle: DynamicProviderFieldsHandle) => void;
}

function FormRow({
  label,
  description,
  required,
  error,
  children,
}: {
  label: string;
  description?: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6 border-b border-border/40 py-4">
      <div className="flex-[0_0_50%]">
        <h3 className="text-[13px] font-medium text-foreground">
          {label}
          {required && <span className="ml-0.5 text-destructive">*</span>}
        </h3>
        {description && (
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex-[0_0_45%]">
        {children}
        {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
      </div>
    </div>
  );
}

function formatLabel(name: string): string {
  return name
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function resolveFieldType(
  field: MetaDataSchemaField,
):
  | 'input'
  | 'input_number'
  | 'radio'
  | 'datepicker'
  | 'daterangepicker'
  | 'datetime'
  | 'multiselect'
  | 'rangepicker'
  | 'select' {
  if (field.values && field.values.length > 0 && field.data_type !== 'list') {
    return 'select';
  }

  switch (field.data_type) {
    case 'string':
      return 'input';
    case 'float':
    case 'int':
    case 'integer':
      return 'input_number';
    case 'boolean':
      return 'radio';
    case 'date':
      return 'datepicker';
    case 'date range':
      return 'daterangepicker';
    case 'datetime':
      return 'datetime';
    case 'list':
      return 'multiselect';
    case 'rangepicker':
      return 'rangepicker';
    default:
      return 'input';
  }
}

function parseRange(description?: string): { min: number; max: number; step: number } {
  if (description) {
    const match = description.match(/(-?\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*(-?\d+(?:\.\d+)?)/);
    if (match) {
      const min = parseFloat(match[1]);
      const max = parseFloat(match[2]);
      const isFloat = match[1].includes('.') || match[2].includes('.');
      return { min, max, step: isFloat ? 0.1 : 1 };
    }
  }
  return { min: 0, max: 2, step: 1 };
}

function DateRangeField({
  field,
  currentValue,
  onFieldChange,
}: {
  field: MetaDataSchemaField;
  currentValue: unknown;
  onFieldChange: (value: unknown) => void;
}) {
  const rangeValue =
    currentValue && typeof currentValue === 'object' && !Array.isArray(currentValue)
      ? (currentValue as { start?: string; end?: string })
      : { start: '', end: '' };

  return (
    <div className="flex items-center gap-2">
      <TextInput
        name={`${field.name}-start`}
        type="date"
        value={rangeValue.start ?? ''}
        onChange={(e) => onFieldChange({ ...rangeValue, start: e.target.value })}
      />
      <span className="text-xs text-muted-foreground">to</span>
      <TextInput
        name={`${field.name}-end`}
        type="date"
        value={rangeValue.end ?? ''}
        onChange={(e) => onFieldChange({ ...rangeValue, end: e.target.value })}
      />
    </div>
  );
}

export default function DynamicProviderFields({
  schema,
  values,
  onChange,
  onValidityChange,
}: DynamicProviderFieldsProps) {
  useEffect(() => {
    const defaults: Record<string, unknown> = {};
    for (const field of schema) {
      if (values[field.name] == null) {
        const def = getDefaultValue(field);
        if (def !== undefined) defaults[field.name] = def;
      }
    }
    if (Object.keys(defaults).length > 0) {
      onChange({ ...values, ...defaults });
    }
  }, [schema]);

  const {
    control,
    trigger,
    formState: { errors },
  } = useForm({
    mode: 'onChange',
    values,
  });

  useEffect(() => {
    onValidityChange?.({ trigger });
  }, [onValidityChange, trigger]);

  const handleChange = (name: string, value: unknown) => {
    onChange({ ...values, [name]: value });
  };

  return (
    <>
      {schema.map((field) => {
        const isRequired = field.required === 1;
        const label = formatLabel(field.name);
        const fieldType = resolveFieldType(field);
        const fieldError = errors[field.name]?.message as string | undefined;
        const rules = buildFieldRules(field);

        switch (fieldType) {
          case 'select':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <SelectInput
                  name={field.name}
                  control={control}
                  rules={rules}
                  placeholder={`Select ${label.toLowerCase()}`}
                  options={
                    field.values
                      ? toSelectOptions(field.values, { valueKey: 'value', labelKey: 'label' })
                      : []
                  }
                  onValueChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          case 'input_number':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <Controller
                  name={field.name}
                  control={control}
                  rules={rules}
                  render={({ field: rhf }) => (
                    <TextInput
                      name={field.name}
                      type="number"
                      step={field.data_type === 'float' ? 'any' : '1'}
                      value={rhf.value != null ? String(rhf.value) : ''}
                      error={!!fieldError}
                      onChange={(e) => {
                        const raw = e.target.value;
                        if (raw === '') {
                          rhf.onChange(null);
                          handleChange(field.name, null);
                          return;
                        }
                        const parsed =
                          field.data_type === 'float' ? parseFloat(raw) : parseInt(raw, 10);
                        if (!isNaN(parsed)) {
                          rhf.onChange(parsed);
                          handleChange(field.name, parsed);
                        }
                      }}
                      onBlur={rhf.onBlur}
                      placeholder={field.description}
                    />
                  )}
                />
              </FormRow>
            );

          case 'radio':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <RadioGroupField
                  name={field.name}
                  control={control}
                  rules={rules}
                  orientation="horizontal"
                  options={[
                    { value: 'true', label: 'Yes' },
                    { value: 'false', label: 'No' },
                  ]}
                  transformValue={(v) => v === 'true'}
                  onValueChange={(v) => handleChange(field.name, v === 'true')}
                />
              </FormRow>
            );

          case 'datepicker':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <TextInput
                  name={field.name}
                  control={control}
                  rules={rules}
                  type="date"
                  error={!!fieldError}
                  onValueChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          case 'daterangepicker':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <Controller
                  name={field.name}
                  control={control}
                  rules={rules}
                  render={({ field: rhf }) => (
                    <DateRangeField
                      field={field}
                      currentValue={rhf.value}
                      onFieldChange={(v) => {
                        rhf.onChange(v);
                        handleChange(field.name, v);
                      }}
                    />
                  )}
                />
              </FormRow>
            );

          case 'datetime':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <TextInput
                  name={field.name}
                  control={control}
                  rules={rules}
                  type="datetime-local"
                  error={!!fieldError}
                  onValueChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          case 'multiselect':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <MultiSelectField
                  name={field.name}
                  control={control}
                  rules={rules}
                  options={field.values}
                  placeholder={`Add ${label.toLowerCase()}`}
                  onChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          case 'rangepicker': {
            const range = parseRange(field.description);
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <SliderField
                  name={field.name}
                  control={control}
                  rules={rules}
                  min={range.min}
                  max={range.max}
                  step={range.step}
                  onValueChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );
          }

          case 'input':
          default:
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <TextInput
                  name={field.name}
                  control={control}
                  rules={rules}
                  type={field.format === 'url' ? 'url' : 'text'}
                  error={!!fieldError}
                  placeholder={field.description}
                  onValueChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );
        }
      })}
    </>
  );
}
