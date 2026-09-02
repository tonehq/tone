import { Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';

import { CustomButton, CustomModal, TextInput } from '@/components/shared';
import {
  useCreateAgentLlmEvalFolder,
  useCreateAgentLlmEvalScenariosBulk,
  useGenerateAgentLlmEvalScenarios,
} from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalFolder, GeneratedScenario, ScenarioInput } from '@/types/agentLlmEval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { GENERATE_DEFAULT_COUNT, GENERATE_MAX_COUNT, NEW_FOLDER_OPTION_VALUE } from './constants';
import FolderPicker from './FolderPicker';
import GeneratedScenariosPreview from './GeneratedScenariosPreview';

export default function GenerateScenariosModal({
  open,
  onClose,
  agentId,
  folderOptions,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolderId: string | null;
}) {
  // Two-step flow: dry-run generate → preview table with per-row
  // checkboxes → user confirms → bulk-create only the selected items with
  // ``source='generated'`` so the source badge in the scenarios table
  // still reflects reality. The bulk endpoint is the SAME code path a
  // manual bulk create uses (duplicate keys 409 the whole batch), which
  // keeps the scenario-write invariants in one place.
  const generate = useGenerateAgentLlmEvalScenarios(agentId);
  const persist = useCreateAgentLlmEvalScenariosBulk(agentId);
  const createFolder = useCreateAgentLlmEvalFolder(agentId);
  const [count, setCount] = useState(String(GENERATE_DEFAULT_COUNT));
  const [folderId, setFolderId] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  // Preview state — ``null`` = the form is showing; a non-null array
  // = the preview table is showing. Kept as separate state (not derived
  // from ``generate.data``) so switching from preview back to form
  // (Regenerate) doesn't tear down the visible table before we're ready.
  const [preview, setPreview] = useState<GeneratedScenario[] | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) {
      // Reset every piece of state on close so a re-open starts fresh
      // (avoids resurrecting a stale preview from a previous session).
      setCount(String(GENERATE_DEFAULT_COUNT));
      setFolderId('');
      setNewFolderName('');
      setPreview(null);
      setSelectedKeys(new Set());
      return;
    }
    setFolderId(defaultFolderId ?? '');
    setNewFolderName('');
  }, [open, defaultFolderId]);

  // Backfill folderId once folders load — see the matching effect on
  // ``ScenarioFormModal`` for the rationale.
  useEffect(() => {
    if (!open || folderId || folderId === NEW_FOLDER_OPTION_VALUE) return;
    if (folderOptions.length === 0) return;
    setFolderId(folderOptions[0].id);
  }, [open, folderId, folderOptions]);

  const resolveFolderIdOrCreate = async (): Promise<string | null> => {
    if (folderId === NEW_FOLDER_OPTION_VALUE) {
      const trimmed = newFolderName.trim();
      if (!trimmed) {
        showToast.error('Folder name is required');
        return null;
      }
      const created = await createFolder.mutateAsync({ name: trimmed });
      setFolderId(created.id);
      return created.id;
    }
    return folderId || null;
  };

  const runGenerate = async () => {
    const parsedCount = Math.max(
      1,
      Math.min(GENERATE_MAX_COUNT, Number(count) || GENERATE_DEFAULT_COUNT),
    );
    try {
      const result = await generate.mutateAsync({
        strategy: 'llm',
        count: parsedCount,
        // Preview only — nothing is written yet. The subsequent
        // ``persist`` mutation writes the user's selection with
        // ``source='generated'``.
        dry_run: true,
      });
      if (result.generated.length === 0) {
        showToast.info(
          'Auto-generate',
          result.note ??
            'The generator returned no usable scenarios. Try again, or tweak the agent’s system prompt.',
        );
        return;
      }
      setPreview(result.generated);
      // Default to every row selected — the common case is "accept all".
      setSelectedKeys(new Set(result.generated.map((s) => s.scenario_key)));
    } catch (error) {
      handleApiError(error);
    }
  };

  const savePreview = async () => {
    if (!preview) return;
    const chosen = preview.filter((s) => selectedKeys.has(s.scenario_key));
    if (chosen.length === 0) return;
    try {
      const resolvedFolderId = await resolveFolderIdOrCreate();
      const result = await persist.mutateAsync({
        source: 'generated',
        scenarios: chosen.map<ScenarioInput>((s) => ({
          scenario_key: s.scenario_key,
          prompt: s.prompt,
          expected_answer: s.expected_answer,
          persona_criteria: s.persona_criteria,
          instruction_criteria: s.instruction_criteria,
          tags: s.tags.length ? s.tags : null,
          folder_id: resolvedFolderId || null,
        })),
      });
      showToast.success(
        `${result.created} scenario${result.created === 1 ? '' : 's'} added`,
        'Generated from the agent’s published system prompt.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const toggleRow = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAll = () => {
    if (!preview) return;
    setSelectedKeys((prev) =>
      prev.size === preview.length ? new Set() : new Set(preview.map((s) => s.scenario_key)),
    );
  };

  const inPreview = preview !== null;
  const anyPending = generate.isPending || persist.isPending || createFolder.isPending;
  // Cancel = full modal close; Regenerate = go back to the form to
  // re-run generation (keeps count + folder inputs so the user can tweak).
  const modalClose = anyPending ? () => undefined : onClose;

  const backToForm = () => {
    setPreview(null);
    setSelectedKeys(new Set());
  };

  return (
    <CustomModal
      open={open}
      onClose={modalClose}
      title={inPreview ? 'Review generated scenarios' : 'Auto-generate scenarios'}
      description={
        inPreview
          ? 'Uncheck any scenario you don’t want. Only checked rows will be saved.'
          : 'Uses the org’s judge model + this agent’s system prompt to draft scenarios. You’ll review the drafts before saving.'
      }
      width={inPreview ? 'sm:max-w-5xl' : 'sm:max-w-lg'}
      footer={
        inPreview ? (
          <div className="flex items-center justify-between gap-2">
            <CustomButton type="text" onClick={backToForm} disabled={anyPending}>
              ← Regenerate
            </CustomButton>
            <div className="flex gap-2">
              <CustomButton type="default" onClick={onClose} disabled={anyPending}>
                Cancel
              </CustomButton>
              <CustomButton
                type="primary"
                onClick={savePreview}
                loading={persist.isPending}
                disabled={selectedKeys.size === 0 || anyPending}
              >
                Save {selectedKeys.size} scenario{selectedKeys.size === 1 ? '' : 's'}
              </CustomButton>
            </div>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <CustomButton type="default" onClick={onClose} disabled={anyPending}>
              Cancel
            </CustomButton>
            <CustomButton
              type="primary"
              onClick={runGenerate}
              loading={generate.isPending}
              icon={<Sparkles className="size-3.5" />}
            >
              Generate preview
            </CustomButton>
          </div>
        )
      }
    >
      {inPreview && preview ? (
        <GeneratedScenariosPreview
          rows={preview}
          selectedKeys={selectedKeys}
          onToggleRow={toggleRow}
          onToggleAll={toggleAll}
        />
      ) : (
        <div className="flex flex-col gap-3">
          <TextInput
            name="count"
            label="How many scenarios?"
            type="number"
            min={1}
            max={GENERATE_MAX_COUNT}
            value={count}
            onChange={(e) => setCount(e.target.value)}
            helperText={`Between 1 and ${GENERATE_MAX_COUNT}. Nothing is saved until you review the preview.`}
          />
          <FolderPicker
            folders={folderOptions}
            value={folderId}
            onChange={setFolderId}
            newFolderName={newFolderName}
            onNewFolderNameChange={setNewFolderName}
          />
        </div>
      )}
    </CustomModal>
  );
}
