import { atom } from 'jotai';

import {
  listKnowledgeBase,
  type KnowledgeBaseUpload,
  type ListKnowledgeBaseParams,
} from '@/services/knowledgeBaseService';

function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

export interface KnowledgeBaseListState {
  items: KnowledgeBaseUpload[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
}

export const knowledgeBaseListAtom = atom<KnowledgeBaseListState>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
});

const trackKb = makeLatestTracker();

export const fetchKnowledgeBaseAtom = atom(
  null,
  async (_get, set, params: ListKnowledgeBaseParams = {}) => {
    const isLatest = trackKb();
    set(knowledgeBaseListAtom, (prev) => ({ ...prev, loading: true }));
    try {
      const data = await listKnowledgeBase(params);
      if (!isLatest()) return;
      set(knowledgeBaseListAtom, {
        items: data.items,
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
        loading: false,
      });
    } catch (err) {
      if (!isLatest()) return;
      set(knowledgeBaseListAtom, (prev) => ({ ...prev, loading: false }));
      throw err;
    }
  },
);
