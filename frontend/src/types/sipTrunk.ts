export type SipTransport = 'udp' | 'tcp' | 'tls';
export type SipAuthMode = 'ip_acl' | 'digest';
export type SipMediaEncryption = 'none' | 'srtp';
export type SipTrunkStatus = 'draft' | 'provisioned' | 'error';

export interface SipGateway {
  host: string;
  port: number;
  transport: SipTransport;
  inbound_enabled: boolean;
  outbound_enabled: boolean;
  priority: number;
}

export interface SipTrunkAuth {
  auth_username: string;
  auth_password: string;
  register_server: string;
}

export interface SipTrunk {
  id: string;
  name: string;
  carrier: string;
  channel_id: string;
  gateways: SipGateway[];
  inbound_enabled: boolean;
  outbound_enabled: boolean;
  auth_mode: SipAuthMode;
  auth_username: string | null;
  register_enabled: boolean;
  tech_prefix: string | null;
  sip_diversion_header: boolean;
  outbound_leading_plus_enabled: boolean;
  number_e164_check_enabled: boolean;
  transfer_enabled: boolean;
  media_encryption: SipMediaEncryption;
  status: SipTrunkStatus;
  status_detail: string | null;
  carrier_config: Record<string, unknown>;
  termination_host: string;
  inbound_uri_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  auth?: SipTrunkAuth;
}

export interface SipTrunkPayload {
  name: string;
  carrier?: string;
  gateways: SipGateway[];
  inbound_enabled?: boolean;
  outbound_enabled?: boolean;
  auth_mode?: SipAuthMode;
  auth?: Partial<SipTrunkAuth>;
  register_enabled?: boolean;
  tech_prefix?: string | null;
  sip_diversion_header?: boolean;
  outbound_leading_plus_enabled?: boolean;
  number_e164_check_enabled?: boolean;
  transfer_enabled?: boolean;
  media_encryption?: SipMediaEncryption;
  is_active?: boolean;
}

export interface SipTrunkPhoneNumber {
  id: string;
  number: string;
  label: string | null;
  channel_id: string;
  assigned_to: {
    agent_id: string;
    agent_name: string;
  } | null;
}

export interface SipCarrierPhoneNumber {
  id: string;
  number: string;
  label: string | null;
}
