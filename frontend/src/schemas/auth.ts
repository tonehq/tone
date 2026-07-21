import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

export type LoginFormData = z.infer<typeof loginSchema>;

export const signupSchema = z.object({
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export type SignupFormData = z.infer<typeof signupSchema>;

// Invite rows are optional per-step (skip is allowed), but if the user has typed
// a non-empty email it must be a valid one. Blank rows are dropped by the
// wizard before submit rather than errored on.
const onboardingInviteEntrySchema = z.object({
  email: z.string().refine((v) => v.length === 0 || z.string().email().safeParse(v).success, {
    message: 'Please enter a valid email',
  }),
  role: z.string().min(1, 'Role is required'),
});

export const onboardingSchema = z.object({
  workspace_name: z
    .string()
    .min(1, 'Workspace name is required')
    .max(100, 'Workspace name must be 100 characters or fewer'),
  invites: z.array(onboardingInviteEntrySchema),
  use_case: z.string().min(1, 'Please pick a use case'),
  industry: z.string(),
});

export type OnboardingFormData = z.infer<typeof onboardingSchema>;

export const onboardOrgSchema = z.object({
  org_name: z
    .string()
    .min(1, 'Organisation name is required')
    .min(2, 'Organisation name must be at least 2 characters'),
});

export type OnboardOrgFormData = z.infer<typeof onboardOrgSchema>;

export const inviteMemberSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  role: z.string().min(1, 'Role is required'),
});

export type InviteMemberFormData = z.infer<typeof inviteMemberSchema>;

export const forgotPasswordSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
});

export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export const SIGNIN_CODE_LENGTH = 6;

export const requestSignInCodeSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
});

export type RequestSignInCodeFormData = z.infer<typeof requestSignInCodeSchema>;

export const verifySignInCodeSchema = z.object({
  code: z
    .string()
    .min(1, 'Code is required')
    .regex(
      new RegExp(`^\\d{${SIGNIN_CODE_LENGTH}}$`),
      `Enter the ${SIGNIN_CODE_LENGTH}-digit code`,
    ),
});

export type VerifySignInCodeFormData = z.infer<typeof verifySignInCodeSchema>;

export interface VerifySignInCodePayload extends VerifySignInCodeFormData {
  email: string;
}

export const acceptInviteSchema = z
  .object({
    first_name: z.string().min(1, 'First name is required'),
    last_name: z.string().min(1, 'Last name is required'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  });

export type AcceptInviteFormData = z.infer<typeof acceptInviteSchema>;
