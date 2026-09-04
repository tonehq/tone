import { Folder as FolderIcon } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomModal, SelectInput, TextInput } from '@/components/shared';
import { useTriggerAgentLlmEvalRun } from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalFolder, AgentLlmEvalScenario } from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { getRunEvalScopeOptions } from './constants';
import ToggleChip from './ToggleChip';
import type { FolderScope } from './types';

export default function RunEvalModal({
  open,
  onClose,
  agentId,
  scenarios,
  folders,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenarios: AgentLlmEvalScenario[];
  folders: AgentLlmEvalFolder[];
  defaultFolderId: FolderScope;
}) {
  const trigger = useTriggerAgentLlmEvalRun(agentId);
  const [judge, setJudge] = useState('');
  const [scope, setScope] = useState<'all' | 'tags' | 'folders'>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  // Each entry: a folder id. Chip-toggle multi-select mirroring the tag picker.
  const [selectedFolderIds, setSelectedFolderIds] = useState<string[]>([]);

  const tagOptions = useMemo(() => {
    const all = new Set<string>();
    for (const s of scenarios) for (const t of s.tags ?? []) all.add(t);
    return Array.from(all)
      .sort()
      .map((t) => ({ value: t, label: t }));
  }, [scenarios]);

  const folderOptions = useMemo(
    () =>
      folders.map((f) => ({
        value: f.id,
        label: f.name,
        count: f.count,
      })),
    [folders],
  );

  const scopeOptions = useMemo(() => getRunEvalScopeOptions(scenarios.length), [scenarios.length]);

  useEffect(() => {
    if (!open) {
      setJudge('');
      setScope('all');
      setSelectedTags([]);
      setSelectedFolderIds([]);
      return;
    }
    // If a folder was open when the user opened the modal, pre-seed the
    // multi-select with that one folder — saves them re-picking. They can
    // then check additional folders before running.
    if (defaultFolderId !== null) {
      setScope('folders');
      setSelectedFolderIds([defaultFolderId]);
    }
  }, [open, defaultFolderId]);

  const selectedFoldersCount = useMemo(() => {
    if (!selectedFolderIds.length) return 0;
    return folderOptions
      .filter((o) => selectedFolderIds.includes(o.value))
      .reduce((n, o) => n + o.count, 0);
  }, [selectedFolderIds, folderOptions]);

  const toggleFolder = (value: string) => {
    setSelectedFolderIds((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

  const toggleTag = (value: string) => {
    setSelectedTags((prev) =>
      prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value],
    );
  };

  const canSubmit =
    scope !== 'folders' || (selectedFolderIds.length > 0 && selectedFoldersCount > 0);

  const submit = async () => {
    try {
      await trigger.mutateAsync({
        judge_model: judge.trim() || undefined,
        tags: scope === 'tags' && selectedTags.length ? selectedTags : undefined,
        // Send the plural `folder_ids` field on multi-select. Backend
        // prefers `folder_ids` when both are provided.
        folder_ids: scope === 'folders' && selectedFolderIds.length ? selectedFolderIds : undefined,
      });
      showToast.success(
        'Evaluation started',
        'Your scenarios are running now. Open the Runs tab in a moment to see the results.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Run LLM eval"
      description="Enqueues an async job. Refresh in a few seconds to see the run."
      width="max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={trigger.isPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            loading={trigger.isPending}
            disabled={!canSubmit}
          >
            Run eval
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <SelectInput
          name="scope"
          label="Scope"
          value={scope}
          onValueChange={(v) => setScope((v as 'all' | 'tags' | 'folders') ?? 'all')}
          options={scopeOptions}
        />
        {scope === 'folders' && folderOptions.length > 0 && (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              {folderOptions.map((f) => {
                const active = selectedFolderIds.includes(f.value);
                const isEmpty = f.count === 0;
                return (
                  <ToggleChip
                    key={f.value}
                    active={active}
                    onClick={() => toggleFolder(f.value)}
                    disabled={isEmpty}
                    title={isEmpty ? 'Folder is empty' : `${f.label} (${f.count})`}
                    className="inline-flex items-center gap-1.5"
                  >
                    <FolderIcon className="size-3" />
                    <span>{f.label}</span>
                    <span
                      className={cn(
                        'inline-flex min-w-[1rem] items-center justify-center rounded-full px-1 text-[10px] font-semibold',
                        active
                          ? 'bg-primary-foreground/20 text-primary-foreground'
                          : 'bg-card text-muted-foreground',
                      )}
                    >
                      {f.count}
                    </span>
                  </ToggleChip>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {selectedFolderIds.length === 0
                ? 'Pick one or more folders.'
                : `${selectedFoldersCount} scenario${selectedFoldersCount === 1 ? '' : 's'} across ${selectedFolderIds.length} folder${selectedFolderIds.length === 1 ? '' : 's'} will run.`}
            </p>
          </div>
        )}
        {scope === 'tags' && tagOptions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tagOptions.map((t) => {
              const active = selectedTags.includes(t.value);
              return (
                <ToggleChip key={t.value} active={active} onClick={() => toggleTag(t.value)}>
                  {t.label}
                </ToggleChip>
              );
            })}
          </div>
        )}
        <TextInput
          name="judge_model"
          label="Judge model override (optional)"
          placeholder="Leave blank to use the org default"
          value={judge}
          onChange={(e) => setJudge(e.target.value)}
        />
      </div>
    </CustomModal>
  );
}
