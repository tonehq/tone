'use client';

import { useState } from 'react';

import { EMPTY_DRAFT, type DraftQuestion } from '@/components/knowledge-base/evalsConstants';
import { CustomModal, TextAreaField, TextInput } from '@/components/shared';
import { useAddManualEvalQuestions } from '@/lib/api/evals';
import type { ManualQuestionInput } from '@/types/eval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface AddQuestionModalProps {
  open: boolean;
  onClose: () => void;
  uploadId: string;
  versionId: string | null;
}

// Compact "Add a question" form in a modal so it doesn't occupy vertical space
// in the Manage-Evals toolbar — the questions list stays prominent.
export default function AddQuestionModal({
  open,
  onClose,
  uploadId,
  versionId,
}: AddQuestionModalProps) {
  const addMutation = useAddManualEvalQuestions(uploadId);
  const [draft, setDraft] = useState<DraftQuestion>(EMPTY_DRAFT);

  const canAdd =
    !!versionId &&
    draft.question.trim().length > 0 &&
    draft.expected_answer.trim().length > 0;

  const handleAdd = async () => {
    if (!canAdd || !versionId) return;
    const payload: ManualQuestionInput = {
      question: draft.question.trim(),
      expected_answer: draft.expected_answer.trim(),
      expected_source_snippet: draft.expected_source_snippet.trim() || null,
      category: draft.category.trim() || null,
    };
    try {
      await addMutation.mutateAsync({ versionId, questions: [payload] });
      showToast.success('Question added', 'Your Q&A pair has been saved.');
      setDraft(EMPTY_DRAFT);
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Add a question"
      description="Append a manual Q&A pair to the selected version."
      confirmText="Add question"
      onConfirm={handleAdd}
      confirmLoading={addMutation.isPending}
      confirmDisabled={!canAdd || addMutation.isPending}
    >
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
      </div>
    </CustomModal>
  );
}
