import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export default function ReasonsList({ reasons = [] }) {
  return (
    <div className="evidence-panel p-6">
      <p className="label-tag mb-4">Why this verdict</p>
      <ul className="space-y-3">
        {reasons.map((reason, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-paper-200">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-flag-400" strokeWidth={1.75} />
            <span>{reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
