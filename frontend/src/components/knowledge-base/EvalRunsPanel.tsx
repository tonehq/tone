'use client';

import { useMemo, useState } from 'react';

import { CustomButton, SelectInput } from '@/components/shared';
import { useEvalRunsFiltered } from '@/lib/api/evals';
import {
  useEvaluationConfigResults,
  useEvaluationConfigs,
  useRunEvaluationConfig,
} from '@/lib/api/evaluationConfigs';
import { handleApiError } from '@/utils/helpers';
import { toSelectOptions } from '@/utils/selectUtils';
import { showToast } from '@/utils/toast';

import { MAX_COMPARE } from './evalConfigConstants';
import EvaluationConfigCompare from './EvaluationConfigCompare';
import EvaluationConfigRunsTable from './EvaluationConfigRunsTable';
import EvaluationConfigScoresTable from './EvaluationConfigScoresTable';

interface EvalRunsPanelProps {
  uploadId: string;
}

// Run a config against a frozen source eval run, then view/compare the scores.
export default function EvalRunsPanel({ uploadId }: EvalRunsPanelProps) {
  const { data: configList } = useEvaluationConfigs();
  const configs = useMemo(() => configList?.items ?? [], [configList]);

  const { data: runs = [] } = useEvalRunsFiltered(uploadId, {});
  const [sourceRunId, setSourceRunId] = useState<string>('');
  const [selectedConfigId, setSelectedConfigId] = useState<string>('');
  const [selectedPassIds, setSelectedPassIds] = useState<string[]>([]);

  const runMutation = useRunEvaluationConfig();
  const { data: resultsData } = useEvaluationConfigResults(sourceRunId || null, undefined, true);
  const passes = useMemo(() => resultsData?.runs ?? [], [resultsData]);
  const results = useMemo(() => resultsData?.results ?? [], [resultsData]);

  const runOptions = useMemo(
    () =>
      toSelectOptions(runs, {
        valueKey: 'run_id',
        labelKey: 'run_id',
        labelFormatter: (r) => `Run #${r.run_number}${r.judge_model ? ` · ${r.judge_model}` : ''}`,
      }),
    [runs],
  );
  const configOptions = useMemo(
    () =>
      toSelectOptions(configs, {
        valueKey: 'id',
        labelKey: 'name',
        labelFormatter: (c) => (c.is_default ? `${c.name} (default)` : c.name),
      }),
    [configs],
  );

  const selectedPasses = useMemo(
    () => passes.filter((p) => selectedPassIds.includes(p.config_run_id)),
    [passes, selectedPassIds],
  );

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

  return (
    <div className="flex flex-col gap-5 py-4">
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

      {sourceRunId && (
        <section className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-foreground">
            Config runs for this eval run — select up to {MAX_COMPARE} to compare
          </h3>
          <EvaluationConfigRunsTable
            passes={passes}
            configs={configs}
            selectedIds={selectedPassIds}
            maxCompare={MAX_COMPARE}
            onToggle={togglePass}
          />

          {selectedPasses.length > 0 && (
            <>
              <h3 className="mt-2 text-sm font-semibold text-foreground">Compare</h3>
              <EvaluationConfigCompare
                passes={selectedPasses}
                results={results}
                configs={configs}
              />
              <h3 className="mt-2 text-sm font-semibold text-foreground">Per-question scores</h3>
              <EvaluationConfigScoresTable
                passes={selectedPasses}
                results={results}
                configs={configs}
              />
            </>
          )}
        </section>
      )}
    </div>
  );
}
