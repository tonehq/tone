import { atom } from 'jotai';

import { authApi, type UpdateProfilePayload } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';

export const updateProfileAtom = atom(null, async (_get, _set, payload: UpdateProfilePayload) => {
  const updated = await authApi.updateMe(payload);
  useAuthStore.getState().setUser(updated);
  return updated;
});
