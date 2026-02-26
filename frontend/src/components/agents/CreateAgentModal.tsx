'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import { AgentType } from '@/types/agent';
import { PhoneIncoming, PhoneOutgoing } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface CreateAgentModalProps {
  open: boolean;
  onClose: () => void;
}

const agentOptions = [
  {
    type: 'outbound' as AgentType,
    title: 'Outbound',
    description: 'Automate calls within workflows using Zapier, REST API, or HighLevel',
    icon: PhoneOutgoing,
  },
  {
    type: 'inbound' as AgentType,
    title: 'Inbound',
    description: 'Manage incoming calls via phone, Zapier, REST API, or HighLevel',
    icon: PhoneIncoming,
  },
];

const CreateAgentModal: React.FC<CreateAgentModalProps> = ({ open, onClose }) => {
  const router = useRouter();

  const handleSelectAgent = (type: AgentType) => {
    onClose();
    if (type === 'inbound' || type === 'outbound') {
      router.push(`/agents/create/${type}`);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Choose type of agent"
      hideFooter
      width="sm:max-w-[560px]"
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {agentOptions.map((option) => (
          <CustomButton
            key={option.type}
            type="default"
            onClick={() => handleSelectAgent(option.type)}
            className="flex h-auto items-start gap-3 rounded-xl border border-border p-4 text-left transition-all hover:border-primary hover:shadow-md hover:-translate-y-0.5"
          >
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
              <option.icon className="size-5 text-primary" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-foreground">{option.title}</p>
              <p className="mt-0.5 text-sm font-normal text-muted-foreground leading-snug whitespace-normal">
                {option.description}
              </p>
            </div>
          </CustomButton>
        ))}
      </div>
    </CustomModal>
  );
};

export default CreateAgentModal;
