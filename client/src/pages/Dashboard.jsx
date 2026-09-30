import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import Hero from '../components/Hero.jsx';
import UploadCard from '../components/UploadCard.jsx';
import StatCard from '../components/StatCard.jsx';
import AuthenticityGauge from '../components/AuthenticityGauge.jsx';
import SuspiciousTimeline from '../components/SuspiciousTimeline.jsx';
import ReasonsList from '../components/ReasonsList.jsx';
import RecentReports from '../components/RecentReports.jsx';
import { getStats, getHistory } from '../api/client.js';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [reports, setReports] = useState([]);
  const [result, setResult] = useState(null); // { upload, analysis, filename }
  const [loadError, setLoadError] = useState('');

  const refresh = async () => {
    try {
      const [statsData, historyData] = await Promise.all([getStats(), getHistory()]);
      setStats(statsData);
      setReports(historyData);
      setLoadError('');
    } catch (e) {
      setLoadError(
        'Could not reach the backend. Is uvicorn running at http://localhost:8000?'
      );
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleAnalysisComplete = (payload) => {
    setResult(payload);
    refresh(); // pick up the new entry in stats + history
  };

  return (
    <div>
      <Hero />

      {loadError && (
        <section className="mx-auto max-w-6xl px-6 pb-4">
          <div className="border border-flag-600 bg-flag-500/10 px-4 py-3 font-mono text-[12px] text-flag-400">
            {loadError}
          </div>
        </section>
      )}

      <section className="mx-auto max-w-6xl px-6 pb-10">
        <div className="grid gap-4 sm:grid-cols-4">
          <StatCard
            label="Videos analyzed"
            value={stats ? stats.total_analyzed.toLocaleString() : '—'}
            sublabel="all time"
          />
          <StatCard
            label="Flagged as fake"
            value={stats ? stats.flagged_fake.toLocaleString() : '—'}
            sublabel={
              stats && stats.total_analyzed
                ? `${((stats.flagged_fake / stats.total_analyzed) * 100).toFixed(1)}% of total`
                : undefined
            }
            tone="flag"
          />
          <StatCard
            label="Confirmed authentic"
            value={stats ? stats.confirmed_authentic.toLocaleString() : '—'}
            sublabel={
              stats && stats.total_analyzed
                ? `${((stats.confirmed_authentic / stats.total_analyzed) * 100).toFixed(1)}% of total`
                : undefined
            }
            tone="verified"
          />
          <StatCard
            label="Avg. confidence"
            value={stats ? `${stats.avg_confidence}%` : '—'}
            sublabel="across all analyses"
            tone="scanner"
          />
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-6xl px-6 pb-10">
        <UploadCard onAnalysisComplete={handleAnalysisComplete} />
      </section>

      {result && (
        <section className="mx-auto max-w-6xl px-6 pb-10">
          <div className="mb-4 flex items-baseline justify-between">
            <p className="label-tag">Latest analysis · {result.filename}</p>
            <span className="font-mono text-[11px] text-muted-500">
              case #{result.upload.id.slice(0, 6)}
            </span>
          </div>
          <div className="mb-4 flex justify-end">
            <Link
              to={`/report/${result.upload.id}`}
              className="focus-ring inline-flex items-center gap-1 font-mono text-[11px] text-scanner-400 hover:text-scanner-300"
            >
              View full report <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid gap-4 sm:grid-cols-[0.85fr_1.15fr]">
            <AuthenticityGauge
              fakeProbability={result.analysis.fake_probability}
              authenticityScore={result.analysis.authenticity_score}
              verdict={
                result.analysis.verdict === 'Authentic'
                  ? 'Authentic'
                  : `Likely ${result.analysis.verdict}`
              }
              riskLevel={result.analysis.risk_level}
              confidenceLabel={result.analysis.confidence_label}
            />
            <ReasonsList reasons={result.analysis.reasons} />
          </div>
          {result.analysis.timeline_segments?.length > 0 && (
            <div className="mt-4">
              <SuspiciousTimeline
                duration={
                  result.analysis.timeline_segments[result.analysis.timeline_segments.length - 1]
                    .end
                }
                segments={result.analysis.timeline_segments}
              />
            </div>
          )}
          <p className="mt-3 font-mono text-[11px] text-muted-500">
            Model: {result.analysis.model_used} — heuristic forensic signals, not a trained
            deepfake classifier yet.
          </p>
        </section>
      )}

      <section className="mx-auto max-w-6xl px-6 pb-20">
        <RecentReports
          reports={reports.map((r) => ({
            id: r.id,
            filename: r.filename,
            date: r.date,
            duration: r.duration,
            verdict: r.verdict || 'Pending',
            score: r.score ?? 0,
          }))}
        />
        {reports.length === 0 && !loadError && (
          <p className="mt-3 font-mono text-[11px] text-muted-500">
            No reports yet — analyze a video above to see it here.
          </p>
        )}
      </section>
    </div>
  );
}
