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
            className="flex h-auto items-start gap-3 rounded-xl border border-border p-5 text-left transition-all duration-200 hover:border-primary hover:ring-2 hover:ring-primary/20 hover:shadow-md hover:scale-[1.02]"
          >
            <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary/10">
              <option.icon className="size-6 text-primary" />
            </div>
            <div className="flex-1">
              <p className="text-[15px] font-semibold text-foreground">{option.title}</p>
              <p className="mt-1 text-sm font-normal leading-snug text-muted-foreground whitespace-normal">
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
