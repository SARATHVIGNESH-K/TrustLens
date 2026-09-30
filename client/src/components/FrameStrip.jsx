import React, { useState } from 'react';
import { Layers, Move } from 'lucide-react';
import { motion } from 'framer-motion';

// Parses "frame_00005_2500ms.jpg" -> 2500 (ms)
function frameTimestampMs(url) {
  const match = url.match(/_(\d+)ms\.jpg$/);
  return match ? parseInt(match[1], 10) : null;
}

function isSuspicious(tsMs, segments) {
  if (tsMs === null) return false;
  const tsSec = tsMs / 1000;
  return segments.some(
    (seg) => seg.status === 'suspicious' && tsSec >= seg.start && tsSec < seg.end
  );
}

export default function FrameStrip({ frameUrls = [], segments = [], videoId }) {
  const [active, setActive] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [heatmapError, setHeatmapError] = useState(false);

  const toggleHeatmap = () => {
    if (showHeatmap) {
      setShowHeatmap(false);
    } else {
      setShowHeatmap(true);
      setHeatmapLoading(true);
      setHeatmapError(false);
    }
  };

  const getHeatmapUrl = (url) => {
    if (!videoId) return null;
    const filename = url.split('/').pop();
    return `/api/report/${videoId}/heatmap/${filename}`;
  };

  if (frameUrls.length === 0) {
    return (
      <div className="evidence-panel p-6">
        <p className="label-tag mb-2">Manipulated region viewer</p>
        <p className="font-mono text-[12px] text-muted-500">
          No extracted frames available for this video yet.
        </p>
      </div>
    );
  }

  return (
    <div className="evidence-panel p-6">
      <div className="mb-4 flex items-center justify-between">
        <span className="label-tag">Manipulated region viewer</span>
        <span className="font-mono text-[11px] text-muted-500">
          {frameUrls.length} extracted frame{frameUrls.length !== 1 ? 's' : ''}
        </span>
      </div>

      {active !== null && (
        <div className="mb-4 border border-ink-600">
          <div className="relative overflow-hidden">
            <img
              src={frameUrls[active]}
              alt={`Frame at ${((frameTimestampMs(frameUrls[active]) || 0) / 1000).toFixed(1)}s`}
              className="w-full max-h-96 object-contain bg-ink-900 pointer-events-none"
            />
            {showHeatmap && (
              <motion.img
                drag
                dragMomentum={false}
                src={getHeatmapUrl(frameUrls[active])}
                alt="AI Explainability Heatmap"
                className="absolute inset-0 w-full h-full max-h-96 object-contain transition-opacity duration-300 cursor-move"
                onLoad={() => setHeatmapLoading(false)}
                onError={() => { setHeatmapLoading(false); setHeatmapError(true); }}
                style={{ opacity: heatmapLoading ? 0 : 1 }}
              />
            )}
            {showHeatmap && heatmapLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-ink-900/50 pointer-events-none">
                <span className="font-mono text-xs text-scanner-400 animate-pulse">Generating AI Heatmap...</span>
              </div>
            )}
            {showHeatmap && heatmapError && (
              <div className="absolute inset-0 flex items-center justify-center bg-ink-900/80 pointer-events-none">
                <span className="font-mono text-xs text-flag-400">Heatmap unavailable (model error or no face detected)</span>
              </div>
            )}
            {showHeatmap && !heatmapLoading && !heatmapError && (
              <div className="absolute top-2 right-2 bg-ink-950/80 p-1.5 rounded text-muted-400 flex items-center gap-1.5 pointer-events-none border border-ink-700">
                <Move className="h-3 w-3" />
                <span className="font-mono text-[9px] uppercase">Draggable</span>
              </div>
            )}
          </div>
          <div className="flex items-center justify-between border-t border-ink-600 px-3 py-2 bg-ink-900">
            <div className="flex items-center gap-4">
              <span className="font-mono text-[11px] text-muted-500">
                t = {((frameTimestampMs(frameUrls[active]) || 0) / 1000).toFixed(1)}s
              </span>
              <button
                onClick={toggleHeatmap}
                className={`focus-ring inline-flex items-center gap-1.5 px-2 py-1 text-[10px] font-mono border transition-colors ${
                  showHeatmap 
                    ? 'border-scanner-500 text-scanner-400 bg-scanner-500/10' 
                    : 'border-ink-600 text-muted-400 hover:text-paper-200 hover:border-ink-500'
                }`}
              >
                <Layers className="h-3 w-3" />
                {showHeatmap ? 'Hide Heatmap' : 'Show AI Explainability Heatmap'}
              </button>
            </div>
            {isSuspicious(frameTimestampMs(frameUrls[active]), segments) ? (
              <span className="font-mono text-[11px] text-flag-400">
                Falls within a flagged segment
              </span>
            ) : (
              <span className="font-mono text-[11px] text-verified-400">
                Falls within a normal segment
              </span>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1.5">
        {frameUrls.map((url, i) => {
          const ts = frameTimestampMs(url);
          const suspicious = isSuspicious(ts, segments);
          return (
            <button
              key={url}
              onClick={() => {
                if (i !== active) {
                  setActive(i);
                  setShowHeatmap(false);
                } else {
                  setActive(null);
                  setShowHeatmap(false);
                }
              }}
              className={`relative h-14 w-20 shrink-0 overflow-hidden border transition-all ${
                active === i
                  ? 'border-scanner-400 ring-1 ring-scanner-400'
                  : suspicious
                  ? 'border-flag-500/70 hover:border-flag-400'
                  : 'border-ink-600 hover:border-ink-500'
              }`}
            >
              <img src={url} alt={`frame ${i}`} className="h-full w-full object-cover" />
              {suspicious && (
                <span className="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-flag-500" />
              )}
            </button>
          );
        })}
      </div>
      <p className="mt-3 font-mono text-[11px] text-muted-500">
        Click a frame to preview it full-size. Frames with a red dot fall inside a flagged
        timeline segment.
      </p>
    </div>
  );
}
