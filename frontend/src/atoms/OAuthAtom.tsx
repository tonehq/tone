import {
  disconnectOAuth as disconnectOAuthApi,
  listOAuthConnections,
} from '@/services/oauthService';
import type { OAuthConnection } from '@/types/oauth';
import { atom } from 'jotai';

interface OAuthState {
  items: OAuthConnection[];
  status: 'idle' | 'loading' | 'error';
  error: string | null;
  initialized: boolean;
}

const initialState: OAuthState = {
  items: [],
  status: 'idle',
  error: null,
  initialized: false,
};

const oauthStateAtom = atom<OAuthState>(initialState);

const oauthAtom = atom((get) => get(oauthStateAtom));

const fetchOAuthAtom = atom(null, async (get, set): Promise<void> => {
  const current = get(oauthStateAtom);
  if (current.status === 'loading') return;
  set(oauthStateAtom, { ...current, status: 'loading', error: null });
  try {
    const items = await listOAuthConnections();
    set(oauthStateAtom, {
      items,
      status: 'idle',
      error: null,
      initialized: true,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Failed to load connections';
    set(oauthStateAtom, { ...current, status: 'error', error: message });
    throw err;
  }
});

const disconnectOAuthAtom = atom(null, async (_get, set, connectionId: string) => {
  await disconnectOAuthApi(connectionId);
  await set(fetchOAuthAtom);
});

const resetOAuthAtom = atom(null, (_get, set) => {
  set(oauthStateAtom, initialState);
});

export { disconnectOAuthAtom, fetchOAuthAtom, oauthAtom, oauthStateAtom, resetOAuthAtom };
export type { OAuthState };
