import { BookOpen, Plus } from 'lucide-react';

import { CustomButton } from '@/components/shared';

interface KnowledgeBaseEmptyStateProps {
  onAdd: () => void;
  hasFilter: boolean;
}

export default function KnowledgeBaseEmptyState({
  onAdd,
  hasFilter,
}: KnowledgeBaseEmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-5 py-14">
      <span className="inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
        <BookOpen className="size-5" strokeWidth={1.75} />
      </span>
      <div className="max-w-sm text-center">
        <p className="font-display text-[15px] font-semibold text-foreground">
          {hasFilter ? 'No matching documents' : 'No documents yet'}
        </p>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try clearing the search or status filter.'
            : 'Upload your first document to build your knowledge base.'}
        </p>
      </div>
      {!hasFilter && (
        <CustomButton type="primary" icon={<Plus size={15} />} className="h-10" onClick={onAdd}>
          Add sources
        </CustomButton>
      )}
    </div>
  );
}
