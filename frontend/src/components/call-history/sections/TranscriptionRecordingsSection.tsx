'use client';

import { TextInput } from '@/components/shared';
import { Separator } from '@/components/ui/separator';
import { getCallLogAudioUrl } from '@/services/callLogService';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { formatChatTimestamp } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { Loader2, Search } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

interface TranscriptionRecordingsSectionProps {
  callLog: CallLogRow;
}

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

const TranscriptionRecordingsSection: React.FC<TranscriptionRecordingsSectionProps> = ({
  callLog,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioLoading, setAudioLoading] = useState(false);

  useEffect(() => {
    if (!callLog.recording_upload_id) {
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
        if (!cancelled) handleApiError(err);
      } finally {
        if (!cancelled) setAudioLoading(false);
      }
    };

    fetchAudioUrl();
    return () => {
      cancelled = true;
    };
  }, [callLog.id, callLog.recording_upload_id]);

  const filteredTranscript = useMemo(() => {
    if (!callLog.transcript) return [];
    if (!searchTerm.trim()) return callLog.transcript;
    const lower = searchTerm.toLowerCase();
    return callLog.transcript.filter((msg) => msg.text.toLowerCase().includes(lower));
  }, [callLog.transcript, searchTerm]);

  return (
    <div className="flex flex-col">
      {/* Audio Player */}
      <div>
        <h3 className="mb-2 text-sm font-medium text-foreground">Audio Recording</h3>
        {callLog.recording_upload_id ? (
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

      <Separator className="my-6" />

      {/* Transcription */}
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

            <div className="flex flex-col gap-3">
              {filteredTranscript.length === 0 ? (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  No matching messages
                </p>
              ) : (
                filteredTranscript.map((msg, index) => {
                  const isUser = msg.role === 'user';
                  const formattedTime = formatChatTimestamp(msg.timestamp);
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
                        {formattedTime && (
                          <p className="mt-1 text-right text-[10px] opacity-50">{formattedTime}</p>
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
  );
};

export default TranscriptionRecordingsSection;
