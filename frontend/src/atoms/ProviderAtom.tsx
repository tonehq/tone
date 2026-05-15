import { atom } from 'jotai';
import { loadable } from 'jotai/utils';

import {
  deleteAccount,
  deleteModel,
  deleteServiceProvider,
  getProvidersWithAccounts,
  listAccounts,
  listModelsByProvider,
  listServiceProviders,
  upsertAccount,
  upsertModel,
  upsertServiceProvider,
} from '@/services/providerService';
import type {
  ListAccountsParams,
  ListModelsParams,
  ListProvidersParams,
  PaginationInfo,
} from '@/services/providerService';
import type {
  Account,
  AccountUpsertPayload,
  ModelProviderWithAccounts,
  ModelUpsertPayload,
  ServiceProvider,
  ServiceProviderModel,
  ServiceProviderUpsertPayload,
} from '@/types/provider';

// ── Service Providers ──────────────────────────────────────────────

interface ProvidersState {
  providers: ServiceProvider[];
  pagination: PaginationInfo | null;
  loading: boolean;
  loadingMore: boolean;
}

const providersAtom = atom<ProvidersState>({
  providers: [],
  pagination: null,
  loading: false,
  loadingMore: false,
});

interface FetchProvidersPayload {
  params?: ListProvidersParams;
  append?: boolean;
}

const fetchProvidersAtom = atom(null, async (_get, set, payload?: FetchProvidersPayload) => {
  const params = payload?.params;
  const append = payload?.append ?? false;

  if (append) {
    set(providersAtom, (prev) => ({ ...prev, loadingMore: true }));
  } else {
    set(providersAtom, (prev) => ({ ...prev, loading: true }));
  }

  try {
    const result = await listServiceProviders({ page_size: 15, ...params });

    set(providersAtom, (prev) => ({
      providers: append ? [...prev.providers, ...result.providers] : result.providers,
      pagination: result.pagination,
      loading: false,
      loadingMore: false,
    }));
  } catch (error) {
    set(providersAtom, (prev) => ({ ...prev, loading: false, loadingMore: false }));
    throw error;
  }
});

const upsertProviderAtom = atom(
  null,
  async (_get, _set, payload: ServiceProviderUpsertPayload) => await upsertServiceProvider(payload),
);

const deleteProviderAtom = atom(null, async (_get, _set, providerId: number) => {
  await deleteServiceProvider(providerId);
});

// ── Models ─────────────────────────────────────────────────────────

interface ModelsState {
  models: ServiceProviderModel[];
  pagination: PaginationInfo | null;
  loading: boolean;
}

const modelsAtom = atom<ModelsState>({
  models: [],
  pagination: null,
  loading: false,
});

const fetchModelsAtom = atom(null, async (_get, set, params: ListModelsParams) => {
  set(modelsAtom, { models: [], pagination: null, loading: true });
  try {
    const result = await listModelsByProvider(params);
    set(modelsAtom, {
      models: result.models,
      pagination: result.pagination,
      loading: false,
    });
  } catch (error) {
    set(modelsAtom, (prev) => ({ ...prev, loading: false }));
    throw error;
  }
});

const upsertModelAtom = atom(
  null,
  async (_get, _set, payload: ModelUpsertPayload) => await upsertModel(payload),
);

const deleteModelAtom = atom(null, async (_get, _set, modelId: number) => {
  await deleteModel(modelId);
});

// ── Accounts (org-scoped provider instances) ───────────────────────

interface AccountsState {
  accounts: Account[];
  pagination: PaginationInfo | null;
  loading: boolean;
  loadingMore: boolean;
}

const accountsAtom = atom<AccountsState>({
  accounts: [],
  pagination: null,
  loading: false,
  loadingMore: false,
});

interface FetchAccountsPayload {
  params?: ListAccountsParams;
  append?: boolean;
}

const fetchAccountsAtom = atom(null, async (_get, set, payload?: FetchAccountsPayload) => {
  const params = payload?.params;
  const append = payload?.append ?? false;

  if (append) {
    set(accountsAtom, (prev) => ({ ...prev, loadingMore: true }));
  } else {
    set(accountsAtom, (prev) => ({ ...prev, loading: true }));
  }

  try {
    const result = await listAccounts(params);
    set(accountsAtom, (prev) => ({
      accounts: append ? [...prev.accounts, ...result.accounts] : result.accounts,
      pagination: result.pagination,
      loading: false,
      loadingMore: false,
    }));
  } catch (error) {
    set(accountsAtom, (prev) => ({ ...prev, loading: false, loadingMore: false }));
    throw error;
  }
});

const upsertAccountAtom = atom(
  null,
  async (_get, _set, payload: AccountUpsertPayload) => await upsertAccount(payload),
);

const deleteAccountAtom = atom(null, async (_get, _set, uuid: string) => {
  await deleteAccount(uuid);
});

// ── Loadable atom for AgentFormPage — fetches org-scoped accounts ──

const providersRefreshAtom = atom(0);

const providersRowsAtom = atom<Promise<ModelProviderWithAccounts[]>>(async (get) => {
  get(providersRefreshAtom);
  return await getProvidersWithAccounts();
});

const loadableProvidersAtom = loadable(providersRowsAtom);

const refetchProvidersAtom = atom(null, (_get, set) => {
  set(providersRefreshAtom, (c) => c + 1);
});

// Backward-compat aliases
const servicesAtom = accountsAtom;
const fetchServicesAtom = fetchAccountsAtom;
const upsertServiceAtom = upsertAccountAtom;
const deleteServiceAtom = deleteAccountAtom;

export {
  providersAtom,
  fetchProvidersAtom,
  upsertProviderAtom,
  deleteProviderAtom,
  modelsAtom,
  fetchModelsAtom,
  upsertModelAtom,
  deleteModelAtom,
  accountsAtom,
  fetchAccountsAtom,
  upsertAccountAtom,
  deleteAccountAtom,
  servicesAtom,
  fetchServicesAtom,
  upsertServiceAtom,
  deleteServiceAtom,
  loadableProvidersAtom,
  refetchProvidersAtom,
};
