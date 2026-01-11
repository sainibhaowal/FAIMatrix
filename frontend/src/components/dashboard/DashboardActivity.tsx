"use client";

import React from "react";
import { Activity, Clock, Upload, Sparkles, Network } from "lucide-react";
import { Card, Badge, EmptyState } from "@/components/ui";

type ActivityItem = {
  id: string;
  type: "upload" | "evolution" | "graph";
  title: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

type DailyActivity = {
  date: string;
  count: number;
};

interface DashboardActivityProps {
  dailyActivity: DailyActivity[];
  recentActivity: ActivityItem[];
}

export function DashboardActivity({ dailyActivity, recentActivity }: DashboardActivityProps) {
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      {/* Activity Chart */}
      <Card className="lg:col-span-3" glow>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Activity size={16} className="text-[var(--faim-primary)]" />
            Activity (7 days)
          </h2>
          <Badge variant="primary" size="xs">Live</Badge>
        </div>
        <ActivityChart data={dailyActivity} />
      </Card>

      {/* Recent Activity */}
      <Card className="lg:col-span-2" glow>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Clock size={16} className="text-[var(--faim-primary)]" />
            Recent Activity
          </h2>
        </div>
        <RecentActivityList items={recentActivity} />
      </Card>
    </div>
  );
}

function ActivityChart({ data }: { data: DailyActivity[] }) {
  if (!data.length) {
    return (
      <EmptyState
        icon="inbox"
        title="No activity yet"
        description="Upload documents to see your activity"
        size="sm"
      />
    );
  }

  const max = Math.max(...data.map((d) => d.count), 1);

  return (
    <div className="flex items-end justify-between gap-2 h-32">
      {data.map((day, i) => {
        const height = (day.count / max) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-2">
            <div className="w-full flex flex-col items-center justify-end h-24">
              <div
                className={[
                  "w-full max-w-8 rounded-t-md",
                  "bg-gradient-to-t from-[var(--faim-primary)] to-[var(--faim-secondary)]",
                  "transition-all duration-500 hover:opacity-80",
                  "shadow-[0_0_12px_rgba(34,211,238,0.3)]",
                ].join(" ")}
                style={{ height: `${Math.max(height, 4)}%` }}
                title={`${day.count} activities`}
              />
            </div>
            <span className="text-[10px] text-[var(--text-muted)]">{day.date}</span>
          </div>
        );
      })}
    </div>
  );
}

function RecentActivityList({ items }: { items: ActivityItem[] }) {
  if (!items.length) {
    return (
      <EmptyState
        icon="inbox"
        title="No recent activity"
        description="Your activity will appear here"
        size="sm"
      />
    );
  }

  const iconMap = {

    upload: <Upload size={14} className="text-[var(--faim-secondary)]" />,
    evolution: <Sparkles size={14} className="text-[var(--faim-accent)]" />,
    graph: <Network size={14} className="text-[var(--faim-success)]" />,
  };

  return (
    <div className="space-y-3 max-h-[200px] overflow-y-auto pr-1">
      {items.map((item) => (
        <div key={item.id} className="flex items-start gap-3 group">
          <div className="flex-shrink-0 mt-0.5">{iconMap[item.type]}</div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[var(--text-primary)] truncate group-hover:text-[var(--faim-primary)] transition-colors">
              {item.title}
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              {formatRelativeTime(item.timestamp)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diff = now - then;

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(timestamp).toLocaleDateString();
}
