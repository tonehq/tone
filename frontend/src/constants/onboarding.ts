import type { SelectOption } from '@/components/shared';

export interface UseCaseOption {
  value: string;
  label: string;
  description: string;
}

export const USE_CASE_OPTIONS: UseCaseOption[] = [
  {
    value: 'customer_support',
    label: 'Customer Support',
    description: 'Handle inbound support calls and FAQs.',
  },
  {
    value: 'sales',
    label: 'Sales',
    description: 'Qualify leads and pitch products over the phone.',
  },
  {
    value: 'lead_qualification',
    label: 'Lead Qualification',
    description: 'Score and route inbound leads to the right team.',
  },
  {
    value: 'appointment_booking',
    label: 'Appointment Booking',
    description: 'Schedule appointments and confirm reminders.',
  },
  {
    value: 'feedback_collection',
    label: 'Feedback Collection',
    description: 'Run post-call surveys and collect NPS.',
  },
  {
    value: 'other',
    label: 'Something Else',
    description: 'I have a different use case in mind.',
  },
];

export const INDUSTRY_OPTIONS: SelectOption[] = [
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'logistics', label: 'Logistics' },
  { value: 'home_services', label: 'Home Services' },
  { value: 'debt_collection', label: 'Debt Collection' },
  { value: 'retail_consumer_goods', label: 'Retail & Consumer Goods' },
  { value: 'travel_hospitality', label: 'Travel & Hospitality' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'car_dealerships', label: 'Car Dealerships' },
  { value: 'other', label: 'Other' },
];

export interface OnboardingInviteRole {
  value: string;
  label: string;
}

export const ONBOARDING_INVITE_ROLES: OnboardingInviteRole[] = [
  { value: 'admin', label: 'Admin' },
  { value: 'developer', label: 'Developer' },
  { value: 'observer', label: 'Observer' },
];
