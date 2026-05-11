import { GoogleIcon } from '@/components/icons/google';
import { Phone, Sheet } from 'lucide-react';

export interface ProviderCardConfig {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconBorder: string;
  accentColor: string;
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
  },
  {
    key: 'google_sheets',
    name: 'Google Sheets',
    description: 'Read and write spreadsheet data during conversations.',
    icon: <Sheet size={20} className="text-emerald-600 dark:text-emerald-400" />,
    iconBg: 'bg-emerald-50 dark:bg-emerald-500/10',
    iconBorder: 'border-emerald-200/50 dark:border-emerald-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-emerald-500',
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
    key: 'telnyx',
    name: 'Telnyx',
    description: 'Global carrier for programmable voice and messaging APIs.',
    icon: <Phone size={18} className="text-teal-600 dark:text-teal-400" />,
    iconBg: 'bg-teal-50 dark:bg-teal-500/10',
    iconBorder: 'border-teal-200/50 dark:border-teal-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-teal-500',
  },
  {
    key: 'exotel',
    name: 'Exotel',
    description: 'Cloud telephony for customer engagement across India and Southeast Asia.',
    icon: <Phone size={18} className="text-blue-600 dark:text-blue-400" />,
    iconBg: 'bg-blue-50 dark:bg-blue-500/10',
    iconBorder: 'border-blue-200/50 dark:border-blue-500/20 shadow-sm dark:shadow-none',
    accentColor: 'bg-blue-500',
  },
];
