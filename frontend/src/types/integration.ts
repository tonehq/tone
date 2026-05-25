export interface Channel {
  id: string;
  name: string;
  channel_type: string;
  created_at: string;
  updated_at: string;
  config?: Record<string, unknown>;
}

export interface ChannelUpsertPayload {
  id?: string;
  name: string;
  channel_type: string;
  config: Record<string, string>;
}
