import { deleteDocuments, getDocuments } from '@/services/knowledgeBaseService';
import type { GetDocumentsParams } from '@/services/knowledgeBaseService';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';
import { atom } from 'jotai';

interface KnowledgeBasePagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

interface KnowledgeBaseState {
  documents: KnowledgeBaseDocument[];
  pagination: KnowledgeBasePagination;
}

const defaultPagination: KnowledgeBasePagination = {
  page: 1,
  page_size: 10,
  total: 0,
  total_pages: 1,
};

const knowledgeBaseAtom = atom<KnowledgeBaseState>({
  documents: [],
  pagination: defaultPagination,
});

function parseResponse(res: unknown): KnowledgeBaseState {
  if (res && typeof res === 'object' && !Array.isArray(res)) {
    const obj = res as Record<string, unknown>;
    const docs = Array.isArray(obj.data) ? (obj.data as KnowledgeBaseDocument[]) : [];
    const pag = obj.pagination as KnowledgeBasePagination | undefined;
    return {
      documents: docs,
      pagination: pag ?? { ...defaultPagination, total: docs.length },
    };
  }
  if (Array.isArray(res)) {
    return {
      documents: res as KnowledgeBaseDocument[],
      pagination: { ...defaultPagination, total: res.length },
    };
  }
  return { documents: [], pagination: defaultPagination };
}

export const fetchDocumentsAtom = atom(null, async (_get, set, params?: GetDocumentsParams) => {
  const res = await getDocuments(params);
  set(knowledgeBaseAtom, parseResponse(res));
});

export const deleteDocumentsAtom = atom(null, async (_get, set, documentIds: number[]) => {
  await deleteDocuments(documentIds);
  const res = await getDocuments();
  set(knowledgeBaseAtom, parseResponse(res));
});

export default knowledgeBaseAtom;
