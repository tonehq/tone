import type { MetaDataSchemaField, ValidatorFn } from '@/types/provider';
import type { RegisterOptions } from 'react-hook-form';

function url_validator(value: unknown): string | true {
  if (value == null || value === '') return true;
  try {
    new URL(String(value));
    return true;
  } catch {
    return 'Please enter a valid URL';
  }
}

function range_validator(value: unknown, field: MetaDataSchemaField): string | true {
  if (value == null || value === '') return true;
  const num = Number(value);
  if (isNaN(num)) return 'Must be a number';

  const match = field.description?.match(/(-?\d+(?:\.\d+)?)\s*(?:[-–]|to)\s*(-?\d+(?:\.\d+)?)/);
  if (match) {
    const min = parseFloat(match[1]);
    const max = parseFloat(match[2]);
    if (num < min || num > max) return `Must be between ${min} and ${max}`;
  }
  return true;
}

function min_validator(value: unknown, field: MetaDataSchemaField): string | true {
  if (value == null || value === '') return true;
  const num = Number(value);
  if (isNaN(num)) return 'Must be a number';

  const match = field.description?.match(/Min:\s*(-?\d+(?:\.\d+)?)/i);
  if (match) {
    const min = parseFloat(match[1]);
    if (num < min) return `Must be at least ${min}`;
  }
  return true;
}

const VALIDATORS: Record<string, ValidatorFn> = {
  url_validator,
  range_validator,
  min_validator,
};

export function buildFieldRules(field: MetaDataSchemaField): RegisterOptions {
  const rules: RegisterOptions = {};

  if (field.required === 1 && field.data_type !== 'rangepicker') {
    rules.required = 'Please enter a value for this field';
  }

  const validatorFn = VALIDATORS[field.validator];
  if (validatorFn) {
    rules.validate = (value: unknown) => validatorFn(value, field);
  }

  return rules;
}

export function getDefaultValue(field: MetaDataSchemaField): number | undefined {
  if (field.validator === 'min_validator') {
    const match = field.description?.match(/Min:\s*(-?\d+(?:\.\d+)?)/i);
    if (match) return parseFloat(match[1]);
  }
  return undefined;
}
