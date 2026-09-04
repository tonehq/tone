'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { FileUp, Loader2, Play, Plus } from 'lucide-react';

import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import EvalQuestionRow from '@/components/knowledge-base/EvalQuestionRow';
import {
  CustomButton,
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
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface ManageEvalsTabProps {
  uploadId: string;
}

export interface DraftQuestion {
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

export default function ManageEvalsTab({ uploadId }: ManageEvalsTabProps) {
  const { data: questions = [], isLoading } = useEvalQuestions(uploadId);
  const addMutation = useAddManualEvalQuestions(uploadId);
  const updateMutation = useUpdateEvalQuestion(uploadId);
  const deleteMutation = useDeleteEvalQuestion(uploadId);
  const runMutation = useTriggerEvalRun(uploadId);
  const uploadCsvMutation = useUploadEvalQuestionsCsv(uploadId);
  const csvInputRef = useRef<HTMLInputElement | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);

  const { data: runsResp } = useIngestionRuns(uploadId, {
    status_filter: ['ready'],
    page_size: 100,
    sort_by: 'run_number',
    sort_order: 'desc',
  });
  const readyRuns = useMemo(() => runsResp?.data ?? [], [runsResp]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  useEffect(() => {
    if (readyRuns.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !readyRuns.some((r) => r.id === selectedRunId)) {
      const active = readyRuns.find((r) => r.is_active);
      setSelectedRunId((active ?? readyRuns[0]).id);
    }
  }, [readyRuns, selectedRunId]);

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
  // Two-step delete: clicking the trash icon opens the shared
  // `ConfirmDeleteModal`, NOT the native browser `window.confirm` popup.
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
    // Guard against re-targeting the confirm modal if it's already open for
    // another row — rapid clicks on different trash icons could otherwise
    // silently swap the target and cause the user to delete a row they
    // weren't looking at when they hit Confirm.
    if (deletingId || deleteConfirmRow) return;
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

  return (
    <div className="flex flex-col gap-6 py-4">
      {/* ── Section heading + description ─────────────────────────── */}
      <div>
        <h2 className="text-lg font-semibold text-foreground">Manual eval questions</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Add your own Q&amp;A pairs, then hit Run to score them against the selected ingestion
          pipeline (defaults to the active run).
        </p>
      </div>

      {/*
        Sticky toolbar — the modal used to keep the Run CTA in a fixed footer;
        as a tab body the toolbar has to travel with the scroll, so we pin it
        to the top of the scroll container. `backdrop-blur` keeps the content
        readable when questions scroll behind it.
      */}
      <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/95 px-4 py-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <p className="text-sm font-medium text-foreground">
          {questions.length} total · {manualCount} manual
        </p>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {hasReadyRuns && (
            <div className="flex items-center gap-2">
              <label
                htmlFor="eval-ingestion-run"
                className="shrink-0 text-[11px] uppercase tracking-wide text-muted-foreground"
              >
                Ingest recipe
              </label>
              <div className="min-w-[220px] sm:min-w-[260px]">
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
          {!hasReadyRuns ? (
            <CustomTooltip content="No ready ingestion runs to evaluate against">
              <span>{runButton}</span>
            </CustomTooltip>
          ) : (
            runButton
          )}
        </div>
      </div>

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
          <span className="font-mono">external_id</span>. Rows are appended — existing questions are
          not replaced.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {/*
            TODO(shared-file-input): consider reusing the shared
            `@/components/contacts/shared/ContactFileInput` here. Kept as a raw
            styled native input for now to preserve this control's exact look +
            behavior (no extension-rejection toast); ContactFileInput is a
            controlled button+filename picker with different chrome, so swapping
            it is a visual/behavior change out of scope for this refactor.
          */}
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
              onChange={(e) => setDraft((d) => ({ ...d, expected_source_snippet: e.target.value }))}
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
            {questions.map((row) => (
              <EvalQuestionRow
                key={row.id}
                row={row}
                isEditing={editingId === row.id}
                editDraft={editDraft}
                setEditDraft={setEditDraft}
                canSaveEdit={canSaveEdit}
                savingEdit={updateMutation.isPending}
                isDeleting={deletingId === row.id}
                onStartEdit={startEdit}
                onCancelEdit={cancelEdit}
                onSaveEdit={handleSaveEdit}
                onRequestDelete={requestDelete}
              />
            ))}
          </ul>
        )}
      </section>

      {/* Destructive-confirm dialog — the shared contacts-feature primitive. */}
      <ConfirmDeleteModal
        open={deleteConfirmRow !== null}
        onClose={() => {
          if (!deletingId) setDeleteConfirmRow(null);
        }}
        onConfirm={performDelete}
        title="Delete this question?"
        description="Historic eval results for this question will also be removed. This cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        loading={deletingId !== null}
        impact={
          deleteConfirmRow ? (
            <p className="rounded-md bg-muted/60 px-3 py-2 text-sm italic text-muted-foreground">
              &ldquo;{deleteConfirmRow.question.slice(0, 200)}
              {deleteConfirmRow.question.length > 200 ? '…' : ''}&rdquo;
            </p>
          ) : undefined
        }
      />
    </div>
  );
}
