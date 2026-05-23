import {
  createOrganization,
  deleteOrganization,
  getAssociatedTenants,
  switchOrganization,
  updateOrganization,
} from '@/services/organizationService';
import { setToken } from '@/services/auth/helper';
import { useAuthStore } from '@/stores/auth';
import type { OrganizationListItem, OrganizationUpdatePayload } from '@/types/organization';
import { atom } from 'jotai';

interface OrganizationState {
  organizationList: OrganizationListItem[];
}

const organizationAtom = atom<OrganizationState>({
  organizationList: [],
});

// Keep the Zustand auth store in sync — the sidebar workspace switcher
// reads `organizations` from there, separately from this Jotai atom.
const syncAuthStoreOrganizations = (orgs: OrganizationListItem[]) => {
  useAuthStore
    .getState()
    .setOrganizations(orgs.map((o) => ({ id: o.id, name: o.name, role: o.role })));
};

const refetchAndSync = async (
  set: (atom: typeof organizationAtom, value: OrganizationState) => void,
) => {
  const res = await getAssociatedTenants();
  const list = Array.isArray(res) ? res : [];
  set(organizationAtom, { organizationList: list });
  syncAuthStoreOrganizations(list);
};

export const fetchOrganizationList = atom(null, async (_get, set) => {
  await refetchAndSync(set);
});

export const createOrganizationAtom = atom(null, async (_get, set, name: string) => {
  await createOrganization(name);
  await refetchAndSync(set);
});

export const updateOrganizationAtom = atom(
  null,
  async (_get, set, { orgId, payload }: { orgId: string; payload: OrganizationUpdatePayload }) => {
    await updateOrganization(orgId, payload);
    await refetchAndSync(set);
  },
);

export const deleteOrganizationAtom = atom(null, async (_get, set, orgId: string) => {
  await deleteOrganization(orgId);
  await refetchAndSync(set);
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
