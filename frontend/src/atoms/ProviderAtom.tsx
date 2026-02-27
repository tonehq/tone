import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import { getServiceProviders } from '@/services/providerService';
import type { ServiceProvider } from '@/types/provider';

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
