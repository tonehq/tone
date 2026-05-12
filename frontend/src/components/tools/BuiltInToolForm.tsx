'use client';

import { CustomButton, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import SettingsSection from '@/components/tools/SettingsSection';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  TOOL_TYPE_AUTH_SECTIONS,
  TOOL_TYPE_HEADER,
  TOOL_TYPE_META_SECTIONS,
  TOOL_TYPE_OAUTH_PROVIDER,
} from '@/constants/toolForm';
import { type BuiltInToolFormData, builtInToolSchema } from '@/schemas/tool';
import { getOAuthConnections } from '@/services/oauthService';
import type { OAuthConnection } from '@/types/oauth';
import type { Tool, ToolParametersSchema, ToolType } from '@/types/tool';
import { cn } from '@/utils/cn';
import { showToast } from '@/utils/toast';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  ArrowLeft,
  Check,
  Copy,
  LinkIcon,
  Loader2,
  MoreVertical,
  Save,
  Settings,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';

interface BuiltInToolFormProps {
  toolType: ToolType;
  name: string;
  description: string;
  metaData: Record<string, string>;
  authConfig: Record<string, string>;
  parameters: ToolParametersSchema;
  toolRecord: Tool | null;
  isEditMode: boolean;
  saving: boolean;
  saved: boolean;
  oauthConnectionId: number | null;
  onMetaDataChange: (data: Record<string, string>) => void;
  onAuthConfigChange: (data: Record<string, string>) => void;
  onOAuthConnectionIdChange: (id: number | null) => void;
  onSave: (data: BuiltInToolFormData) => void;
  onDelete?: () => void;
  onBack: () => void;
  onDirty: () => void;
}

