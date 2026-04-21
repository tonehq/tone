'use client';

import CustomButton from '@/components/shared/CustomButton';
import Logo from '@/components/shared/Logo';
import { ArrowLeft, Home } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useMemo } from 'react';

export default function NotFound() {
  const router = useRouter();

  // Pre-compute wave bar heights — smooth bell curve
  const waveHeights = useMemo(() => {
    const count = 48;
    const heights: number[] = [];
    for (let i = 0; i < count; i++) {
      const t = i / (count - 1); // 0..1
      const bell = Math.exp(-Math.pow((t - 0.5) * 3.2, 2));
      const h = 4 + bell * 28;
      heights.push(h);
    }
    return heights;
  }, []);

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-6">
      {/* Background: soft center glow */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 45% at 50% 48%, hsl(var(--primary) / 0.03) 0%, transparent 100%)',
        }}
      />

      {/* Floating orbs — very faint */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="nf-orb nf-orb-1" />
        <div className="nf-orb nf-orb-2" />
      </div>

      {/* Logo — fixed top */}
      <div className="nf-entrance absolute left-1/2 top-8 -translate-x-1/2">
        <Logo showTagline={false} />
      </div>

      {/* Main centered block */}
      <div className="relative z-10 flex flex-col items-center text-center">
        {/* 404 number */}
        <div className="relative mb-6 select-none" aria-hidden="true">
          <span className="nf-404">404</span>
        </div>

        {/* Waveform — standalone, below the number */}
        <div className="nf-waveform mb-8" aria-hidden="true">
          {waveHeights.map((h, i) => (
            <div
              key={i}
              className="nf-wave-bar"
              style={
                {
                  '--bar-h': `${h}px`,
                  animationDelay: `${i * 0.05}s`,
                } as React.CSSProperties
              }
            />
          ))}
        </div>

        {/* Copy */}
        <h1
          className="nf-entrance mb-2 text-xl font-semibold tracking-tight text-foreground"
          style={{ animationDelay: '0.12s' }}
        >
          Page not found
        </h1>
        <p
          className="nf-entrance mb-8 max-w-xs text-sm leading-relaxed text-muted-foreground"
          style={{ animationDelay: '0.2s' }}
        >
          This page doesn&apos;t exist or has been moved.
        </p>

        {/* Actions */}
        <div className="nf-entrance flex items-center gap-3" style={{ animationDelay: '0.28s' }}>
          <CustomButton type="default" icon={<ArrowLeft size={16} />} onClick={() => router.back()}>
            Go back
          </CustomButton>
          <CustomButton
            type="primary"
            icon={<Home size={16} />}
            onClick={() => router.push('/home')}
          >
            Home
          </CustomButton>
        </div>
      </div>

      <style jsx>{`
        /* ── Entrance ──────────────────────────────────────── */
        .nf-entrance {
          opacity: 0;
          transform: translateY(10px);
          animation: nf-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
        }

        @keyframes nf-rise {
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* ── 404 ───────────────────────────────────────────── */
        .nf-404 {
          display: block;
          font-family: var(--font-mono), ui-monospace, monospace;
          font-size: clamp(96px, 16vw, 160px);
          font-weight: 800;
          line-height: 1;
          letter-spacing: -0.05em;
          background: linear-gradient(
            160deg,
            hsl(268 55% 58%) 0%,
            hsl(268 40% 62%) 45%,
            hsl(38 85% 55%) 100%
          );
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          opacity: 0;
          transform: translateY(14px);
          animation: nf-rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.04s forwards;
        }

        /* ── Waveform ──────────────────────────────────────── */
        .nf-waveform {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 3px;
          opacity: 0;
          animation: nf-fade-in 0.6s ease 0.3s forwards;
        }

        @keyframes nf-fade-in {
          to {
            opacity: 1;
          }
        }

        .nf-wave-bar {
          width: 2.5px;
          height: var(--bar-h, 8px);
          border-radius: 9999px;
          background: hsl(var(--primary) / 0.25);
          transform-origin: center;
          animation: nf-pulse 2s ease-in-out infinite alternate;
        }

        @keyframes nf-pulse {
          0% {
            transform: scaleY(0.45);
            opacity: 0.35;
          }
          100% {
            transform: scaleY(1);
            opacity: 1;
          }
        }

        /* ── Orbs ──────────────────────────────────────────── */
        .nf-orb {
          position: absolute;
          border-radius: 50%;
          filter: blur(100px);
        }

        .nf-orb-1 {
          width: 320px;
          height: 320px;
          top: 10%;
          right: 5%;
          background: hsl(268 47% 54% / 0.04);
          animation: nf-drift 22s ease-in-out infinite;
        }

        .nf-orb-2 {
          width: 260px;
          height: 260px;
          bottom: 10%;
          left: 8%;
          background: hsl(38 85% 55% / 0.03);
          animation: nf-drift 18s ease-in-out infinite reverse;
        }

        @keyframes nf-drift {
          0%,
          100% {
            transform: translate(0, 0);
          }
          50% {
            transform: translate(15px, -10px);
          }
        }
      `}</style>
    </div>
  );
}
