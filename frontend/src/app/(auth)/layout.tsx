'use client';

import { Mic, ShieldCheck, Zap } from 'lucide-react';
import { motion, useMotionValue, useSpring, useTransform, type MotionValue } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';

import { Logo } from '@/components/ui/logo';
import { ThemeToggle } from '@/components/shared';
import { AgentFlowAnimation } from '@/components/auth/agent-flow-animation';

const STATS = [
  { icon: Mic, value: '50+', label: 'Voice models' },
  { icon: Zap, value: '<500ms', label: 'Latency' },
  { icon: ShieldCheck, value: '99.9%', label: 'Uptime' },
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="flex min-h-screen">
      <div className="flex w-full flex-col lg:w-[50%] bg-background border-r border-border">
        <motion.div
          className="flex items-center justify-between p-6"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          <Logo size="md" />
          <ThemeToggle />
        </motion.div>

        <div className="flex flex-1 items-center justify-center px-8 pb-12">
          <motion.div
            key={pathname}
            className="w-full max-w-[400px]"
            initial="hidden"
            animate="visible"
            variants={{
              hidden: { opacity: 0 },
              visible: {
                opacity: 1,
                transition: { staggerChildren: 0.08, delayChildren: 0.1 },
              },
            }}
          >
            {children}
          </motion.div>
        </div>
      </div>

      <BrandedPanel />
    </div>
  );
}

const PROBE_LABELS = [
  'stt.transcript',
  'llm.tokens',
  'tts.synth',
  'voice.latency',
  'channel.bridge',
  'pipe.healthy',
];

function pseudoHex(seed: number): string {
  const v = (seed * 9301 + 49297) % 233280 >>> 0;
  return v.toString(16).padStart(4, '0').slice(-4);
}

function BrandedPanel() {
  const panelRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0.5);
  const mouseY = useMotionValue(0.4);
  const leadX = useSpring(mouseX, { stiffness: 120, damping: 22, mass: 0.6 });
  const leadY = useSpring(mouseY, { stiffness: 120, damping: 22, mass: 0.6 });
  const parallaxX = useTransform(leadX, [0, 1], [-10, 10]);
  const parallaxY = useTransform(leadY, [0, 1], [-6, 6]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = panelRef.current?.getBoundingClientRect();
    if (!rect) return;
    mouseX.set((e.clientX - rect.left) / rect.width);
    mouseY.set((e.clientY - rect.top) / rect.height);
  };

  return (
    <div
      ref={panelRef}
      onMouseMove={handleMouseMove}
      className="hidden lg:flex lg:w-[50%] relative flex-col items-center justify-center overflow-hidden bg-gradient-to-br from-[#1a1040] via-[#2d1b69] to-[#1a1040] px-12 pt-10 pb-32"
    >
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-primary/20 blur-[150px]" />

      <ScannerProbe mouseX={mouseX} mouseY={mouseY} />

      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)',
          backgroundSize: '28px 28px',
        }}
      />

      <motion.div
        className="relative z-10 mb-4 w-full flex justify-center"
        style={{ x: parallaxX, y: parallaxY }}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
      >
        <AgentFlowAnimation />
      </motion.div>

      <motion.div
        className="relative z-10 text-center max-w-xl px-4"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.12, delayChildren: 0.3 } },
        }}
      >
        <h1 className="font-display text-[clamp(2rem,4vw,3.25rem)] font-semibold leading-[1.05] tracking-[-0.02em] text-white">
          <motion.span
            className="block text-white"
            variants={{
              hidden: { opacity: 0, y: 18, filter: 'blur(8px)' },
              visible: {
                opacity: 1,
                y: 0,
                filter: 'blur(0px)',
                transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
              },
            }}
          >
            Build AI Agents
          </motion.span>
          <motion.span
            className="block"
            variants={{
              hidden: { opacity: 0, y: 18, filter: 'blur(8px)' },
              visible: {
                opacity: 1,
                y: 0,
                filter: 'blur(0px)',
                transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
              },
            }}
          >
            <span className="bg-gradient-to-r from-violet-200 via-violet-100 to-fuchsia-200 bg-clip-text text-transparent">
              That Sound Human
            </span>
          </motion.span>
        </h1>
        <motion.p
          className="mt-4 text-[13.5px] leading-relaxed text-white/60 max-w-md mx-auto"
          variants={{
            hidden: { opacity: 0, y: 10 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
          }}
        >
          Create, deploy, and manage intelligent voice agents with configurable LLM, STT, and TTS
          pipelines.
        </motion.p>
      </motion.div>

      <motion.div
        className="relative z-10 mt-7 grid w-full max-w-[480px] grid-cols-3 gap-3"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.1, delayChildren: 0.6 } },
        }}
      >
        {STATS.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </motion.div>

      <motion.div
        className="relative z-10 mt-5 flex items-center justify-center gap-6 text-[10px] uppercase tracking-widest text-white/25"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.12, delayChildren: 0.9 } },
        }}
      >
        {['Trusted by 1,000+ teams', 'divider', 'SOC 2 compliant', 'divider', '99.9% uptime'].map(
          (item, i) =>
            item === 'divider' ? (
              <motion.span
                key={i}
                className="h-3 w-px bg-white/10"
                variants={{
                  hidden: { opacity: 0, scaleY: 0 },
                  visible: { opacity: 1, scaleY: 1, transition: { duration: 0.3 } },
                }}
              />
            ) : (
              <motion.span
                key={i}
                variants={{
                  hidden: { opacity: 0, x: -6 },
                  visible: { opacity: 1, x: 0, transition: { duration: 0.4 } },
                }}
              >
                {item}
              </motion.span>
            ),
        )}
      </motion.div>
    </div>
  );
}

