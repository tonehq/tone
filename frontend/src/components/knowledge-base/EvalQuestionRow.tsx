'use client';

import type { Dispatch, SetStateAction } from 'react';
import { Pencil, Trash2 } from 'lucide-react';

import type { DraftQuestion } from '@/components/knowledge-base/ManageEvalsTab';
import { CustomButton, CustomTooltip, TextAreaField, TextInput } from '@/components/shared';
import type { EvalQuestion } from '@/types/eval';
import { cn } from '@/utils/cn';

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

interface EvalQuestionRowProps {
  row: EvalQuestion;
  isEditing: boolean;
  editDraft: DraftQuestion;
  setEditDraft: Dispatch<SetStateAction<DraftQuestion>>;
  canSaveEdit: boolean;
  savingEdit: boolean;
  isDeleting: boolean;
  onStartEdit: (row: EvalQuestion) => void;
  onCancelEdit: () => void;
  onSaveEdit: () => void;
  onRequestDelete: (row: EvalQuestion) => void;
}

// One eval-question list item: a read view (source/category badges + Q/A +
// edit/delete actions) and an inline edit form. Extracted from ManageEvalsTab
// so the tab body stays orchestration-only.
export default function EvalQuestionRow({
  row,
  isEditing,
  editDraft,
  setEditDraft,
  canSaveEdit,
  savingEdit,
  isDeleting,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onRequestDelete,
}: EvalQuestionRowProps) {
  const badge = sourceBadge(row);
  return (
    <li
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
            onChange={(e) => setEditDraft((d) => ({ ...d, question: e.target.value }))}
            isRequired
            rows={2}
          />
          <TextAreaField
            name={`edit-expected-${row.id}`}
            label="Expected answer"
            value={editDraft.expected_answer}
            onChange={(e) => setEditDraft((d) => ({ ...d, expected_answer: e.target.value }))}
            isRequired
            rows={2}
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <TextInput
              name={`edit-category-${row.id}`}
              label="Category"
              value={editDraft.category}
              onChange={(e) => setEditDraft((d) => ({ ...d, category: e.target.value }))}
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
            <CustomButton type="default" size="sm" onClick={onCancelEdit}>
              Cancel
            </CustomButton>
            <CustomButton
              type="primary"
              size="sm"
              onClick={onSaveEdit}
              disabled={!canSaveEdit || savingEdit}
              loading={savingEdit}
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
                onClick={() => onStartEdit(row)}
                disabled={isDeleting}
              >
                <Pencil className="size-3.5" />
              </CustomButton>
            </CustomTooltip>
            <CustomTooltip content="Delete">
              <CustomButton
                type="text"
                size="icon-xs"
                aria-label="Delete question"
                onClick={() => onRequestDelete(row)}
                disabled={isDeleting}
                loading={isDeleting}
              >
                {!isDeleting && <Trash2 className="size-3.5 text-destructive" />}
              </CustomButton>
            </CustomTooltip>
          </div>
        </div>
      )}
    </li>
  );
}
