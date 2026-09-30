import React from 'react';
import { motion } from 'framer-motion';

// Deterministic pseudo-random frame "noise" pattern so the filmstrip looks like
// distinct video frames without loading real images.
const FRAME_SEEDS = [12, 45, 8, 67, 23, 91, 34, 56, 19, 72, 41, 63];

function FilmFrame({ seed, flagged }) {
  const hue = 200 + (seed % 30);
  return (
    <div
      className={`relative h-16 w-24 shrink-0 border ${
        flagged ? 'border-flag-500/70' : 'border-ink-600'
      } overflow-hidden`}
      style={{
        background: `linear-gradient(135deg, hsl(${hue} 18% 16%), hsl(${hue + 12} 14% 10%))`,
      }}
    >
      {flagged && (
        <span className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-flag-500" />
      )}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.04) 3px, rgba(255,255,255,0.04) 4px)',
        }}
      />
    </div>
  );
}

export default function Hero() {
  const flaggedIndices = new Set([4, 5]);

  return (
    <section className="mx-auto max-w-6xl px-6 pt-16 pb-14 sm:pt-24">
      <div className="grid gap-12 sm:grid-cols-[1.1fr_0.9fr] sm:items-center">
        <div>
          <p className="label-tag mb-5">Frame-level video forensics</p>
          <h1 className="font-display text-4xl leading-[1.08] text-paper-100 sm:text-5xl">
            See exactly where a video
            <br />
            stops telling the truth.
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-relaxed text-muted-400">
            Upload a video and TrustLens inspects it frame by frame — face
            consistency, blink rhythm, lip sync, compression traces — and
            shows you the evidence behind every verdict, not just a score.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="#upload"
              className="focus-ring border border-scanner-500 bg-scanner-500/10 px-5 py-2.5 text-sm text-scanner-400 hover:bg-scanner-500/20 transition-colors"
            >
              Analyze a video
            </a>
            <a
              href="#how-it-works"
              className="focus-ring px-2 py-2.5 text-sm text-muted-400 hover:text-paper-200 transition-colors"
            >
              How the analysis works
            </a>
          </div>
        </div>

        <div className="evidence-panel p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="label-tag">Sample scan · case #04127</span>
            <span className="font-mono text-[11px] text-flag-400">2 frames flagged</span>
          </div>
          <div className="relative overflow-hidden">
            <div className="flex gap-1 overflow-x-hidden">
              {FRAME_SEEDS.map((seed, i) => (
                <FilmFrame key={i} seed={seed} flagged={flaggedIndices.has(i)} />
              ))}
            </div>
            <motion.div
              className="pointer-events-none absolute inset-y-0 left-0 w-10 bg-gradient-to-r from-transparent via-scanner-400/60 to-transparent"
              initial={{ x: '-10%' }}
              animate={{ x: '620%' }}
              transition={{ duration: 2.6, ease: 'easeInOut', delay: 0.4 }}
            />
          </div>
          <div className="mt-4 flex items-center justify-between font-mono text-[11px] text-muted-400">
            <span>00:00</span>
            <span className="text-flag-400">00:09 — 00:13 suspicious</span>
            <span>00:24</span>
          </div>
        </div>
      </div>
    </section>
  );
}
