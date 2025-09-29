// API response types for settings members/invitations

export interface OrganizationMemberApi {
  member_id: number;
  user_id: number;
  email: string;
  username: string;
  first_name: string | null;
  last_name: string | null;
  role: 'owner' | 'admin' | 'member' | 'viewer' | string;
  status: 'active' | 'inactive' | string;
  joined_at: number; // epoch seconds
  last_activity_at: number | null; // epoch seconds or null
}

export interface OrganizationInviteApi {
  member_id: number;
  email: string;
  username: string;
  name: string;
  role: 'owner' | 'admin' | 'member' | 'viewer' | string;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled' | string;
}

// UI row types for table rendering
export interface MemberRow {
  key: string;
  name: string; // display name or email
  email: string;
  joinedDate: string;
  role: string;
  avatar: string | null;
}

export interface InvitationRow {
  member_id: string;
  name?: string;
  username?: string;
  email: string;
  invitedDate: string;
  status: string;
  role: string;
}
