export interface User {
  id: string | number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  role?: string | null;
  is_active?: boolean;
  is_verified?: boolean;
  organization_id?: string | null;
  auth_provider?: string | null;
  last_login_at?: number | null;
}

export interface Organization {
  id: string;
  name: string;
  slug?: string | null;
  description?: string | null;
  logo_url?: string | null;
  subscription_plan?: string | null;
  subscription_status?: string | null;
  status?: string | null;
}

export interface UserOrganization {
  id: string;
  name: string;
  role?: string | null;
  is_active?: boolean;
}

export interface AuthLoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
  expires_in?: number;
  user?: User;
  organization?: Organization | null;
  email_verification_token?: string;
  // Legacy fields (kept so older backends without refresh_token still work)
  user_id?: string | number;
  email?: string;
  organizations?: UserOrganization[];
  profile?: Record<string, unknown> | null;
  [key: string]: unknown;
}

export interface InvitationValidation {
  valid: boolean;
  email: string;
  role: string;
  organization_id: string;
  organization_name: string;
  account_exists: boolean;
}
