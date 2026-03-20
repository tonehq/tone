'use client';

import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { TextInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { getCallLogAudioUrl } from '@/services/callLogService';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { Clock, Loader2, Phone, PhoneOff, Radio, Search } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

interface CallDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  callLog: CallLogRow | null;
}

const formatTimestamp = (ts: number | null): string => {
  if (!ts) return '-';
  return new Date(ts * 1000).toLocaleString();
};

const formatDuration = (seconds: number | null): string => {
  if (seconds == null) return '-';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

const escapeRegex = (str: string): string => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function HighlightText({ text, highlight }: { text: string; highlight: string }) {
  if (!highlight.trim()) return <>{text}</>;

  const regex = new RegExp(`(${escapeRegex(highlight)})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="rounded-sm bg-yellow-200 px-0.5 dark:bg-yellow-800">
            {part}
          </mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  completed: {
    label: 'Completed',
    className: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
  in_progress: {
    label: 'In Progress',
    className: 'border-amber-200 bg-amber-50 text-amber-700',
  },
  failed: {
    label: 'Failed',
    className: 'border-red-200 bg-red-50 text-red-700',
  },
};

const CallDetailDrawer: React.FC<CallDetailDrawerProps> = ({ open, onClose, callLog }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);

  useEffect(() => {
    if (!open || !callLog?.audio_file_path) {
      setAudioUrl(null);
      return;
    }

    let cancelled = false;
    const fetchAudioUrl = async () => {
      setAudioLoading(true);
      try {
        const url = await getCallLogAudioUrl(callLog.id);
        if (!cancelled) setAudioUrl(url);
      } catch (err) {
        handleApiError(err);
      } finally {
        if (!cancelled) setAudioLoading(false);
      }
    };

    fetchAudioUrl();
    return () => {
      cancelled = true;
    };
  }, [open, callLog?.id, callLog?.audio_file_path]);

  const filteredTranscript = useMemo(() => {
    if (!callLog?.transcript) return [];
    if (!searchTerm.trim()) return callLog.transcript;
    const lower = searchTerm.toLowerCase();
    return callLog.transcript.filter((msg) => msg.text.toLowerCase().includes(lower));
  }, [callLog?.transcript, searchTerm]);

  const statusConfig = callLog ? STATUS_CONFIG[callLog.status] || null : null;

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{callLog?.agent_name || 'Call Details'}</SheetTitle>
          <SheetDescription className="sr-only">Detailed view of the call log</SheetDescription>
        </SheetHeader>

        {callLog && (
          <div className="flex-1 overflow-y-auto px-4 pb-6">
            {/* Header badges */}
            <div className="flex flex-wrap items-center gap-2">
              <AgentTypeBadge agentType={callLog.agent_type} />
              {statusConfig && (
                <Badge variant="outline" className={cn('px-2.5 py-1', statusConfig.className)}>
                  {statusConfig.label}
                </Badge>
              )}
              {callLog.duration_seconds != null && (
                <Badge variant="outline" className="px-2.5 py-1">
                  <Clock className="size-3.5" />
                  {formatDuration(callLog.duration_seconds)}
                </Badge>
              )}
            </div>

            <Separator className="my-4" />

            {/* Audio Player */}
            <div>
              <h3 className="mb-2 text-sm font-medium text-foreground">Audio Recording</h3>
              {callLog.audio_file_path ? (
                audioLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    Loading audio...
                  </div>
                ) : audioUrl ? (
                  <audio controls src={audioUrl} className="w-full" />
                ) : (
                  <p className="text-sm text-muted-foreground">Failed to load audio</p>
                )
              ) : (
                <p className="text-sm text-muted-foreground">No audio recording available</p>
              )}
            </div>

            <Separator className="my-4" />

            {/* Call Details Grid */}
            <div>
              <h3 className="mb-3 text-sm font-medium text-foreground">Call Details</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="flex items-start gap-2">
                  <Phone className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">From Number</p>
                    <p className="text-sm">{callLog.from_number || '-'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <PhoneOff className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">To Number</p>
                    <p className="text-sm">{callLog.to_number || '-'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Radio className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">Transport Type</p>
                    <p className="text-sm">{callLog.transport_type || '-'}</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <Clock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">Call Start Time</p>
                    <p className="text-sm">{formatTimestamp(callLog.started_at)}</p>
                  </div>
                </div>
                <div className="col-span-2 flex items-start gap-2">
                  <Clock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">Call End Time</p>
                    <p className="text-sm">{formatTimestamp(callLog.ended_at)}</p>
                  </div>
                </div>
              </div>
            </div>

            <Separator className="my-4" />

            {/* Transcription Section */}
            <div>
              <h3 className="mb-2 text-sm font-medium text-foreground">Transcription</h3>

              {callLog.transcript && callLog.transcript.length > 0 ? (
                <>
                  <div className="mb-3">
                    <TextInput
                      placeholder="Search transcription..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      leftIcon={<Search className="size-4" />}
                    />
                  </div>

                  <div className="flex max-h-[40vh] flex-col gap-3 overflow-y-auto">
                    {filteredTranscript.length === 0 ? (
                      <p className="py-4 text-center text-sm text-muted-foreground">
                        No matching messages
                      </p>
                    ) : (
                      filteredTranscript.map((msg, index) => {
                        const isUser = msg.role === 'user';
                        return (
                          <div
                            key={index}
                            className={cn('flex', isUser ? 'justify-start' : 'justify-end')}
                          >
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
                              <p className="whitespace-pre-wrap">
                                <HighlightText text={msg.text} highlight={searchTerm} />
                              </p>
                              {msg.timestamp && (
                                <p className="mt-1 text-right text-[10px] opacity-50">
                                  {msg.timestamp}
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </>
              ) : (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No transcription available
                </p>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
};

export default CallDetailDrawer;
