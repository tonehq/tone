export interface OrganizationMemberApi {
  member_id: number;
  user_id: number;
  email: string;
  username: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  status: string;
  joined_at: number | null;
  last_activity_at: number | null;
  [key: string]: unknown;
}

export interface OrganizationInviteApi {
  member_id: number;
  email: string;
  username: string;
  name: string;
  role: string;
  status: string;
  [key: string]: unknown;
}
