import { atom } from 'jotai';

interface SettingsState {
  organizationList: any[];
}

export const settingsAtom = atom<SettingsState>({
  organizationList: [],
});

export const fetchOrganizationList = atom(null, async (_, set, args: any) => {
  set(settingsAtom, (prev: any) => ({ ...prev, organizationList: args }));
});

export default settingsAtom;
