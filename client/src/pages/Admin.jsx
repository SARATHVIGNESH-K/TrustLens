import React, { useEffect, useState } from 'react';
import StatCard from '../components/StatCard.jsx';
import { getStats, getHistory } from '../api/client.js';

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, historyData] = await Promise.all([getStats(), getHistory()]);
        setStats(statsData);
        setLogs(historyData);
      } catch (err) {
        setError('Failed to fetch admin data.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 pb-20">
      <div className="mb-8">
        <h1 className="font-mono text-xl text-paper-200">Admin Panel</h1>
        <p className="mt-2 text-sm text-muted-500">
          System overview, model performance, and recent activity logs.
        </p>
      </div>

      {error && (
        <div className="mb-6 border border-flag-600 bg-flag-500/10 px-4 py-3 font-mono text-[12px] text-flag-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="font-mono text-[11px] text-muted-500">Loading system data...</div>
      ) : (
        <div className="space-y-10">
          {/* System Stats Section */}
          <section>
            <h2 className="mb-4 font-mono text-sm text-paper-200">System Usage & Stats</h2>
            <div className="grid gap-4 sm:grid-cols-4">
              <StatCard
                label="Total Analyses"
                value={stats ? stats.total_analyzed.toLocaleString() : '—'}
                sublabel="all time"
              />
              <StatCard
                label="Detection Rate (Fake)"
                value={stats && stats.total_analyzed ? `${((stats.flagged_fake / stats.total_analyzed) * 100).toFixed(1)}%` : '—'}
                sublabel={`${stats?.flagged_fake || 0} flagged`}
                tone="flag"
              />
              <StatCard
                label="Authentic Rate"
                value={stats && stats.total_analyzed ? `${((stats.confirmed_authentic / stats.total_analyzed) * 100).toFixed(1)}%` : '—'}
                sublabel={`${stats?.confirmed_authentic || 0} passed`}
                tone="verified"
              />
              <StatCard
                label="Model Certainty"
                value={stats ? `${stats.avg_confidence}%` : '—'}
                sublabel="average confidence score"
                tone="scanner"
              />
            </div>
          </section>

          {/* Model Performance Mockup Section */}
          <section>
            <h2 className="mb-4 font-mono text-sm text-paper-200">Model Configuration</h2>
            <div className="evidence-panel p-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <h3 className="font-mono text-[11px] text-muted-500 uppercase tracking-wider mb-2">Primary Classifier</h3>
                  <p className="text-sm text-paper-200">ViT Deepfake Detector (v2)</p>
                  <p className="mt-1 font-mono text-[11px] text-verified-400">Status: Active & Loaded</p>
                </div>
                <div>
                  <h3 className="font-mono text-[11px] text-muted-500 uppercase tracking-wider mb-2">Analysis Parameters</h3>
                  <ul className="text-sm text-paper-200 space-y-1">
                    <li>Max Frames Sampled: <span className="font-mono">128</span></li>
                    <li>High-Risk Threshold: <span className="font-mono">0.65</span></li>
                    <li>Interpolation: <span className="font-mono">cv2.INTER_CUBIC</span></li>
                  </ul>
                </div>
              </div>
            </div>
          </section>

          {/* Upload Logs Section */}
          <section>
            <h2 className="mb-4 font-mono text-sm text-paper-200">Recent Upload Logs</h2>
            <div className="evidence-panel p-0 overflow-hidden">
              <table className="w-full text-left text-sm text-paper-200">
                <thead className="bg-ink-600/50 font-mono text-[11px] text-muted-500 uppercase tracking-wider border-b border-ink-600">
                  <tr>
                    <th className="px-6 py-3">File Name</th>
                    <th className="px-6 py-3">Date</th>
                    <th className="px-6 py-3">Verdict</th>
                    <th className="px-6 py-3 text-right">Probability</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink-600">
                  {logs.slice(0, 10).map((log) => (
                    <tr key={log.id} className="hover:bg-ink-600/20 transition-colors">
                      <td className="px-6 py-3 truncate max-w-xs">{log.filename}</td>
                      <td className="px-6 py-3 font-mono text-[11px]">{log.date}</td>
                      <td className="px-6 py-3">
                        <span
                          className={`font-mono text-[11px] ${
                            log.verdict === 'Authentic' ? 'text-verified-400' : 'text-flag-400'
                          }`}
                        >
                          {log.verdict || 'Pending'}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-right font-mono text-[11px]">
                        {log.score ?? 0}%
                      </td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr>
                      <td colSpan="4" className="px-6 py-8 text-center font-mono text-[11px] text-muted-500">
                        No recent logs available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
