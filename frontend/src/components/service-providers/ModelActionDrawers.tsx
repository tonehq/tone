'use client';

import { CustomModal } from '@/components/shared';

import ApiKeyEditDrawer from './api-key-edit-drawer';
import ModelFormDrawer from './model-form-drawer';
import ModelProviderEditDrawer from './model-provider-edit-drawer';
import type { ModelActions } from './useModelActions';

interface ModelActionDrawersProps {
  actions: ModelActions;
}

/**
 * Renders the edit/delete surfaces launched from the model-row detail drawer.
 * State + side effects live in `useModelActions`; this component is JSX only.
 */
const ModelActionDrawers = ({ actions }: ModelActionDrawersProps) => (
  <>
    <ModelFormDrawer
      open={actions.addModelOpen}
      editing={null}
      providers={actions.providerOptions}
      onClose={actions.closeAddModel}
      onSubmit={actions.submitNewModel}
      isPending={actions.savingNewModel}
    />

    <ModelFormDrawer
      open={actions.modelEditOpen}
      editing={actions.editingModel}
      onClose={actions.closeModelEdit}
      onSubmit={actions.submitModel}
      isPending={actions.savingModel}
    />

    <ModelProviderEditDrawer
      open={actions.providerEditOpen}
      editing={actions.editingProvider}
      loading={actions.providerEditLoading}
      onClose={actions.closeProviderEdit}
      onSubmit={actions.submitProvider}
      isPending={actions.savingProvider}
    />

    <ApiKeyEditDrawer
      open={actions.keyEditOpen}
      editing={actions.editingKey}
      loading={actions.keyEditLoading}
      onClose={actions.closeKeyEdit}
      onSubmit={actions.submitKey}
      isPending={actions.savingKey}
    />

    <CustomModal
      open={!!actions.deleteModelTarget}
      onClose={() => !actions.deletingModel && actions.closeDeleteModel()}
      title="Delete model?"
      description={
        actions.deleteModelTarget
          ? `This permanently deletes "${
              actions.deleteModelTarget.display_name || actions.deleteModelTarget.name
            }" from the global catalog for every organization. Agents referencing it may stop working.`
          : ''
      }
      confirmText="Delete"
      confirmType="danger"
      confirmLoading={actions.deletingModel}
      onConfirm={actions.confirmDeleteModel}
    />

    <CustomModal
      open={!!actions.deleteKeyTarget}
      onClose={() => !actions.deletingKey && actions.closeDeleteKey()}
      title="Delete API key?"
      description={
        actions.deleteKeyTarget
          ? `This permanently deletes the ${
              actions.deleteKeyTarget.label ? `"${actions.deleteKeyTarget.label}" ` : ''
            }API key for ${actions.deleteKeyTarget.provider}. Agents using this credential will stop working.`
          : ''
      }
      confirmText="Delete"
      confirmType="danger"
      confirmLoading={actions.deletingKey}
      onConfirm={actions.confirmDeleteKey}
    />
  </>
);

export default ModelActionDrawers;
