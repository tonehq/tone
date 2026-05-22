import { useMutation, useQuery } from '@tanstack/react-query';

import axios from '@/utils/axios';
import type { AuthLoginResponse, InvitationValidation, Organization, User } from '@/types/auth';
import type { AcceptInviteFormData, LoginFormData, SignupFormData } from '@/schemas/auth';

export interface AcceptInvitationPayload {
  token: string;
  password?: string;
  first_name?: string;
  last_name?: string;
}

export const authApi = {
  login: async (payload: LoginFormData): Promise<AuthLoginResponse> => {
    const { data } = await axios.post<AuthLoginResponse>('/auth/login', payload);
    return data;
  },
  signup: async (payload: SignupFormData): Promise<AuthLoginResponse> => {
    const { data } = await axios.post<AuthLoginResponse>('/auth/signup', {
      email: payload.email,
      password: payload.password,
      first_name: payload.first_name,
      last_name: payload.last_name,
      organization_name: payload.organization_name?.trim() || undefined,
    });
    return data;
  },
  refresh: async (refresh_token: string): Promise<AuthLoginResponse> => {
    const { data } = await axios.post<AuthLoginResponse>('/auth/refresh', { refresh_token });
    return data;
  },
  logout: async (payload: { access_token?: string; refresh_token?: string } = {}) => {
    const { data } = await axios.post('/auth/logout', payload);
    return data;
  },
  me: async (): Promise<User> => {
    const { data } = await axios.get<User>('/users/me');
    return data;
  },
  myOrg: async (): Promise<Organization | null> => {
    const { data } = await axios.get<Organization | null>('/org/me');
    return data;
  },
  forgotPassword: async (email: string) => {
    const { data } = await axios.post('/auth/forgot-password', { email });
    return data;
  },
  resetPassword: async (params: { token: string; new_password: string }) => {
    const { data } = await axios.post('/auth/reset-password', params);
    return data;
  },
  verifyEmail: async (token: string) => {
    const { data } = await axios.post('/auth/verify-email', { token });
    return data;
  },
  resendVerification: async (email: string) => {
    const { data } = await axios.post('/auth/resend-verification', { email });
    return data;
  },
  changePassword: async (new_password: string) => {
    const { data } = await axios.post('/auth/change-password', { new_password });
    return data;
  },
  validateInvitation: async (token: string): Promise<InvitationValidation> => {
    const { data } = await axios.get<InvitationValidation>('/auth/validate-invitation', {
      params: { token },
    });
    return data;
  },
  acceptInvitation: async (payload: AcceptInvitationPayload): Promise<AuthLoginResponse> => {
    const body: Record<string, unknown> = { token: payload.token };
    if (payload.password) body.password = payload.password;
    if (payload.first_name) body.first_name = payload.first_name;
    if (payload.last_name) body.last_name = payload.last_name;
    const { data } = await axios.post<AuthLoginResponse>('/auth/accept-invitation', body);
    return data;
  },
};

export function useLogin() {
  return useMutation({ mutationFn: authApi.login });
}

export function useSignup() {
  return useMutation({ mutationFn: authApi.signup });
}

export function useForgotPassword() {
  return useMutation({ mutationFn: authApi.forgotPassword });
}

export function useResetPassword() {
  return useMutation({ mutationFn: authApi.resetPassword });
}

export function useVerifyEmail() {
  return useMutation({ mutationFn: authApi.verifyEmail });
}

export function useResendVerification() {
  return useMutation({ mutationFn: authApi.resendVerification });
}

export function useChangePassword() {
  return useMutation({ mutationFn: authApi.changePassword });
}

export function useValidateInvitation(token: string) {
  return useQuery({
    queryKey: ['invitation', token],
    queryFn: () => authApi.validateInvitation(token),
    enabled: !!token,
    retry: false,
  });
}

export function useAcceptInvitation() {
  return useMutation({ mutationFn: authApi.acceptInvitation });
}

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    enabled,
    retry: false,
  });
}

export function useMyOrganization(enabled = true) {
  return useQuery({
    queryKey: ['my-org'],
    queryFn: authApi.myOrg,
    enabled,
    retry: false,
  });
}

export { type AcceptInviteFormData };
