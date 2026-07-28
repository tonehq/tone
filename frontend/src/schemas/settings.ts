import { z } from 'zod';

import { PERSONAL_EMAIL_ERROR, isBusinessEmail } from '@/lib/emailDomain';

export const inviteMemberSchema = z.object({
  name: z.string().min(1, 'Please enter a name'),
  email: z
    .string()
    .min(1, 'Please enter an email address')
    .email('Please enter a valid email address')
    .refine(isBusinessEmail, PERSONAL_EMAIL_ERROR),
});

export type InviteMemberFormData = z.infer<typeof inviteMemberSchema>;

export const addChannelSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  auth_token: z.string().min(1, 'Auth token is required'),
  account_sid: z.string().min(1, 'Account SID is required'),
});

export type AddChannelFormData = z.infer<typeof addChannelSchema>;
