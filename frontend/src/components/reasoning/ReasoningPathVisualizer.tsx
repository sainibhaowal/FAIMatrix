/**
 * Reasoning path visualizer component
 * Shows multi-hop reasoning chains with confidence scores
 */

import React from "react";
import { Card, CardContent, CardHeader, Badge } from "@/components/ui";
import { ChevronRight, GitCommit, ArrowRight } from "lucide-react";

interface Hop {
  node_id: string;
  node_label: string;
  edge_type: string;
  edge_weight: number;
  next_node_id: string;
  next_node_label: string;
  reasoning: string;
}

interface ReasoningPath {
  path_id: string;
  start_node: string;
  end_node: string;
  hops: Hop[];
  confidence: number;
  path_length: number;
  explanation: string;
}

interface ReasoningPathVisualizerProps {
  paths: ReasoningPath[];
  selectedPathId?: string;
  onPathSelect?: (pathId: string) => void;
  className?: string;
}

export function ReasoningPathVisualizer({
  paths,
  selectedPathId,
  onPathSelect,
  className = "",
}: ReasoningPathVisualizerProps) {
  if (!paths || paths.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <p className="text-muted-foreground text-center">
            No reasoning paths available
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {paths.map((path) => (
        <Card
          key={path.path_id}
          className={`cursor-pointer transition-all hover:border-primary ${
            selectedPathId === path.path_id
              ? "border-primary ring-1 ring-primary"
              : ""
          }`}
          onClick={() => onPathSelect?.(path.path_id)}
        >
          <CardHeader
            title={`Path (${path.path_length} hops)`}
            action={
              <Badge
                variant={
                  path.confidence > 0.8
                    ? "primary"
                    : path.confidence > 0.5
                      ? "secondary"
                      : "outline"
                }
              >
                {(path.confidence * 100).toFixed(0)}%
              </Badge>
            }
          />
          <CardContent>
            <div className="space-y-3">
              {/* Path visualization */}
              <div className="flex items-center gap-2 text-sm">
                <GitCommit className="w-4 h-4 text-muted-foreground" />
                <span className="font-medium truncate max-w-[150px]">
                  {path.hops[0]?.node_label || "Start"}
                </span>

                {path.hops.map((hop, idx) => (
                  <React.Fragment key={idx}>
                    <div className="flex items-center gap-1">
                      <ArrowRight className="w-3 h-3 text-muted-foreground" />
                      <Badge variant="outline" className="text-xs">
                        {hop.edge_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {(hop.edge_weight * 100).toFixed(0)}%
                      </span>
                    </div>
                    <ChevronRight className="w-3 h-3 text-muted-foreground" />
                    <span className="truncate max-w-[150px]">
                      {hop.next_node_label}
                    </span>
                  </React.Fragment>
                ))}
              </div>

              {/* Explanation */}
              {selectedPathId === path.path_id && (
                <div className="mt-3 p-3 bg-muted rounded-md text-sm">
                  <pre className="whitespace-pre-wrap font-sans text-xs">
                    {path.explanation}
                  </pre>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
