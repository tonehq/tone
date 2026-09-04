import type { AgentLlmEvalFolder } from '@/types/agentLlmEval';

/** Impact summary shown in the "Delete folder" confirmation modal — spells
 * out the folder being deleted and how many scenarios go with it. Rendered
 * from ``LlmEvalsStepBody``; extracted so the modal's ``impact`` prop stays a
 * plain component reference instead of an inline IIFE. */
export default function FolderDeleteImpact({ folder }: { folder: AgentLlmEvalFolder | undefined }) {
  return (
    <div className="space-y-2 text-sm text-foreground">
      {folder ? (
        <>
          <p>
            You’re about to delete the folder{' '}
            <span className="font-medium">{folder.name}</span> and every scenario in it.
          </p>
          {folder.count > 0 ? (
            <p className="text-muted-foreground">
              <span className="font-medium text-foreground">{folder.count}</span> scenario
              {folder.count === 1 ? '' : 's'} will be removed. To keep any of them, edit each
              scenario and change its folder before deleting.
            </p>
          ) : (
            <p className="text-muted-foreground">This folder is empty.</p>
          )}
        </>
      ) : null}
    </div>
  );
}
