import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Download } from 'lucide-react';
import { getReport, analyzeVideo, downloadReportPdf } from '../api/client.js';
import AuthenticityGauge from '../components/AuthenticityGauge.jsx';
import ReasonsList from '../components/ReasonsList.jsx';
import SuspiciousTimeline from '../components/SuspiciousTimeline.jsx';
import MetadataPanel from '../components/MetadataPanel.jsx';
import FrameStrip from '../components/FrameStrip.jsx';

export default function ReportDetail() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      setLoading(true);
      const data = await getReport(id);
      setReport(data);
      setError('');
    } catch (e) {
      setError(
        e?.response?.status === 404
          ? 'No report found with this ID.'
          : 'Could not reach the backend. Is uvicorn running at http://localhost:8000?'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const runAnalysis = async () => {
    setAnalyzing(true);
    try {
      await analyzeVideo(id);
      await load();
    } catch (e) {
      setError(e?.response?.data?.detail || 'Analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadReportPdf(id, `TrustLens_Report_${report.original_filename.replace(/\.[^.]+$/, '')}.pdf`);
    } catch (e) {
      setError('Could not generate the PDF report.');
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16">
        <p className="font-mono text-[12px] text-muted-500">Loading report…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="evidence-panel mx-auto max-w-md p-8 text-center">
          <p className="label-tag mb-3">Report unavailable</p>
          <p className="text-sm text-muted-400">{error}</p>
          <Link
            to="/"
            className="focus-ring mt-5 inline-block border border-ink-600 px-4 py-2 text-sm text-paper-200 hover:border-scanner-600 hover:text-scanner-400"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const { analysis } = report;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <Link
        to="/"
        className="focus-ring mb-6 inline-flex items-center gap-1.5 font-mono text-[11px] text-muted-400 hover:text-paper-200"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to dashboard
      </Link>

      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <p className="label-tag">Case report</p>
          <h1 className="font-display text-2xl text-paper-100">{report.original_filename}</h1>
        </div>
        <span className="font-mono text-[11px] text-muted-500">case #{report.id.slice(0, 6)}</span>
      </div>

      {analysis && (
        <div className="mb-4 flex justify-end">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="focus-ring inline-flex items-center gap-2 border border-ink-600 px-4 py-2 text-sm text-paper-200 hover:border-scanner-600 hover:text-scanner-400 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            {downloading ? 'Generating PDF…' : 'Download report (PDF)'}
          </button>
        </div>
      )}

      {report.video_url && (
        <div className="evidence-panel mb-4 p-3">
          <video src={report.video_url} controls className="max-h-96 w-full bg-ink-950" />
        </div>
      )}

      {!analysis ? (
        <div className="evidence-panel p-8 text-center">
          <p className="label-tag mb-3">Not yet analyzed</p>
          <p className="mb-5 text-sm text-muted-400">
            This video was uploaded but hasn't been run through forensic analysis yet.
          </p>
          <button
            onClick={runAnalysis}
            disabled={analyzing}
            className="focus-ring inline-flex items-center gap-2 border border-scanner-500 bg-scanner-500/10 px-5 py-2.5 text-sm text-scanner-400 hover:bg-scanner-500/20 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${analyzing ? 'animate-spin' : ''}`} />
            {analyzing ? 'Analyzing…' : 'Run authenticity analysis'}
          </button>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-[0.85fr_1.15fr]">
            <AuthenticityGauge
              fakeProbability={analysis.fake_probability}
              authenticityScore={analysis.authenticity_score}
              verdict={analysis.verdict === 'Authentic' ? 'Authentic' : `Likely ${analysis.verdict}`}
              riskLevel={analysis.risk_level}
              confidenceLabel={analysis.confidence_label}
            />
            <ReasonsList reasons={analysis.reasons} />
          </div>

          {analysis.timeline_segments?.length > 0 && (
            <div className="mt-4">
              <SuspiciousTimeline
                duration={analysis.timeline_segments[analysis.timeline_segments.length - 1].end}
                segments={analysis.timeline_segments}
              />
            </div>
          )}

          <div className="mt-4">
            <FrameStrip frameUrls={report.frame_urls} segments={analysis.timeline_segments || []} videoId={report.id} />
          </div>

          {/* AI Classifier Panel */}
          {analysis.forensic_signals?.ai_classifier?.available && (
            <div className="mt-4 evidence-panel p-5">
              <p className="label-tag mb-3">🤖 AI Deepfake Classifier (ViT)</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div>
                  <p className="font-mono text-[10px] text-muted-500 uppercase mb-1">AI Fake Score</p>
                  <p className="font-display text-xl" style={{
                    color: analysis.forensic_signals.ai_classifier.fake_probability >= 60 ? '#C1443C' : '#34D399'
                  }}>
                    {analysis.forensic_signals.ai_classifier.fake_probability}%
                  </p>
                </div>
                <div>
                  <p className="font-mono text-[10px] text-muted-500 uppercase mb-1">Frames Checked</p>
                  <p className="font-mono text-sm text-paper-200">{analysis.forensic_signals.ai_classifier.total_frames_analyzed}</p>
                </div>
                <div>
                  <p className="font-mono text-[10px] text-muted-500 uppercase mb-1">High-Risk Frames</p>
                  <p className="font-mono text-sm text-flag-400">{analysis.forensic_signals.ai_classifier.high_risk_frame_count}</p>
                </div>
                <div>
                  <p className="font-mono text-[10px] text-muted-500 uppercase mb-1">Peak Frame Score</p>
                  <p className="font-mono text-sm text-paper-200">{Math.round(analysis.forensic_signals.ai_classifier.max_frame_score * 100)}%</p>
                </div>
              </div>
            </div>
          )}

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <MetadataPanel metadata={report.metadata} sizeBytes={report.size_bytes} />
            <div className="evidence-panel p-6">
              <p className="label-tag mb-3">Raw forensic signals</p>
              <pre className="max-h-64 overflow-auto font-mono text-[11px] leading-relaxed text-muted-400">
                {JSON.stringify(analysis.forensic_signals, null, 2)}
              </pre>
            </div>
          </div>

          <p className="mt-4 font-mono text-[11px] text-muted-500">
            Engine: {analysis.model_used} — Analyzed {new Date(analysis.analyzed_at).toLocaleString()}.
          </p>
        </>
      )}
    </div>
  );
}
