/**
 * Reasoning health monitoring dashboard
 * Shows system metrics and recommendations
 */

import React from "react";
import {
  Card,
  CardContent,
  CardHeader,
  Badge,
  Progress,
} from "@/components/ui";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  Activity,
  Clock,
  Brain,
} from "lucide-react";

interface HealthMetrics {
  queries_analyzed: number;
  avg_response_time_ms: number;
  avg_confidence: number;
  high_confidence_rate: number;
  low_confidence_rate: number;
  user_satisfaction: number;
  correction_rate: number;
  avg_hops_used: number;
  multi_hop_usage_rate: number;
  timeout_rate: number;
  empty_result_rate: number;
  contradiction_rate: number;
  is_healthy: boolean;
}

interface HealthDashboardProps {
  metrics: HealthMetrics;
  className?: string;
}

export function HealthDashboard({
  metrics,
  className = "",
}: HealthDashboardProps) {
  const getTrendIcon = (
    value: number,
    threshold: number,
    higherIsBetter: boolean = true,
  ) => {
    if (higherIsBetter) {
      if (value >= threshold * 1.1)
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      if (value <= threshold * 0.9)
        return <TrendingDown className="w-4 h-4 text-red-500" />;
    } else {
      if (value <= threshold * 0.9)
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      if (value >= threshold * 1.1)
        return <TrendingDown className="w-4 h-4 text-red-500" />;
    }
    return <Minus className="w-4 h-4 text-yellow-500" />;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Overall health */}
      <Card
        className={metrics.is_healthy ? "border-green-500" : "border-red-500"}
      >
        <CardHeader
          title="System Health"
          action={
            <Badge variant={metrics.is_healthy ? "success" : "error"}>
              {metrics.is_healthy ? "Healthy" : "Degraded"}
            </Badge>
          }
        >
          <div className="flex items-center gap-2 mt-1">
            <Activity className="w-5 h-5" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* User satisfaction */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">User Satisfaction</span>
                {getTrendIcon(metrics.user_satisfaction, 0.7)}
              </div>
              <Progress value={metrics.user_satisfaction * 100} />
              <p className="text-xs text-muted-foreground">
                {(metrics.user_satisfaction * 100).toFixed(0)}%
              </p>
            </div>

            {/* Confidence */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Avg Confidence</span>
                {getTrendIcon(metrics.avg_confidence, 0.7)}
              </div>
              <Progress value={metrics.avg_confidence * 100} />
              <p className="text-xs text-muted-foreground">
                {(metrics.avg_confidence * 100).toFixed(0)}%
              </p>
            </div>

            {/* Response time */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Response Time</span>
                <Clock className="w-4 h-4" />
              </div>
              <Progress
                value={Math.max(0, 100 - metrics.avg_response_time_ms / 10)}
                className={
                  metrics.avg_response_time_ms > 500 ? "text-red-500" : ""
                }
              />
              <p className="text-xs text-muted-foreground">
                {metrics.avg_response_time_ms.toFixed(0)}ms
              </p>
            </div>

            {/* Multi-hop usage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Multi-hop Usage</span>
                <Brain className="w-4 h-4" />
              </div>
              <Progress value={metrics.multi_hop_usage_rate * 100} />
              <p className="text-xs text-muted-foreground">
                {(metrics.multi_hop_usage_rate * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detailed metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader title="Quality Distribution" className="text-sm pb-2" />
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>High confidence</span>
              <span className="text-green-600">
                {(metrics.high_confidence_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Low confidence</span>
              <span className="text-red-600">
                {(metrics.low_confidence_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Corrections needed</span>
              <span
                className={metrics.correction_rate > 0.3 ? "text-red-600" : ""}
              >
                {(metrics.correction_rate * 100).toFixed(0)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Error Rates" className="text-sm pb-2" />
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Timeouts</span>
              <span
                className={metrics.timeout_rate > 0.1 ? "text-red-600" : ""}
              >
                {(metrics.timeout_rate * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Empty results</span>
              <span>{(metrics.empty_result_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Contradictions</span>
              <span
                className={
                  metrics.contradiction_rate > 0.1 ? "text-yellow-600" : ""
                }
              >
                {(metrics.contradiction_rate * 100).toFixed(1)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Activity" className="text-sm pb-2" />
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Queries analyzed</span>
              <span>{metrics.queries_analyzed}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Avg hops used</span>
              <span>{metrics.avg_hops_used.toFixed(1)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Multi-hop rate</span>
              <span>{(metrics.multi_hop_usage_rate * 100).toFixed(0)}%</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
