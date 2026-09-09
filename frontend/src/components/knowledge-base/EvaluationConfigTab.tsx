'use client';

import { Plus } from 'lucide-react';
import { useMemo, useState } from 'react';

import {
  AppLoader,
  CheckboxField,
  CustomButton,
  CustomModal,
  SelectInput,
} from '@/components/shared';
import { useEvalRunsFiltered } from '@/lib/api/evals';
import {
  useDeleteEvaluationConfig,
  useEvaluationConfigResults,
  useEvaluationConfigs,
  useRunEvaluationConfig,
  useSetDefaultEvaluationConfig,
} from '@/lib/api/evaluationConfigs';
import type { EvaluationConfig } from '@/types/evaluationConfig';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import { MAX_COMPARE } from './evalConfigConstants';
import EvaluationConfigCompare from './EvaluationConfigCompare';
import EvaluationConfigListItem from './EvaluationConfigListItem';
import EvaluationConfigModal from './EvaluationConfigModal';

interface EvaluationConfigTabProps {
  uploadId: string;
}

const HINT_CLASS =
  'rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground';

export default function EvaluationConfigTab({ uploadId }: EvaluationConfigTabProps) {
  const { data: configList, isLoading: configsLoading } = useEvaluationConfigs();
  const configs = useMemo(() => configList?.items ?? [], [configList]);

  const { data: runs = [] } = useEvalRunsFiltered(uploadId, {});
  const [sourceRunId, setSourceRunId] = useState<string>('');
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [selectedPassIds, setSelectedPassIds] = useState<string[]>([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EvaluationConfig | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<EvaluationConfig | null>(null);

  const runMutation = useRunEvaluationConfig();
  const deleteMutation = useDeleteEvaluationConfig();
  const setDefaultMutation = useSetDefaultEvaluationConfig();

  const { data: resultsData } = useEvaluationConfigResults(sourceRunId || null, undefined, true);
  const passes = useMemo(() => resultsData?.runs ?? [], [resultsData]);
  const results = useMemo(() => resultsData?.results ?? [], [resultsData]);

  const runOptions = useMemo(
    () =>
      runs.map((r) => ({
        value: r.run_id,
        label: `Run #${r.run_number}${r.judge_model ? ` · ${r.judge_model}` : ''}`,
      })),
    [runs],
  );
  const configOptions = useMemo(
    () =>
      configs.map((c) => ({
        value: c.id,
        label: c.is_default ? `${c.name} (default)` : c.name,
      })),
    [configs],
  );

  const selectedPasses = useMemo(
    () => passes.filter((p) => selectedPassIds.includes(p.config_run_id)),
    [passes, selectedPassIds],
  );

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };
  const openEdit = (config: EvaluationConfig) => {
    setEditing(config);
    setModalOpen(true);
  };

  const togglePass = (configRunId: string, checked: boolean) => {
    setSelectedPassIds((prev) => {
      if (checked) {
        if (prev.includes(configRunId) || prev.length >= MAX_COMPARE) return prev;
        return [...prev, configRunId];
      }
      return prev.filter((id) => id !== configRunId);
    });
  };

  const handleRun = async () => {
    if (!sourceRunId || !selectedConfigId) return;
    try {
      await runMutation.mutateAsync({
        source_run_id: sourceRunId,
        evaluation_config_id: selectedConfigId,
      });
      showToast.success('Re-grade queued', 'Scores will appear here once the judge finishes.');
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleSetDefault = async (config: EvaluationConfig) => {
    try {
      await setDefaultMutation.mutateAsync(config.id);
      showToast.success('Default updated', `${config.name} is now the default judge.`);
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(deleteTarget.id);
      showToast.success('Config deleted', `${deleteTarget.name} was removed.`);
      setDeleteTarget(null);
    } catch (error) {
      handleApiError(error);
    }
  };

  const busy = deleteMutation.isPending || setDefaultMutation.isPending || runMutation.isPending;

  return (
    <div className="flex flex-col gap-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Evaluation config</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Re-grade a past eval run with a different judge — model, custom prompt, and metrics —
            then compare the scores. Configs are shared across your organization.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={openCreate}>
          New config
        </CustomButton>
      </div>

      {/* Config list ─────────────────────────────────────────── */}
      {configsLoading ? (
        <AppLoader />
      ) : configs.length === 0 ? (
        <div className={HINT_CLASS}>
          No evaluation configs yet — create one to start comparing judges.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {configs.map((config) => (
            <EvaluationConfigListItem
              key={config.id}
              config={config}
              busy={busy}
              onEdit={openEdit}
              onDelete={setDeleteTarget}
              onSetDefault={handleSetDefault}
            />
          ))}
        </div>
      )}

      {/* Run panel ───────────────────────────────────────────── */}
      <section className="rounded-xl border border-border bg-card p-4">
        <h3 className="text-sm font-semibold text-foreground">Run a config</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Pick a past eval run (the frozen answers) and a config to grade it with.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <SelectInput
            name="source_run"
            label="Source eval run"
            placeholder={runOptions.length ? 'Select a run' : 'No eval runs yet'}
            options={runOptions}
            value={sourceRunId || undefined}
            onValueChange={setSourceRunId}
            disabled={runOptions.length === 0}
          />
          <SelectInput
            name="config"
            label="Evaluation config"
            placeholder={configOptions.length ? 'Select a config' : 'Create a config first'}
            options={configOptions}
            value={selectedConfigId || undefined}
            onValueChange={setSelectedConfigId}
            disabled={configOptions.length === 0}
          />
        </div>
        <div className="mt-3">
          <CustomButton
            type="primary"
            loading={runMutation.isPending}
            disabled={!sourceRunId || !selectedConfigId}
            onClick={handleRun}
          >
            Run re-grade
          </CustomButton>
        </div>
      </section>

      {/* Results + compare ───────────────────────────────────── */}
      {sourceRunId && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-foreground">
            Results for this run — select up to {MAX_COMPARE} to compare
          </h3>
          {passes.length === 0 ? (
            <div className={HINT_CLASS}>
              No re-grades yet for this run. Run a config above to see scores here.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {passes.map((pass) => (
                <CheckboxField
                  key={pass.config_run_id}
                  id={`pass-${pass.config_run_id}`}
                  label={`Run #${pass.config_run_number} · ${pass.total} scored`}
                  checked={selectedPassIds.includes(pass.config_run_id)}
                  disabled={
                    !selectedPassIds.includes(pass.config_run_id) &&
                    selectedPassIds.length >= MAX_COMPARE
                  }
                  onCheckedChange={(checked) => togglePass(pass.config_run_id, checked === true)}
                />
              ))}
            </div>
          )}
          <EvaluationConfigCompare passes={selectedPasses} results={results} configs={configs} />
        </section>
      )}

      <EvaluationConfigModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        config={editing}
      />

      <CustomModal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete evaluation config"
        description={
          deleteTarget
            ? `Delete "${deleteTarget.name}"? Past results from this config are kept.`
            : ''
        }
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleteMutation.isPending}
        onConfirm={handleDelete}
      />
    </div>
  );
}
