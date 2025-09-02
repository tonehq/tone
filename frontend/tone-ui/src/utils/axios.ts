import Axios from "axios";
import Cookies from "js-cookie";

const axiosInstance = Axios.create({
  baseURL: "http://localhost:8000",
});

axiosInstance.interceptors.request.use(function (config) {
  
  const tenant_id = Cookies.get("1");
  const accessToken = Cookies.get("clickshow_access_token");

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
  }
);

export default axiosInstance;
