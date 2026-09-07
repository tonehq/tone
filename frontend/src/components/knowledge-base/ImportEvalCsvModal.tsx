'use client';

import { useEffect, useRef, useState } from 'react';

import { CustomModal } from '@/components/shared';

interface ImportEvalCsvModalProps {
  open: boolean;
  uploading: boolean;
  onClose: () => void;
  onUpload: (file: File) => Promise<void>;
}

// CSV import, moved into a modal. Appends rows to the selected version.
export default function ImportEvalCsvModal({
  open,
  uploading,
  onClose,
  onUpload,
}: ImportEvalCsvModalProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (open) {
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    }
  }, [open]);

  const handleConfirm = async () => {
    if (!file) return;
    await onUpload(file);
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Import from CSV"
      description="Rows are appended to the selected version."
      confirmText="Upload"
      confirmLoading={uploading}
      confirmDisabled={!file}
      onConfirm={handleConfirm}
    >
      <div className="flex flex-col gap-3">
        <p className="text-xs text-muted-foreground">
          Required columns: <span className="font-mono">question</span>,{' '}
          <span className="font-mono">expected_answer</span>. Optional:{' '}
          <span className="font-mono">expected_source_snippet</span>,{' '}
          <span className="font-mono">category</span>,{' '}
          <span className="font-mono">external_id</span>.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full cursor-pointer text-xs text-muted-foreground file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary hover:file:bg-primary/20"
          disabled={uploading}
        />
      </div>
    </CustomModal>
  );
}
