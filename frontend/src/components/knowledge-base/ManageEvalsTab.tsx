'use client';

import { useEffect, useMemo, useState } from 'react';
import { FileUp, Loader2, Play, Plus, Sparkles } from 'lucide-react';

import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import AddQuestionModal from '@/components/knowledge-base/AddQuestionModal';
import EvalQuestionRow from '@/components/knowledge-base/EvalQuestionRow';
import EvalVersionBar from '@/components/knowledge-base/EvalVersionBar';
import GenerateEvalModal from '@/components/knowledge-base/GenerateEvalModal';
import ImportCsvModal from '@/components/knowledge-base/ImportCsvModal';
import { EMPTY_DRAFT, type DraftQuestion } from '@/components/knowledge-base/evalsConstants';
import { CustomButton, CustomTooltip, SelectInput } from '@/components/shared';
import {
  useApproveAllEvalQuestions,
  useApproveEvalQuestion,
  useDeleteEvalQuestion,
  useEvalQuestions,
  useEvalVersions,
  useGenerateEvalVersion,
  useRejectAllEvalQuestions,
  useTriggerEvalRun,
  useUpdateEvalQuestion,
} from '@/lib/api/evals';
import { useIngestionRuns } from '@/lib/api/ingestion-runs';
import type {
  EvalQuestion,
  EvalVersion,
  GenerateEvalVersionPayload,
  UpdateQuestionPatch,
} from '@/types/eval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface ManageEvalsTabProps {
  uploadId: string;
}

