'use client';

import { CheckboxField, RadioGroupField, SelectInput, TextInput } from '@/components/shared';
import { Slider } from '@/components/ui/slider';
import type { MetaDataSchemaField } from '@/types/provider';
import { X } from 'lucide-react';
import { type KeyboardEvent, type ReactNode, useState } from 'react';

interface DynamicProviderFieldsProps {
  schema: MetaDataSchemaField[];
  values: Record<string, unknown>;
  onChange: (values: Record<string, unknown>) => void;
}

function FormRow({
  label,
  description,
  required,
  children,
}: {
  label: string;
  description?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-6">
      <div className="flex-[0_0_55%]">
        <h3 className="text-sm font-semibold text-foreground">
          {label}
          {required && <span className="ml-0.5 text-destructive">*</span>}
        </h3>
        {description && (
          <p className="mt-0.5 text-[13px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="flex-[0_0_40%]">{children}</div>
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

function MultiSelectField({
  field,
  currentValue,
  onFieldChange,
}: {
  field: MetaDataSchemaField;
  currentValue: unknown;
  onFieldChange: (value: unknown) => void;
}) {
  const [tagInput, setTagInput] = useState('');
  const selectedValues = Array.isArray(currentValue) ? (currentValue as string[]) : [];

  // If predefined values exist, render checkboxes
  if (field.values && field.values.length > 0) {
    return (
      <div className="flex flex-col gap-2">
        {field.values.map((opt) => {
          const isChecked = selectedValues.includes(opt.value);
          return (
            <CheckboxField
              key={opt.value}
              id={`${field.name}-${opt.value}`}
              label={opt.label}
              checked={isChecked}
              onCheckedChange={(checked) => {
                const next = checked
                  ? [...selectedValues, opt.value]
                  : selectedValues.filter((v) => v !== opt.value);
                onFieldChange(next);
              }}
            />
          );
        })}
      </div>
    );
  }

  // Otherwise render a tag input for free-form list
  const addTag = () => {
    const trimmed = tagInput.trim();
    if (trimmed && !selectedValues.includes(trimmed)) {
      onFieldChange([...selectedValues, trimmed]);
      setTagInput('');
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <TextInput
          name={`${field.name}-input`}
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addTag();
            }
          }}
          placeholder={`Add ${formatLabel(field.name).toLowerCase()}`}
        />
      </div>
      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {selectedValues.map((val) => (
            <span
              key={val}
              className="inline-flex items-center gap-1 rounded-md border bg-muted px-2 py-0.5 text-xs"
            >
              {val}
              <button
                type="button"
                onClick={() => onFieldChange(selectedValues.filter((v) => v !== val))}
                className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Parse "min-max" (e.g. "0-2") from description, fallback to 0–2. */
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
}: DynamicProviderFieldsProps) {
  const handleChange = (name: string, value: unknown) => {
    onChange({ ...values, [name]: value });
  };

  return (
    <>
      {schema.map((field) => {
        const currentValue = values[field.name];
        const isRequired = field.required === 1;
        const label = formatLabel(field.name);
        const fieldType = resolveFieldType(field);

        switch (fieldType) {
          // Single-select dropdown (values array present, non-list)
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
                  value={currentValue != null ? String(currentValue) : ''}
                  onValueChange={(v) => handleChange(field.name, v)}
                  placeholder={`Select ${label.toLowerCase()}`}
                  options={
                    field.values?.map((opt) => ({
                      value: opt.value,
                      label: opt.label,
                    })) ?? []
                  }
                />
              </FormRow>
            );

          // Number input (int / integer / float)
          case 'input_number':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <TextInput
                  name={field.name}
                  type="number"
                  step={field.data_type === 'float' ? 'any' : '1'}
                  value={currentValue != null ? String(currentValue) : ''}
                  onChange={(e) => {
                    const raw = e.target.value;
                    if (raw === '') {
                      handleChange(field.name, null);
                      return;
                    }
                    const parsed =
                      field.data_type === 'float' ? parseFloat(raw) : parseInt(raw, 10);
                    if (!isNaN(parsed)) {
                      handleChange(field.name, parsed);
                    }
                  }}
                  placeholder={field.description}
                />
              </FormRow>
            );

          // Boolean radio (Yes / No)
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
                  value={currentValue != null ? String(currentValue) : ''}
                  onValueChange={(v) => handleChange(field.name, v === 'true')}
                  orientation="horizontal"
                  options={[
                    { value: 'true', label: 'Yes' },
                    { value: 'false', label: 'No' },
                  ]}
                />
              </FormRow>
            );

          // Date picker (native)
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
                  type="date"
                  value={currentValue != null ? String(currentValue) : ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                />
              </FormRow>
            );

          // Date range picker (two date inputs)
          case 'daterangepicker':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <DateRangeField
                  field={field}
                  currentValue={currentValue}
                  onFieldChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          // Datetime picker (native)
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
                  type="datetime-local"
                  value={currentValue != null ? String(currentValue) : ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                />
              </FormRow>
            );

          // Multiselect (checkboxes if values exist, tag input otherwise)
          case 'multiselect':
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <MultiSelectField
                  field={field}
                  currentValue={currentValue}
                  onFieldChange={(v) => handleChange(field.name, v)}
                />
              </FormRow>
            );

          // Range picker (slider)
          case 'rangepicker': {
            const range = parseRange(field.description);
            const sliderValue = currentValue != null ? Number(currentValue) : range.min;
            return (
              <FormRow
                key={field.name}
                label={label}
                description={field.description}
                required={isRequired}
              >
                <div className="w-full px-1">
                  <Slider
                    value={[sliderValue]}
                    onValueChange={([v]) => handleChange(field.name, v)}
                    min={range.min}
                    max={range.max}
                    step={range.step}
                  />
                  <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                    <span>{range.min}</span>
                    <span>{sliderValue}</span>
                    <span>{range.max}</span>
                  </div>
                </div>
              </FormRow>
            );
          }

          // Default: text input (string)
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
                  type={field.format === 'url' ? 'url' : 'text'}
                  value={currentValue != null ? String(currentValue) : ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  placeholder={field.description}
                />
              </FormRow>
            );
        }
      })}
    </>
  );
}
