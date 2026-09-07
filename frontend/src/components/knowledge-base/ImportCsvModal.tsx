'use client';

import { useRef, useState } from 'react';

import { CustomModal } from '@/components/shared';
import { useUploadEvalQuestionsCsv } from '@/lib/api/evals';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface ImportCsvModalProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  versionId: string | null;
}

// CSV import moved into a modal so the Manage-Evals toolbar stays compact and
// the questions list isn't pushed down by an always-open import card.
export default function ImportCsvModal({
  open,
  onClose,
  uploadId,
  versionId,
}: ImportCsvModalProps) {
  const uploadCsvMutation = useUploadEvalQuestionsCsv(uploadId);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const reset = () => {
    setCsvFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleClose = () => {
    if (uploadCsvMutation.isPending) return;
    reset();
    onClose();
  };

  const handleUpload = async () => {
    if (!csvFile || !versionId || uploadCsvMutation.isPending) return;
    try {
      const summary = await uploadCsvMutation.mutateAsync({ versionId, file: csvFile });
      showToast.success(
        'Questions imported',
        `Added ${summary.question_count} question(s) from ${csvFile.name}.`,
      );
      reset();
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={handleClose}
      title="Import from CSV"
      confirmText="Upload"
      onConfirm={handleUpload}
      confirmLoading={uploadCsvMutation.isPending}
      confirmDisabled={!csvFile || !versionId || uploadCsvMutation.isPending}
    >
      <div className="flex flex-col gap-3">
        <p className="text-xs text-muted-foreground">
          Required columns: <span className="font-mono">question</span>,{' '}
          <span className="font-mono">expected_answer</span>. Optional:{' '}
          <span className="font-mono">expected_source_snippet</span>,{' '}
          <span className="font-mono">category</span>, <span className="font-mono">external_id</span>
          . Rows are appended to the selected version.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
          className="block w-full cursor-pointer text-xs text-muted-foreground file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary hover:file:bg-primary/20"
          disabled={uploadCsvMutation.isPending || !versionId}
        />
      </div>
    </CustomModal>
  );
}
