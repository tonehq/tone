import Axios from 'axios';
import Cookies from 'js-cookie';

import { BACKEND_URL } from '@/urls';

const axiosInstance = Axios.create({
  baseURL: BACKEND_URL,
});

axiosInstance.interceptors.request.use(function (config) {
  const tenant_id = Cookies.get('org_tenant_id');
  const accessToken = Cookies.get('tone_access_token');

  if (tenant_id) {
    config.headers['tenant_id'] = Number(tenant_id);
  }
  if (accessToken) {
    config.headers['Authorization'] = `Bearer ${accessToken}`;
  }

  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
    }
    return Promise.reject(error);
  },
);

export default axiosInstance;
