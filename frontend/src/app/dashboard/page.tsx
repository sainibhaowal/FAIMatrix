"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { Skeleton, Card, SkeletonText } from "@/components/ui";
import {
  API_BASE_URL,
  fetchHealth,
  type HealthStatus,
  buildFaimHeaders,
} from "@/lib/api";
import {
  DashboardHeader,
  NeuralCoreHero,
  DashboardMetrics,
  UsageSummary,
  DashboardActivity,
  QuickActions,
} from "@/components";

/* =============================================================================
   Types
============================================================================= */

type UsageStats = {
  api_calls_today: number;
  api_calls_month: number;
  storage_bytes: number;
  documents_count: number;
  nodes_count?: number;
  token_usage?: number;
  token_limit?: number;
};

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

/* =============================================================================
   Dashboard Page
============================================================================= */

export default function DashboardPage() {
  const router = useRouter();
  const { toast } = useToast();

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [dailyActivity, setDailyActivity] = useState<DailyActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Personalized greeting based on time
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 5) return { text: "Good night", emoji: "🌙" };
    if (hour < 12) return { text: "Good morning", emoji: "☀️" };
    if (hour < 17) return { text: "Good afternoon", emoji: "🌤️" };
    if (hour < 21) return { text: "Good evening", emoji: "🌅" };
    return { text: "Good night", emoji: "🌙" };
  }, []);

  // Load data
  const loadData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);

    try {
      const h = await fetchHealth();
      setHealth(h);

      // Load usage stats
      try {
        const res = await fetch(`${API_BASE_URL}/usage/summary`, {
          headers: buildFaimHeaders(),
        });
        if (res.ok) {
          setUsage(await res.json());
        }
      } catch {
        // Usage endpoint might not exist yet - use mock data for demo
        setUsage({
          api_calls_today: 42,
          api_calls_month: 1247,
          storage_bytes: 52428800, // 50MB
          documents_count: 18,
          nodes_count: 1247,
          token_usage: 420000,
          token_limit: 1000000,
        });
      }

      // Load recent activity
      try {
        const actRes = await fetch(`${API_BASE_URL}/usage/activity/recent`, {
          headers: buildFaimHeaders(),
        });
        if (actRes.ok) {
          setActivity(await actRes.json());
        }
      } catch {
        // Mock activity data
        setActivity([

          {
            id: "2",
            type: "upload",
            title: "Uploaded: research_notes.pdf",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: "3",
            type: "evolution",
            title: "Memory evolved: 47 nodes consolidated",
            timestamp: new Date(Date.now() - 10800000).toISOString(),
          },
          {
            id: "4",
            type: "graph",
            title: 'New graph created: "Project Alpha"',
            timestamp: new Date(Date.now() - 86400000).toISOString(),
          },
        ]);
      }

      // Load daily activity for chart
      try {
        const chartRes = await fetch(`${API_BASE_URL}/usage/activity/daily`, {
          headers: buildFaimHeaders(),
        });
        if (chartRes.ok) {
          setDailyActivity(await chartRes.json());
        }
      } catch {
        // Mock chart data
        const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
        setDailyActivity(
          days.map((day) => ({
            date: day,
            count: Math.floor(Math.random() * 50) + 5,
          }))
        );
      }
    } catch (e) {
      console.warn("[dashboard] Failed to load data:", e);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if no input is focused
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }


        e.preventDefault();
        router.push("/dashboard/storage");
      if (e.key === "g" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        router.push("/dashboard/graph");
      } else if (e.key === "r" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        loadData(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router, loadData]);

  const isHealthy = health?.status === "ok";
  const tokenPercent = usage?.token_limit
    ? Math.round((usage.token_usage ?? 0) / usage.token_limit * 100)
    : 0;

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-6 pb-8">
      <DashboardHeader
        greeting={greeting}
        isHealthy={isHealthy}
        version={health?.version}
        refreshing={refreshing}
        onRefresh={() => loadData(true)}
      />

      <NeuralCoreHero
        isHealthy={isHealthy}
        nodesCount={usage?.nodes_count}
      />

      <DashboardMetrics
        messagesCount={usage?.api_calls_today ?? 0}
        documentsCount={usage?.documents_count ?? 0}
        nodesCount={usage?.nodes_count ?? 0}
        latency="12ms"
      />

      <UsageSummary
        used={usage?.token_usage ?? 0}
        limit={usage?.token_limit ?? 1000000}
        percent={tokenPercent}
      />

      <DashboardActivity
        dailyActivity={dailyActivity}
        recentActivity={activity}
      />

      <QuickActions />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton height="2rem" width="60%" />
        <Skeleton height="1rem" width="40%" className="mt-2" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <Skeleton circle height={40} />
            <Skeleton height="1.5rem" width="50%" className="mt-3" />
            <Skeleton height="0.75rem" width="30%" className="mt-1" />
          </Card>
        ))}
      </div>
      <Card>
        <Skeleton height="0.875rem" width="30%" />
        <Skeleton height="0.5rem" width="100%" className="mt-3" />
      </Card>
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <Skeleton height="8rem" />
        </Card>
        <Card className="lg:col-span-2">
          <SkeletonText lines={5} />
        </Card>
      </div>
    </div>
  );
}
