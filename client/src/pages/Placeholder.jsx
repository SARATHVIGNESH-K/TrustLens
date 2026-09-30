import React from 'react';

export default function Placeholder({ title, note }) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-24">
      <div className="evidence-panel mx-auto max-w-md p-8 text-center">
        <p className="label-tag mb-3">Not yet wired up</p>
        <h1 className="font-display text-2xl text-paper-100">{title}</h1>
        <p className="mt-3 text-sm text-muted-400">{note}</p>
      </div>
    </div>
  );
}
