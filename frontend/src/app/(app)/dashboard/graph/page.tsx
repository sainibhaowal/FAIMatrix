"use client";

export default function GraphPage() {
  return (
    <div className="space-y-6 pb-8 text-slate-100">
      <header>
        <h1 className="text-xl font-semibold">Synapse Explorer</h1>
        <p className="mt-1 text-sm text-slate-400">Purified for native graph reconstruction.</p>
      </header>

      <div className="min-h-[500px] border-2 border-dashed border-slate-800 rounded-3xl flex items-center justify-center">
        <p className="text-slate-500 font-mono text-sm">
          Graph view purified. Ready for FAIM-native visualization.
        </p>
      </div>
    </div>
  );
}
