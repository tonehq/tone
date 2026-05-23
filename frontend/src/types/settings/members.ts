export interface OrganizationMemberApi {
  member_id: string;
  user_id: string;
  email: string;
  username: string;
  first_name: string | null;
  last_name: string | null;
  role: string;
  status: string;
  joined_at: string | null;
  last_activity_at: string | null;
  [key: string]: unknown;
}

export interface OrganizationInviteApi {
  member_id: string;
  email: string;
  username: string;
  name: string;
  role: string;
  status: string;
  [key: string]: unknown;
}
