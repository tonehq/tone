'use client';

import { useEffect, useState } from 'react';
import { useAtom, useSetAtom } from 'jotai';
import Cookies from 'js-cookie';
import { Check, ChevronDown } from 'lucide-react';

import { CustomButton } from '@/components/shared';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { TENANT_ID } from '@/constants';
import organizationAtom, {
  fetchOrganizationList,
  switchOrganizationAtom,
} from '@/atoms/OrganizationAtom';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

export interface SidebarOrganizationProps {
  isExpanded: boolean;
}

function getCurrentOrgName(): string {
  try {
    const loginDataRaw = Cookies.get('login_data');
    if (!loginDataRaw) return '';
    const loginData = JSON.parse(loginDataRaw);
    const tenantId = Cookies.get(TENANT_ID) || '';
    const orgs = loginData.organizations;
    if (Array.isArray(orgs)) {
      const match = orgs.find((o: any) => String(o.id) === String(tenantId));
      if (match) return match.name;
      if (orgs.length > 0) return orgs[0].name;
    }
    // Fallback: check current_organization from login data
    if (loginData.current_organization?.name) {
      return loginData.current_organization.name;
    }
  } catch {
    // ignore parse errors
  }
  return '';
}

export function SidebarOrganization({ isExpanded }: SidebarOrganizationProps) {
  const [orgState] = useAtom(organizationAtom);
  const fetchOrgs = useSetAtom(fetchOrganizationList);
  const switchOrg = useSetAtom(switchOrganizationAtom);
  const [currentOrgId, setCurrentOrgId] = useState('');

  useEffect(() => {
    setCurrentOrgId(Cookies.get(TENANT_ID) || '');
    fetchOrgs();
  }, [fetchOrgs]);

  // Derive name: prefer atom list match, then login_data cookie fallback
  const currentOrg = orgState.organizationList.find((o) => String(o.id) === String(currentOrgId));
  const orgName = currentOrg?.name || getCurrentOrgName() || 'My Workspace';
  const orgInitial = orgName.charAt(0).toUpperCase();

  const handleSwitch = async (orgId: string) => {
    if (orgId === currentOrgId) return;
    try {
      await switchOrg(orgId);
    } catch (error) {
      handleApiError(error);
    }
  };

  const avatar = (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-[13px] font-semibold text-primary">
      {orgInitial}
    </div>
  );

  if (!isExpanded) {
    return (
      <DropdownMenu>
        <Tooltip>
          <TooltipTrigger asChild>
            <DropdownMenuTrigger asChild>
              <CustomButton
                type="text"
                htmlType="button"
                className={cn(
                  'mx-auto flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10',
                  'text-[13px] font-semibold text-primary transition-colors hover:bg-primary/15',
                )}
              >
                {orgInitial}
              </CustomButton>
            </DropdownMenuTrigger>
          </TooltipTrigger>
          <TooltipContent side="right">{orgName}</TooltipContent>
        </Tooltip>
        <DropdownMenuContent side="right" align="start" className="w-56">
          <DropdownMenuLabel className="text-xs text-muted-foreground">
            Organizations
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {orgState.organizationList.map((org) => (
            <DropdownMenuItem key={org.id} onClick={() => handleSwitch(org.id)}>
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-primary/10 text-[11px] font-semibold text-primary">
                {org.name.charAt(0).toUpperCase()}
              </div>
              <span className="flex-1 truncate text-sm">{org.name}</span>
              {String(org.id) === String(currentOrgId) && (
                <Check size={14} className="text-primary" />
              )}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <CustomButton
          type="text"
          fullWidth
          htmlType="button"
          className="flex items-center gap-2.5 rounded-lg px-2 py-2 text-foreground transition-colors hover:bg-muted/60"
        >
          {avatar}
          <span className="flex-1 truncate text-left text-[13px] font-medium text-foreground">
            {orgName}
          </span>
          <ChevronDown size={14} className="shrink-0 text-muted-foreground" />
        </CustomButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="bottom" align="start" className="w-56">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Organizations
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {orgState.organizationList.map((org) => (
          <DropdownMenuItem key={org.id} onClick={() => handleSwitch(org.id)}>
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-primary/10 text-[11px] font-semibold text-primary">
              {org.name.charAt(0).toUpperCase()}
            </div>
            <span className="flex-1 truncate text-sm">{org.name}</span>
            {String(org.id) === String(currentOrgId) && (
              <Check size={14} className="text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
