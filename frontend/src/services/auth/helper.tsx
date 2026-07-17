import { FIREBASE_SIGNUP, LOGIN_DATA, SIGNUP, TENANT_ID } from '@/constants';

import axios from '@/utils/axios';
import { handleApiError } from '@/utils/helpers';

// Persists only the non-sensitive session payload. The access/refresh tokens
// are set as httpOnly cookies by the server response and are never handled here.
export const setToken = async (LogInData: any) => {
  if (typeof window === 'undefined') return LogInData;

  if (LogInData?.user_id != null) {
    localStorage.setItem('user_id', String(LogInData.user_id));
  }
  localStorage.setItem(LOGIN_DATA, JSON.stringify(LogInData));

  const orgs = LogInData?.organizations;
  if (Array.isArray(orgs) && orgs.length > 0 && orgs[0]?.id) {
    localStorage.setItem(TENANT_ID, String(orgs[0].id));
  }

  return LogInData;
};

export const login = async (email: string, password: string) => {
  const { data: LogInData } = await axios.post('/auth/login', {
    email,
    password,
  });
  setToken(LogInData);
  return LogInData;
};

export const createteam = async (data: string) => {
  const res = await axios.post(`/org/create_tenants?name=${data}`);
  return res;
};

export const forgotPassword = async (email: string) => {
  const { data } = await axios.get('/auth/forget-password', {
    params: { email },
  });
  return data;
};

export const signup = async (
  email: string,
  password: string,
  profile: any = {},
  firebase_token: string | null = null,
  org_name: string | null = null,
) => {
  if (firebase_token !== null) {
    return await axios
      .post(
        FIREBASE_SIGNUP,
        { email, profile },
        { headers: { Authorization: `Bearer ${firebase_token}` } },
      )
      .then((res) => {
        setToken(res.data);
      })
      .catch((err) => {
        handleApiError(err);
      });
  }
  return await axios.post(SIGNUP, {
    email,
    password,
    profile,
    org_name,
  });
};

export const getOrganization = async () => {
  const res = await axios.get('/org/get_associated_tenants');
  return res;
};

export const createOrganization = async (data: any) => {
  const res = await axios.post(`/org/create_tenants?name=${data.name}`);
  return res;
};
