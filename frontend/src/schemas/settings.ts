import { z } from 'zod';

export const inviteMemberSchema = z.object({
  name: z.string().min(1, 'Please enter a name'),
  email: z
    .string()
    .min(1, 'Please enter an email address')
    .email('Please enter a valid email address'),
});

export type InviteMemberFormData = z.infer<typeof inviteMemberSchema>;

export const addChannelSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  auth_token: z.string().min(1, 'Auth token is required'),
  account_sid: z.string().min(1, 'Account SID is required'),
});

export type AddChannelFormData = z.infer<typeof addChannelSchema>;

export const publicKeySchema = z.object({
  keyName: z.string().min(1, 'Key name is required'),
});

export type PublicKeyFormData = z.infer<typeof publicKeySchema>;
