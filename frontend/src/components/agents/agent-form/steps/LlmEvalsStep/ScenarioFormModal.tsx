import { useEffect, useState } from 'react';

import { CustomButton, CustomModal, TextAreaField, TextInput } from '@/components/shared';
import {
  useCreateAgentLlmEvalScenario,
  useUpdateAgentLlmEvalScenario,
} from '@/lib/api/agentLlmEvals';
import type {
  AgentLlmEvalFolder,
  AgentLlmEvalScenario,
  ScenarioInput,
  ScenarioPatch,
} from '@/types/agentLlmEval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import FolderPicker from './FolderPicker';
import { useFolderPicker } from './useFolderPicker';

export default function ScenarioFormModal({
  open,
  onClose,
  agentId,
  scenario,
  folderOptions,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenario: AgentLlmEvalScenario | null;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolderId: string | null;
}) {
  const isEdit = !!scenario;
  const create = useCreateAgentLlmEvalScenario(agentId);
  const update = useUpdateAgentLlmEvalScenario(agentId);
  const {
    folderId,
    setFolderId,
    newFolderName,
    setNewFolderName,
    resolveFolderIdOrCreate,
    isCreatingFolder,
  } = useFolderPicker(agentId, { open, folderOptions });

  const [key, setKey] = useState('');
  const [prompt, setPrompt] = useState('');
  const [expected, setExpected] = useState('');
  const [persona, setPersona] = useState('');
  const [instruction, setInstruction] = useState('');
  const [tags, setTags] = useState('');

  // Initialise once when the modal opens or the target scenario changes.
  // Deliberately omit ``folderOptions`` from deps — the folders query has
  // ``staleTime: 0`` so its data reference changes on every background
  // refetch. Including it here would silently reset the user's mid-edit
  // folder pick every time the query refetches.
  useEffect(() => {
    if (!open) return;
    setKey(scenario?.scenario_key ?? '');
    setPrompt(scenario?.prompt ?? '');
    setExpected(scenario?.expected_answer ?? '');
    setPersona(scenario?.persona_criteria ?? '');
    setInstruction(scenario?.instruction_criteria ?? '');
    setTags((scenario?.tags ?? []).join(', '));
    setFolderId(scenario?.folder_id ?? defaultFolderId ?? '');
    setNewFolderName('');
  }, [open, scenario, defaultFolderId, setFolderId, setNewFolderName]);

  const submit = async () => {
    const parsedTags = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      // Resolve the folder id — either an existing selection or a
      // just-created folder from the "+ Create new folder…" affordance.
      const { folderId: resolvedFolderId, valid } = await resolveFolderIdOrCreate();
      if (!valid) return;

      if (isEdit && scenario) {
        // Only send fields the user actually changed — otherwise a
        // concurrent edit (another tab / user) gets silently reverted.
        // Tags need a stringified-set compare because the DB stores them
        // as a JSONB array whose order we shouldn't rely on for equality.
        const originalTags = (scenario.tags ?? []).slice().sort().join(',');
        const nextTags = parsedTags.slice().sort().join(',');
        const patch: ScenarioPatch = {
          scenario_key: key !== scenario.scenario_key ? key : undefined,
          prompt: prompt !== scenario.prompt ? prompt : undefined,
          expected_answer: expected !== (scenario.expected_answer ?? '') ? expected : undefined,
          persona_criteria: persona !== (scenario.persona_criteria ?? '') ? persona : undefined,
          instruction_criteria:
            instruction !== (scenario.instruction_criteria ?? '') ? instruction : undefined,
          tags: nextTags !== originalTags ? parsedTags : undefined,
          folder_id:
            resolvedFolderId && resolvedFolderId !== scenario.folder_id
              ? resolvedFolderId
              : undefined,
        };
        await update.mutateAsync({ scenarioId: scenario.id, patch });
        showToast.success('Scenario updated');
      } else {
        const input: ScenarioInput = {
          scenario_key: key,
          prompt,
          expected_answer: expected || null,
          persona_criteria: persona || null,
          instruction_criteria: instruction || null,
          tags: parsedTags.length ? parsedTags : null,
          folder_id: resolvedFolderId || null,
        };
        await create.mutateAsync(input);
        showToast.success('Scenario created');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const pending = create.isPending || update.isPending || isCreatingFolder;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit scenario' : 'New scenario'}
      description="A prompt + optional expected answer or judging criteria."
      width="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={pending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            disabled={pending || !key.trim() || !prompt.trim()}
            loading={pending}
          >
            {isEdit ? 'Save changes' : 'Create scenario'}
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput
          name="scenario_key"
          label="Scenario key"
          placeholder="e.g. simple_room_booking"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          isRequired
        />
        <TextAreaField
          name="prompt"
          label="Prompt"
          placeholder="The user message the agent should respond to"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          isRequired
        />
        <TextAreaField
          name="expected_answer"
          label="Expected answer (optional)"
          placeholder="Used by the correctness metric"
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
          rows={3}
        />
        <TextAreaField
          name="persona_criteria"
          label="Persona criteria (optional)"
          placeholder="How the agent should sound (empathetic, professional, etc.)"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          rows={2}
        />
        <TextAreaField
          name="instruction_criteria"
          label="Instruction criteria (optional)"
          placeholder="What the agent must / must not do"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={2}
        />
        <TextInput
          name="tags"
          label="Tags"
          placeholder="Comma-separated (e.g. booking, happy_path)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
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
