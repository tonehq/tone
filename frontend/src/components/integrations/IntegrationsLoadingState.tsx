import { Loader2 } from 'lucide-react';

/** Loading placeholder for the integrations list while the first fetch runs. */
export default function IntegrationsLoadingState() {
  return (
    <div className="flex items-center justify-center py-20 text-muted-foreground">
      <Loader2 className="mr-2 size-4 animate-spin" />
      <span className="text-sm">Loading integrations…</span>
    </div>
  );
}
