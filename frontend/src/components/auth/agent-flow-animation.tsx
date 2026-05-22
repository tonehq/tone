'use client';

import { motion } from 'framer-motion';
import { AudioLines, Headphones, Mic, Sparkles, Waves } from 'lucide-react';

const BAR_COUNT = 28;
const BAR_HEIGHTS = Array.from({ length: BAR_COUNT }, (_, i) => {
  // Procedural but stable heights — taller toward the centre, shorter at edges.
  const t = i / (BAR_COUNT - 1);
  const bell = 1 - Math.pow(2 * t - 1, 2); // 0..1, peaks in the middle
  const jitter = Math.sin(i * 12.9898) * 43758.5453;
  const noise = (jitter - Math.floor(jitter)) * 0.5;
  return 0.25 + bell * 0.55 + noise * 0.2;
});

interface OrbitIcon {
  Icon: typeof Mic;
  // Position is expressed as offsets from the central plate, in pixels.
  x: number;
  y: number;
  delay: number;
  size?: number;
}

const ORBIT_ICONS: OrbitIcon[] = [
  { Icon: Mic, x: -118, y: -78, delay: 0.2 },
  { Icon: Headphones, x: 118, y: -64, delay: 0.45 },
  { Icon: Sparkles, x: -132, y: 64, delay: 0.65, size: 14 },
  { Icon: AudioLines, x: 128, y: 78, delay: 0.85 },
  { Icon: Waves, x: 0, y: -132, delay: 1.05, size: 14 },
];

export function AgentFlowAnimation() {
  return (
    <div className="relative mx-auto flex h-[240px] w-full max-w-[440px] items-center justify-center">
      {/* Faint concentric rings that pulse outward */}
      <PulseRing delay={0} />
      <PulseRing delay={0.6} />
      <PulseRing delay={1.2} />

      {/* Floating accent icons */}
      {ORBIT_ICONS.map(({ Icon, x, y, delay, size = 16 }, idx) => (
        <motion.div
          key={idx}
          className="absolute flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] backdrop-blur-md"
          style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)` }}
          initial={{ opacity: 0, scale: 0.7, x: '-50%', y: '-50%' }}
          animate={{ opacity: 1, scale: 1, x: '-50%', y: '-50%' }}
          transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
        >
          <motion.div
            animate={{ y: [0, -3, 0] }}
            transition={{
              duration: 3 + idx * 0.4,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: idx * 0.3,
            }}
            className="text-white/65"
          >
            <Icon style={{ width: size, height: size }} />
          </motion.div>
        </motion.div>
      ))}

      {/* Centre stack: glyph plate + waveform */}
      <motion.div
        className="relative z-10 flex flex-col items-center"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
      >
        <Glyph />
        <Waveform />
      </motion.div>
    </div>
  );
}

function PulseRing({ delay }: { delay: number }) {
  return (
    <motion.span
      className="absolute h-[260px] w-[260px] rounded-full border border-white/10"
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: [0, 0.45, 0], scale: [0.7, 1.25, 1.55] }}
      transition={{ duration: 3.6, repeat: Infinity, ease: 'easeOut', delay }}
    />
  );
}

function Glyph() {
  return (
    <motion.div
      className="relative flex h-[84px] w-[84px] items-center justify-center rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.02] shadow-[0_24px_48px_-12px_rgba(124,58,237,0.55)] backdrop-blur-xl"
      animate={{ y: [0, -4, 0] }}
      transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
    >
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-400/20 via-transparent to-fuchsia-400/10" />
      <ToneGlyph />
      <motion.span
        className="absolute -inset-1 rounded-[20px] border border-violet-300/30"
        animate={{ opacity: [0.2, 0.6, 0.2] }}
        transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
      />
    </motion.div>
  );
}

/**
 * Tone glyph — a stylised mark that reads as "voice / AI" rather than a
 * literal icon. Two stacked sound-curves with a centred AI sparkle.
 */
function ToneGlyph() {
  return (
    <svg
      width={36}
      height={36}
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="tone-glyph-stroke" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stopColor="#E9D5FF" />
          <stop offset="100%" stopColor="#C4B5FD" />
        </linearGradient>
      </defs>
      <path
        d="M6 18 C 10 12, 14 12, 18 18 C 22 24, 26 24, 30 18"
        stroke="url(#tone-glyph-stroke)"
        strokeWidth={1.6}
        strokeLinecap="round"
      />
      <path
        d="M6 24 C 10 20, 14 20, 18 24 C 22 28, 26 28, 30 24"
        stroke="url(#tone-glyph-stroke)"
        strokeWidth={1.4}
        strokeLinecap="round"
        opacity={0.55}
      />
      <path
        d="M18 5 C 18 8.5, 16 10.5, 12.5 10.5 C 16 10.5, 18 12.5, 18 16 C 18 12.5, 20 10.5, 23.5 10.5 C 20 10.5, 18 8.5, 18 5 Z"
        fill="url(#tone-glyph-stroke)"
      />
    </svg>
  );
}

function Waveform() {
  return (
    <div className="mt-5 flex h-[36px] items-center justify-center gap-[3px]" aria-hidden="true">
      {BAR_HEIGHTS.map((h, i) => {
        const isCenter = Math.abs(i - BAR_COUNT / 2) < 4;
        return (
          <motion.span
            key={i}
            className={
              isCenter
                ? 'w-[3px] rounded-full bg-gradient-to-b from-violet-200 to-violet-400'
                : 'w-[3px] rounded-full bg-white/35'
            }
            initial={{ scaleY: h * 0.4 }}
            animate={{
              scaleY: [h * 0.45, h, h * 0.55, h * 0.85, h * 0.4],
            }}
            transition={{
              duration: 1.6 + (i % 5) * 0.18,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: (i % 7) * 0.07,
            }}
            style={{
              height: '100%',
              transformOrigin: 'center',
            }}
          />
        );
      })}
    </div>
  );
}
