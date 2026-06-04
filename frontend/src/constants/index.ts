export const ACCESS_TOKEN = 'access_token';
export const TENANT_ID = 'active_org_id';
export const USER_PROFILE = 'profile';
export const LOGIN_DATA = 'login_data';

export const LOGIN = '/auth/login';
export const SIGNUP = '/auth/signup';
export const FORGOT_PASSWORD = '/auth/forget-password';
export const FIREBASE_SIGNUP = '/auth/signup_with_firebase';

export const ROUTE_LOGIN = '/login';
export const ROUTE_HOME = '/home';

export const BACKEND_URL = `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/v1`;

// Grafana Loki logs link (Call History → per-call logs). Environment-specific: the base
// host and the Loki "app" label differ between staging and production.
export const GRAFANA_BASE_URL = process.env.NEXT_PUBLIC_GRAFANA_BASE_URL;
export const GRAFANA_LOG_APP = process.env.NEXT_PUBLIC_GRAFANA_LOG_APP;
