"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BookOpen, X, ChevronDown } from "lucide-react";

export type TocItem = {
  id: string;
  label: string;
  children?: { id: string; label: string }[];
};

export const K = {
  card: "rounded-[16px] border border-white/8 bg-white/[0.03] p-4",
  sub: "text-[10px] font-medium uppercase tracking-widest text-slate-500",
  mono: "font-mono",
  chip: "rounded-md border border-white/8 bg-white/[0.04] px-1.5 py-0.5 font-mono text-[10px] text-slate-300",
};

export function SectionHeading({
  id,
  kicker,
  title,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 border-b border-white/6 pb-10">
      <div className="mb-5">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-fuchsia-300/80">
          {kicker}
        </p>
        <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">
          {title}
        </h2>
      </div>
      <div className="space-y-4 text-sm leading-relaxed text-slate-300">
        {children}
      </div>
    </section>
  );
}

export function SubHeading({
  id,
  children,
}: {
  id: string;
  children: React.ReactNode;
}) {
  return (
    <h3 id={id} className="scroll-mt-24 pt-5 text-sm font-semibold text-cyan-200">
      {children}
    </h3>
  );
}

export function Callout({
  tone,
  title,
  children,
}: {
  tone: "info" | "success" | "warn";
  title: string;
  children: React.ReactNode;
}) {
  const tones = {
    info: { border: "border-sky-400/30", bg: "bg-sky-400/[0.06]", text: "text-sky-300" },
    success: { border: "border-emerald-400/30", bg: "bg-emerald-400/[0.06]", text: "text-emerald-300" },
    warn: { border: "border-amber-400/30", bg: "bg-amber-400/[0.06]", text: "text-amber-300" },
  } as const;
  const t = tones[tone];
  return (
    <div className={`flex gap-3 rounded-[14px] border ${t.border} ${t.bg} p-4`}>
      <span className={`mt-0.5 shrink-0 text-sm ${t.text}`}>◆</span>
      <div>
        <p className={`text-xs font-semibold ${t.text}`}>{title}</p>
        <div className="mt-1 text-xs leading-relaxed text-slate-300">{children}</div>
      </div>
    </div>
  );
}

export interface DTableRow {
  key?: string;
  cells: React.ReactNode[];
}

export function DTable({
  head,
  rows,
}: {
  head: string[];
  rows: DTableRow[];
}) {
  return (
    <div className="overflow-x-auto rounded-[14px] border border-white/8">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-white/8 text-[10px] uppercase tracking-widest text-slate-500">
            {head.map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.key ?? String(i)} className="border-b border-white/4 last:border-b-0 text-slate-300">
              {row.cells.map((cell, j) => (
                <td key={j} className="px-3 py-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ManualShell({
  open,
  onClose,
  title,
  subtitle,
  toc,
  accent = "#e879f9",
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle: string;
  toc: TocItem[];
  accent?: string;
  children: React.ReactNode;
}) {
  const [activeId, setActiveId] = useState<string>(toc[0]?.id ?? "");
  const contentRef = useRef<HTMLDivElement | null>(null);

  const allIds = useMemo(() => {
    const ids: string[] = [];
    for (const item of toc) {
      ids.push(item.id);
      for (const child of item.children ?? []) ids.push(child.id);
    }
    return ids;
  }, [toc]);

  useEffect(() => {
    if (!open) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveId(entry.target.id);
        }
      },
      { root: contentRef.current, rootMargin: "-10% 0px -75% 0px" },
    );
    for (const id of allIds) {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    }
    return () => observer.disconnect();
  }, [allIds, open]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  const scrollTo = (id: string) => {
    setActiveId(id);
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[100] flex flex-col bg-[#04060c]/97 backdrop-blur-xl text-slate-100">
      <div className="flex items-center justify-between gap-4 border-b border-white/8 bg-black/40 px-5 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border bg-white/[0.04]"
            style={{ borderColor: `${accent}4D`, color: accent }}
          >
            <BookOpen size={16} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-tight text-white">{title}</p>
            <p className="truncate font-mono text-[10px] uppercase tracking-widest text-slate-500">
              {subtitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden sm:inline-flex rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-2 py-1 font-mono text-[10px] text-emerald-300">
            READ-ONLY
          </span>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
            aria-label="Close manual"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-[300px] shrink-0 border-r border-white/8 bg-black/30 lg:block overflow-y-auto custom-scrollbar">
          <div className="p-4">
            <p className="px-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Table of Contents
            </p>
            <nav className="mt-3 space-y-1">
              {toc.map((item) => {
                const active = activeId === item.id;
                const childActive = item.children?.some((c) => c.id === activeId);
                return (
                  <div key={item.id}>
                    <button
                      type="button"
                      onClick={() => scrollTo(item.id)}
                      className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                        active || childActive
                          ? "bg-fuchsia-400/10 text-fuchsia-200"
                          : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                      }`}
                    >
                      <span className={active || childActive ? "font-semibold" : ""}>
                        {item.label}
                      </span>
                      {childActive && !active && (
                        <span className="h-1.5 w-1.5 rounded-full bg-fuchsia-400" />
                      )}
                    </button>
                    {item.children && (active || childActive) && (
                      <div className="ml-3 space-y-0.5 border-l border-white/8 pl-2">
                        {item.children.map((child) => (
                          <button
                            key={child.id}
                            type="button"
                            onClick={() => scrollTo(child.id)}
                            className={`block w-full rounded-md px-2 py-1.5 text-left text-[11px] transition-colors ${
                              activeId === child.id
                                ? "bg-cyan-400/10 text-cyan-200 font-medium"
                                : "text-slate-500 hover:text-slate-300"
                            }`}
                          >
                            {child.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </nav>
          </div>
        </aside>

        <div className="lg:hidden border-b border-white/8 bg-black/30 px-4 py-2 overflow-x-auto custom-scrollbar">
          <div className="flex gap-1.5">
            {toc.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => scrollTo(item.id)}
                className={`shrink-0 rounded-lg border px-2.5 py-1.5 text-[10px] font-mono transition-colors ${
                  activeId === item.id
                    ? "border-fuchsia-400/40 bg-fuchsia-400/10 text-fuchsia-200"
                    : "border-white/10 text-slate-400"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        <main ref={contentRef} className="min-w-0 flex-1 overflow-y-auto custom-scrollbar">
          <div className="mx-auto max-w-4xl space-y-10 px-5 py-8 sm:px-8">{children}</div>
        </main>
      </div>
    </div>,
    document.body,
  );
}

export function Chevron() {
  return <ChevronDown size={14} className="text-slate-600" />;
}
