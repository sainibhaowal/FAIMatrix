import Link from "next/link";
import { ArrowLeft, CheckCircle2, FileCode2, ShieldCheck } from "lucide-react";

import { Footer, Navbar } from "@/components";
import BenchmarkResultsBoard from "@/components/landing/BenchmarkResultsBoard";
import { BENCHMARK_REPORT_DATE } from "@/lib/benchmarkResults";

export default function BenchmarksPage() {
  return (
    <div className="min-h-screen bg-[#050a14] text-white">
      <Navbar />

      <main className="mx-auto max-w-[1280px] px-4 pb-20 pt-28 sm:px-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-slate-400 transition-colors hover:text-cyan-300"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Back to FAIMATRIX Overview
        </Link>

        <header className="mt-6 border-b border-slate-800/80 pb-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-200">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Verified Evaluation Report · {BENCHMARK_REPORT_DATE}
          </div>
          <h1 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-5xl">
            Empirical Retrieval &amp; Memory Benchmarks
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400 sm:text-base">
            Full un-sampled splits across{" "}
            <code className="text-cyan-200">BeIR/scifact</code>,{" "}
            <code className="text-cyan-200">BeIR/nfcorpus</code>,{" "}
            <code className="text-cyan-200">BeIR/arguana</code>, and{" "}
            <code className="text-cyan-200">LoCoMo</code> comparing Pure FAIM
            Zero-ML (CPU &amp; CUDA), FAIM + Granite 97M Multilingual R2, and
            the in-process <code className="text-slate-200">BM25-Baseline</code>
            .
          </p>
        </header>

        <section className="mt-10">
          <BenchmarkResultsBoard compact={false} showFullPageLink={false} />
        </section>

        <section className="mt-12 grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-cyan-300">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Key Engineering Takeaways
            </div>
            <ul className="mt-4 space-y-3 text-xs leading-6 text-slate-300">
              <li>
                <strong className="text-white">
                  Pure FAIM Zero-ML runs identically on CPU &amp; GPU:
                </strong>{" "}
                <code className="text-emerald-300">0.6871</code> nDCG@10 on
                SciFact and <code className="text-emerald-300">0.3267</code> on
                NFCorpus with zero ML dependency, beating BM25 at 49–100 ms P50.
              </li>
              <li>
                <strong className="text-white">
                  Granite 97M Flagship (`3-gpu-granite`) lifts every BeIR
                  metric:
                </strong>{" "}
                reaches <code className="text-cyan-300">0.6900</code> nDCG@10 on
                SciFact, <code className="text-cyan-300">0.3314</code> on
                NFCorpus, and <code className="text-cyan-300">0.7266</code>{" "}
                Recall@10 on ArguAna (`304.55 ms` vs BM25 `567.83 ms`).
              </li>
              <li>
                <strong className="text-white">
                  `FAST` beats `BALANCED` by ~18× latency &amp; +0.034 nDCG@10:
                </strong>{" "}
                relevance-first fusion avoids saturating workers while
                preserving accuracy.
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
            <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-purple-300">
              <FileCode2 className="h-4 w-4" aria-hidden="true" />
              Reproducibility &amp; Signed Artifacts
            </div>
            <ul className="mt-4 space-y-3 text-xs leading-6 text-slate-400">
              <li>
                Every run is recorded as a signed JSON artifact indexed in{" "}
                <code className="text-slate-200">
                  faim-benchmarks/results/RESULTS.md
                </code>{" "}
                and{" "}
                <code className="text-slate-200">
                  faim-benchmarks/results/COMPARISON.md
                </code>
                .
              </li>
              <li>
                Failures and trade-offs are published alongside wins, including
                the early 18-worker LoCoMo RAM SIGKILL (resolved via the
                hardware autoscaler) and extractive vs. long-context LoCoMo
                scores (`11.9` vs `92.3` tokens).
              </li>
              <li>
                Live operator benchmarks (`BM-1`–`BM-9`, SRE Golden Signals, and
                stress tests) remain available inside the authenticated
                Dashboard.
              </li>
            </ul>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
