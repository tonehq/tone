import type { CustomTableColumn } from '@/types/components';
import type { ModelRow } from '@/types/service';

import ApiKeyMaskCell from './ApiKeyMaskCell';
import ModelTypeBadge from './ModelTypeBadge';

/** Column defs for the flattened models table (render cells = render logic). */
export function getModelColumns(): CustomTableColumn<ModelRow>[] {
  return [
    {
      key: 'provider',
      title: 'Provider',
      render: (_v, m) => (
        <span className="truncate text-sm font-medium text-foreground">
          {m.provider?.display_name ?? '-'}
        </span>
      ),
    },
    {
      key: 'name',
      title: 'Model',
      dataIndex: 'name',
      sorter: true,
      render: (_v, m) => (
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-sm text-foreground">{m.display_name || m.name}</span>
          {m.display_name && m.display_name !== m.name && (
            <span className="truncate text-xs text-muted-foreground">{m.name}</span>
          )}
        </div>
      ),
    },
    {
      key: 'api_key',
      title: 'API Key',
      width: 'w-[160px]',
      render: (_v, m) => <ApiKeyMaskCell present={m.api_key?.present} />,
    },
    {
      key: 'kind',
      title: 'Type',
      dataIndex: 'kind',
      sorter: true,
      width: 'w-[100px]',
      render: (_v, m) => <ModelTypeBadge kind={m.kind} />,
    },
  ];
}
