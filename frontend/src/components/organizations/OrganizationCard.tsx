'use client';

import OrganizationCardMenu from '@/components/organizations/OrganizationCardMenu';
import {
  type OrgRow,
  getAvatarGradient,
  getInitials,
  roleConfig,
} from '@/components/organizations/constants';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/utils/cn';
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
      className="group relative cursor-pointer gap-0 overflow-hidden py-0 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
      style={{ animationDelay: `${index * 60}ms` }}
      onClick={() => {
        if (isAdminOrOwner) onEdit(org);
      }}
    >
      {/* Gradient accent bar */}
      <div className={cn('h-1 w-full bg-gradient-to-r opacity-80', getAvatarGradient(org.name))} />

      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-2">
          {/* Avatar + Info */}
          <div className="flex min-w-0 flex-1 items-start gap-3.5">
            <div
              className={cn(
                'flex size-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-sm font-semibold text-white shadow-sm',
                getAvatarGradient(org.name),
              )}
            >
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
          <div className={cn('flex items-center gap-1.5 rounded-md px-2 py-1', role.bg)}>
            <RoleIcon className={cn('size-3', role.color)} />
            <span className={cn('text-xs font-medium', role.color)}>{role.label}</span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Calendar className="size-3" />
            <span>{org.joined_at ? formatDate(org.joined_at, 'DD MMM YYYY') : '—'}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default OrganizationCard;
