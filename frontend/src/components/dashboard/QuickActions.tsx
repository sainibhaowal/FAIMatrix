"use client";

import React from "react";
import Link from "next/link";
import { Upload, Network, Sparkles, ArrowRight } from "lucide-react";

export function QuickActions() {
  return (
    <section>
      <h2 className="text-sm font-semibold text-[var(--text-secondary)] mb-3 flex items-center gap-2">
        <Sparkles size={14} />
        Quick Actions
        <span className="text-[var(--text-muted)] font-normal ml-2 text-xs">
          Press key to navigate
        </span>
      </h2>
      <div className="grid gap-3 md:grid-cols-3">

        <QuickActionCard
          href="/dashboard/storage"
          title="Upload Document"
          description="Add files to your knowledge base"
          icon={<Upload size={24} />}
          shortcut="U"
          color="violet"
        />
        <QuickActionCard
          href="/dashboard/graph"
          title="View Graph"
          description="Explore your knowledge connections"
          icon={<Network size={24} />}
          shortcut="G"
          color="pink"
        />
      </div>

      {/* Keyboard shortcuts hint */}
      <footer className="flex items-center justify-center gap-6 py-4 text-xs text-[var(--text-muted)] mt-4">

        <span className="flex items-center gap-1.5">
          <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border-default)] font-mono">U</kbd>
          Upload
        </span>
        <span className="flex items-center gap-1.5">
          <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border-default)] font-mono">G</kbd>
          Graph
        </span>
        <span className="flex items-center gap-1.5">
          <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border-default)] font-mono">R</kbd>
          Refresh
        </span>
        <span className="flex items-center gap-1.5">
          <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border-default)] font-mono">⌘K</kbd>
          Command
        </span>
      </footer>
    </section>
  );
}

function QuickActionCard({
  href,
  title,
  description,
  icon,
  shortcut,
  color = "cyan",
}: {
  href: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  shortcut: string;
  color?: "cyan" | "violet" | "pink";
}) {
  const colorMap = {
    cyan: {
      icon: "text-[var(--faim-primary)]",
      hover: "group-hover:border-[var(--faim-primary)]/50",
      glow: "group-hover:shadow-[var(--glow-cyan)]",
    },
    violet: {
      icon: "text-[var(--faim-secondary)]",
      hover: "group-hover:border-[var(--faim-secondary)]/50",
      glow: "group-hover:shadow-[var(--glow-violet)]",
    },
    pink: {
      icon: "text-[var(--faim-accent)]",
      hover: "group-hover:border-[var(--faim-accent)]/50",
      glow: "group-hover:shadow-[0_0_20px_rgba(244,114,182,0.15)]",
    },
  };

  const colors = colorMap[color];

  return (
    <Link
      href={href}
      className={[
        "group relative block rounded-2xl",
        "border border-[var(--border-default)]",
        "bg-[var(--surface-1)]",
        "p-5 transition-all duration-300",
        colors.hover,
        colors.glow,
        "hover:-translate-y-1",
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <div className={["opacity-80 group-hover:opacity-100 transition-opacity", colors.icon].join(" ")}>
          {icon}
        </div>
        <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-2)] border border-[var(--border-default)] text-[10px] font-mono text-[var(--text-muted)] group-hover:text-[var(--text-primary)] group-hover:border-[var(--border-primary)] transition-colors">
          {shortcut}
        </kbd>
      </div>
      <div className="mt-4">
        <div className="text-sm font-semibold text-[var(--text-primary)] group-hover:text-[var(--faim-primary)] transition-colors">
          {title}
        </div>
        <div className="text-xs text-[var(--text-tertiary)] mt-1">{description}</div>
      </div>
      <ArrowRight
        size={16}
        className="absolute bottom-5 right-5 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"
      />
    </Link>
  );
}
