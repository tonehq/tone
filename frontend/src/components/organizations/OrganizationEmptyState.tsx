import { CustomButton, IconChip } from '@/components/shared';
import { Building2, Plus } from 'lucide-react';

interface OrganizationEmptyStateProps {
  onCreate: () => void;
}

const OrganizationEmptyState: React.FC<OrganizationEmptyStateProps> = ({ onCreate }) => (
  <div className="flex flex-col items-center justify-center py-24">
    <IconChip icon={<Building2 strokeWidth={1.75} />} tone="primary" size="2xl" />
    <h3 className="mt-5 text-[15px] font-semibold text-foreground">No organizations yet</h3>
    <p className="mt-1.5 max-w-sm text-center text-[13px] leading-relaxed text-muted-foreground">
      Create your first organization to start collaborating with your team.
    </p>
    <CustomButton type="primary" icon={<Plus />} onClick={onCreate} className="mt-5">
      Create Organization
    </CustomButton>
  </div>
);

export default OrganizationEmptyState;
