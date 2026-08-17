'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Save } from 'lucide-react';

import { CheckboxField, CustomButton, CustomModal, TextInput } from '@/components/shared';
import {
  getFieldSpecs,
  type ParamFieldSpec,
  type ParamSection,
} from '@/components/knowledge-base/optionParamSchemas';

type ParamValue = string | number | boolean | null;

interface OptionParamsModalProps {
  open: boolean;
  onClose: () => void;
  section: ParamSection;
  /** Selected option slug, e.g. "docling" / "recursive_char". */
  option: string;
  /** Existing params for that option (from the parent form's JSONB field). */
  initialValues: Record<string, unknown> | null | undefined;
  /** Called with the cleaned params object. Pass an empty object to clear. */
  onSave: (values: Record<string, unknown>) => void;
  /** Human title for the modal, e.g. "Tokeniser params — recursive_char". */
  title: string;
}

function inputToState(spec: ParamFieldSpec, raw: unknown): ParamValue {
  if (raw === undefined || raw === null) {
    return spec.defaultValue !== undefined ? (spec.defaultValue as ParamValue) : '';
  }
  if (spec.type === 'boolean') return Boolean(raw);
  if (spec.type === 'number') return String(raw);
  return String(raw);
}

function stateToOutput(spec: ParamFieldSpec, value: ParamValue): unknown {
  if (spec.type === 'boolean') return Boolean(value);
  if (spec.type === 'number') {
    if (value === '' || value === null || value === undefined) return undefined;
    const n = Number(value);
    return Number.isFinite(n) ? n : undefined;
  }
  const s = typeof value === 'string' ? value.trim() : '';
  return s === '' ? undefined : s;
}

export default function OptionParamsModal({
  open,
  onClose,
  section,
  option,
  initialValues,
  onSave,
  title,
}: OptionParamsModalProps) {
  // Referentially stable per (section, option) — prevents the seed effect
  // from re-firing on every parent render (which was wiping in-progress
  // edits).
  const specs = useMemo(() => getFieldSpecs(section, option), [section, option]);

  const [values, setValues] = useState<Record<string, ParamValue>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Read `initialValues` off a ref inside the effect so a fresh object
  // identity from the parent (paramsEditor state churn) never resets
  // in-progress user edits. The effect fires only when the modal opens or
  // the target option/section changes — the intentional re-seed moments.
  const initialValuesRef = useRef(initialValues);
  useEffect(() => {
    initialValuesRef.current = initialValues;
  }, [initialValues]);

  useEffect(() => {
    if (!open) return;
    const next: Record<string, ParamValue> = {};
    for (const spec of specs) {
      next[spec.key] = inputToState(spec, initialValuesRef.current?.[spec.key]);
    }
    setValues(next);
    setErrors({});
  }, [open, option, section, specs]);

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    for (const spec of specs) {
      if (spec.type === 'number') {
        const raw = values[spec.key];
        if (raw === '' || raw === null || raw === undefined) continue;
        const n = Number(raw);
        if (!Number.isFinite(n)) {
          next[spec.key] = 'Must be a number.';
          continue;
        }
        if (spec.min !== undefined && n < spec.min) {
          next[spec.key] = `Must be ≥ ${spec.min}.`;
        }
      }
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    const out: Record<string, unknown> = {};
    for (const spec of specs) {
      const v = stateToOutput(spec, values[spec.key]);
      if (v !== undefined) out[spec.key] = v;
    }
    onSave(out);
    onClose();
  };

  const handleReset = () => {
    const next: Record<string, ParamValue> = {};
    for (const spec of specs) {
      next[spec.key] = spec.defaultValue !== undefined ? (spec.defaultValue as ParamValue) : '';
    }
    setValues(next);
    setErrors({});
  };

  const footer = (
    <div className="flex w-full items-center justify-between gap-2">
      <CustomButton type="default" onClick={handleReset}>
        Reset to defaults
      </CustomButton>
      <div className="flex items-center gap-2">
        <CustomButton type="default" onClick={onClose}>
          Cancel
        </CustomButton>
        <CustomButton type="primary" onClick={handleSave}>
          <Save className="mr-1 size-4" />
          Save params
        </CustomButton>
      </div>
    </div>
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={title}
      description="These parameters are passed to the selected option. Leave blank to use its built-in defaults."
      width="sm:max-w-lg"
      footer={footer}
    >
      {specs.length === 0 ? (
        <div className="py-6 text-sm text-muted-foreground">
          This option takes no user-editable parameters.
        </div>
      ) : (
        <div className="flex flex-col gap-4 py-2">
          {specs.map((spec) => {
            const value = values[spec.key];
            if (spec.type === 'boolean') {
              return (
                <CheckboxField
                  key={spec.key}
                  label={spec.label}
                  checked={Boolean(value)}
                  onCheckedChange={(v) => setValues((s) => ({ ...s, [spec.key]: Boolean(v) }))}
                  helperText={spec.helperText}
                />
              );
            }
            return (
              <TextInput
                key={spec.key}
                name={spec.key}
                label={spec.label}
                type={spec.type === 'number' ? 'number' : 'text'}
                min={spec.min}
                step={spec.step}
                placeholder={spec.placeholder}
                value={value === null || value === undefined ? '' : String(value)}
                onChange={(e) => setValues((s) => ({ ...s, [spec.key]: e.target.value }))}
                error={!!errors[spec.key]}
                helperText={errors[spec.key] ?? spec.helperText}
              />
            );
          })}
        </div>
      )}
    </CustomModal>
  );
}