function ScannerProbe({
  mouseX,
  mouseY,
}: {
  mouseX: MotionValue<number>;
  mouseY: MotionValue<number>;
}) {
  const probeX = useSpring(mouseX, { stiffness: 220, damping: 24 });
  const probeY = useSpring(mouseY, { stiffness: 220, damping: 24 });
  const haloX = useSpring(mouseX, { stiffness: 90, damping: 28 });
  const haloY = useSpring(mouseY, { stiffness: 90, damping: 28 });

  const left = useTransform(probeX, (v) => `${v * 100}%`);
  const top = useTransform(probeY, (v) => `${v * 100}%`);
  const haloLeft = useTransform(haloX, (v) => `${v * 100}%`);
  const haloTop = useTransform(haloY, (v) => `${v * 100}%`);

  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1800);
    return () => clearInterval(id);
  }, []);
  const label = PROBE_LABELS[tick % PROBE_LABELS.length];
  const traceId = pseudoHex(tick + 1);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <motion.div
        className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full bg-violet-400/15 blur-2xl"
        style={{ left: haloLeft, top: haloTop, width: 220, height: 220 }}
      />

      <motion.div className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left, top }}>
        <motion.div
          key={tick}
          className="rounded-full border border-violet-300/40"
          initial={{ width: 8, height: 8, opacity: 0.6 }}
          animate={{ width: 220, height: 220, opacity: 0 }}
          transition={{ duration: 1.8, ease: 'easeOut' }}
          style={{ marginLeft: -110, marginTop: -110 }}
        />
      </motion.div>

      <motion.div className="absolute" style={{ left, top, x: '-50%', y: '-50%' }}>
        <svg width={48} height={48} viewBox="0 0 48 48" className="text-violet-300/70" fill="none">
          <path
            d="M6 14 L6 6 L14 6"
            stroke="currentColor"
            strokeWidth={1.2}
            strokeLinecap="round"
          />
          <path
            d="M34 6 L42 6 L42 14"
            stroke="currentColor"
            strokeWidth={1.2}
            strokeLinecap="round"
          />
          <path
            d="M6 34 L6 42 L14 42"
            stroke="currentColor"
            strokeWidth={1.2}
            strokeLinecap="round"
          />
          <path
            d="M34 42 L42 42 L42 34"
            stroke="currentColor"
            strokeWidth={1.2}
            strokeLinecap="round"
          />
          <circle cx={24} cy={24} r={1.5} fill="currentColor" />
          <line x1={24} y1={16} x2={24} y2={20} stroke="currentColor" strokeWidth={1} />
          <line x1={24} y1={28} x2={24} y2={32} stroke="currentColor" strokeWidth={1} />
          <line x1={16} y1={24} x2={20} y2={24} stroke="currentColor" strokeWidth={1} />
          <line x1={28} y1={24} x2={32} y2={24} stroke="currentColor" strokeWidth={1} />
        </svg>
      </motion.div>

      <motion.div className="absolute" style={{ left, top, x: 32, y: 12 }}>
        <div className="flex items-center gap-1.5 rounded-md border border-violet-300/25 bg-violet-950/40 px-2 py-1 backdrop-blur-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-mono text-[10px] text-violet-100/80">
            {label}
            <span className="text-violet-300/60"> · 0x{traceId}</span>
          </span>
        </div>
      </motion.div>
    </div>
  );
}

function StatCard({ stat }: { stat: (typeof STATS)[number] }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const tiltX = useMotionValue(0);
  const tiltY = useMotionValue(0);
  const springTiltX = useSpring(tiltX, { stiffness: 220, damping: 18 });
  const springTiltY = useSpring(tiltY, { stiffness: 220, damping: 18 });
  const rotateX = useTransform(springTiltY, [-1, 1], [8, -8]);
  const rotateY = useTransform(springTiltX, [-1, 1], [-8, 8]);

  const handleMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    tiltX.set(px * 2);
    tiltY.set(py * 2);
  };
  const handleLeave = () => {
    tiltX.set(0);
    tiltY.set(0);
  };

  return (
    <motion.div
      ref={cardRef}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
        },
      }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      style={{
        rotateX,
        rotateY,
        transformPerspective: 800,
        transformStyle: 'preserve-3d',
      }}
      className="group relative flex flex-col items-center justify-center gap-1 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-5 min-w-0 cursor-default text-center backdrop-blur-sm transition-colors hover:border-white/20 hover:bg-white/[0.06]"
    >
      <div
        className="mb-1.5 flex h-7 w-7 items-center justify-center rounded-lg bg-white/[0.06] ring-1 ring-white/10"
        style={{ transform: 'translateZ(20px)' }}
      >
        <stat.icon className="h-3.5 w-3.5 text-violet-200" />
      </div>
      <span
        className="font-display text-[22px] font-semibold leading-none tracking-tight text-white"
        style={{ transform: 'translateZ(30px)' }}
      >
        {stat.value}
      </span>
      <span
        className="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/45"
        style={{ transform: 'translateZ(15px)' }}
      >
        {stat.label}
      </span>
    </motion.div>
  );
}
