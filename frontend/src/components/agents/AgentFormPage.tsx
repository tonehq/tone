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
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Loader2,
  MessageSquare,
  Phone,
  Save,
  Settings,
  Volume2,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

interface AgentFormPageProps {
  agentType: 'inbound' | 'outbound';
  agentId?: string;
}

export default function AgentFormPage({ agentType, agentId }: AgentFormPageProps) {
  const router = useRouter();
  const isEditMode = !!agentId;

  const [providersLoadable] = useAtom(loadableProvidersAtom);
  const [activeTab, setActiveTab] = useState('general');
  const [formData, setFormData] = useState<AgentFormState>(() => defaultFormState(agentType));
  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [_assigning, setAssigning] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deletingAgent, setDeletingAgent] = useState(false);
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
        showToast.error('Error', 'Agent not found');
      }
    } catch (error) {
      handleApiError(error);
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
        agent_id: agentId ? Number(agentId) : undefined,
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

      setFormData((prev) => ({
        ...prev,
        phoneNumbers: [...prev.phoneNumbers, ...phoneNumbers],
      }));
      showToast.success('Success', 'Phone number(s) assigned successfully');
    } catch (error) {
      handleApiError(error);
      throw error;
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
        agent_id: agentId ? Number(agentId) : undefined,
      });
      setFormData((prev) => ({
        ...prev,
        phoneNumbers: prev.phoneNumbers.filter((pn) => pn.no !== unassignTarget.no),
      }));
      setUnassignTarget(null);
      showToast.success('Success', 'Phone number unassigned successfully');
    } catch (error) {
      handleApiError(error);
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
      showToast.success(
        'Success',
        isEditMode ? 'Agent saved successfully' : 'Agent created successfully',
      );
      if (!isEditMode) {
        router.push('/agents');
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setSaving(false);
    }
  };

  const openDeleteConfirm = () => setDeleteConfirmOpen(true);

  const handleConfirmDeleteAgent = async () => {
    setDeletingAgent(true);
    try {
      if (isEditMode) {
        await deleteAgent(Number(agentId));
        router.push('/agents');
      } else {
        router.push('/agents');
      }
    } catch (error) {
      handleApiError(error);
    } finally {
      setDeletingAgent(false);
      setDeleteConfirmOpen(false);
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
              llmMetaData: formData.llmMetaData,
            }}
            llmProviders={llmProviders}
            providersLoading={providersLoading}
            onFormChange={handleFormChange}
            onDeleteAgent={openDeleteConfirm}
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
              ttsMetaData: formData.ttsMetaData,
              sttMetaData: formData.sttMetaData,
            }}
            ttsProviders={ttsProviders}
            sttProviders={sttProviders}
            providersLoading={providersLoading}
            onFormChange={handleFormChange}
          />
        ),
      },
      {
        key: 'prompt',
        label: 'Prompt',
        icon: <MessageSquare size={16} />,
        children: (
          <PromptPage
            formData={{ voicePrompting: formData.voicePrompting }}
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
                    <CustomButton type="default" onClick={() => setUnassignTarget(pn)}>
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

    [formData, llmProviders, ttsProviders, sttProviders, providersLoading, isEditMode],
  );

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-3">
        <Loader2 className="size-10 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Status banner */}
      <div
        className={cn(
          'flex shrink-0 items-center gap-2 px-6 py-1.5 text-[13px] leading-tight',
          formData.phoneNumbers?.length > 0
            ? 'bg-emerald-50/80 text-emerald-800'
            : 'bg-amber-50/80 text-amber-800',
        )}
      >
        {formData.phoneNumbers?.length > 0 ? (
          <>
            <CheckCircle2 size={13} className="shrink-0 text-emerald-600" />
            <span>
              <span className="font-medium">Phone assigned:</span>{' '}
              {formData.phoneNumbers.map((pn) => pn.no).join(', ')}
            </span>
          </>
        ) : (
          <>
            <AlertTriangle size={13} className="shrink-0 text-amber-600" />
            <span>
              <span className="font-medium">No phone number</span>
              <span className="mx-1 opacity-40">&mdash;</span>
              Your agent can&apos;t {agentType === 'inbound' ? 'receive' : 'make'} calls yet.
            </span>
          </>
        )}
      </div>

      {/* Breadcrumb bar */}
      <div className="flex shrink-0 items-center justify-between border-b border-border/60 bg-muted/30 px-6 py-2">
        <nav className="flex items-center gap-1.5 text-[13px]">
          <CustomButton
            type="link"
            htmlType="button"
            className="!p-0 text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground"
            onClick={() => router.push('/agents')}
          >
            Agents
          </CustomButton>
          <ChevronRight size={12} className="text-muted-foreground/40" />
          <span className="max-w-[240px] truncate font-medium text-foreground">
            {formData.name || 'Untitled Agent'}
          </span>
        </nav>
        <div className="flex shrink-0 items-center gap-2">
          <CustomButton type="default" icon={<Phone size={14} />}>
            Test Agent
          </CustomButton>
          <CustomButton
            type="primary"
            icon={saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save size={14} />}
            onClick={handleSave}
            loading={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </CustomButton>
        </div>
      </div>

      {/* Agent identity sub-header */}
      <div className="flex shrink-0 items-center gap-4 bg-background px-6 py-3.5">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-primary/20 bg-primary/10 text-base font-bold text-primary">
          {formData.name?.charAt(0)?.toUpperCase() || 'A'}
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold tracking-tight text-foreground">
            {formData.name || 'Untitled Agent'}
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <AgentTypeBadge agentType={agentType} />
            {formData.phoneNumbers?.length > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                <Phone size={11} />
                {formData.phoneNumbers[0].no}
                {formData.phoneNumbers.length > 1 && ` +${formData.phoneNumbers.length - 1}`}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tabs + content */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CustomTab
          activeKey={activeTab}
          onTabChange={setActiveTab}
          className="flex min-h-0 flex-1 flex-col overflow-hidden"
          tabBarClassName="shrink-0 border-b border-border bg-background px-6"
          contentClassName="min-h-0 flex-1 overflow-auto bg-muted/20 px-8 py-6"
          items={configTabItems}
        />
      </div>

      {/* Modals */}
      <AssignPhoneNumberModal
        open={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        currentPhoneNumbers={formData.phoneNumbers}
        onAssign={handleAssignPhoneNumbers}
        agentId={agentId ? Number(agentId) : undefined}
      />

      <CustomModal
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        title="Delete Agent"
        description="Deleting an agent will erase personalized data, voice profiles, and integrations. Are you sure?"
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deletingAgent}
        onConfirm={handleConfirmDeleteAgent}
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
          Are you sure you want to unassign <strong>{unassignTarget?.no}</strong>? This will remove
          it from the agent.
        </p>
      </CustomModal>
    </div>
  );
}
