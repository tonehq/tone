'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { FileUp, Loader2, Pencil, Play, Plus, Trash2 } from 'lucide-react';

import {
  CustomButton,
  CustomModal,
  CustomTooltip,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import {
  useAddManualEvalQuestions,
  useDeleteEvalQuestion,
  useEvalQuestions,
  useTriggerEvalRun,
  useUpdateEvalQuestion,
  useUploadEvalQuestionsCsv,
} from '@/lib/api/evals';
import { useIngestionRuns } from '@/lib/api/ingestion-runs';
import type { EvalQuestion, ManualQuestionInput, UpdateQuestionPatch } from '@/types/eval';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface ManualEvalsModalProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
}

interface DraftQuestion {
  question: string;
  expected_answer: string;
  expected_source_snippet: string;
  category: string;
}

const EMPTY_DRAFT: DraftQuestion = {
  question: '',
  expected_answer: '',
  expected_source_snippet: '',
  category: '',
};

// Human label for the `generated_by_model` audit tag. LLM-generated rows use
// the model name (e.g. 'gpt-4o'); benchmark imports use the source key
// (e.g. 'hotpotqa-mini'); manual rows are always 'manual'.
function sourceBadge(row: EvalQuestion): { label: string; className: string } {
  const src = row.generated_by_model;
  if (!src) return { label: 'unknown', className: 'bg-muted text-muted-foreground' };
  if (src === 'manual') {
    return {
      label: 'manual',
      className:
        'bg-primary/10 text-primary ring-1 ring-primary/20 dark:bg-primary/20 dark:text-primary-foreground',
    };
  }
  return {
    label: src,
    className: 'bg-muted text-muted-foreground ring-1 ring-border/60',
  };
}

