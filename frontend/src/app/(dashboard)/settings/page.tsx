'use client';

import Apikeys from '@/components/settings/Apikeys';
import Integrations from '@/components/settings/Integrations';
import { CustomButton, TextInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Search, Trash2, UserPlus } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
  const [allowAccessRequests, setAllowAccessRequests] = useState(true);
  const [autoVerifySameDomain, setAutoVerifySameDomain] = useState(false);
  const [activeSidebar] = useState('Integrations');

  const members = [
    { id: 1, name: 'Karthik', email: 'karthik@productfusion.co', role: 'Owner', avatar: 'K' },
  ];

  return (
    <div className="animate-page flex gap-4 p-6">
      {activeSidebar === 'Members' && (
        <div className="p-6">
          {/* Search and Invite */}
          <div className="mb-6 flex items-center justify-between">
            <div className="w-[300px]">
              <TextInput
                name="search-members"
                placeholder="Search members..."
                leftIcon={<Search />}
              />
            </div>
            <CustomButton type="primary" icon={<UserPlus size={18} />}>
              Invite user
            </CustomButton>
          </div>

          {/* Members List */}
          <div>
            {members.map((member) => (
              <div
                key={member.id}
                className="flex items-center justify-between rounded-md p-3 transition-colors hover:bg-muted/50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-400 text-sm font-semibold text-white">
                    {member.avatar}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{member.name}</p>
                    <p className="text-sm text-muted-foreground">{member.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="secondary">{member.role}</Badge>
                  <Button variant="ghost" size="icon-xs" disabled>
                    <Trash2 className="size-4 text-muted-foreground" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSidebar === 'Organization' && (
        <div className="p-6">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Access Settings</h2>

          <div className="rounded-md border border-border bg-muted/30 p-6">
            <div className="mb-4">
              <div className="flex items-start gap-3">
                <Switch checked={allowAccessRequests} onCheckedChange={setAllowAccessRequests} />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Allow users to request access
                  </p>
                  <p className="text-sm text-muted-foreground">
                    When enabled, users can request to join your organization during signup
                  </p>
                </div>
              </div>
            </div>

            {allowAccessRequests && (
              <div className="ml-6 border-l-2 border-border pl-6">
                <div className="flex items-start gap-3">
                  <Switch
                    checked={autoVerifySameDomain}
                    onCheckedChange={setAutoVerifySameDomain}
                  />
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      Auto-approve users with same email domain
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Automatically approve access requests from users with the same email domain
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeSidebar === 'API Key' && <Apikeys />}

      {activeSidebar === 'Integrations' && <Integrations />}
    </div>
  );
}
