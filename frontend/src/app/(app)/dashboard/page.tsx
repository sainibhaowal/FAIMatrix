"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
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

type ScorecardMetrics = {
  graph_id: string;
  graph_version: number;
  graph_hash: string;
  dimension_D?: number;
  entropy_H?: number;
  pressure_lambda?: number;
  node_count: number;
  edge_count: number;
  redundancy?: number;
  novelty?: number;
  energy?: number;
  computed_at?: string;
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
  const { data: session } = useSession();
  const { toast } = useToast();

  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [metrics, setMetrics] = useState<ScorecardMetrics | null>(null);
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

  const userId = session?.user?.id;

  // Load data
  const loadData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);

    try {
      const h = await fetchHealth();
      setHealth(h);

      const headers = buildFaimHeaders();
      const graphId = session?.user?.graph_id || "U:DEFAULT";

      // Load metrics scorecard from faim_native v1 API
      try {
        const res = await fetch(`${API_BASE_URL}/metrics/scorecard?graph_id=${graphId}`, {
          headers,
        });
        if (res.ok) {
          setMetrics(await res.json());
        }
      } catch (err) {
        console.warn("[dashboard] Failed to load metrics:", err);
      }

      // Load recent activity from backend
      try {
        const actRes = await fetch(`${API_BASE_URL}/usage/activity/recent${userId ? `?user_id=${userId}` : ""}`, {
          headers,
        });
        if (actRes.ok) {
          setActivity(await actRes.json());
        }
      } catch (err) {
        console.warn("[dashboard] Failed to load activity:", err);
      }
    } catch (e) {
      console.warn("[dashboard] Failed to load data:", e);
      toast.error("Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast, userId, session?.user?.graph_id]);

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
        tenantId={session?.user?.tenant_id || "default"}
      />

      <NeuralCoreHero
        isHealthy={isHealthy}
        nodesCount={metrics?.node_count}
      />

      <DashboardMetrics
        dimensionD={metrics?.dimension_D ?? 0}
        entropyH={metrics?.entropy_H ?? 0}
        nodesCount={metrics?.node_count ?? 0}
        edgeCount={metrics?.edge_count ?? 0}
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
