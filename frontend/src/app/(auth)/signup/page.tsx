'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { MailCheck } from 'lucide-react';

import { signupSchema, type SignupFormData } from '@/schemas/auth';
import { showToast, handleApiError } from '@/lib/toast';
import { Form, TextInput } from '@/components/shared';
import { Button } from '@/components/ui/button';
import { useSignup } from '@/lib/api/auth';

export default function SignupPage() {
  const signup = useSignup();

  const { control, handleSubmit, watch } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      first_name: '',
      last_name: '',
      email: '',
      password: '',
    },
  });

  const email = watch('email');

  const onSubmit = async (values: SignupFormData) => {
    try {
      await signup.mutateAsync(values);
      showToast.success('Account created!', 'Check your email to verify.', 4);
    } catch (err) {
      handleApiError(err);
    }
  };

  if (signup.isSuccess) {
    return (
      <div className="animate-page text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
          <MailCheck className="h-8 w-8 text-primary" />
        </div>
        <h2 className="text-2xl font-bold">Check your email</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          We&apos;ve sent a verification link to <strong>{email}</strong>
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          Click the link in the email to verify your account and start using Tone.
        </p>
        <Link href="/login">
          <Button variant="outline" className="mt-6">
            Back to Login
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-page">
      <div className="mb-8">
        <h2 className="text-[28px] font-semibold tracking-tight">Create your account</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Start building AI voice agents in minutes
        </p>
      </div>
      <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
        <div className="grid grid-cols-2 gap-3">
          <TextInput
            name="first_name"
            control={control}
            label="First Name"
            placeholder="Jane"
            isRequired
          />
          <TextInput
            name="last_name"
            control={control}
            label="Last Name"
            placeholder="Doe"
            isRequired
          />
        </div>
        <TextInput
          name="email"
          control={control}
          type="email"
          label="Email"
          placeholder="you@company.com"
          isRequired
        />
        <TextInput
          name="password"
          control={control}
          type="password"
          label="Password"
          placeholder="Min. 8 characters"
          isRequired
        />
        <Button type="submit" className="w-full" loading={signup.isPending}>
          Create Account
        </Button>
      </Form>
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
