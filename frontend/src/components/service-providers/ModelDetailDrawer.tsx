import { Pencil, Trash2 } from 'lucide-react';

import { CustomButton, CustomDrawer } from '@/components/shared';
import type { ModelRow } from '@/types/service';
import { formatDate } from '@/utils/date';

import DetailField from './DetailField';
import ModelTypeBadge from './ModelTypeBadge';

interface ModelDetailDrawerProps {
  model: ModelRow | null;
  open: boolean;
  onClose: () => void;
  onEditProvider: (model: ModelRow) => void;
  onEditModel: (model: ModelRow) => void;
  onDeleteModel: (model: ModelRow) => void;
  onEditApiKey: (model: ModelRow) => void;
  onDeleteApiKey: (model: ModelRow) => void;
}

const ModelDetailDrawer = ({
  model,
  open,
  onClose,
  onEditProvider,
  onEditModel,
  onDeleteModel,
  onEditApiKey,
  onDeleteApiKey,
}: ModelDetailDrawerProps) => (
  <CustomDrawer
    open={open}
    onClose={onClose}
    title={model ? model.display_name || model.name : 'Model details'}
    description={model?.provider?.display_name ?? undefined}
    width="sm:max-w-lg"
  >
    {model && (
      <div className="flex flex-col gap-6">
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Provider</h3>
            <CustomButton
              type="default"
              size="sm"
              icon={<Pencil className="size-3.5" />}
              onClick={() => onEditProvider(model)}
            >
              Edit
            </CustomButton>
          </div>
          <DetailField label="Name">{model.provider?.display_name ?? '—'}</DetailField>
          <DetailField label="Slug">
            <span className="text-muted-foreground">{model.provider?.slug ?? '—'}</span>
          </DetailField>
        </section>

        <section className="flex flex-col gap-4 border-t border-border pt-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Model</h3>
            <div className="flex items-center gap-2">
              <CustomButton
                type="default"
                size="sm"
                icon={<Pencil className="size-3.5" />}
                onClick={() => onEditModel(model)}
              >
                Edit
              </CustomButton>
              <CustomButton
                type="default"
                size="sm"
                icon={<Trash2 className="size-3.5" />}
                onClick={() => onDeleteModel(model)}
              >
                Delete
              </CustomButton>
            </div>
          </div>
          <DetailField label="Type">
            <ModelTypeBadge kind={model.kind} />
          </DetailField>
          <DetailField label="Status">
            <span
              className={
                model.is_active ? 'text-emerald-600 dark:text-emerald-400' : 'text-muted-foreground'
              }
            >
              {model.is_active ? 'Active' : 'Inactive'}
            </span>
          </DetailField>
          <DetailField label="Model name">{model.name}</DetailField>
          {model.display_name && (
            <DetailField label="Display name">{model.display_name}</DetailField>
          )}
          <DetailField label="Description">
            <span className="text-muted-foreground">{model.description || '—'}</span>
          </DetailField>
          <DetailField label="Base URL">
            <span className="break-all text-muted-foreground">{model.base_url || '—'}</span>
          </DetailField>
          <div className="grid grid-cols-2 gap-4">
            <DetailField label="Created">
              <span className="tabular-nums text-muted-foreground">
                {formatDate(model.created_at)}
              </span>
            </DetailField>
            <DetailField label="Updated">
              <span className="tabular-nums text-muted-foreground">
                {formatDate(model.updated_at)}
              </span>
            </DetailField>
          </div>
        </section>

        <section className="flex flex-col gap-4 border-t border-border pt-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">API key</h3>
            {model.api_key?.present && (
              <div className="flex items-center gap-2">
                <CustomButton
                  type="default"
                  size="sm"
                  icon={<Pencil className="size-3.5" />}
                  onClick={() => onEditApiKey(model)}
                >
                  Edit
                </CustomButton>
                <CustomButton
                  type="default"
                  size="sm"
                  icon={<Trash2 className="size-3.5" />}
                  onClick={() => onDeleteApiKey(model)}
                >
                  Delete
                </CustomButton>
              </div>
            )}
          </div>
          {model.api_key?.present ? (
            <>
              <DetailField label="Label">
                {model.api_key.label || (
                  <span className="text-muted-foreground">Unlabeled key</span>
                )}
              </DetailField>
              <div className="grid grid-cols-2 gap-4">
                <DetailField label="Default">{model.api_key.is_default ? 'Yes' : 'No'}</DetailField>
                <DetailField label="Active">{model.api_key.is_active ? 'Yes' : 'No'}</DetailField>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No API key configured for this model&apos;s provider and type.
            </p>
          )}
        </section>
      </div>
    )}
  </CustomDrawer>
);

export default ModelDetailDrawer;
