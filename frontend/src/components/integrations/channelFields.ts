/** Provider field maps for the channel form modal. Co-located constants so the
 * modal stays JSX/logic-only and the per-provider shapes are reusable. */

export interface ChannelField {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
  optional?: boolean;
  helperText?: string;
}

export const CHANNEL_FIELDS: Record<string, ChannelField[]> = {
  twilio: [
    { name: 'account_sid', label: 'Account SID', placeholder: 'Enter account SID' },
    { name: 'auth_token', label: 'Auth Token', type: 'password', placeholder: 'Enter auth token' },
  ],
  telnyx: [
    { name: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter API key' },
    {
      name: 'account_sid',
      label: 'Account SID',
      placeholder: 'Enter account SID',
      optional: true,
      helperText: 'Required to place outbound calls.',
    },
    {
      name: 'application_sid',
      label: 'TeXML Application SID',
      placeholder: 'Enter TeXML application SID',
      optional: true,
      helperText: 'Required to place outbound calls.',
    },
  ],
  plivo: [
    { name: 'auth_id', label: 'Auth ID', placeholder: 'Enter auth ID' },
    { name: 'auth_token', label: 'Auth Token', type: 'password', placeholder: 'Enter auth token' },
  ],
  livekit: [
    { name: 'url', label: 'Server URL', placeholder: 'wss://your-project.livekit.cloud' },
    { name: 'api_key', label: 'API Key', placeholder: 'Enter API key' },
    { name: 'api_secret', label: 'API Secret', type: 'password', placeholder: 'Enter API secret' },
    {
      name: 'sip_uri',
      label: 'SIP URI',
      placeholder: 'sip:xxxxxxxx.sip.livekit.cloud',
      optional: true,
      helperText: 'From LiveKit → Telephony → SIP trunks. Required for SIP trunking.',
    },
  ],
  daily: [{ name: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter API key' }],
};

export const CHANNEL_TYPE_OPTIONS = [
  { label: 'Twilio', value: 'twilio' },
  { label: 'Telnyx', value: 'telnyx' },
  { label: 'Plivo', value: 'plivo' },
  { label: 'LiveKit', value: 'livekit' },
  { label: 'Daily', value: 'daily' },
];

export const ALL_FIELD_NAMES = [
  'name',
  'account_sid',
  'application_sid',
  'auth_token',
  'auth_id',
  'url',
  'api_key',
  'api_secret',
  'sip_uri',
];
