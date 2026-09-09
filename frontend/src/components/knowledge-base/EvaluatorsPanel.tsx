'use client';

import { Pencil, Plus, Star, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';

import { CustomButton, CustomModal, CustomTable } from '@/components/shared';
import {
  useDeleteEvaluationConfig,
  useEvaluationConfigs,
  useSetDefaultEvaluationConfig,
} from '@/lib/api/evaluationConfigs';
import type { CustomTableColumn } from '@/types/components';
import type { EvaluationConfig } from '@/types/evaluationConfig';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import EvaluationConfigModal from './EvaluationConfigModal';
import JudgePromptModal from './JudgePromptModal';

// Manage the org-wide judges (evaluators): create / edit / delete / set default.
// A pure table view — running + comparing lives in the sibling Runs tab.
export default function EvaluatorsPanel() {
  const { data: configList, isLoading } = useEvaluationConfigs();
  const configs = useMemo(() => configList?.items ?? [], [configList]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<EvaluationConfig | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<EvaluationConfig | null>(null);
  const [promptView, setPromptView] = useState<EvaluationConfig | null>(null);

  const deleteMutation = useDeleteEvaluationConfig();
  const setDefaultMutation = useSetDefaultEvaluationConfig();
  const busy = deleteMutation.isPending || setDefaultMutation.isPending;

  const openCreate = () => {
    setEditing(null);
    setModalOpen(true);
  };
  const openEdit = (config: EvaluationConfig) => {
    setEditing(config);
    setModalOpen(true);
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

  const columns = useMemo<CustomTableColumn<EvaluationConfig>[]>(
    () => [
      {
        key: 'name',
        title: 'Name',
        render: (_v, r) => (
          <div className="flex items-center gap-2">
            <span className="font-medium text-foreground">{r.name}</span>
            {r.is_default && (
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                Default
              </span>
            )}
          </div>
        ),
      },
      { key: 'judge_model', title: 'Judge model', dataIndex: 'judge_model' },
      {
        key: 'metrics',
        title: 'Metrics',
        align: 'center',
        render: (_v, r) => r.metrics_enabled.length,
      },
      {
        key: 'prompt',
        title: 'Prompt',
        render: (_v, r) =>
          r.judge_prompt ? (
            <CustomButton type="text" size="xs" onClick={() => setPromptView(r)}>
              View
            </CustomButton>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        render: (_v, r) => (
          <div className="flex items-center justify-end gap-1">
            {!r.is_default && (
              <CustomButton
                type="text"
                size="icon-xs"
                aria-label="Set as default"
                disabled={busy}
                onClick={() => handleSetDefault(r)}
              >
                <Star className="size-4" />
              </CustomButton>
            )}
            <CustomButton
              type="text"
              size="icon-xs"
              aria-label="Edit config"
              disabled={busy}
              onClick={() => openEdit(r)}
            >
              <Pencil className="size-4" />
            </CustomButton>
            <CustomButton
              type="text"
              size="icon-xs"
              aria-label="Delete config"
              disabled={busy}
              onClick={() => setDeleteTarget(r)}
            >
              <Trash2 className="size-4" />
            </CustomButton>
          </div>
        ),
      },
    ],
    [busy],
  );

  return (
    <div className="flex flex-col gap-4 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Evaluators</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            The org-wide judges used to score eval runs — a model, optional custom rubric prompt,
            and metrics. Run them from the Runs tab.
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus className="size-4" />} onClick={openCreate}>
          New config
        </CustomButton>
      </div>

      <CustomTable
        columns={columns}
        dataSource={configs}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        emptyState="No evaluators yet — create one to start comparing judges."
      />

      <EvaluationConfigModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        config={editing}
      />

      <JudgePromptModal
        open={promptView !== null}
        onClose={() => setPromptView(null)}
        configName={promptView?.name ?? ''}
        prompt={promptView?.judge_prompt ?? null}
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
