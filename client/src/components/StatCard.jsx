import React from 'react';

export default function StatCard({ label, value, sublabel, tone = 'neutral' }) {
  const toneClass = {
    neutral: 'text-paper-100',
    flag: 'text-flag-400',
    verified: 'text-verified-400',
    scanner: 'text-scanner-400',
  }[tone];

  return (
    <div className="evidence-panel px-5 py-4">
      <p className="label-tag">{label}</p>
      <p className={`mt-2 font-display text-3xl ${toneClass}`}>{value}</p>
      {sublabel && <p className="mt-1 font-mono text-[11px] text-muted-500">{sublabel}</p>}
    </div>
  );
}
