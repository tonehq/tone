'use client';

import { CustomModal } from '@/components/shared';
import { cn } from '@/utils/cn';
import React from 'react';

interface TranscriptMessage {
  role: string;
  text: string;
  timestamp?: string;
}

interface TranscriptionModalProps {
  open: boolean;
  onClose: () => void;
  transcript: TranscriptMessage[] | null;
  agentName: string;
}

const TranscriptionModal: React.FC<TranscriptionModalProps> = ({
  open,
  onClose,
  transcript,
  agentName,
}) => (
  <CustomModal
    open={open}
    onClose={onClose}
    title={`Transcription${agentName ? ` — ${agentName}` : ''}`}
    width="md:max-w-xl"
    hideFooter
  >
    <div className="flex max-h-[60vh] flex-col gap-3 overflow-y-auto">
      {!transcript || transcript.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No transcription available</p>
      ) : (
        transcript.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div key={index} className={cn('flex', isUser ? 'justify-start' : 'justify-end')}>
              <div
                className={cn(
                  'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm',
                  isUser
                    ? 'rounded-bl-sm bg-muted text-foreground'
                    : 'rounded-br-sm bg-primary text-primary-foreground',
                )}
              >
                <p className="mb-0.5 text-xs font-medium opacity-70">
                  {isUser ? 'User' : 'Assistant'}
                </p>
                <p className="whitespace-pre-wrap">{msg.text}</p>
                {msg.timestamp && (
                  <p className="mt-1 text-right text-[10px] opacity-50">{msg.timestamp}</p>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  </CustomModal>
);

export default TranscriptionModal;
