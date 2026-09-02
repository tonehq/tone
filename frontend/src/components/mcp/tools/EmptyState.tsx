import { IconChip } from '@/components/shared';
import { Wrench } from 'lucide-react';

export default function EmptyState({ hasFilter }: { hasFilter: boolean }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <IconChip icon={<Wrench strokeWidth={1.75} />} tone="muted" size="xl" />
      <div className="max-w-sm text-center">
        <p className="font-semibold text-foreground">
          {hasFilter ? 'No tools match your search' : 'No tools available'}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {hasFilter
            ? 'Try a different search term.'
            : 'This MCP server is connected but did not expose any tools.'}
        </p>
      </div>
    </div>
  );
}
