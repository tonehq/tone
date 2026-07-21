'use client';

import { TextInput } from '@/components/shared';

import type { OnboardingForm } from '../types';

interface WorkspaceStepProps {
  form: OnboardingForm;
}

export default function WorkspaceStep({ form }: WorkspaceStepProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Name your workspace</h1>
        <p className="text-sm text-muted-foreground">
          This is what your team will see across Tone. You can rename it later.
        </p>
      </div>
      <TextInput
        name="workspace_name"
        control={form.control}
        label="Workspace name"
        placeholder="Acme AI"
        isRequired
      />
    </div>
  );
}
