'use client';

import { loadableProvidersAtom } from '@/atoms/ProviderAtom';
import { CallConfigurationTab, GeneralTab, VoiceTab } from '@/components/agents/agent-form';
import PromptPage from '@/components/agents/agent-form/promptPage';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import AssignPhoneNumberModal from '@/components/agents/AssignPhoneNumberModal';
import type { TabItem } from '@/components/shared';
import { CustomButton, CustomModal, CustomTab } from '@/components/shared';
import { deleteAgent, getAgent, upsertAgent } from '@/services/agentsService';
import type { AgentFormState } from '@/types/agent';
import {
  apiAgentToFormState,
  defaultFormState,
  formStateToUpsertPayload,
} from '@/utils/agentFormUtils';
import axiosInstance from '@/utils/axios';
import { cn } from '@/utils/cn';
import { useNotification } from '@/utils/notification';
import { useAtom } from 'jotai';
import { startCase } from 'lodash';
import { ArrowLeft, Loader2, Phone, Save, Settings, Volume2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

interface AgentFormPageProps {
  agentType: 'inbound' | 'outbound';
  agentId?: string;
}

export default function AgentFormPage({ agentType, agentId }: AgentFormPageProps) {
  const router = useRouter();
  const isEditMode = !!agentId;
  const { notify, contextHolder } = useNotification();

  const [providersLoadable] = useAtom(loadableProvidersAtom);
  const [activeTab, setActiveTab] = useState('general');
  const [currentMenu, setCurrentMenu] = useState('configure');
  const [formData, setFormData] = useState<AgentFormState>(() => defaultFormState(agentType));
  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [_assigning, setAssigning] = useState(false);
  const [unassignTarget, setUnassignTarget] = useState<{ no: string; type: string } | null>(null);
  const [unassigning, setUnassigning] = useState(false);

  const providers = providersLoadable.state === 'hasData' ? providersLoadable.data : [];
  const providersLoading = providersLoadable.state === 'loading';
  const llmProviders = providers.filter((p) => p.provider_type === 'llm');
  const ttsProviders = providers.filter((p) => p.provider_type === 'tts');
  const sttProviders = providers.filter((p) => p.provider_type === 'stt');

  const loadAgentData = useCallback(async () => {
    if (!agentId) return;
    setLoading(true);
    try {
      const agent = await getAgent(agentId);
      if (agent) {
        setFormData(apiAgentToFormState(agent, agentType));
      } else {
        notify.error('Error', 'Agent not found');
      }
    } catch {
      notify.error('Error', 'Failed to load agent');
    } finally {
      setLoading(false);
    }
  }, [agentId, agentType]);

  useEffect(() => {
    if (isEditMode) {
      loadAgentData();
    }
  }, [isEditMode, loadAgentData]);

  const handleFormChange = (partial: any) => {
    setFormData((prev) => ({ ...prev, ...partial }));
  };

  const handleAssignPhoneNumbers = async (phoneNumbers: { type: string; no: string }[]) => {
    setAssigning(true);
    try {
      const channel = formData?.channels?.find((channel: any) => channel.type === 'twilio');
      const payload = {
        phone_number: phoneNumbers,
        phone_number_sid: channel?.meta_data?.account_sid,
        phone_number_auth_token: channel?.meta_data?.auth_token,
        provider: 'twilio',
        channel_id: channel?.id,
        country_code: '+1',
        number_type: 'international',
        capabilities: {
          voice: true,
          sms: false,
          mms: true,
        },
        status: 'active',
      };
      await axiosInstance.post('/channel_phone_number/upsert_channel_phone_number', payload);

      setFormData((prev) => ({ ...prev, phoneNumbers }));
      notify.success('Success', 'Phone number(s) assigned successfully');
    } catch {
      notify.error('Error', 'Failed to assign phone number(s). Please try again.');
    } finally {
      setAssigning(false);
    }
  };

  const handleConfirmUnassign = async () => {
    if (!unassignTarget) return;
    const channel = formData?.channels?.find((c: any) => c.type === unassignTarget.type);
    setUnassigning(true);
    try {
      await axiosInstance.post('/channel_phone_number/detach_channel_phone_number', {
        channel_id: channel?.id,
        phone_number: unassignTarget.no,
      });
      setFormData((prev) => ({
        ...prev,
        phoneNumbers: prev.phoneNumbers.filter((pn) => pn.no !== unassignTarget.no),
      }));
      setUnassignTarget(null);
      notify.success('Success', 'Phone number unassigned successfully');
    } catch {
      notify.error('Error', 'Failed to unassign phone number. Please try again.');
    } finally {
      setUnassigning(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = formStateToUpsertPayload(
        formData,
        agentType,
        isEditMode ? Number(agentId) : undefined,
      );
      await upsertAgent(payload);
      notify.success(
        'Success',
        isEditMode ? 'Agent saved successfully' : 'Agent created successfully',
      );
      if (!isEditMode) {
        router.push('/agents');
      }
    } catch {
      notify.error(
        'Error',
        isEditMode
          ? 'Failed to save agent. Please try again.'
          : 'Failed to create agent. Please try again.',
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAgent = async () => {
    if (
      typeof window !== 'undefined' &&
      window.confirm(
        'Deleting an agent will erase personalized data, voice profiles, and integrations. Are you sure?',
      )
    ) {
      if (isEditMode) {
        try {
          await deleteAgent(Number(agentId));
          router.push('/agents');
        } catch {
          notify.error('Error', 'Failed to delete agent');
        }
      } else {
        router.push('/agents');
      }
    }
  };

  const configTabItems: TabItem[] = useMemo(
    () => [
      {
        key: 'general',
        label: 'General',
        icon: <Settings size={16} />,
        children: (
          <GeneralTab
            formData={{
              name: formData.name,
              description: formData.description,
              aiModel: formData.aiModel,
              end_call_message: formData.end_call_message,
              first_message: formData.first_message,
              customVocabulary: formData.customVocabulary,
              filterWords: formData.filterWords,
              useRealisticFillerWords: formData.useRealisticFillerWords,
            }}
            llmProviders={llmProviders}
            providersLoading={providersLoading}
            onFormChange={handleFormChange}
            onDeleteAgent={handleDeleteAgent}
          />
        ),
      },
      {
        key: 'voice',
        label: 'Voice',
        icon: <Volume2 size={16} />,
        children: (
          <VoiceTab
            formData={{
              language: formData.language,
              voiceSpeed: formData.voiceSpeed,
              voiceProvider: formData.voiceProvider,
              sttProvider: formData.sttProvider,
              patienceLevel: formData.patienceLevel as 'low' | 'medium' | 'high',
              speechRecognition: formData.speechRecognition as 'fast' | 'accurate',
            }}
            ttsProviders={ttsProviders}
            sttProviders={sttProviders}
            providersLoading={providersLoading}
            onFormChange={handleFormChange}
          />
        ),
      },
      {
        key: 'call-config',
        label: 'Call Configuration',
        icon: <Phone size={16} />,
        children: (
          <CallConfigurationTab
            formData={{
              callRecording: formData.callRecording,
              callTranscription: formData.callTranscription,
            }}
            onFormChange={handleFormChange}
          />
        ),
      },
      {
        key: 'assign-number',
        label: 'Assign Number',
        icon: <Phone size={16} />,
        children: (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-foreground">Assign Number</h3>
              {isEditMode && (
                <CustomButton
                  type="primary"
                  icon={<Phone size={16} />}
                  onClick={() => setAssignModalOpen(true)}
                >
                  Assign New Number
                </CustomButton>
              )}
            </div>

            {!formData.phoneNumbers?.length ? (
              <p className="text-sm text-muted-foreground">
                {isEditMode
                  ? 'No phone numbers assigned yet. Click "Assign New Number" to add one.'
                  : 'Save the agent first to assign phone numbers.'}
              </p>
            ) : (
              <div className="space-y-2">
                {formData.phoneNumbers.map((pn) => (
                  <div
                    key={pn.no}
                    className="flex items-center gap-3 rounded-md border border-border bg-background px-4 py-3"
                  >
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">
                      <Phone size={15} className="text-muted-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">{pn.no}</p>
                      <p className="text-xs capitalize text-muted-foreground">{pn.type}</p>
                    </div>
                    <CustomButton
                      type="default"
                      onClick={() => setUnassignTarget(pn)}
                    >
                      Unassign
                    </CustomButton>
                  </div>
                ))}
              </div>
            )}
          </div>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [formData, llmProviders, ttsProviders, sttProviders, providersLoading],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-3">
        <Loader2 className="size-10 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      {/* Left Sidebar */}
      <div className="flex w-[280px] flex-col border-r border-border bg-background">
        <div className="px-3 py-2">
          <CustomButton
            type="text"
            icon={<ArrowLeft size={16} />}
            onClick={() => router.push('/agents')}
          >
            Back to Agents
          </CustomButton>
        </div>

        <div className="border-b border-border px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground">
              {formData.name?.charAt(0)?.toUpperCase() || 'A'}
            </div>
            <div className="min-w-0 space-y-1">
              <h3 className="truncate text-sm font-semibold text-foreground">{formData.name}</h3>
              <AgentTypeBadge agentType={agentType} />
              {formData.phoneNumbers?.length > 0 && (
                <div className="mt-1 space-y-0.5">
                  {formData.phoneNumbers.map((pn) => (
                    <p
                      key={pn.no}
                      className="flex items-center gap-1 text-xs text-muted-foreground"
                    >
                      <Phone size={12} />
                      {pn.no}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="px-3 py-3">
          <CustomButton type="primary" fullWidth icon={<Phone size={16} />}>
            Test Agent
          </CustomButton>
        </div>

        <div className="flex-1 space-y-1 px-3 py-2">
          {['configure', 'prompt'].map((item) => {
            const isActive = item === currentMenu;
            return (
              <CustomButton
                key={item}
                type="text"
                htmlType="button"
                fullWidth
                className={cn(
                  'justify-start rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-accent text-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                )}
                onClick={() => setCurrentMenu(item)}
              >
                {startCase(item)}
              </CustomButton>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <div
          className={cn(
            'flex items-center border-b border-border px-6 py-2.5',
            formData.phoneNumbers?.length > 0 ? 'bg-emerald-50' : 'bg-muted',
          )}
        >
          <div className="flex-1 text-[13px]">
            {formData.phoneNumbers?.length > 0 ? (
              <>
                <strong>Phone assigned:</strong>{' '}
                {formData.phoneNumbers.map((pn) => pn.no).join(', ')}
              </>
            ) : (
              <>
                <strong>Important</strong> Your agent doesn&apos;t have a phone number and
                can&apos;t {agentType === 'inbound' ? 'receive' : 'make'} calls.
              </>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between border-b border-border bg-background px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">{startCase(currentMenu)}</h2>
          <CustomButton
            type="primary"
            icon={saving ? <Loader2 className="size-4 animate-spin" /> : <Save size={16} />}
            onClick={handleSave}
            loading={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </CustomButton>
        </div>

        {currentMenu === 'configure' && (
          <div className="flex flex-1 flex-col overflow-hidden">
            <CustomTab
              activeKey={activeTab}
              onTabChange={setActiveTab}
              className="flex flex-1 flex-col overflow-hidden"
              tabBarClassName="px-6 border-b border-border"
              contentClassName="flex-1 overflow-auto bg-background px-8 py-6"
              items={configTabItems}
            />
          </div>
        )}
        {currentMenu === 'prompt' && (
          <PromptPage
            formData={{ voicePrompting: formData.voicePrompting }}
            onFormChange={handleFormChange}
          />
        )}
      </div>

      <AssignPhoneNumberModal
        open={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        currentPhoneNumbers={formData.phoneNumbers}
        onAssign={handleAssignPhoneNumbers}
      />

      <CustomModal
        open={!!unassignTarget}
        onClose={() => setUnassignTarget(null)}
        title="Unassign Phone Number"
        confirmText="Unassign"
        confirmType="danger"
        confirmLoading={unassigning}
        onConfirm={handleConfirmUnassign}
      >
        <p className="text-sm text-foreground">
          Are you sure you want to unassign{' '}
          <strong>{unassignTarget?.no}</strong>? This will remove it from the agent.
        </p>
      </CustomModal>

      {contextHolder}
    </div>
  );
}
