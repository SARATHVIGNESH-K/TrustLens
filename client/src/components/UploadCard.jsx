import React, { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileVideo, X, AlertCircle } from 'lucide-react';
import { uploadVideo, analyzeVideo } from '../api/client.js';

const ACCEPTED_TYPES = ['video/mp4', 'video/x-msvideo', 'video/quicktime', 'video/x-matroska'];
const ACCEPTED_EXT = ['.mp4', '.avi', '.mov', '.mkv'];
const MAX_SIZE_MB = 500;

// stage: 'idle' | 'uploading' | 'analyzing' | 'done' | 'error'
export default function UploadCard({ onAnalysisComplete }) {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('idle');
  const inputRef = useRef(null);

  const validate = (f) => {
    const extOk = ACCEPTED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext));
    if (!extOk && !ACCEPTED_TYPES.includes(f.type)) {
      return 'Unsupported format. Use MP4, AVI, MOV, or MKV.';
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File exceeds the ${MAX_SIZE_MB}MB limit.`;
    }
    return '';
  };

  const handleFile = (f) => {
    const err = validate(f);
    if (err) {
      setError(err);
      setFile(null);
      return;
    }
    setError('');
    setFile(f);
    setStage('idle');
    setProgress(0);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragActive(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }, []);

  const runPipeline = async () => {
    if (!file) return;
    setError('');
    try {
      setStage('uploading');
      setProgress(0);
      const uploadResult = await uploadVideo(file, (pct) => setProgress(pct));

      setStage('analyzing');
      const analysis = await analyzeVideo(uploadResult.id);

      setStage('done');
      onAnalysisComplete?.({ upload: uploadResult, analysis, filename: file.name });
    } catch (e) {
      setStage('error');
      const detail = e?.response?.data?.detail;
      setError(
        typeof detail === 'string'
          ? detail
          : e?.message || 'Something went wrong talking to the backend.'
      );
    }
  };

  const clearFile = () => {
    setFile(null);
    setProgress(0);
    setError('');
    setStage('idle');
    if (inputRef.current) inputRef.current.value = '';
  };

  const isBusy = stage === 'uploading' || stage === 'analyzing';

  return (
    <div id="upload" className="evidence-panel p-6">
      <div className="mb-5 flex items-center justify-between">
        <span className="label-tag">Submit evidence</span>
        <span className="font-mono text-[11px] text-muted-400">MP4 · AVI · MOV · MKV · ≤500MB</span>
      </div>

      {!file ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center gap-3 border border-dashed py-14 text-center transition-colors ${
            dragActive
              ? 'border-scanner-500 bg-scanner-500/5'
              : 'border-ink-600 hover:border-ink-500'
          }`}
        >
          <UploadCloud
            className={`h-7 w-7 ${dragActive ? 'text-scanner-400' : 'text-muted-500'}`}
            strokeWidth={1.5}
          />
          <div>
            <p className="text-sm text-paper-200">Drop a video here, or click to browse</p>
            <p className="mt-1 font-mono text-[11px] text-muted-500">
              Sent to the TrustLens backend for real metadata and frame extraction
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".mp4,.avi,.mov,.mkv,video/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </div>
      ) : (
        <div className="border border-ink-600 p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <FileVideo className="h-5 w-5 shrink-0 text-scanner-500" strokeWidth={1.5} />
              <div className="min-w-0">
                <p className="truncate text-sm text-paper-200">{file.name}</p>
                <p className="font-mono text-[11px] text-muted-500">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
            </div>
            {!isBusy && (
              <button
                onClick={clearFile}
                aria-label="Remove file"
                className="focus-ring text-muted-500 hover:text-flag-400"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {stage === 'uploading' && (
            <div className="mt-4">
              <div className="h-1 w-full bg-ink-600">
                <div
                  className="h-1 bg-scanner-500 transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="mt-1.5 font-mono text-[11px] text-muted-500">
                Uploading — {progress}%
              </p>
            </div>
          )}

          {stage === 'analyzing' && (
            <div className="mt-4">
              <div className="h-1 w-full overflow-hidden bg-ink-600">
                <div className="h-1 w-1/3 animate-pulse bg-scanner-500" />
              </div>
              <p className="mt-1.5 font-mono text-[11px] text-muted-500">
                Extracting frames and running forensic analysis…
              </p>
            </div>
          )}

          {stage === 'done' && (
            <p className="mt-4 font-mono text-[11px] text-verified-400">
              Analysis complete — see results below
            </p>
          )}

          {stage === 'idle' && (
            <button
              onClick={runPipeline}
              className="focus-ring mt-4 w-full border border-scanner-500 bg-scanner-500/10 py-2.5 text-sm text-scanner-400 hover:bg-scanner-500/20 transition-colors"
            >
              Run authenticity analysis
            </button>
          )}

          {stage === 'error' && (
            <button
              onClick={runPipeline}
              className="focus-ring mt-4 w-full border border-flag-500 bg-flag-500/10 py-2.5 text-sm text-flag-400 hover:bg-flag-500/20 transition-colors"
            >
              Retry analysis
            </button>
          )}
        </div>
      )}

      {error && (
        <div className="mt-3 flex items-start gap-2 font-mono text-[11px] text-flag-400">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
