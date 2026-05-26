import { atom } from 'jotai';

import {
  createProviderModel,
  createService,
  deleteProviderModel,
  deleteProviderServices,
  deleteService,
  getService,
  listProviderKeys,
  listProviderModels,
  listServices,
  updateProviderModel,
  updateService,
  type ListProviderKeysParams,
  type ListProviderModelsParams,
  type ListServicesParams,
  type ModelUpsertPayload,
} from '@/services/servicesService';
import type {
  ProviderModel,
  ProviderUsage,
  Service,
  ServiceKind,
  ServiceUpsertPayload,
} from '@/types/service';

// Each fetch atom tags its call with an incrementing token, so when filters,
// sort, or page change rapidly we can drop responses that aren't from the
// most recent dispatch. Without this the last-resolved (not last-dispatched)
// response wins and the UI flashes back to stale data.
function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

// ─── aggregated cards state (Services page) ────────────────────────────────
export interface ServicesState {
  items: ProviderUsage[];
  total: number;
  page: number;
  page_size: number;
  loading: boolean;
  loadingMore: boolean;
}

const initialServicesState: ServicesState = {
  items: [],
  total: 0,
  page: 1,
  page_size: 12,
  loading: false,
  loadingMore: false,
};

const servicesAtom = atom<ServicesState>(initialServicesState);
export default servicesAtom;

export interface FetchServicesArgs extends ListServicesParams {
  append?: boolean;
}

const trackServicesRequest = makeLatestTracker();

export const fetchServicesAtom = atom(null, async (_get, set, args: FetchServicesArgs = {}) => {
  const { append = false, ...params } = args;
  const isLatest = trackServicesRequest();
  set(servicesAtom, (prev) => ({
    ...prev,
    loading: append ? prev.loading : true,
    loadingMore: append,
  }));
  try {
    const res = await listServices(params);
    if (!isLatest()) return;
    set(servicesAtom, (prev) => ({
      ...prev,
      items: append ? [...prev.items, ...res.rows] : res.rows,
      total: res.total,
      page: res.page,
      page_size: res.page_size,
      loading: false,
      loadingMore: false,
    }));
  } catch (err) {
    if (!isLatest()) return;
    set(servicesAtom, (prev) => ({ ...prev, loading: false, loadingMore: false }));
    throw err;
  }
});

// ─── upsert (create OR update individual ApiKey) ───────────────────────────
export const upsertServiceAtom = atom(
  null,
  async (_get, _set, payload: { id?: string; values: ServiceUpsertPayload }): Promise<Service> => {
    if (payload.id) return updateService(payload.id, payload.values);
    return createService(payload.values);
  },
);

// ─── delete individual ApiKey ──────────────────────────────────────────────
export const deleteServiceAtom = atom(null, async (_get, _set, id: string) => {
  await deleteService(id);
});

// ─── fetch a single ApiKey (used by card edit) ─────────────────────────────
export const fetchServiceAtom = atom(
  null,
  async (_get, _set, id: string): Promise<Service> => getService(id),
);

// ─── delete every ApiKey for (org, provider) — optionally scoped to one kind ─
export const deleteProviderAtom = atom(
  null,
  async (
    _get,
    _set,
    payload: { providerId: string; serviceType?: ServiceKind },
  ): Promise<{ deleted: number }> =>
    deleteProviderServices(payload.providerId, payload.serviceType),
);

// ─── per-provider keys state (detail page) ─────────────────────────────────
export interface ProviderKeysState {
  providerId: string | null;
  items: Service[];
  total: number;
  page: number;
  page_size: number;
  loading: boolean;
}

const initialProviderKeysState: ProviderKeysState = {
  providerId: null,
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  loading: false,
};

export const providerKeysAtom = atom<ProviderKeysState>(initialProviderKeysState);

const trackProviderKeysRequest = makeLatestTracker();

export const fetchProviderKeysAtom = atom(
  null,
  async (_get, set, args: { providerId: string; params?: ListProviderKeysParams }) => {
    const isLatest = trackProviderKeysRequest();
    set(providerKeysAtom, (prev) => ({ ...prev, loading: true, providerId: args.providerId }));
    try {
      const res = await listProviderKeys(args.providerId, args.params);
      if (!isLatest()) return;
      set(providerKeysAtom, {
        providerId: args.providerId,
        items: res.rows,
        total: res.total,
        page: res.page,
        page_size: res.page_size,
        loading: false,
      });
    } catch (err) {
      if (!isLatest()) return;
      set(providerKeysAtom, (prev) => ({ ...prev, loading: false }));
      throw err;
    }
  },
);

// ─── per-provider models state (detail page) ───────────────────────────────
export interface ProviderModelsState {
  providerId: string | null;
  items: ProviderModel[];
  total: number;
  page: number;
  page_size: number;
  loading: boolean;
}

const initialProviderModelsState: ProviderModelsState = {
  providerId: null,
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
  loading: false,
};

export const providerModelsAtom = atom<ProviderModelsState>(initialProviderModelsState);

// ─── model CRUD atoms (detail page models tab) ─────────────────────────────
export const upsertProviderModelAtom = atom(
  null,
  async (
    _get,
    _set,
    args: {
      providerId: string;
      modelId?: string;
      values: ModelUpsertPayload;
    },
  ): Promise<ProviderModel> => {
    if (args.modelId) return updateProviderModel(args.providerId, args.modelId, args.values);
    return createProviderModel(args.providerId, args.values);
  },
);

export const deleteProviderModelAtom = atom(
  null,
  async (_get, _set, args: { providerId: string; modelId: string }): Promise<void> => {
    await deleteProviderModel(args.providerId, args.modelId);
  },
);

const trackProviderModelsRequest = makeLatestTracker();

export const fetchProviderModelsAtom = atom(
  null,
  async (_get, set, args: { providerId: string; params?: ListProviderModelsParams }) => {
    const isLatest = trackProviderModelsRequest();
    set(providerModelsAtom, (prev) => ({ ...prev, loading: true, providerId: args.providerId }));
    try {
      const res = await listProviderModels(args.providerId, args.params);
      if (!isLatest()) return;
      set(providerModelsAtom, {
        providerId: args.providerId,
        items: res.rows,
        total: res.total,
        page: res.page,
        page_size: res.page_size,
        loading: false,
      });
    } catch (err) {
      if (!isLatest()) return;
      set(providerModelsAtom, (prev) => ({ ...prev, loading: false }));
      throw err;
    }
  },
);
