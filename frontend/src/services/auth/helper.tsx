import Cookies from 'js-cookie';

import { ACCESS_TOKEN, FIREBASE_SIGNUP, SIGNUP, TENANT_ID } from '@/constants';

import axios from '@/utils/axios';
import { decodeJWT } from '@/utils/jwt';

export const login = async (email: string, password: string) => {
  const { data: LogInData } = await axios.post('/auth/login', {
    email,
    password,
  });
  setToken(LogInData);

  return LogInData;
};

export const setToken = async (LogInData: any) => {
  const decoded = decodeJWT(LogInData['access_token']);
  Cookies.set(ACCESS_TOKEN, LogInData['access_token'], {
    expires: new Date(decoded.exp * 1000),
  });

  Cookies.set('user_id', LogInData?.['user_id'], {
    expires: new Date(decoded.exp * 1000),
  });

  Cookies.set('login_data', JSON.stringify(LogInData), {
    expires: new Date(decoded.exp * 1000),
  });

  Cookies.set(
    TENANT_ID,
    LogInData['organizations']?.length ? LogInData['organizations']?.[0]?.['id'] : '',
    {
      expires: new Date(decoded.exp * 1000),
    },
  );

  return LogInData;
};

export const createteam = async (data: string) => {
  const res = await axios.post(`/org/create_tenants?name=${data}`);
  return res;
};

export const forgotPassword = async (email: string) => {
  const { data } = await axios.get('/auth/forget-password', {
    params: {
      email,
    },
  });
  return data;
};

export const signup = async (
  email: string,
  username: string,
  password: string,
  profile: any = {},
  firebase_token: string | null = null,
  org_name: string | null = null,
) => {
  if (firebase_token !== null) {
    return await axios
      .post(
        FIREBASE_SIGNUP,
        {
          email,
          profile,
        },
        {
          headers: {
            Authorization: `Bearer ${firebase_token}`,
          },
        },
      )
      .then((res) => {
        setToken(res.data);
      })
      .catch((err) => {
        alert('something went wrong');
      });
  } else {
    return await axios.post(SIGNUP, {
      email,
      password,
      username,
      profile,
      org_name,
    });
  }
};

export const getOrganization = async () => {
  const res = await axios.get('/org/get_associated_tenants');
  return res;
};

export const createOrganization = async (data: any) => {
  const res = await axios.post(`/org/create_tenants?name=${data.name}`);
  return res;
};