export default function ManualEvalsModal({ open, onClose, uploadId }: ManualEvalsModalProps) {
  const { data: questions = [], isLoading } = useEvalQuestions(open ? uploadId : null);
  const addMutation = useAddManualEvalQuestions(uploadId);
  const updateMutation = useUpdateEvalQuestion(uploadId);
  const deleteMutation = useDeleteEvalQuestion(uploadId);
  const runMutation = useTriggerEvalRun(uploadId);
  const uploadCsvMutation = useUploadEvalQuestionsCsv(uploadId);
  const csvInputRef = useRef<HTMLInputElement | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const { data: runsResp } = useIngestionRuns(open ? uploadId : null, {
    status_filter: ['ready'],
    page_size: 100,
    sort_by: 'run_number',
    sort_order: 'desc',
  });
  const readyRuns = useMemo(() => runsResp?.data ?? [], [runsResp]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  useEffect(() => {
    if (!open || readyRuns.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !readyRuns.some((r) => r.id === selectedRunId)) {
      const active = readyRuns.find((r) => r.is_active);
      setSelectedRunId((active ?? readyRuns[0]).id);
    }
  }, [open, readyRuns, selectedRunId]);

  const runOptions = useMemo(
    () =>
      readyRuns.map((r) => ({
        value: r.id,
        label: `Run #${r.run_number}${r.is_active ? ' (active)' : ''} · ${r.parser} · ${r.embedding_model}`,
      })),
    [readyRuns],
  );

  const [draft, setDraft] = useState<DraftQuestion>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<DraftQuestion>(EMPTY_DRAFT);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  // Two-step delete: clicking the trash icon opens a themed confirm modal
  // (matches the destructive-confirm pattern used elsewhere in the app —
  // `CustomModal` with `confirmType="danger"`), NOT the native browser
  // `window.confirm` popup.
  const [deleteConfirmRow, setDeleteConfirmRow] = useState<EvalQuestion | null>(null);

  // Trim once at read-time so we don't fight React strict-mode double-renders
  // over what "empty" means. Backend enforces min_length=1 too.
  const canAddDraft = draft.question.trim().length > 0 && draft.expected_answer.trim().length > 0;
  const canSaveEdit =
    editDraft.question.trim().length > 0 && editDraft.expected_answer.trim().length > 0;

  const manualCount = useMemo(
    () => questions.filter((q) => q.generated_by_model === 'manual').length,
    [questions],
  );

  const handleAdd = async () => {
    if (!canAddDraft) return;
    const payload: ManualQuestionInput = {
      question: draft.question.trim(),
      expected_answer: draft.expected_answer.trim(),
      expected_source_snippet: draft.expected_source_snippet.trim() || null,
      category: draft.category.trim() || null,
    };
    try {
      await addMutation.mutateAsync([payload]);
      showToast.success('Question added', 'Your Q&A pair has been saved.');
      setDraft(EMPTY_DRAFT);
    } catch (error) {
      handleApiError(error);
    }
  };

  const startEdit = (row: EvalQuestion) => {
    setEditingId(row.id);
    setEditDraft({
      question: row.question,
      expected_answer: row.expected_answer,
      expected_source_snippet: row.expected_source_snippet ?? '',
      category: row.category ?? '',
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft(EMPTY_DRAFT);
  };

  const handleSaveEdit = async () => {
    if (!editingId || !canSaveEdit) return;
    const patch: UpdateQuestionPatch = {
      question: editDraft.question.trim(),
      expected_answer: editDraft.expected_answer.trim(),
      expected_source_snippet: editDraft.expected_source_snippet.trim() || null,
      category: editDraft.category.trim() || null,
    };
    try {
      await updateMutation.mutateAsync({ questionId: editingId, patch });
      showToast.success('Question updated');
      cancelEdit();
    } catch (error) {
      handleApiError(error);
    }
  };

  const requestDelete = (row: EvalQuestion) => {
    if (deletingId) return;
    setDeleteConfirmRow(row);
  };

  const performDelete = async () => {
    const row = deleteConfirmRow;
    if (!row || deletingId) return;
    setDeletingId(row.id);
    try {
      await deleteMutation.mutateAsync(row.id);
      showToast.success('Question deleted');
      if (editingId === row.id) cancelEdit();
      setDeleteConfirmRow(null);
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeletingId(null);
    }
  };

  const resetCsvInput = () => {
    setCsvFile(null);
    if (csvInputRef.current) csvInputRef.current.value = '';
  };

  const handleCsvUpload = async () => {
    if (!csvFile || uploadCsvMutation.isPending) return;
    try {
      const summary = await uploadCsvMutation.mutateAsync(csvFile);
      showToast.success(
        'Questions imported',
        `Added ${summary.question_count} question(s) from ${csvFile.name}.`,
      );
      resetCsvInput();
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleRunEval = async () => {
    try {
      await runMutation.mutateAsync(
        selectedRunId ? { ingestion_run_id: selectedRunId } : undefined,
      );
      showToast.success(
        'Eval run queued',
        'Scoring runs in the background — results appear in the ingestion runs table when done.',
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  const hasReadyRuns = readyRuns.length > 0;
  const runDisabled = questions.length === 0 || runMutation.isPending || !hasReadyRuns;
  const runButton = (
    <CustomButton
      type="primary"
      onClick={handleRunEval}
      loading={runMutation.isPending}
      disabled={runDisabled}
    >
      <Play className="mr-1 size-4" />
      Run eval
    </CustomButton>
  );

  const footer = (
    <div className="flex w-full items-center justify-between gap-3">
      <span className="shrink-0 text-xs text-muted-foreground">
        {questions.length} total · {manualCount} manual
      </span>
      {hasReadyRuns && (
        <div className="flex min-w-0 flex-1 items-center justify-end gap-2">
          <label
            htmlFor="eval-ingestion-run"
            className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground"
          >
            Ingest recipe
          </label>
          <div className="min-w-[260px]">
            <SelectInput
              name="eval-ingestion-run"
              value={selectedRunId ?? undefined}
              onValueChange={(v) => setSelectedRunId(v || null)}
              options={runOptions}
              placeholder="Select an ingestion run"
              disabled={runMutation.isPending}
            />
          </div>
        </div>
      )}
      <div className="flex shrink-0 items-center gap-2">
        <CustomButton type="default" onClick={onClose}>
          Close
        </CustomButton>
        {!hasReadyRuns ? (
          <CustomTooltip content="No ready ingestion runs to evaluate against">
            <span>{runButton}</span>
          </CustomTooltip>
        ) : (
          runButton
        )}
      </div>
    </div>
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Manual eval questions"
      description="Add your own Q&A pairs, then hit Run to score them against the selected ingestion pipeline (defaults to the active run)."
      width="sm:max-w-3xl"
      footer={footer}
    >
      <div className="flex flex-col gap-6 py-2">
        {/* ── CSV upload ───────────────────────────────────────────── */}
        <section className="rounded-lg border border-border/60 bg-muted/30 p-4">
          <div className="mb-3 flex items-center gap-2">
            <FileUp className="size-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Import from CSV</h3>
          </div>
          <p className="mb-3 text-xs text-muted-foreground">
            Required columns: <span className="font-mono">question</span>,{' '}
            <span className="font-mono">expected_answer</span>. Optional:{' '}
            <span className="font-mono">expected_source_snippet</span>,{' '}
            <span className="font-mono">category</span>,{' '}
            <span className="font-mono">external_id</span>. Rows are appended — existing questions
            are not replaced.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
              className="block w-full cursor-pointer text-xs text-muted-foreground file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-primary/10 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-primary hover:file:bg-primary/20"
              disabled={uploadCsvMutation.isPending}
            />
            <CustomButton
              type="primary"
              size="sm"
              onClick={handleCsvUpload}
              disabled={!csvFile || uploadCsvMutation.isPending}
              loading={uploadCsvMutation.isPending}
            >
              Upload
            </CustomButton>
          </div>
        </section>

        {/* ── Add form ─────────────────────────────────────────────── */}
        <section className="rounded-lg border border-border/60 bg-muted/30 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Plus className="size-4 text-primary" />
            <h3 className="text-sm font-semibold text-foreground">Add a question</h3>
          </div>
          <div className="flex flex-col gap-3">
            <TextAreaField
              name="draft-question"
              label="Question"
              placeholder="e.g. What time is checkout?"
              value={draft.question}
              onChange={(e) => setDraft((d) => ({ ...d, question: e.target.value }))}
              isRequired
              rows={2}
            />
            <TextAreaField
              name="draft-expected-answer"
              label="Expected answer"
              placeholder="e.g. Checkout is at 11:00 AM."
              value={draft.expected_answer}
              onChange={(e) => setDraft((d) => ({ ...d, expected_answer: e.target.value }))}
              isRequired
              rows={2}
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextInput
                name="draft-category"
                label="Category (optional)"
                placeholder="e.g. policy, pricing"
                value={draft.category}
                onChange={(e) => setDraft((d) => ({ ...d, category: e.target.value }))}
              />
              <TextInput
                name="draft-snippet"
                label="Expected source snippet (optional)"
                placeholder="Verbatim phrase from the KB doc"
                value={draft.expected_source_snippet}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, expected_source_snippet: e.target.value }))
                }
              />
            </div>
            <div className="flex justify-end">
              <CustomButton
                type="primary"
                onClick={handleAdd}
                disabled={!canAddDraft || addMutation.isPending}
                loading={addMutation.isPending}
              >
                Add question
              </CustomButton>
            </div>
          </div>
        </section>

        {/* ── Existing questions ────────────────────────────────────── */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Questions
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                (auto-generated + manual)
              </span>
            </h3>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Loading questions…
            </div>
          ) : questions.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/60 py-8 text-center text-sm text-muted-foreground">
              No questions yet. Add one above, or let the pipeline auto-generate a set.
            </div>
          ) : (
            <ul className="flex flex-col gap-2">
              {questions.map((row) => {
                const isEditing = editingId === row.id;
                const badge = sourceBadge(row);
                const isDeletingRow = deletingId === row.id;
                return (
                  <li
                    key={row.id}
                    className={cn(
                      'rounded-lg border border-border/60 bg-background p-3 transition-shadow',
                      isEditing && 'ring-1 ring-primary/40',
                    )}
                  >
                    {isEditing ? (
                      <div className="flex flex-col gap-3">
                        <TextAreaField
                          name={`edit-question-${row.id}`}
                          label="Question"
                          value={editDraft.question}
                          onChange={(e) =>
                            setEditDraft((d) => ({ ...d, question: e.target.value }))
                          }
                          isRequired
                          rows={2}
                        />
                        <TextAreaField
                          name={`edit-expected-${row.id}`}
                          label="Expected answer"
                          value={editDraft.expected_answer}
                          onChange={(e) =>
                            setEditDraft((d) => ({ ...d, expected_answer: e.target.value }))
                          }
                          isRequired
                          rows={2}
                        />
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          <TextInput
                            name={`edit-category-${row.id}`}
                            label="Category"
                            value={editDraft.category}
                            onChange={(e) =>
                              setEditDraft((d) => ({ ...d, category: e.target.value }))
                            }
                          />
                          <TextInput
                            name={`edit-snippet-${row.id}`}
                            label="Expected source snippet"
                            value={editDraft.expected_source_snippet}
                            onChange={(e) =>
                              setEditDraft((d) => ({
                                ...d,
                                expected_source_snippet: e.target.value,
                              }))
                            }
                          />
                        </div>
                        <div className="flex justify-end gap-2">
                          <CustomButton type="default" size="sm" onClick={cancelEdit}>
                            Cancel
                          </CustomButton>
                          <CustomButton
                            type="primary"
                            size="sm"
                            onClick={handleSaveEdit}
                            disabled={!canSaveEdit || updateMutation.isPending}
                            loading={updateMutation.isPending}
                          >
                            Save
                          </CustomButton>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="mb-1 flex flex-wrap items-center gap-2">
                            <span className="text-xs font-medium tabular-nums text-muted-foreground">
                              #{row.question_ord + 1}
                            </span>
                            <span
                              className={cn(
                                'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium',
                                badge.className,
                              )}
                            >
                              {badge.label}
                            </span>
                            {row.category && (
                              <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border/60">
                                {row.category}
                              </span>
                            )}
                          </div>
                          <p className="text-sm font-medium text-foreground">{row.question}</p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            <span className="font-medium text-foreground/70">Expected:</span>{' '}
                            {row.expected_answer}
                          </p>
                          {row.expected_source_snippet && (
                            <p className="mt-1 line-clamp-2 text-xs italic text-muted-foreground">
                              “{row.expected_source_snippet}”
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-1">
                          <CustomTooltip content="Edit">
                            <CustomButton
                              type="text"
                              size="icon-xs"
                              aria-label="Edit question"
                              onClick={() => startEdit(row)}
                              disabled={isDeletingRow}
                            >
                              <Pencil className="size-3.5" />
                            </CustomButton>
                          </CustomTooltip>
                          <CustomTooltip content="Delete">
                            <CustomButton
                              type="text"
                              size="icon-xs"
                              aria-label="Delete question"
                              onClick={() => requestDelete(row)}
                              disabled={isDeletingRow}
                              loading={isDeletingRow}
                            >
                              {!isDeletingRow && <Trash2 className="size-3.5 text-destructive" />}
                            </CustomButton>
                          </CustomTooltip>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      {/*
        Destructive-confirm dialog — matches the app-wide pattern used by
        `ConfirmDeleteModal` in the contacts feature (CustomModal +
        `confirmType="danger"`). Kept inline here so no cross-feature import
        is introduced and no existing file changes. Rendered as a sibling of
        the outer CustomModal so Radix stacks the two dialogs cleanly.
      */}
      <CustomModal
        open={deleteConfirmRow !== null}
        onClose={() => {
          if (!deletingId) setDeleteConfirmRow(null);
        }}
        title="Delete this question?"
        description="Historic eval results for this question will also be removed. This cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        confirmType="danger"
        confirmLoading={deletingId !== null}
        onConfirm={performDelete}
        width="sm:max-w-md"
      >
        {deleteConfirmRow && (
          <p className="rounded-md bg-muted/60 px-3 py-2 text-sm italic text-muted-foreground">
            &ldquo;{deleteConfirmRow.question.slice(0, 200)}
            {deleteConfirmRow.question.length > 200 ? '…' : ''}&rdquo;
          </p>
        )}
      </CustomModal>
    </CustomModal>
  );
}
