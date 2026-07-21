'use client';

import { FileUp } from 'lucide-react';
import { useEffect, useRef, useState, type ReactNode } from 'react';

import { CustomButton } from '@/components/shared';
import { showToast } from '@/utils/toast';

/**
 * The shared contact-import file picker: a "Choose file" button + selected-filename
 * display + client-side extension validation + a supported-types hint, with an optional
 * right-aligned slot for a "Download sample" affordance.
 *
 * WHAT: validates the picked file's extension against `allowedExtensions` on select —
 * a disallowed type is rejected (inline error + toast) and the value is cleared, so the
 * parent never receives an unsupported file. Clearing the parent's `value` (e.g. on a
 * modal reset) also clears the native input.
 *
 * WHEN: reuse in every contact-import modal (the dormant SyncContactsModal and the
 * UploadContactsModal) so there is ONE file-input + validation implementation.
 */
export interface ContactFileInputProps {
  /** The native `<input accept>` value (MIME + extension hints for the OS file dialog). */
  accept: string;
  /** Allowed extensions, dot-prefixed (e.g. `['.csv', '.xlsx']`); matched case-insensitively. */
  allowedExtensions: string[];
  /** The currently selected file (owned by the parent). */
  value: File | null;
  /** Called with the picked file, or `null` when cleared/rejected. */
  onChange: (file: File | null) => void;
  /** Field label above the control. */
  label?: string;
  /** Helper text shown below the control when there is no validation error. */
  hint?: string;
  /** Right-aligned slot next to the label — typically a "Download sample" button. */
  sampleSlot?: ReactNode;
}

function hasAllowedExtension(fileName: string, allowed: string[]): boolean {
  const lower = fileName.toLowerCase();
  return allowed.some((ext) => lower.endsWith(ext.toLowerCase()));
}

export default function ContactFileInput({
  accept,
  allowedExtensions,
  value,
  onChange,
  label = 'File',
  hint,
  sampleSlot,
}: ContactFileInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const allowedLabel = allowedExtensions.join(', ');

  // Keep the native input in sync when the parent clears the value (e.g. modal reset), so
  // the previously-chosen filename doesn't linger and a stale error is cleared.
  useEffect(() => {
    if (value === null) {
      if (inputRef.current) inputRef.current.value = '';
      setError(null);
    }
  }, [value]);

  const handleSelect = (file: File | null) => {
    if (!file) {
      setError(null);
      onChange(null);
      return;
    }
    if (!hasAllowedExtension(file.name, allowedExtensions)) {
      const message = `Unsupported file type. Please upload a ${allowedLabel} file.`;
      setError(message);
      showToast.error(message);
      onChange(null);
      if (inputRef.current) inputRef.current.value = '';
      return;
    }
    setError(null);
    onChange(file);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground">{label}</span>
        {sampleSlot}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => handleSelect(e.target.files?.[0] ?? null)}
      />
      <div className="flex items-center gap-3 rounded-lg border border-input bg-background px-3 py-2">
        <CustomButton
          type="default"
          size="sm"
          icon={<FileUp className="size-4" />}
          onClick={() => inputRef.current?.click()}
        >
          Choose file
        </CustomButton>
        <span
          className={`min-w-0 flex-1 truncate text-sm ${
            value ? 'text-foreground' : 'text-muted-foreground'
          }`}
          title={value?.name}
        >
          {value?.name ?? 'No file chosen'}
        </span>
      </div>
      {error ? (
        <p className="text-xs text-red-600" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}
