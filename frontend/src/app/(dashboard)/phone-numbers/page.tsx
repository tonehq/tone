'use client';

import { CustomButton } from '@/components/shared';
import { Card, CardContent } from '@/components/ui/card';
import { Phone, Plus } from 'lucide-react';

export default function PhoneNumbersPage() {
  return (
    <div className="animate-page flex h-full flex-col p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Phone Numbers</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage phone numbers linked to your voice agents
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus className="size-4" />}>
          Link Phone Number
        </CustomButton>
      </div>

      <Card className="flex flex-1 items-center justify-center">
        <CardContent className="flex flex-col items-center gap-4 py-12">
          <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
            <Phone className="size-6 text-muted-foreground" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-foreground">No phone numbers yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Link a phone number to an agent to start receiving calls
            </p>
          </div>
          <CustomButton type="primary" icon={<Plus className="size-4" />}>
            Link Phone Number
          </CustomButton>
        </CardContent>
      </Card>
    </div>
  );
}
