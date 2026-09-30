import React, { useState } from 'react';

// segments: [{ start, end, status: 'normal' | 'suspicious', reason }]
export default function SuspiciousTimeline({ duration = 40, segments = [] }) {
  const [active, setActive] = useState(null);

  return (
    <div className="evidence-panel p-6">
      <div className="mb-4 flex items-center justify-between">
        <span className="label-tag">Suspicious timeline</span>
        <span className="font-mono text-[11px] text-muted-500">00:00 → {String(Math.floor(duration / 60)).padStart(2, '0')}:{String(duration % 60).padStart(2, '0')}</span>
      </div>

      <div className="flex h-8 w-full overflow-hidden border border-ink-600">
        {segments.map((seg, i) => {
          const widthPct = ((seg.end - seg.start) / duration) * 100;
          const isSuspicious = seg.status === 'suspicious';
          return (
            <button
              key={i}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              className={`focus-ring h-full border-r border-ink-900 last:border-r-0 transition-opacity ${
                isSuspicious ? 'bg-flag-500/70 hover:bg-flag-500' : 'bg-verified-500/40 hover:bg-verified-500/60'
              }`}
              style={{ width: `${widthPct}%` }}
              aria-label={`${seg.start}s to ${seg.end}s, ${seg.status}`}
            />
          );
        })}
      </div>

      <div className="mt-3 min-h-[2.5rem]">
        {active !== null ? (
          <p className="font-mono text-[12px] text-paper-200">
            <span className={segments[active].status === 'suspicious' ? 'text-flag-400' : 'text-verified-400'}>
              {String(segments[active].start).padStart(2, '0')}s–{String(segments[active].end).padStart(2, '0')}s
            </span>{' '}
            — {segments[active].reason}
          </p>
        ) : (
          <p className="font-mono text-[11px] text-muted-500">Hover a segment for detail</p>
        )}
      </div>

      <div className="mt-3 flex gap-5 font-mono text-[11px] text-muted-500">
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 bg-verified-500/60" /> Normal</span>
        <span className="flex items-center gap-1.5"><span className="h-2 w-2 bg-flag-500/70" /> Suspicious</span>
      </div>
    </div>
  );
}
