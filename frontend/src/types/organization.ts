export interface OrganizationListItem {
  id: string;
  name: string;
  slug: string;
  role: string;
  joined_at: number;
}

export interface OrganizationDetails {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  website_url: string | null;
  status: string;
  subscription_plan: string;
  member_count: number;
  created_at: number;
  updated_at: number;
}

export interface OrganizationUpdatePayload {
  name?: string;
  description?: string;
  logo_url?: string;
  website_url?: string;
}

export interface OrganizationUpdateResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  website_url: string | null;
  message: string;
}

export interface OrganizationCreateResponse {
  id: string;
  name: string;
  slug: string;
  role: string;
}
