import { Bot, BrainCircuit, Mic, Shield, Sparkles, Zap } from 'lucide-react';
import React, { memo } from 'react';

import Logo from '@/components/shared/Logo';
import { ThemeToggle } from '@/components/shared/ThemeToggle';

interface ContainerProps {
  children: React.ReactNode;
}

const AUDIO_BAR_COUNT = 12;

const FEATURES = [
  { icon: Bot, value: '50+', label: 'Voice Models' },
  { icon: Zap, value: '<500ms', label: 'Latency' },
  { icon: Shield, value: '99.9%', label: 'Uptime' },
] as const;

const Container = memo(({ children }: ContainerProps) => (
  <div className="flex min-h-screen">
    {/* ── Left Side — Form ───────────────────────────────────────── */}
    <div className="relative flex flex-1 flex-col bg-background">
      <header className="absolute left-6 top-6 z-10 flex w-[calc(100%-3rem)] items-center justify-between md:left-8 md:top-8 md:w-[calc(100%-4rem)]">
        <Logo className="h-12" showTagline />
        <ThemeToggle />
      </header>

      <div className="flex flex-1 items-center justify-center px-6">{children}</div>
    </div>

    {/* ── Right Side — Branding ──────────────────────────────────── */}
    <div
      className="relative hidden flex-1 overflow-hidden md:flex"
      style={{
        background: 'linear-gradient(145deg, #0e0e0f 0%, #1a1035 30%, #2d1b69 60%, #4c1d95 100%)',
      }}
    >
      {/* Dot grid overlay */}
      <div
        className="absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px)',
          backgroundSize: '32px 32px',
        }}
      />

      {/* Floating orbs */}
      <div
        className="absolute -left-24 -top-24 size-[400px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(129,74,200,0.15) 0%, transparent 70%)',
          animation: 'auth-float-1 18s ease-in-out infinite',
        }}
      />
      <div
        className="absolute -bottom-32 -right-24 size-[500px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%)',
          animation: 'auth-float-2 22s ease-in-out infinite',
        }}
      />
      <div
        className="absolute left-[30%] top-[20%] size-[300px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(223,122,254,0.08) 0%, transparent 70%)',
          animation: 'auth-float-3 15s ease-in-out infinite',
        }}
      />

      {/* Centered content */}
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center p-12">
        {/* AI Agent visual — neural network nodes */}
        <div className="relative mb-10" aria-hidden="true">
          <div className="relative flex items-center justify-center">
            {/* Central brain icon */}
            <div className="flex size-16 items-center justify-center rounded-2xl border border-white/[0.08] bg-white/[0.06] backdrop-blur-sm">
              <BrainCircuit className="size-8 text-white/80" />
            </div>
            {/* Orbiting satellites */}
            <div
              className="absolute -left-10 -top-6 flex size-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.04]"
              style={{ animation: 'pulse-ring 3s ease-in-out infinite' }}
            >
              <Mic className="size-4 text-white/60" />
            </div>
            <div
              className="absolute -right-10 -top-4 flex size-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.04]"
              style={{ animation: 'pulse-ring 3s ease-in-out 0.5s infinite' }}
            >
              <Sparkles className="size-4 text-white/60" />
            </div>
            <div
              className="absolute -bottom-6 -right-8 flex size-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.04]"
              style={{ animation: 'pulse-ring 3s ease-in-out 1s infinite' }}
            >
              <Bot className="size-4 text-white/60" />
            </div>
          </div>
        </div>

        {/* Voice waveform visualization */}
        <div className="mb-8 flex items-end gap-[3px]" aria-hidden="true">
          {Array.from({ length: AUDIO_BAR_COUNT }).map((_, i) => (
            <div
              key={i}
              className="w-[3px] origin-bottom rounded-full"
              style={{
                height: '24px',
                backgroundColor: 'rgba(255, 255, 255, 0.35)',
                animation: `audio-bar 1.4s ease-in-out ${i * 0.1}s infinite`,
              }}
            />
          ))}
        </div>

        {/* Headline */}
        <h1 className="mb-4 text-center text-[2.5rem] font-bold leading-[1.1] tracking-tight text-white">
          Build AI Agents
          <br />
          That Sound Human
        </h1>

        {/* Subtitle */}
        <p className="mb-12 max-w-sm text-center text-[15px] leading-relaxed text-white/50">
          Create, deploy, and manage intelligent voice agents with configurable LLM, STT, and TTS
          pipelines.
        </p>

        {/* Feature stats — glassmorphism cards */}
        <div className="flex gap-4">
          {FEATURES.map((feature) => (
            <div
              key={feature.label}
              className="flex-1 rounded-xl border border-white/[0.06] p-5 text-center transition-colors hover:border-white/[0.12]"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                backdropFilter: 'blur(16px)',
              }}
            >
              <div className="mx-auto mb-3 flex size-10 items-center justify-center rounded-lg bg-white/[0.06]">
                <feature.icon className="size-5 text-white/70" />
              </div>
              <div className="text-2xl font-bold text-white">{feature.value}</div>
              <div className="mt-1 text-xs text-white/40">{feature.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Trust indicators — pinned to bottom */}
      <div className="absolute inset-x-0 bottom-0 z-10 flex items-center justify-center gap-3 p-6 text-[11px] font-medium tracking-wider text-white/25 uppercase">
        <span>Trusted by 1,000+ teams</span>
        <span aria-hidden="true" className="text-white/10">
          &middot;
        </span>
        <span>SOC 2 Compliant</span>
        <span aria-hidden="true" className="text-white/10">
          &middot;
        </span>
        <span>99.9% Uptime</span>
      </div>
    </div>
  </div>
));

Container.displayName = 'Container';

export default memo(Container);
