"use client";

import React, { useState, useEffect } from "react";
import { buildFaimHeaders } from "@/lib/api-client";
import { Cpu, Zap, Search, Info, HelpCircle } from "lucide-react";

interface EmbedderPanelProps {
  graphId: string;
}

const EmbedderPanel: React.FC<EmbedderPanelProps> = ({ graphId }) => {
  const [status, setStatus] = useState<any>(null);
  const [textA, setTextA] = useState("");
  const [textB, setTextB] = useState("");
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function fetchStatus() {
      try {
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        const headers = buildFaimHeaders();
        if (session && (session as any).accessToken) {
          (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
        }

        const res = await fetch("/api/ops/embedder/status", {
          headers,
        });
        if (res.ok) {
          const data = await res.json();
          setStatus(data);
        }
      } catch (err) {
        console.error("Embedder status fail:", err);
      }
    }
    fetchStatus();
  }, []);

  const handleCompare = async () => {
    if (!textA.trim() || !textB.trim()) return;
    setLoading(true);
    try {
      const { getSession } = await import("next-auth/react");
      const session = await getSession();
      const headers = {
        ...buildFaimHeaders(),
        "Content-Type": "application/json",
      };
      if (session && (session as any).accessToken) {
        (headers as any)["Authorization"] = `Bearer ${(session as any).accessToken}`;
      }

      const res = await fetch("/api/ops/embedder/similarity", {
        method: "POST",
        headers,
        body: JSON.stringify({ text_a: textA, text_b: textB }),
      });
      if (res.ok) {
        const data = await res.json();
        setSimilarity(data.similarity);
      }
    } catch (err) {
      console.error("Comparison fail:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-5 p-1">
      <header className="px-2">
        <h2 className="text-xs font-bold text-slate-100 uppercase tracking-widest flex items-center gap-2">
          <Cpu className="w-3 h-3 text-violet-400" />
          Embedding Sandbox
        </h2>
        <p className="text-[10px] text-slate-500 mt-1">
          Explore FAIM's linguistic vector space. Test how the local model perceives concept proximity.
        </p>
      </header>

      {/* Model Stats */}
      {status && (
        <div className="mx-2 p-3 bg-violet-500/5 border border-violet-500/10 rounded-xl grid grid-cols-2 gap-4">
           <div>
             <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1">Local Model</span>
             <span className="text-[10px] font-mono text-violet-300">{status.model}</span>
           </div>
           <div className="text-right">
             <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1">Dimensions</span>
             <span className="text-[10px] font-mono text-cyan-400">{status.dimension}d</span>
           </div>
           <div>
             <span className="text-[9px] font-bold text-slate-500 uppercase block mb-1">Compute Unit</span>
             <div className="flex items-center gap-1.5 justify-start">
                <Zap className="w-2.5 h-2.5 text-amber-500" />
                <span className="text-[10px] font-mono text-slate-300 uppercase">{status.device}</span>
             </div>
           </div>
        </div>
      )}

      {/* Comparison Sandbox */}
      <div className="flex-1 space-y-4 px-2">
        <div className="space-y-2">
           <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">Observation A</label>
           <textarea
             value={textA}
             onChange={(e) => setTextA(e.target.value)}
             placeholder="Enter first concept or sentence..."
             className="w-full h-16 bg-slate-950/60 border border-slate-800 rounded-xl p-3 text-[11px] text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-violet-500/30 transition-all resize-none"
           />
        </div>

        <div className="space-y-2">
           <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">Observation B</label>
           <textarea
             value={textB}
             onChange={(e) => setTextB(e.target.value)}
             placeholder="Enter second concept or sentence..."
             className="w-full h-16 bg-slate-950/60 border border-slate-800 rounded-xl p-3 text-[11px] text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-violet-500/30 transition-all resize-none"
           />
        </div>

        <button
          onClick={handleCompare}
          disabled={loading || !textA.trim() || !textB.trim()}
          className="w-full py-2.5 rounded-xl bg-violet-600/20 border border-violet-500/30 text-[11px] font-bold text-violet-200 hover:bg-violet-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
          ) : (
            <Search className="w-3.5 h-3.5" />
          )}
          Compare Vectors
        </button>

        {similarity !== null && !loading && (
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 animate-in fade-in slide-in-from-bottom-2 duration-300">
             <div className="flex justify-between items-center mb-3">
               <span className="text-[10px] font-bold text-slate-400 uppercase">Semantic Similarity</span>
               <span className={`text-xs font-mono font-bold ${similarity > 0.7 ? 'text-emerald-400' : similarity > 0.4 ? 'text-amber-400' : 'text-slate-400'}`}>
                 {(similarity * 100).toFixed(2)}%
               </span>
             </div>
             
             <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-1000 ${similarity > 0.7 ? 'bg-emerald-500' : similarity > 0.4 ? 'bg-amber-500' : 'bg-slate-600'}`}
                  style={{ width: `${similarity * 100}%` }}
                />
             </div>

             <div className="mt-4 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/50 flex gap-2.5 items-start">
                <Info className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                <p className="text-[10px] text-slate-500 italic leading-relaxed">
                  {similarity > 0.8 ? "Highly redundant concepts. FAIM will likely merge or create an inheritance link." : 
                   similarity > 0.5 ? "Strong semantic overlap. These topics are likely in the same local cluster." :
                   "Weak connection. These concepts occupy distant regions in the vector space."}
                </p>
             </div>
          </div>
        )}
      </div>

      <footer className="px-2 pb-2">
         <div className="p-3 bg-slate-900/30 border border-dashed border-slate-800 rounded-xl flex items-center gap-3">
            <HelpCircle className="w-4 h-4 text-slate-600" />
            <span className="text-[9px] text-slate-600 font-medium">
              Similarity is calculated using Cosine Distance on the output layer of the sentence-transformer.
            </span>
         </div>
      </footer>
    </div>
  );
};

export default EmbedderPanel;
