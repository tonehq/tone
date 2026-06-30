import { Phone, Radio, Video } from 'lucide-react';

export type ProviderCategory = 'google' | 'productivity' | 'dev_crm';

/** Human label for a catalog category. */
export const PROVIDER_CATEGORY_LABELS: Record<string, string> = {
  google: 'Google',
  productivity: 'Productivity',
  dev_crm: 'Dev & CRM',
};

export interface ProviderCardConfig {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconBorder: string;
  accentColor: string;
  category?: ProviderCategory;
}

/**
 * OAuth integrations are now driven entirely by the ``app_integrations`` DB
 * catalog (see ``dev/seed_app_integrations.py``). This list intentionally
 * stays empty — kept exported only to preserve the ``ProviderCardConfig[]``
 * shape that older consumers import. New visual configs for OAuth providers
 * belong in the DB (``icon_url``), not here.
 */
export const OAUTH_PROVIDERS: ProviderCardConfig[] = [];

export const API_KEY_PROVIDERS: ProviderCardConfig[] = [
  {
    key: 'twilio',
    name: 'Twilio',
    description: 'Cloud communications platform for voice, SMS, and phone numbers.',
    icon: <Phone size={18} className="text-red-500" />,
    iconBg: 'bg-red-50 dark:bg-red-500/10',
    iconBorder: 'border-red-200/50 dark:border-red-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-red-500',
  },
  {
    key: 'plivo',
    name: 'Plivo',
    description: 'Cloud communications platform for voice calls and phone numbers.',
    icon: <Phone size={18} className="text-emerald-500" />,
    iconBg: 'bg-emerald-50 dark:bg-emerald-500/10',
    iconBorder: 'border-emerald-200/50 dark:border-emerald-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-emerald-500',
  },
  {
    key: 'livekit',
    name: 'LiveKit',
    description: 'Real-time WebRTC platform for in-browser voice calls.',
    icon: <Radio size={18} className="text-blue-500" />,
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconBorder: 'border-blue-200/50 dark:border-blue-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-blue-500',
  },
  {
    key: 'daily',
    name: 'Daily',
    description: 'WebRTC API for in-browser voice and video calls.',
    icon: <Video size={18} className="text-violet-500" />,
    iconBg: 'bg-violet-50 dark:bg-violet-500/10',
    iconBorder: 'border-violet-200/50 dark:border-violet-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-violet-500',
  },
];
