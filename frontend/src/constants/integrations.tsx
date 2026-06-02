import { GoogleIcon } from '@/components/icons/google';
import { Phone, Sheet } from 'lucide-react';

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

export const OAUTH_PROVIDERS: ProviderCardConfig[] = [
  {
    key: 'google_calendar',
    name: 'Google Calendar',
    description: 'Create events, check availability, and manage schedules from voice calls.',
    icon: <GoogleIcon className="size-5" />,
    iconBg: 'bg-white dark:bg-white/10',
    iconBorder: 'border-border/50 shadow-sm dark:shadow-none',
    accentColor: 'bg-blue-500',
    category: 'google',
  },
  {
    key: 'google_sheets',
    name: 'Google Sheets',
    description: 'Read and write spreadsheet data during conversations.',
    icon: <Sheet size={20} className="text-emerald-600 dark:text-emerald-400" />,
    iconBg: 'bg-emerald-50 dark:bg-emerald-500/10',
    iconBorder: 'border-emerald-200/50 dark:border-emerald-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-emerald-500',
    category: 'google',
  },
];

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
];
