import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Trash2 } from 'lucide-react';
import { getHistory, deleteHistoryItem } from '../api/client.js';

export default function History() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await getHistory();
      setReports(data);
      setError('');
    } catch (err) {
      setError('Failed to load history. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDelete = async (e, id) => {
    e.preventDefault();
    if (!window.confirm('Are you sure you want to delete this analysis?')) {
      return;
    }
    try {
      await deleteHistoryItem(id);
      await fetchHistory();
    } catch (err) {
      console.error(err);
      alert('Failed to delete item.');
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 pb-20">
      <div className="mb-8">
        <h1 className="font-mono text-xl text-paper-200">Analysis History</h1>
        <p className="mt-2 text-sm text-muted-500">
          Search and review past video authenticity reports.
        </p>
      </div>

      {error && (
        <div className="mb-6 border border-flag-600 bg-flag-500/10 px-4 py-3 font-mono text-[12px] text-flag-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="font-mono text-[11px] text-muted-500">Loading history...</div>
      ) : (
        <div className="evidence-panel p-6">
          {reports.length === 0 ? (
            <p className="font-mono text-[11px] text-muted-500">No reports found.</p>
          ) : (
            <div className="divide-y divide-ink-600">
              {reports.map((r) => (
                <div key={r.id} className="group flex items-center justify-between gap-4 py-3.5">
                  <Link
                    to={`/report/${r.id}`}
                    className="focus-ring flex-1 min-w-0"
                  >
                    <p className="truncate text-sm text-paper-200 group-hover:text-scanner-300 transition-colors">
                      {r.filename}
                    </p>
                    <p className="mt-0.5 font-mono text-[11px] text-muted-500">
                      {r.date} · {r.duration}
                    </p>
                  </Link>
                  <div className="flex items-center gap-4 shrink-0">
                    <span
                      className={`font-mono text-[11px] ${
                        r.verdict === 'Authentic' ? 'text-verified-400' : 'text-flag-400'
                      }`}
                    >
                      {r.verdict || 'Pending'} · {r.score ?? 0}%
                    </span>
                    <Link
                      to={`/report/${r.id}`}
                      className="focus-ring text-muted-500 hover:text-paper-200 transition-colors"
                      title="View Report"
                    >
                      <ArrowUpRight className="h-4 w-4" />
                    </Link>
                    <button
                      onClick={(e) => handleDelete(e, r.id)}
                      className="focus-ring text-muted-500 hover:text-flag-400 transition-colors"
                      title="Delete Report"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
