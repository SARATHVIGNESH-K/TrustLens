import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';

export default function RecentReports({ reports = [] }) {
  return (
    <div className="evidence-panel p-6">
      <div className="mb-4 flex items-center justify-between">
        <span className="label-tag">Recent reports</span>
        <Link to="/history" className="focus-ring font-mono text-[11px] text-scanner-400 hover:text-scanner-300">
          View all
        </Link>
      </div>

      <div className="divide-y divide-ink-600">
        {reports.map((r) => (
          <Link
            to={`/report/${r.id}`}
            key={r.id}
            className="focus-ring group flex items-center justify-between gap-4 py-3.5"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-paper-200">{r.filename}</p>
              <p className="mt-0.5 font-mono text-[11px] text-muted-500">{r.date} · {r.duration}</p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span
                className={`font-mono text-[11px] ${
                  r.verdict === 'Authentic' ? 'text-verified-400' : 'text-flag-400'
                }`}
              >
                {r.verdict} · {r.score}%
              </span>
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-500 group-hover:text-paper-200 transition-colors" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