export default function ManageEvalsTab({ uploadId }: ManageEvalsTabProps) {
  const { data: versions = [], isLoading: versionsLoading } = useEvalVersions(uploadId);

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  useEffect(() => {
    if (versions.length === 0) {
      setSelectedVersionId(null);
      return;
    }
    if (!selectedVersionId || !versions.some((v) => v.id === selectedVersionId)) {
      setSelectedVersionId(versions[0].id);
    }
  }, [versions, selectedVersionId]);

  const selectedVersion: EvalVersion | null =
    versions.find((v) => v.id === selectedVersionId) ?? null;

  const { data: questions = [], isLoading: questionsLoading } = useEvalQuestions(
    uploadId,
    selectedVersionId,
  );

  const updateMutation = useUpdateEvalQuestion(uploadId);
  const deleteMutation = useDeleteEvalQuestion(uploadId);
  const approveMutation = useApproveEvalQuestion(uploadId);
  const approveAllMutation = useApproveAllEvalQuestions(uploadId);
  const rejectAllMutation = useRejectAllEvalQuestions(uploadId);
  const generateMutation = useGenerateEvalVersion(uploadId);
  const runMutation = useTriggerEvalRun(uploadId);

  const [generateOpen, setGenerateOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);

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

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<DraftQuestion>(EMPTY_DRAFT);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);
  const [deleteConfirmRow, setDeleteConfirmRow] = useState<EvalQuestion | null>(null);

  const canSaveEdit =
    editDraft.question.trim().length > 0 && editDraft.expected_answer.trim().length > 0;

  const approvedCount = selectedVersion?.counts.approved ?? 0;

  const handleGenerate = async (payload: GenerateEvalVersionPayload) => {
    try {
      await generateMutation.mutateAsync(payload);
      showToast.success(
        'Generation queued',
        'The eval set is being drafted — it will appear here shortly.',
      );
      setGenerateOpen(false);
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

  const handleApprove = async (row: EvalQuestion) => {
    if (approvingId) return;
    setApprovingId(row.id);
    try {
      await approveMutation.mutateAsync(row.id);
    } catch (error) {
      handleApiError(error);
    } finally {
      setApprovingId(null);
    }
  };

  const handleApproveAll = async () => {
    if (!selectedVersionId) return;
    try {
      await approveAllMutation.mutateAsync(selectedVersionId);
      showToast.success('All questions approved');
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleRejectAll = async () => {
    if (!selectedVersionId) return;
    try {
      await rejectAllMutation.mutateAsync(selectedVersionId);
      showToast.success('All questions rejected', 'The version is now empty.');
    } catch (error) {
      handleApiError(error);
    }
  };

  const requestDelete = (row: EvalQuestion) => {
    if (deletingId || deleteConfirmRow) return;
    setDeleteConfirmRow(row);
  };

  const performDelete = async () => {
    const row = deleteConfirmRow;
    if (!row || deletingId) return;
    setDeletingId(row.id);
    try {
      await deleteMutation.mutateAsync(row.id);
      showToast.success('Question rejected');
      if (editingId === row.id) cancelEdit();
      setDeleteConfirmRow(null);
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeletingId(null);
    }
  };

  const handleRunEval = async () => {
    if (!selectedVersionId) return;
    try {
      await runMutation.mutateAsync({
        eval_version_id: selectedVersionId,
        ingestion_run_id: selectedRunId ?? undefined,
      });
      showToast.success(
        'Eval run queued',
        'Scoring the approved questions in the background — results appear in the Eval results tab.',
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  const hasReadyRuns = readyRuns.length > 0;
  const runDisabled =
    approvedCount === 0 || runMutation.isPending || !hasReadyRuns || !selectedVersionId;
  const runButton = (
    <CustomButton
      type="primary"
      size="sm"
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
      <div>
        <h2 className="text-lg font-semibold text-foreground">Manage evals</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Generate an eval version, review each question, approve the good ones (reject deletes),
          then run the approved set against a ready ingestion recipe.
        </p>
      </div>

      <EvalVersionBar
        versions={versions}
        selectedVersion={selectedVersion}
        onSelectVersion={setSelectedVersionId}
        onOpenGenerate={() => setGenerateOpen(true)}
        onApproveAll={handleApproveAll}
        onRejectAll={handleRejectAll}
        approvingAll={approveAllMutation.isPending}
        rejectingAll={rejectAllMutation.isPending}
      />

      {versionsLoading ? (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Loading versions…
        </div>
      ) : versions.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border/60 py-10 text-center">
          <p className="text-sm text-muted-foreground">
            No eval versions yet. Generate your first set to start reviewing.
          </p>
          <CustomButton type="primary" size="sm" onClick={() => setGenerateOpen(true)}>
            <Sparkles className="mr-1 size-4" />
            Generate evals
          </CustomButton>
        </div>
      ) : (
        <>
          {/* Compact action toolbar — Add / Import / Run stay up top without
              eating vertical space; the questions list sits right below. */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-muted/30 px-4 py-2.5">
            <p className="text-sm font-medium text-foreground">
              {selectedVersion?.counts.total ?? 0} question(s) · {approvedCount} approved
            </p>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <CustomButton
                type="default"
                size="sm"
                onClick={() => setAddOpen(true)}
                disabled={!selectedVersionId}
              >
                <Plus className="mr-1 size-4" />
                Add question
              </CustomButton>
              <CustomButton
                type="default"
                size="sm"
                onClick={() => setImportOpen(true)}
                disabled={!selectedVersionId}
              >
                <FileUp className="mr-1 size-4" />
                Import CSV
              </CustomButton>
              <div className="mx-1 hidden h-6 w-px bg-border/60 sm:block" aria-hidden />
              {hasReadyRuns && (
                <div className="min-w-[200px] sm:min-w-[240px]">
                  <SelectInput
                    name="eval-ingestion-run"
                    value={selectedRunId ?? undefined}
                    onValueChange={(v) => setSelectedRunId(v || null)}
                    options={runOptions}
                    placeholder="Ingest recipe"
                    disabled={runMutation.isPending}
                  />
                </div>
              )}
              {runDisabled && approvedCount === 0 ? (
                <CustomTooltip content="Approve at least one question to run">
                  <span>{runButton}</span>
                </CustomTooltip>
              ) : !hasReadyRuns ? (
                <CustomTooltip content="No ready ingestion runs to evaluate against">
                  <span>{runButton}</span>
                </CustomTooltip>
              ) : (
                runButton
              )}
            </div>
          </div>

          {/* Questions */}
          <section>
            {questionsLoading ? (
              <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading questions…
              </div>
            ) : selectedVersion?.status === 'generating' ? (
              <div className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border/60 py-8 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Generating questions…
              </div>
            ) : questions.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/60 py-8 text-center text-sm text-muted-foreground">
                No questions in this version. Add one above or generate a new version.
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
                    isApproving={approvingId === row.id}
                    onStartEdit={startEdit}
                    onCancelEdit={cancelEdit}
                    onSaveEdit={handleSaveEdit}
                    onApprove={handleApprove}
                    onRequestDelete={requestDelete}
                  />
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      <GenerateEvalModal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        versions={versions}
        generating={generateMutation.isPending}
        onGenerate={handleGenerate}
      />

      <AddQuestionModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        uploadId={uploadId}
        versionId={selectedVersionId}
      />

      <ImportCsvModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        uploadId={uploadId}
        versionId={selectedVersionId}
      />

      <ConfirmDeleteModal
        open={deleteConfirmRow !== null}
        onClose={() => {
          if (!deletingId) setDeleteConfirmRow(null);
        }}
        onConfirm={performDelete}
        title="Reject this question?"
        description="Rejecting deletes the question from this version. This cannot be undone."
        confirmText="Reject"
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
