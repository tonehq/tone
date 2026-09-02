import { CalendarDays, Settings, Shield } from 'lucide-react';

/* ================================================================ */
/*  TYPES                                                            */
/* ================================================================ */

export interface MetaField {
  key: string;
  label: string;
  placeholder: string;
  helperText?: string;
  type?: string;
}

export interface MetaSectionConfig {
  title: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  fields: MetaField[];
}

export interface ToolTypeHeaderConfig {
  icon: React.ElementType;
  color: string;
  bg: string;
  label: string;
}

/* ================================================================ */
/*  TOOL TYPE META SECTIONS                                          */
/* ================================================================ */

export const TOOL_TYPE_META_SECTIONS: Record<string, MetaSectionConfig> = {
  google_calendar: {
    title: 'Calendar Settings',
    description: 'Configure the Google Calendar for event creation',
    icon: CalendarDays,
    iconColor: 'text-teal-600 dark:text-teal-400',
    iconBg: 'bg-teal-50 dark:bg-teal-500/10',
    fields: [
      {
        key: 'calendar_id',
        label: 'Calendar ID',
        placeholder: 'Enter Calendar ID',
        helperText: 'The ID of the Google Calendar. Defaults to "primary" if not specified.',
      },
      {
        key: 'timezone',
        label: 'Timezone',
        placeholder: 'America/New_York',
        helperText:
          'The time zone for the calendar event (e.g., America/New_York). Defaults to UTC if not specified.',
      },
    ],
  },
  send_sms: {
    title: 'SMS Settings',
    description: 'Configure the SMS sending number',
    icon: Shield,
    iconColor: 'text-amber-600 dark:text-amber-400',
    iconBg: 'bg-amber-50 dark:bg-amber-500/10',
    fields: [{ key: 'from_number', label: 'From Number', placeholder: '+1234567890' }],
  },
};

/* ================================================================ */
/*  TOOL TYPE HEADER CONFIG                                          */
/* ================================================================ */

export const TOOL_TYPE_HEADER: Record<string, ToolTypeHeaderConfig> = {
  google_calendar: {
    icon: CalendarDays,
    color: 'text-teal-700 dark:text-teal-400',
    bg: 'bg-teal-100 dark:bg-teal-500/15',
    label: 'Google Calendar',
  },
  send_sms: {
    icon: Shield,
    color: 'text-amber-700 dark:text-amber-400',
    bg: 'bg-amber-100 dark:bg-amber-500/15',
    label: 'SMS',
  },
  google_sheets: {
    icon: Settings,
    color: 'text-emerald-700 dark:text-emerald-400',
    bg: 'bg-emerald-100 dark:bg-emerald-500/15',
    label: 'Google Sheets',
  },
};

/* ================================================================ */
/*  HTTP METHOD / AUTH OPTIONS                                       */
/* ================================================================ */

export const METHOD_OPTIONS = [
  { value: 'GET', label: 'GET' },
  { value: 'POST', label: 'POST' },
  { value: 'PUT', label: 'PUT' },
  { value: 'DELETE', label: 'DELETE' },
  { value: 'PATCH', label: 'PATCH' },
];

export const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400',
  POST: 'bg-sky-50 text-sky-700 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-400',
  PUT: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400',
  DELETE: 'bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-500/10 dark:text-red-400',
  PATCH: 'bg-teal-50 text-teal-700 ring-teal-600/20 dark:bg-teal-500/10 dark:text-teal-400',
};

export interface AuthField {
  key: string;
  label: string;
  placeholder: string;
  type?: string;
}

export interface AuthSectionConfig {
  title: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  iconBg: string;
  fields: AuthField[];
}

export const TOOL_TYPE_AUTH_SECTIONS: Record<string, AuthSectionConfig> = {
  send_sms: {
    title: 'SMS Credentials',
    description: 'Provide your Twilio credentials to enable this tool',
    icon: Shield,
    iconColor: 'text-amber-600 dark:text-amber-400',
    iconBg: 'bg-amber-50 dark:bg-amber-500/10',
    fields: [
      {
        key: 'account_sid',
        label: 'Account SID',
        placeholder: 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
      },
      {
        key: 'auth_token',
        label: 'Auth Token',
        placeholder: 'Enter auth token',
        type: 'password',
      },
    ],
  },
};

export const TOOL_TYPE_OAUTH_PROVIDER: Record<string, string> = {
  google_calendar: 'google_calendar',
  google_sheets: 'google_sheets',
};

export const AUTH_TYPE_OPTIONS = [
  { value: 'none', label: 'No Authentication' },
  { value: 'api_key', label: 'API Key' },
  { value: 'bearer', label: 'Bearer Token' },
  { value: 'basic', label: 'Basic Auth' },
  { value: 'oauth', label: 'OAuth Connection' },
];
