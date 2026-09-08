import { Sparkles } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  CustomButton,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { useGenerateAgentLlmEvalVersion } from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalFolder, AgentLlmEvalScenarioVersion } from '@/types/agentLlmEval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { GENERATE_DEFAULT_COUNT, GENERATE_MAX_COUNT, versionLabel } from './constants';
import FolderPicker from './FolderPicker';
import { useFolderPicker } from './useFolderPicker';

type GenerateMode = 'new' | 'overwrite';

const MODE_OPTIONS: { value: GenerateMode; label: string }[] = [
  { value: 'new', label: 'New version' },
  { value: 'overwrite', label: 'Overwrite an existing version' },
];

export default function GenerateScenariosModal({
  open,
  onClose,
  agentId,
  folderOptions,
  defaultFolderId,
  versions,
  onGenerated,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolderId: string | null;
  versions: AgentLlmEvalScenarioVersion[];
  // Called with the reserved version's id so the parent can select it and show
  // the "Generating…" indicator immediately (without waiting for a refresh).
  onGenerated?: (versionId: string) => void;
}) {
  // Generation runs as a background job: the request returns immediately, the
  // version shows a "Generating…" indicator, and the scenarios land as
  // ``pending`` under it for review (approve/reject) once the worker finishes.
  const generate = useGenerateAgentLlmEvalVersion(agentId);
  const {
    folderId,
    setFolderId,
    newFolderName,
    setNewFolderName,
    resolveFolderIdOrCreate,
    isCreatingFolder,
  } = useFolderPicker(agentId, { open, folderOptions });
  const [mode, setMode] = useState<GenerateMode>('new');
  const [overwriteVersionId, setOverwriteVersionId] = useState('');
  const [generationPrompt, setGenerationPrompt] = useState('');
  const [count, setCount] = useState(String(GENERATE_DEFAULT_COUNT));

  // Only versions that have NOT been run can be overwritten.
  const overwritable = useMemo(
    () => versions.filter((v) => !v.has_results && v.status !== 'generating'),
    [versions],
  );
  const overwriteOptions = useMemo(
    () => overwritable.map((v) => ({ value: v.id, label: versionLabel(v) })),
    [overwritable],
  );

  useEffect(() => {
    if (!open) {
      setMode('new');
      setOverwriteVersionId('');
      setGenerationPrompt('');
      setCount(String(GENERATE_DEFAULT_COUNT));
      setFolderId('');
      setNewFolderName('');
      return;
    }
    setFolderId(defaultFolderId ?? '');
    setNewFolderName('');
  }, [open, defaultFolderId, setFolderId, setNewFolderName]);

  const anyPending = generate.isPending || isCreatingFolder;
  const canGenerate = mode === 'new' || (mode === 'overwrite' && !!overwriteVersionId);

  const runGenerate = async () => {
    const parsedCount = Math.max(
      1,
      Math.min(GENERATE_MAX_COUNT, Number(count) || GENERATE_DEFAULT_COUNT),
    );
    try {
      const { folderId: resolvedFolderId } = await resolveFolderIdOrCreate();
      const result = await generate.mutateAsync({
        mode,
        version_id: mode === 'overwrite' ? overwriteVersionId : null,
        parent_id: resolvedFolderId || null,
        generation_prompt: generationPrompt.trim() || null,
        count: parsedCount,
      });
      // Select the reserved version so the "Generating…" chip shows right away
      // (a new version otherwise stays unselected until a manual refresh).
      onGenerated?.(result.version_id);
      showToast.success(
        'Generation started',
        'Scenarios are generating in the background — they’ll appear here for review when ready.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={anyPending ? () => undefined : onClose}
      title="Auto-generate scenarios"
      description="Uses the org’s judge model + this agent’s prompt/workflow to draft scenarios. Drafts are saved as pending for you to approve or reject."
      width="sm:max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={anyPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={runGenerate}
            loading={generate.isPending}
            disabled={!canGenerate || anyPending}
            icon={<Sparkles className="size-3.5" />}
          >
            Generate
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <SelectInput
          name="generate-mode"
          label="Version"
          value={mode}
          onValueChange={(v) => v && setMode(v as GenerateMode)}
          options={MODE_OPTIONS}
        />
        {mode === 'overwrite' && (
          <SelectInput
            name="overwrite-version"
            label="Version to overwrite"
            value={overwriteVersionId || undefined}
            onValueChange={(v) => v && setOverwriteVersionId(v)}
            options={overwriteOptions}
            placeholder={overwriteOptions.length ? 'Select a version' : 'No overwritable versions'}
          />
        )}
        <TextAreaField
          name="generation-prompt"
          label="Custom prompt (optional)"
          value={generationPrompt}
          onChange={(e) => setGenerationPrompt(e.target.value)}
          placeholder="e.g. Focus on edge cases around refunds and cancellations."
          rows={3}
        />
        <TextInput
          name="count"
          label="How many scenarios?"
          type="number"
          min={1}
          max={GENERATE_MAX_COUNT}
          value={count}
          onChange={(e) => setCount(e.target.value)}
          helperText={`Between 1 and ${GENERATE_MAX_COUNT}. Drafts are saved as pending for review.`}
        />
        <FolderPicker
          folders={folderOptions}
          value={folderId}
          onChange={setFolderId}
          newFolderName={newFolderName}
          onNewFolderNameChange={setNewFolderName}
        />
      </div>
    </CustomModal>
  );
}
