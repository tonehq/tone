'use client';

import '@livekit/components-styles';

import {
  BarVisualizer,
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
  useRemoteParticipants,
  useTracks,
  useVoiceAssistant,
  VoiceAssistantControlBar,
} from '@livekit/components-react';
import { ConnectionState, Track } from 'livekit-client';
import { Bot, PhoneOff } from 'lucide-react';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { startWebCall, type WebCallSession } from '@/services/webrtcService';

const AGENT_WAIT_TIMEOUT_MS = 15000;

function statusLabel(
  connection: ConnectionState,
  agentState: string | undefined,
  hasAgent: boolean,
) {
  if (connection === ConnectionState.Connecting) return 'Connecting to the room…';
  if (connection === ConnectionState.Reconnecting) return 'Reconnecting…';
  if (connection !== ConnectionState.Connected) return 'Disconnected';
  if (!hasAgent) return 'Waiting for the agent to join…';
  if (agentState === 'speaking') return 'Agent is speaking';
  if (agentState === 'thinking') return 'Agent is thinking…';
  if (agentState === 'listening') return 'Listening…';
  return 'Connected — say hello';
}

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-neutral-950 text-neutral-100">
      {children}
    </div>
  );
}

function CallEnded() {
  return (
    <Screen>
      <div className="flex size-20 items-center justify-center rounded-full bg-neutral-800 ring-1 ring-neutral-700">
        <PhoneOff className="size-8 text-neutral-300" strokeWidth={1.5} />
      </div>
      <div className="text-lg font-medium">Call ended</div>
      <div className="text-sm text-neutral-400">Thanks for calling. You can close this tab.</div>
    </Screen>
  );
}

function CallStage({ onStale }: { onStale: () => void }) {
  const connection = useConnectionState();
  const { state: agentState, audioTrack } = useVoiceAssistant();
  const remotes = useRemoteParticipants();
  const micTracks = useTracks([Track.Source.Microphone], { onlySubscribed: true });
  const remoteAudio = micTracks.find((track) => !track.participant.isLocal);
  const visualizerTrack = audioTrack ?? remoteAudio;
  const hasAgent = remotes.length > 0 || !!visualizerTrack;

  useEffect(() => {
    if (connection !== ConnectionState.Connected || hasAgent) return;
    const timer = setTimeout(onStale, AGENT_WAIT_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [connection, hasAgent, onStale]);

  return (
    <div className="flex h-screen flex-col items-center justify-between bg-neutral-950 py-12 text-neutral-100">
      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <div className="flex flex-col items-center gap-4">
          <div className="flex size-24 items-center justify-center rounded-full bg-neutral-800 ring-1 ring-neutral-700">
            <Bot className="size-10 text-neutral-300" strokeWidth={1.5} />
          </div>
          <div className="text-lg font-medium">AI Voice Agent</div>
          <div className="flex items-center gap-2 text-sm text-neutral-400">
            <span
              className={`size-2 rounded-full ${hasAgent ? 'bg-emerald-500' : 'bg-amber-500'}`}
            />
            {statusLabel(connection, agentState, hasAgent)}
          </div>
        </div>

        <div className="h-28 w-full max-w-sm">
          <BarVisualizer
            state={agentState}
            trackRef={visualizerTrack}
            barCount={7}
            className="h-full w-full"
          />
        </div>
      </div>

      <RoomAudioRenderer />
      <VoiceAssistantControlBar />
    </div>
  );
}

export default function CallPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug;
  const [session, setSession] = useState<WebCallSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    startWebCall(slug)
      .then((s) => {
        if (cancelled) return;
        if (s.provider === 'daily') {
          window.location.href = `${s.url}?t=${s.token}`;
          return;
        }
        setSession(s);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err?.response?.data?.detail ?? 'This call link is unavailable.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (error) {
    return (
      <Screen>
        <div className="flex size-20 items-center justify-center rounded-full bg-neutral-800 ring-1 ring-neutral-700">
          <PhoneOff className="size-8 text-neutral-300" strokeWidth={1.5} />
        </div>
        <div className="text-lg font-medium">Unable to join</div>
        <div className="text-sm text-neutral-400">{error}</div>
      </Screen>
    );
  }

  if (ended) {
    return <CallEnded />;
  }

  if (loading || !session) {
    return (
      <Screen>
        <div className="text-sm text-neutral-300">Connecting…</div>
      </Screen>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={session.url}
      token={session.token}
      connect
      audio
      video={false}
      onDisconnected={() => setEnded(true)}
      className="h-screen"
    >
      <CallStage onStale={() => setEnded(true)} />
    </LiveKitRoom>
  );
}
