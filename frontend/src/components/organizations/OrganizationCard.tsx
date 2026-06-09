'use client';

import OrganizationCardMenu from '@/components/organizations/OrganizationCardMenu';
import { type OrgRow, getInitials, roleConfig } from '@/components/organizations/constants';
import { Card, CardContent } from '@/components/ui/card';
import { formatDate } from '@/utils/date';
import { Calendar } from 'lucide-react';

interface OrganizationCardProps {
  org: OrgRow;
  index: number;
  onEdit: (org: OrgRow) => void;
  onDelete: (org: OrgRow) => void;
}

const OrganizationCard: React.FC<OrganizationCardProps> = ({ org, index, onEdit, onDelete }) => {
  const role = roleConfig[org.role] ?? roleConfig.member;
  const RoleIcon = role.icon;
  const isAdminOrOwner = org.role === 'admin' || org.role === 'owner';

  return (
    <Card
      className="group relative cursor-pointer gap-0 overflow-hidden rounded-xl border-border py-0 transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20"
      style={{ animationDelay: `${index * 60}ms` }}
      onClick={() => {
        if (isAdminOrOwner) onEdit(org);
      }}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2">
          {/* Avatar + Info */}
          <div className="flex min-w-0 flex-1 items-start gap-3.5">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-border bg-background font-mono text-sm font-semibold text-foreground transition-colors group-hover:border-primary/40">
              {getInitials(org.name)}
            </div>

            <div className="min-w-0 flex-1">
              <h3 className="truncate text-[15px] font-semibold text-foreground" title={org.name}>
                {org.name}
              </h3>
              <p className="mt-0.5 truncate text-xs text-muted-foreground" title={org.slug}>
                {org.slug}
              </p>
            </div>
          </div>

          {/* Actions menu */}
          {isAdminOrOwner && (
            <OrganizationCardMenu
              orgId={org.id}
              role={org.role}
              onEdit={() => onEdit(org)}
              onDelete={() => onDelete(org)}
            />
          )}
        </div>

        {/* Meta row */}
        <div className="mt-4 flex items-center gap-4 border-t border-border/50 pt-3.5">
          <div className="flex items-center gap-1.5 rounded-md border border-border px-2 py-1">
            <RoleIcon className="size-3 text-foreground" />
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              {role.label}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Calendar className="size-3" />
            <span>{org.joined_at ? formatDate(org.joined_at, 'DD MMM YYYY') : '—'}</span>
          </div>
        </div>
      </CardContent>

      {/* hairline accent that wipes in on hover */}
      <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
    </Card>
  );
};

export default OrganizationCard;
