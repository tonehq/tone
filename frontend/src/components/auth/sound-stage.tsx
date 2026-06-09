'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';

import { Logo } from '@/components/ui/logo';

function Line({ children, delay }: { children: React.ReactNode; delay: number }) {
  return (
    <span className="block overflow-hidden">
      <motion.span
        className="block"
        initial={{ y: '110%' }}
        animate={{ y: '0%' }}
        transition={{ delay, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.span>
    </span>
  );
}

/** Monospace SMPTE-style timecode, ticking like a studio transport. */
function Timecode() {
  const [t, setT] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setT((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const hh = String(Math.floor(t / 3600) % 24).padStart(2, '0');
  const mm = String(Math.floor(t / 60) % 60).padStart(2, '0');
  const ss = String(t % 60).padStart(2, '0');
  return <span className="tabular-nums text-white/55">{`${hh}:${mm}:${ss}`}</span>;
}

/** Continuous oscilloscope line + faint mirror, rendered on canvas. */
function Oscilloscope() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduce =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    let raf = 0;
    let width = 0;
    let height = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const draw = (time: number) => {
      const t = time / 1000;
      ctx.clearRect(0, 0, width, height);
      const mid = height / 2;

      // sample the composite signal once so the line + mirror agree
      const step = 2;
      const points: Array<[number, number]> = [];
      for (let x = 0; x <= width; x += step) {
        const phase = x / width;
        // envelope: a single travelling "utterance" packet across the line
        const env =
          0.35 +
          0.65 * Math.exp(-Math.pow((phase - ((t * 0.18) % 1.4) + 0.2) * 3.2, 2)) +
          0.12 * Math.sin(phase * 3 + t);
        const y =
          Math.sin(phase * 26 + t * 4) * 0.55 +
          Math.sin(phase * 61 - t * 2.3) * 0.28 +
          Math.sin(phase * 9 + t * 1.4) * 0.22;
        points.push([x, mid + y * env * (height * 0.34)]);
      }

      // faint mirror
      ctx.beginPath();
      points.forEach(([x, y], i) => {
        const my = mid - (y - mid);
        if (i === 0) ctx.moveTo(x, my);
        else ctx.lineTo(x, my);
      });
      ctx.strokeStyle = 'rgba(99,102,241,0.14)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // main line with glow
      ctx.beginPath();
      points.forEach(([x, y], i) => {
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.shadowColor = 'rgba(99,102,241,0.5)';
      ctx.shadowBlur = 12;
      ctx.strokeStyle = 'rgba(129,140,248,0.95)';
      ctx.lineWidth = 1.75;
      ctx.lineJoin = 'round';
      ctx.stroke();
      ctx.shadowBlur = 0;

      // playhead — a sweeping amber tick
      const px = ((t * 0.18) % 1.4) - 0.2;
      if (px >= 0 && px <= 1) {
        const x = px * width;
        const yi = Math.min(points.length - 1, Math.round(x / step));
        const y = points[yi]?.[1] ?? mid;
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#fbbf24';
        ctx.shadowColor = 'rgba(251,191,36,0.8)';
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      if (!reduce) raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="relative">
      <canvas ref={canvasRef} className="h-24 w-full" />
      {/* baseline */}
      <div className="absolute left-0 right-0 top-1/2 h-px bg-white/[0.06]" />
    </div>
  );
}

function GrainOverlay() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 opacity-[0.25] mix-blend-soft-light"
      style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      }}
    />
  );
}

/**
 * SoundStage — the visual half of the auth experience.
 *
 * A recording-studio canvas: a living oscilloscope waveform (the product's
 * "tone"), a blueprint grid, film grain, and monospace studio chrome. The
 * waveform is drawn on <canvas> with requestAnimationFrame so it breathes
 * continuously without thrashing React.
 */
export function SoundStage() {
  return (
    <div className="relative hidden h-full flex-col justify-between overflow-hidden bg-[#08090b] px-12 pb-12 pt-8 lg:flex lg:w-[54%]">
      {/* blueprint grid */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.5]"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
          maskImage: 'radial-gradient(120% 120% at 50% 40%, black 30%, transparent 85%)',
        }}
      />
      {/* single, restrained indigo bloom — far from a full gradient wash */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-32 top-1/3 h-[460px] w-[460px] rounded-full bg-indigo-500/10 blur-[140px]"
      />
      {/* film grain */}
      <GrainOverlay />

      {/* ── top chrome: timecode + LIVE ───────────────────────────────── */}
      <motion.div
        className="relative z-10 flex items-center justify-between"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <Logo size="md" inverted />
        <div className="flex items-center gap-2 font-mono text-[11px] tracking-wider text-white/40">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
          </span>
          <span>LIVE</span>
          <Timecode />
        </div>
      </motion.div>

      {/* ── editorial headline + oscilloscope ─────────────────────────── */}
      <div className="relative z-10 max-w-[34rem]">
        <motion.p
          className="mb-6 font-mono text-[11px] uppercase tracking-[0.32em] text-indigo-300/70"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          Tone — Voice OS
        </motion.p>

        <h1
          className="text-[clamp(2.6rem,4.4vw,4rem)] font-semibold leading-[0.98] tracking-[-0.03em] text-white"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          {['Give your', 'product', 'a voice that'].map((line, i) => (
            <Line key={line} delay={0.28 + i * 0.09}>
              {line}
            </Line>
          ))}
          <Line delay={0.55}>
            <span className="text-indigo-400">listens back.</span>
          </Line>
        </h1>

        <motion.div
          className="mt-9"
          initial={{ opacity: 0, scaleX: 0.96 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 0.7, duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          style={{ transformOrigin: 'left' }}
        >
          <Oscilloscope />
        </motion.div>
      </div>

      {/* ── bottom spec line ──────────────────────────────────────────── */}
      <motion.div
        className="relative z-10 flex items-center gap-5 font-mono text-[11px] text-white/35"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9, duration: 0.6 }}
      >
        {['50+ voices', 'sub-500ms latency', '99.9% uptime', 'SOC 2'].map((spec, i) => (
          <span key={spec} className="flex items-center gap-5">
            {i > 0 && <span className="h-3 w-px bg-white/10" />}
            {spec}
          </span>
        ))}
      </motion.div>
    </div>
  );
}
