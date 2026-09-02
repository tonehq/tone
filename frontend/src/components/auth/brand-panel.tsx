'use client';

import { motion } from 'framer-motion';

import { Logo } from '@/components/ui/logo';
import { BrandWaveform } from '@/components/shared';

function Reveal({ children, delay }: { children: React.ReactNode; delay: number }) {
  return (
    <span className="block overflow-hidden">
      <motion.span
        className="block"
        initial={{ y: '108%' }}
        animate={{ y: '0%' }}
        transition={{ delay, duration: 0.75, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.span>
    </span>
  );
}

export function BrandPanel() {
  return (
    <div className="relative hidden overflow-hidden bg-brand-field lg:flex lg:flex-col">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 grid grid-cols-4 opacity-[0.16]"
      >
        <span className="border-r border-white" />
        <span className="border-r border-white" />
        <span className="border-r border-white" />
      </div>

      <motion.div
        className="relative z-10 flex items-center justify-between gap-6 px-10 pt-8 xl:px-14"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <Logo size="md" inverted />
        <p className="font-mono text-[11px] uppercase tracking-[0.34em] text-white/55">
          Voice agent platform
        </p>
      </motion.div>

      <div className="relative z-10 flex flex-1 flex-col justify-center px-10 xl:px-14">
        <h1 className="font-display text-[clamp(2.9rem,5vw,4.5rem)] font-semibold leading-[0.94] tracking-[-0.04em] text-white">
          {['Give your', 'product'].map((line, i) => (
            <Reveal key={line} delay={0.16 + i * 0.08}>
              {line}
            </Reveal>
          ))}
          <Reveal delay={0.32}>
            <span className="text-white/55">a voice.</span>
          </Reveal>
        </h1>

        <motion.p
          className="mt-8 max-w-[26rem] border-t border-white/25 pt-6 text-[13.5px] leading-relaxed text-white/70"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          Build, deploy and monitor voice agents on your own stack — every model in the pipeline
          swappable, nothing locked in.
        </motion.p>
      </div>

      <motion.div
        className="relative z-10 bg-black/20 px-10 pb-8 pt-7 xl:px-14"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.7, delay: 0.6 }}
      >
        <BrandWaveform className="h-24" />
        <div className="mt-6 flex items-center gap-5 font-mono text-[11px] text-white/45">
          {['Open source · MIT', '55+ providers', 'LLM · STT · TTS'].map((spec, i) => (
            <span key={spec} className="flex items-center gap-5">
              {i > 0 && <span className="h-3 w-px bg-white/20" />}
              {spec}
            </span>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
