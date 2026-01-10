// Agent Builder Page - Create Custom Agents
// Part of FAIM 4-Tab Navigation (Phase 10.4)

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Agent Builder</h1>
          <p className="text-sm text-slate-400 mt-1">
            Build custom agents powered by FAIM memory
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Coming Soon Cards */}
        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <h3 className="font-semibold text-slate-200">Research Agent</h3>
          <p className="text-sm text-slate-400 mt-2">
            An agent that searches and summarizes your knowledge
          </p>
          <div className="mt-4 text-xs text-cyan-400">Coming Soon</div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <h3 className="font-semibold text-slate-200">Writing Agent</h3>
          <p className="text-sm text-slate-400 mt-2">
            Draft documents using your stored context
          </p>
          <div className="mt-4 text-xs text-cyan-400">Coming Soon</div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/5 p-6">
          <h3 className="font-semibold text-slate-200">Custom Agent</h3>
          <p className="text-sm text-slate-400 mt-2">
            Build your own agent with custom prompts
          </p>
          <div className="mt-4 text-xs text-violet-400">+ Create New</div>
        </div>
      </div>
    </div>
  );
}
