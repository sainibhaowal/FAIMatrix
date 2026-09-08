"use client";

import {
  ArrowUpRight,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  FileText,
  Gauge,
  Home,
  Network,
  PanelBottom,
  ScanSearch,
  TerminalSquare,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";


type RailItem = {
  id: string;
  label: string;
  number: string;
  icon: LucideIcon;
  accent: string;
  href?: string;
};

type SubItem = { key: string; label: string; summary: string };

function publishRailState(expanded: boolean) {
  document.documentElement.dataset.faimRail = expanded ? "expanded" : "collapsed";
}

const RAIL_ITEMS: RailItem[] = [
  { id: "hero", label: "Overview", number: "00", icon: Home, accent: "#22d3ee" },
  { id: "core", label: "Core story", number: "01", icon: BrainCircuit, accent: "#22d3ee" },
  { id: "platform", label: "Platform", number: "02", icon: Network, accent: "#a78bfa" },
  { id: "proof", label: "Proof", number: "03", icon: ScanSearch, accent: "#f472b6" },
  { id: "ops", label: "Operations", number: "04", icon: TerminalSquare, accent: "#34d399" },
  { id: "scale", label: "Scale", number: "05", icon: Gauge, accent: "#fbbf24" },
  { id: "docs", label: "Docs", number: "06", icon: FileText, accent: "#67e8f9", href: "/docs" },
  { id: "footer", label: "Footer", number: "07", icon: PanelBottom, accent: "#94a3b8" },
];

const LOCAL_ITEMS = RAIL_ITEMS.filter((item) => !item.href);

const SUBNAV: Record<string, SubItem[]> = {
  core: [
    { key: "stack", label: "Tech stack", summary: "What FAIM is built on." },
    { key: "highlights", label: "Highlights", summary: "Main shipped capabilities." },
    { key: "maximum", label: "Maximum intelligence", summary: "High-level positioning." },
    { key: "outcomes", label: "Outcomes", summary: "Why teams adopt it." },
  ],
  platform: [
    { key: "architecture", label: "Architecture", summary: "Engine versus app layer." },
    { key: "recall", label: "Hybrid recall", summary: "Dense plus graph-aware recall." },
    { key: "comparison", label: "Systems comparison", summary: "Source-backed capability matrix across memory and retrieval systems." },
    { key: "adi", label: "ADI pipeline", summary: "Deterministic end-to-end pipeline." },
    { key: "pillars", label: "Pillars", summary: "Enterprise pillars and controls." },
    { key: "engine", label: "7 powers", summary: "Core engine powers." },
  ],
  proof: [
    { key: "graph", label: "Graph demo", summary: "Interactive knowledge graph." },
    { key: "integration", label: "Integration", summary: "How query and graph state connect." },
    { key: "ingestion", label: "Ingestion", summary: "File-to-graph flow." },
    { key: "quickstart", label: "Quick start", summary: "Get running fast." },
    { key: "math", label: "Math proof", summary: "8 invariants and proof layer." },
    { key: "query", label: "Query explain", summary: "Deterministic score breakdown." },
    { key: "evolution", label: "Evolution", summary: "Self-invent and evolve walkthrough." },
    { key: "fig", label: "FIG View", summary: "3D proof and pulse visualization." },
    { key: "manifesto", label: "Manifesto", summary: "Platform principles." },
    { key: "benchmarks", label: "Benchmarks", summary: "What the engine measures." },
  ],
  ops: [
    { key: "how", label: "How it works", summary: "One compact pipeline view." },
    { key: "docs", label: "Docs & ops", summary: "Operational docs and runbooks." },
    { key: "api", label: "Developer API", summary: "Integration surface." },
    { key: "security", label: "Security", summary: "API keys and scopes." },
    { key: "use-cases", label: "Use cases", summary: "Industries and workflows." },
  ],
  scale: [
    { key: "roadmap", label: "Roadmap", summary: "What’s next." },
    { key: "specs", label: "Tech specs", summary: "Real numbers and runtime facts." },
    { key: "future", label: "Future scale", summary: "GPU-accelerated roadmap." },
    { key: "faq", label: "FAQ", summary: "Common questions." },
    { key: "cta", label: "CTA", summary: "Final call to action." },
  ],
};

export default function SectionTracker() {
  const [activeSection, setActiveSection] = useState("hero");
  const [activeTabs, setActiveTabs] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(SUBNAV).map(([id, items]) => [id, items[0].key])),
  );
  const [expanded, setExpanded] = useState(true);
  useEffect(() => {
    const syncFromHash = () => {
      const [requested, requestedTab] = window.location.hash.slice(1).split("/");
      if (LOCAL_ITEMS.some((item) => item.id === requested)) {
        setActiveSection(requested);
        const firstTab = SUBNAV[requested]?.[0]?.key;
        if (requestedTab && SUBNAV[requested]?.some((item) => item.key === requestedTab)) {
          setActiveTabs((current) => ({ ...current, [requested]: requestedTab }));
        } else if (firstTab) {
          setActiveTabs((current) => ({ ...current, [requested]: firstTab }));
        }
      }
    };

    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);

    return () => {
      window.removeEventListener("hashchange", syncFromHash);
    };
  }, []);

  useEffect(() => {
    const storedExpanded = (() => {
      try {
        const stored = window.localStorage.getItem("faim-atlas-rail-expanded");
        return stored === null ? true : stored === "1";
      } catch {
        return true;
      }
    })();

    window.dispatchEvent(
      new CustomEvent("faim:rail-state", { detail: { expanded: storedExpanded } }),
    );
    publishRailState(storedExpanded);

    try {
      const stored = window.localStorage.getItem("faim-atlas-rail-expanded");
      if (stored !== null) setExpanded(stored === "1");
    } catch {
      // Keep the default shell when storage is unavailable.
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem("faim-atlas-rail-expanded", expanded ? "1" : "0");
    } catch {
      // Ignore persistence failures.
    }
  }, [expanded]);

  const selectSection = (id: string) => {
    window.history.replaceState(null, "", `#${id}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };

  const selectTab = (groupId: string, tabKey: string) => {
    setActiveTabs((current) => ({ ...current, [groupId]: tabKey }));
    window.history.replaceState(null, "", `#${groupId}/${tabKey}`);
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  };

  const toggleRail = () => {
    setExpanded((current) => {
      const next = !current;
      publishRailState(next);
      window.dispatchEvent(
        new CustomEvent("faim:rail-state", { detail: { expanded: next } }),
      );
      return next;
    });
  };

  return (
    <aside
      aria-label="FAIM landing navigation"
      className={`faim-atlas-rail fixed left-3 right-3 top-3 z-50 overflow-hidden border border-white/[0.1] bg-[#070a12]/95 shadow-[0_24px_80px_rgba(0,0,0,0.48)] backdrop-blur-xl transition-[width,height,transform] duration-300 lg:bottom-4 lg:left-4 lg:right-auto lg:top-4 lg:block ${
        expanded ? "lg:w-[232px]" : "lg:w-[76px]"
      }`}
    >
      <div className="relative flex min-h-full flex-col p-3">
        <div className={`mb-4 flex items-center ${expanded ? "gap-3 px-1" : "justify-center"}`}>
          <Image
            src="/logo-coded.svg"
            alt="FAIMATRIX"
            width={44}
            height={44}
            priority
            className="h-10 w-10 shrink-0 rounded-xl border border-cyan-300/30 bg-cyan-300/[0.04] p-1 object-contain"
          />
          {expanded && (
            <div>
              <p className="text-sm font-semibold tracking-[0.16em] text-white">FAIMATRIX</p>
              <p className="mt-1 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-500">
                Public system atlas
              </p>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={toggleRail}
          aria-label={expanded ? "Collapse landing navigation" : "Expand landing navigation"}
          className="mb-3 flex h-10 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.035] font-mono text-[9px] uppercase tracking-[0.16em] text-slate-400 transition-colors hover:border-cyan-400/40 hover:bg-cyan-400/[0.06] hover:text-cyan-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
        >
          {expanded ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          {expanded && <span>Collapse rail</span>}
        </button>

        <nav aria-label="Landing sections" className="min-h-0 flex-1 overflow-y-auto pr-1 custom-scrollbar">
          <div className="grid gap-1">
          {RAIL_ITEMS.map((item) => {
            const active = activeSection === item.id;
            const Icon = item.icon;
            const content = (
              <>
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-white/[0.07] bg-black/20">
                  <Icon className="h-4 w-4" style={{ color: active ? item.accent : undefined }} />
                </span>
                <span className={expanded ? "text-left" : "sr-only"}>
                  <span className="block text-[10px] font-semibold uppercase tracking-[0.14em]">
                    {item.label}
                  </span>
                  <span className="mt-0.5 block font-mono text-[8px] tracking-[0.18em] text-slate-600">
                    {item.number}
                  </span>
                </span>
                {!expanded && (
                  <span className="absolute bottom-1 right-1 font-mono text-[8px] tracking-[0.14em] text-slate-600">
                    {item.number}
                  </span>
                )}
                {active && !item.href && (
                  <span className="absolute inset-y-2 right-0 w-[2px]" style={{ backgroundColor: item.accent }} />
                )}
              </>
            );
            const className = `group relative flex h-12 cursor-pointer items-center border font-mono text-[9px] tracking-[0.12em] transition-all duration-200 ${
              expanded ? "w-full justify-start gap-3 rounded-xl px-2.5" : "w-full justify-center rounded-xl px-2"
            } ${
              active && !item.href
                ? "border-cyan-300/25 bg-cyan-300/[0.08] text-white shadow-[inset_2px_0_0_#67e8f9]"
                : "border-transparent bg-white/[0.02] text-slate-500 hover:border-white/10 hover:bg-white/[0.05] hover:text-slate-200"
            }`;

            const itemButton = item.href ? (
              <Link key={item.id} href={item.href} aria-label={`Open ${item.label}`} title={item.label} className={className}>
                {content}
                <ArrowUpRight className={expanded ? "ml-auto h-3.5 w-3.5 text-slate-600" : "sr-only"} />
              </Link>
            ) : (
              <button key={item.id} type="button" onClick={() => selectSection(item.id)} aria-label={`Open ${item.label}`} title={item.label} aria-current={active ? "page" : undefined} className={className}>
                {content}
              </button>
            );

            const subItems = active ? SUBNAV[item.id] : undefined;
            return (
              <div key={`${item.id}-group`}>
                {itemButton}
                {expanded && active && subItems && (
                  <div className="ml-3 mt-1 max-h-[min(38vh,360px)] overflow-y-auto rounded-xl border-l border-white/[0.09] pl-2 custom-scrollbar">
                    {subItems.map((subItem, index) => {
                      const selected = activeTabs[item.id] === subItem.key;
                      return (
                        <button
                          key={subItem.key}
                          type="button"
                          onClick={() => selectTab(item.id, subItem.key)}
                          title={subItem.summary}
                          aria-current={selected ? "page" : undefined}
                          className={`relative flex min-h-9 w-full cursor-pointer items-center gap-2 rounded-lg border-l px-2 text-left font-mono text-[9px] uppercase tracking-[0.1em] transition-colors ${
                            selected
                              ? "border-cyan-300 bg-cyan-400/[0.08] text-white"
                              : "border-transparent text-slate-500 hover:border-white/20 hover:bg-white/[0.04] hover:text-slate-200"
                          }`}
                        >
                          <span className="w-4 shrink-0 text-[8px] text-slate-600">
                            {String(index + 1).padStart(2, "0")}
                          </span>
                          <span className="truncate">{subItem.label}</span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
          </div>
        </nav>

        <div className="mt-auto border-t border-white/[0.08] pt-3">
          {expanded ? (
            <div className="grid gap-2">
              <Link href="/auth/login" className="rounded-xl border border-white/[0.1] px-3 py-2.5 text-center text-[10px] font-medium text-slate-300 transition-colors hover:border-cyan-400/30 hover:text-white">
                Sign in
              </Link>
              <Link href="/auth/signup" className="rounded-xl border border-cyan-300/30 bg-cyan-400 px-3 py-2.5 text-center text-[10px] font-semibold text-slate-950 transition-colors hover:bg-cyan-300">
                Start building
              </Link>
            </div>
          ) : (
            <Link
              href="/auth/signup"
              aria-label="Start building"
              title="Start building"
              className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/30 bg-cyan-400 text-slate-950 transition-colors hover:bg-cyan-300"
            >
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          )}
        </div>
      </div>
    </aside>
  );
}
