import {
  createOrganization,
  deleteOrganization,
  getAssociatedTenants,
  updateOrganization,
} from '@/services/organizationService';
import type { OrganizationListItem, OrganizationUpdatePayload } from '@/types/organization';
import { atom } from 'jotai';

interface OrganizationState {
  organizationList: OrganizationListItem[];
}

const organizationAtom = atom<OrganizationState>({
  organizationList: [],
});

export const fetchOrganizationList = atom(null, async (_get, set) => {
  const res = await getAssociatedTenants();
  set(organizationAtom, { organizationList: Array.isArray(res) ? res : [] });
});

export const createOrganizationAtom = atom(null, async (_get, set, name: string) => {
  await createOrganization(name);
  const res = await getAssociatedTenants();
  set(organizationAtom, { organizationList: Array.isArray(res) ? res : [] });
});

export const updateOrganizationAtom = atom(
  null,
  async (_get, set, { orgId, payload }: { orgId: string; payload: OrganizationUpdatePayload }) => {
    await updateOrganization(orgId, payload);
    const res = await getAssociatedTenants();
    set(organizationAtom, { organizationList: Array.isArray(res) ? res : [] });
  },
);

export const deleteOrganizationAtom = atom(null, async (_get, set, orgId: string) => {
  await deleteOrganization(orgId);
  const res = await getAssociatedTenants();
  set(organizationAtom, { organizationList: Array.isArray(res) ? res : [] });
});

export default organizationAtom;
