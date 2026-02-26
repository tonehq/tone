import { Mic, Shield, Zap } from 'lucide-react';
import React, { memo } from 'react';

import Logo from '@/components/shared/Logo';

interface ContainerProps {
  children: React.ReactNode;
}

const AUDIO_BAR_COUNT = 12;

const FEATURES = [
  { icon: Mic, value: '50+', label: 'Voice Models' },
  { icon: Zap, value: '<500ms', label: 'Latency' },
  { icon: Shield, value: '99.9%', label: 'Uptime' },
] as const;

const Container = memo(({ children }: ContainerProps) => (
  <div className="flex min-h-screen">
    {/* ── Left Side — Form ───────────────────────────────────────── */}
    <div className="relative flex flex-1 flex-col bg-background">
      <header className="absolute left-6 top-6 z-10 md:left-8 md:top-8">
        <Logo className="h-12" showTagline />
      </header>

      <div className="flex flex-1 items-center justify-center px-6">{children}</div>
    </div>

    {/* ── Right Side — Branding ──────────────────────────────────── */}
    <div
      className="relative hidden flex-1 overflow-hidden md:flex"
      style={{
        background: 'linear-gradient(145deg, #1e1b4b 0%, #312e81 35%, #4338ca 65%, #6d28d9 100%)',
      }}
    >
      {/* Dot grid overlay */}
      <div
        className="absolute inset-0"
        aria-hidden="true"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />

      {/* Floating orbs */}
      <div
        className="absolute -left-24 -top-24 size-[400px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%)',
          animation: 'auth-float-1 18s ease-in-out infinite',
        }}
      />
      <div
        className="absolute -bottom-32 -right-24 size-[500px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(139,92,246,0.2) 0%, transparent 70%)',
          animation: 'auth-float-2 22s ease-in-out infinite',
        }}
      />
      <div
        className="absolute left-[30%] top-[20%] size-[300px] rounded-full"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
          animation: 'auth-float-3 15s ease-in-out infinite',
        }}
      />

      {/* Centered content */}
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center p-12">
        {/* Voice waveform visualization */}
        <div className="mb-10 flex items-end gap-[3px]" aria-hidden="true">
          {Array.from({ length: AUDIO_BAR_COUNT }).map((_, i) => (
            <div
              key={i}
              className="w-[3px] origin-bottom rounded-full"
              style={{
                height: '28px',
                backgroundColor: 'rgba(255, 255, 255, 0.5)',
                animation: `audio-bar 1.4s ease-in-out ${i * 0.1}s infinite`,
              }}
            />
          ))}
        </div>

        {/* Headline */}
        <h1 className="mb-4 text-center text-[2.75rem] font-bold leading-[1.1] tracking-tight text-white">
          Build Voice AI Agents
          <br />
          That Sound Human
        </h1>

        {/* Subtitle */}
        <p className="mb-12 max-w-sm text-center text-[15px] leading-relaxed text-white/60">
          Create, deploy, and manage intelligent voice agents in minutes — not months.
        </p>

        {/* Feature stats — glassmorphism cards */}
        <div className="flex gap-4">
          {FEATURES.map((feature) => (
            <div
              key={feature.label}
              className="flex-1 rounded-xl border border-white/[0.08] p-5 text-center"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                backdropFilter: 'blur(16px)',
              }}
            >
              <div className="mx-auto mb-3 flex size-10 items-center justify-center rounded-lg bg-white/[0.1]">
                <feature.icon className="size-5 text-white/80" />
              </div>
              <div className="text-2xl font-bold text-white">{feature.value}</div>
              <div className="mt-1 text-xs text-white/50">{feature.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Trust indicators — pinned to bottom */}
      <div className="absolute inset-x-0 bottom-0 z-10 flex items-center justify-center gap-3 p-6 text-[11px] font-medium tracking-wider text-white/30 uppercase">
        <span>Trusted by 1,000+ teams</span>
        <span aria-hidden="true" className="text-white/15">
          &middot;
        </span>
        <span>SOC 2 Compliant</span>
        <span aria-hidden="true" className="text-white/15">
          &middot;
        </span>
        <span>99.9% Uptime</span>
      </div>
    </div>
  </div>
));

Container.displayName = 'Container';

export default memo(Container);
