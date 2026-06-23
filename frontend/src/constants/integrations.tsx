import { GoogleIcon } from '@/components/icons/google';
import { Phone, Radio, Sheet, Video } from 'lucide-react';

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
