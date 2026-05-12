import {
  createOrganization,
  deleteOrganization,
  getAssociatedTenants,
  switchOrganization,
  updateOrganization,
} from '@/services/organizationService';
import { setToken } from '@/services/auth/helper';
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

export const switchOrganizationAtom = atom(null, async (_get, _set, orgId: string) => {
  const res = await switchOrganization(orgId);
  // Backend returns { access_token, organization: { id, name, slug }, role }.
  // Normalize into the shape setToken expects (organizations array).
  const tokenData = {
    ...res,
    organizations: res.organization ? [res.organization] : [],
  };
  await setToken(tokenData);
  window.location.reload();
});

export default organizationAtom;