export default function BuiltInToolForm({
  toolType,
  name,
  description,
  metaData,
  authConfig,
  parameters,
  toolRecord,
  isEditMode,
  saving,
  saved,
  oauthConnectionId,
  onMetaDataChange,
  onAuthConfigChange,
  onOAuthConnectionIdChange,
  onSave,
  onDelete,
  onBack,
  onDirty,
}: BuiltInToolFormProps) {
  const [uuidCopied, setUuidCopied] = useState(false);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    settings: true,
    connection: true,
    meta: true,
  });

  // OAuth connections for this tool type
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [connectionsLoading, setConnectionsLoading] = useState(false);

  const oauthProvider = TOOL_TYPE_OAUTH_PROVIDER[toolType];

  useEffect(() => {
    if (!oauthProvider) return;
    setConnectionsLoading(true);
    getOAuthConnections(toolType)
      .then(setConnections)
      .catch(() => setConnections([]))
      .finally(() => setConnectionsLoading(false));
  }, [oauthProvider, toolType]);

  const connectionOptions = useMemo(
    () =>
      connections.map((c) => ({
        value: String(c.id),
        label: c.user_email ?? `Connection #${c.id}`,
      })),
    [connections],
  );

  const { control, handleSubmit, watch, reset } = useForm<BuiltInToolFormData>({
    resolver: zodResolver(builtInToolSchema),
    defaultValues: { name, description },
  });

  useEffect(() => {
    reset({ name, description });
  }, [name, description, reset]);

  const watchedName = watch('name');

  const headerConfig = TOOL_TYPE_HEADER[toolType];
  const metaSection = TOOL_TYPE_META_SECTIONS[toolType];
  const authSection = TOOL_TYPE_AUTH_SECTIONS[toolType];
  const HeaderIcon = headerConfig?.icon ?? Settings;
  const paramCount = Object.keys(parameters?.properties ?? {}).length;

  const handleCopyUuid = useCallback(() => {
    if (!toolRecord?.uuid) return;
    navigator.clipboard.writeText(toolRecord.uuid);
    setUuidCopied(true);
    setTimeout(() => setUuidCopied(false), 2000);
  }, [toolRecord?.uuid]);

  const toggleSection = (key: string) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const onSubmit = (data: BuiltInToolFormData) => {
    onSave(data);
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-background px-5 py-3">
        <div className="flex items-center gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </CustomButton>

          <div
            className={cn(
              'flex size-9 items-center justify-center rounded-xl',
              headerConfig?.bg ?? 'bg-muted',
            )}
          >
            <HeaderIcon size={18} className={headerConfig?.color ?? 'text-muted-foreground'} />
          </div>

          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold text-foreground">
              {watchedName || 'Untitled Tool'}
            </h1>
            {toolRecord?.uuid && (
              <button
                type="button"
                onClick={handleCopyUuid}
                className="group mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
                aria-label="Copy UUID"
              >
                <span className="font-mono">{toolRecord.uuid.slice(0, 13)}...</span>
                {uuidCopied ? (
                  <Check size={10} className="text-emerald-500" />
                ) : (
                  <Copy
                    size={10}
                    className="opacity-0 transition-opacity group-hover:opacity-100"
                  />
                )}
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <CustomButton
            type="primary"
            size="sm"
            icon={
              saving ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : saved ? (
                <Check size={14} />
              ) : (
                <Save size={13} />
              )
            }
            onClick={handleSubmit(onSubmit)}
            loading={saving}
            className={cn(
              'min-w-[80px] transition-colors',
              saved &&
                'bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-600 dark:hover:bg-emerald-700',
            )}
          >
            {saved ? 'Saved' : 'Save'}
          </CustomButton>

          {isEditMode && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <CustomButton
                  type="text"
                  size="icon-sm"
                  className="text-muted-foreground hover:text-foreground"
                >
                  <MoreVertical size={16} />
                </CustomButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-[160px]">
                <DropdownMenuItem
                  onClick={() => {
                    if (toolRecord?.uuid) {
                      navigator.clipboard.writeText(toolRecord.uuid);
                      showToast.success('Tool ID copied');
                    }
                  }}
                >
                  <Copy size={14} />
                  Copy Tool ID
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={onDelete}>
                  <Trash2 size={14} />
                  Delete Tool
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-muted/20">
        <div className="mx-auto max-w-[700px] space-y-4 px-6 py-6">
          {/* Tool Settings */}
          <SettingsSection
            title="Tool Settings"
            description="Configure the basic settings for this tool"
            icon={Settings}
            iconColor="text-foreground/70"
            iconBg="bg-foreground/5 dark:bg-foreground/10"
            isOpen={openSections.settings}
            onToggle={() => toggleSection('settings')}
          >
            <div className="space-y-5">
              <TextInput
                name="name"
                control={control}
                label="Tool Name"
                placeholder="google_calendar_tool"
                isRequired
                className="font-mono"
                onValueChange={onDirty}
              />

              <div className="relative">
                <TextAreaField
                  name="description"
                  control={control}
                  label="Description"
                  placeholder="Describe the tool in a few sentences"
                  rows={4}
                  maxLength={1000}
                  isRequired
                  onValueChange={onDirty}
                />
                <span className="absolute top-0 right-0 text-[11px] tabular-nums text-muted-foreground">
                  {(watch('description') ?? '').length}/1000
                </span>
              </div>
            </div>
          </SettingsSection>

          {/* Google Account Connection (only for OAuth tool types) */}
          {oauthProvider && (
            <SettingsSection
              title="Google Account"
              description="Select which connected Google account this tool should use"
              icon={LinkIcon}
              iconColor="text-blue-600 dark:text-blue-400"
              iconBg="bg-blue-50 dark:bg-blue-500/10"
              isOpen={openSections.connection}
              onToggle={() => toggleSection('connection')}
            >
              <SelectInput
                name="oauth-connection"
                label="Connected Account"
                options={connectionOptions}
                value={oauthConnectionId ? String(oauthConnectionId) : ''}
                onValueChange={(v) => {
                  onOAuthConnectionIdChange(v ? Number(v) : null);
                  onDirty();
                }}
                loading={connectionsLoading}
                placeholder="Select a Google account..."
              />
              {connections.length === 0 && !connectionsLoading && (
                <p className="mt-2 text-[12px] text-muted-foreground">
                  No Google accounts connected.{' '}
                  <a href="/integrations" className="text-primary hover:underline">
                    Connect one in Integrations
                  </a>
                  .
                </p>
              )}
            </SettingsSection>
          )}

          {/* Auth credentials (Twilio SID, Auth Token, etc.) */}
          {authSection && (
            <SettingsSection
              title={authSection.title}
              description={authSection.description}
              icon={authSection.icon}
              iconColor={authSection.iconColor}
              iconBg={authSection.iconBg}
              isOpen={openSections.meta}
              onToggle={() => toggleSection('meta')}
            >
              <div className="space-y-5">
                {authSection.fields.map((field) => (
                  <div key={field.key}>
                    <TextInput
                      name={`tool-auth-${field.key}`}
                      label={field.label}
                      type={field.type}
                      placeholder={field.placeholder}
                      value={authConfig[field.key] ?? ''}
                      onChange={(e) => {
                        onAuthConfigChange({ ...authConfig, [field.key]: e.target.value });
                        onDirty();
                      }}
                    />
                  </div>
                ))}
              </div>
            </SettingsSection>
          )}

          {/* Type-specific settings (Calendar ID, Timezone, etc.) */}
          {metaSection && (
            <SettingsSection
              title={metaSection.title}
              description={metaSection.description}
              icon={metaSection.icon}
              iconColor={metaSection.iconColor}
              iconBg={metaSection.iconBg}
              isOpen={openSections.meta}
              onToggle={() => toggleSection('meta')}
            >
              <div className="space-y-5">
                {metaSection.fields.map((field) => (
                  <div key={field.key}>
                    <TextInput
                      name={`tool-meta-${field.key}`}
                      label={field.label}
                      type={field.type}
                      placeholder={field.placeholder}
                      value={metaData[field.key] ?? ''}
                      onChange={(e) => {
                        onMetaDataChange({ ...metaData, [field.key]: e.target.value });
                        onDirty();
                      }}
                    />
                    {field.helperText && (
                      <p className="mt-1.5 text-[12px] leading-relaxed text-muted-foreground">
                        {field.helperText}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </SettingsSection>
          )}

          {paramCount > 0 && (
            <div className="overflow-hidden rounded-xl border border-border bg-background p-5 shadow-sm">
              <p className="mb-2.5 text-[12px] font-medium text-muted-foreground">
                Accepts {paramCount} parameter{paramCount > 1 ? 's' : ''}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(parameters?.properties ?? {}).map(([paramName, param]) => {
                  const isReq = (parameters?.required ?? []).includes(paramName);
                  return (
                    <span
                      key={paramName}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-mono text-[11px] transition-colors',
                        isReq
                          ? 'bg-foreground/5 text-foreground ring-1 ring-inset ring-foreground/10'
                          : 'bg-muted text-muted-foreground',
                      )}
                    >
                      {paramName}
                      <span className="text-[9px] opacity-50">
                        {(param as { type?: string }).type ?? 'string'}
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
