import { atom } from 'jotai';

import {
  listTtsLanguages,
  listTtsProviders,
  listTtsVoices,
  type TtsLanguage,
  type TtsProvider,
  type TtsVoice,
} from '@/services/ttsService';

function makeLatestTracker() {
  let latest = 0;
  return () => {
    latest += 1;
    const id = latest;
    return () => id === latest;
  };
}

export interface TtsLanguagesState {
  items: TtsLanguage[];
  loading: boolean;
}
export interface TtsProvidersState {
  language: string | null;
  items: TtsProvider[];
  loading: boolean;
}
export interface TtsVoicesState {
  providerId: string | null;
  language: string | null;
  items: TtsVoice[];
  loading: boolean;
}

export const ttsLanguagesAtom = atom<TtsLanguagesState>({ items: [], loading: false });
export const ttsProvidersAtom = atom<TtsProvidersState>({
  language: null,
  items: [],
  loading: false,
});
export const ttsVoicesAtom = atom<TtsVoicesState>({
  providerId: null,
  language: null,
  items: [],
  loading: false,
});

const trackLanguages = makeLatestTracker();
const trackProviders = makeLatestTracker();
const trackVoices = makeLatestTracker();

export const fetchTtsLanguagesAtom = atom(null, async (_get, set) => {
  const isLatest = trackLanguages();
  set(ttsLanguagesAtom, (prev) => ({ ...prev, loading: true }));
  try {
    const items = await listTtsLanguages();
    if (!isLatest()) return;
    set(ttsLanguagesAtom, { items, loading: false });
  } catch (err) {
    if (!isLatest()) return;
    set(ttsLanguagesAtom, (prev) => ({ ...prev, loading: false }));
    throw err;
  }
});

export const fetchTtsProvidersAtom = atom(null, async (_get, set, language: string) => {
  const isLatest = trackProviders();
  set(ttsProvidersAtom, (prev) => ({ ...prev, language, loading: true }));
  try {
    const items = await listTtsProviders(language);
    if (!isLatest()) return;
    set(ttsProvidersAtom, { language, items, loading: false });
  } catch (err) {
    if (!isLatest()) return;
    set(ttsProvidersAtom, (prev) => ({ ...prev, loading: false }));
    throw err;
  }
});

export const fetchTtsVoicesAtom = atom(
  null,
  async (_get, set, args: { providerId: string; language: string }) => {
    const { providerId, language } = args;
    const isLatest = trackVoices();
    set(ttsVoicesAtom, (prev) => ({ ...prev, providerId, language, loading: true }));
    try {
      const items = await listTtsVoices(providerId, language);
      if (!isLatest()) return;
      set(ttsVoicesAtom, { providerId, language, items, loading: false });
    } catch (err) {
      if (!isLatest()) return;
      set(ttsVoicesAtom, (prev) => ({ ...prev, loading: false }));
      throw err;
    }
  },
);
