import React from 'react';

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between border-b border-ink-600 py-2 last:border-b-0">
      <span className="font-mono text-[11px] text-muted-500">{label}</span>
      <span className="font-mono text-[12px] text-paper-200">{value ?? '—'}</span>
    </div>
  );
}

export default function MetadataPanel({ metadata, sizeBytes }) {
  if (!metadata) return null;
  const resolution =
    metadata.width && metadata.height ? `${metadata.width}×${metadata.height}` : '—';

  return (
    <div className="evidence-panel p-6">
      <p className="label-tag mb-3">Video metadata</p>
      <Row label="Duration" value={metadata.duration_sec ? `${metadata.duration_sec.toFixed(2)}s` : null} />
      <Row label="Frame rate" value={metadata.fps ? `${metadata.fps} fps` : null} />
      <Row label="Resolution" value={resolution} />
      <Row label="Codec" value={metadata.codec} />
      <Row
        label="Bitrate"
        value={metadata.bitrate ? `${Math.round(metadata.bitrate / 1000)} kbps` : null}
      />
      <Row label="Frame count" value={metadata.frame_count} />
      <Row label="Creation time" value={metadata.creation_time} />
      <Row
        label="File size"
        value={sizeBytes ? `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB` : null}
      />
    </div>
  );
}
