import { CustomButton } from '@/components/shared';
import { Building2, Plus } from 'lucide-react';

interface OrganizationEmptyStateProps {
  onCreate: () => void;
}

const OrganizationEmptyState: React.FC<OrganizationEmptyStateProps> = ({ onCreate }) => (
  <div className="flex flex-col items-center justify-center py-24">
    <div className="flex size-16 items-center justify-center rounded-2xl bg-primary/10">
      <Building2 className="size-8 text-primary" />
    </div>
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
