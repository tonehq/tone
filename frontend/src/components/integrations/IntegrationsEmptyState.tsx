import { CustomButton } from '@/components/shared';
import { Plus, Sparkles } from 'lucide-react';

/** Empty placeholder shown when the catalog has no integrations yet. */
export default function IntegrationsEmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-background py-16 text-center">
      <Sparkles className="mx-auto size-6 text-teal-500" />
      <h3 className="mt-3 text-[14px] font-semibold text-foreground">No integrations yet</h3>
      <p className="mt-1 text-[12px] text-muted-foreground">
        Add a third-party provider to start connecting accounts.
      </p>
      <div className="mt-4">
        <CustomButton type="primary" size="sm" onClick={onCreate} icon={<Plus size={13} />}>
          New integration
        </CustomButton>
      </div>
    </div>
  );
}
