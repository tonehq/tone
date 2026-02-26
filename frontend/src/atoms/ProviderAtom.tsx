import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import { type ServiceProvider, getServiceProviders } from '@/services/providerService';

const providersRefreshAtom = atom(0);

const providersRowsAtom = atom<Promise<ServiceProvider[]>>(async (get) => {
  get(providersRefreshAtom);
  return await getServiceProviders();
});

const loadableProvidersAtom = loadable(providersRowsAtom);

const refetchProvidersAtom = atom(null, (_get, set) => {
  set(providersRefreshAtom, (c) => c + 1);
});

export { loadableProvidersAtom, refetchProvidersAtom };
