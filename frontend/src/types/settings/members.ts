export interface OrganizationMemberApi {
  id: number;
  user_id?: number;
  name?: string;
  email?: string;
  role?: string;
  joined_date?: string;
  avatar?: string | null;
  [key: string]: unknown;
}

export interface OrganizationInviteApi {
  id: number;
  name?: string;
  email?: string;
  role?: string;
  invited_date?: string;
  status?: string;
  [key: string]: unknown;
}
