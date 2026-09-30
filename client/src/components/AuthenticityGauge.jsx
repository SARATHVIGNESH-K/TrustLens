import React from 'react';
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

export default function AuthenticityGauge({
  fakeProbability = 12,
  authenticityScore,
  verdict = 'Authentic',
  riskLevel = 'Low',
  confidenceLabel = 'High',
}) {
  const calculatedAuthScore =
    authenticityScore !== undefined && authenticityScore !== null
      ? Math.round(authenticityScore)
      : Math.max(0, Math.min(100, Math.round(100 - fakeProbability)));

  const isAuthentic = verdict === 'Authentic' || calculatedAuthScore >= 50;
  // Emerald green for authentic, flag red for deepfake
  const accentColor = isAuthentic ? '#34D399' : '#C1443C';
  const data = [{ name: 'score', value: calculatedAuthScore, fill: accentColor }];

  return (
    <div className="evidence-panel flex flex-col items-center p-6">
      <div className="w-full flex items-center justify-between mb-1">
        <p className="label-tag">Authenticity evaluation</p>
        <span
          className={`font-mono text-[10px] uppercase px-2 py-0.5 border ${
            isAuthentic
              ? 'border-verified-500/40 bg-verified-500/10 text-verified-400'
              : 'border-flag-500/40 bg-flag-500/10 text-flag-400'
          }`}
        >
          {isAuthentic ? 'Verified' : 'Flagged'}
        </span>
      </div>

      <div className="relative mt-2 h-44 w-44">
        <RadialBarChart
          width={176}
          height={176}
          cx={88}
          cy={88}
          innerRadius={68}
          outerRadius={84}
          barSize={10}
          data={data}
          startAngle={90}
          endAngle={-270}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background={{ fill: '#232833' }} dataKey="value" cornerRadius={2} />
        </RadialBarChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="font-display text-4xl font-semibold" style={{ color: accentColor }}>
            {calculatedAuthScore}%
          </span>
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-400 mt-0.5">
            Authenticity
          </span>
        </div>
      </div>

      <div className="mt-4 w-full space-y-2.5 border-t border-ink-600 pt-4">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-muted-500">Verdict</span>
          <span className="font-mono text-sm font-medium" style={{ color: accentColor }}>
            {verdict}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-muted-500">Authenticity score</span>
          <span className="font-mono text-sm text-paper-200">{calculatedAuthScore}%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-muted-500">Manipulation risk</span>
          <span
            className="font-mono text-sm"
            style={{ color: isAuthentic ? '#9CA3AF' : '#F87171' }}
          >
            {fakeProbability}% ({riskLevel} risk)
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] text-muted-500">Confidence</span>
          <span className="font-mono text-sm text-paper-200">{confidenceLabel}</span>
        </div>
      </div>
    </div>
  );
}
