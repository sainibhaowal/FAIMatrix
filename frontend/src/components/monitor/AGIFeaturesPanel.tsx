"use client";

/**
 * FAIM AGI Features Panel
 *
 * NEW COMPONENT - Does not modify any existing code.
 * Provides UI for all 6 AGI features:
 * 1. Batch Upload with Progress
 * 2. Cross-document Inference
 * 3. Semantic Clustering
 * 4. Hidden Insights
 * 5. Image Understanding
 * 6. Self-Inventing Concepts
 *
 * Uses UserContext for multi-tenant user isolation.
 */

import React, { useState, useCallback } from "react";
import {
  Upload,
  Link2,
  Layers,
  Lightbulb,
  Image as ImageIcon,
  Sparkles,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { useUserIds } from "@/contexts/UserContext";

// Types
interface FeatureResult {
  success: boolean;
  data?: any;
  error?: string;
  loading: boolean;
}

interface InferenceLink {
  source: string;
  target: string;
  similarity: number;
}

interface Cluster {
  cluster_id: string;
  label: string;
  size: number;
  coherence: number;
}

interface Insight {
  insight_id: string;
  title: string;
  description: string;
  type: string;
  surprise_score: number;
}

interface Invention {
  concept_id: string;
  title: string;
  description: string;
  confidence: number;
}

// Fallback graph ID only used if user context fails
const FALLBACK_GRAPH_ID = "U:faim-universe";

export default function AGIFeaturesPanel() {
  // Use authenticated user's graph ID from context
  const {
    graphId: userGraphId,
    isLoading: userLoading,
  } = useUserIds();
  const graphId = userGraphId || FALLBACK_GRAPH_ID;

  // Results state for each feature
  const [batchResult, setBatchResult] = useState<FeatureResult>({
    loading: false,
    success: false,
  });
  const [inferenceResult, setInferenceResult] = useState<FeatureResult>({
    loading: false,
    success: false,
  });
  const [clusterResult, setClusterResult] = useState<FeatureResult>({
    loading: false,
    success: false,
  });
  const [insightResult, setInsightResult] = useState<FeatureResult>({
    loading: false,
    success: false,
  });
  const [inventionResult, setInventionResult] = useState<FeatureResult>({
    loading: false,
    success: false,
  });

  // File upload state
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  // ========== Feature Handlers ==========

  const handleBatchUpload = useCallback(async () => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    setBatchResult({ loading: true, success: false });
    setUploadProgress(0);

    try {
      const formData = new FormData();
      Array.from(selectedFiles).forEach((file) => {
        formData.append("files", file);
      });
      formData.append("graph_id", graphId);

      const res = await fetch("/api/v1/batch/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (data.batch_id) {
        // Poll for progress
        const pollProgress = async () => {
          try {
            const statusRes = await fetch(
              `/api/v1/batch/${data.batch_id}/status`,
            );
            const status = await statusRes.json();

            const completed = status.completed_files + status.failed_files;
            const progress = Math.round((completed / status.total_files) * 100);
            setUploadProgress(progress);

            if (
              status.status === "completed" ||
              status.status === "completed_with_errors"
            ) {
              setBatchResult({ loading: false, success: true, data: status });
            } else {
              setTimeout(pollProgress, 1000);
            }
          } catch {
            setBatchResult({
              loading: false,
              success: false,
              error: "Progress check failed",
            });
          }
        };

        pollProgress();
      } else {
        setBatchResult({
          loading: false,
          success: false,
          error: data.detail || "Upload failed",
        });
      }
    } catch (e: any) {
      setBatchResult({ loading: false, success: false, error: e.message });
    }
  }, [selectedFiles, graphId]);

  const handleRunInference = useCallback(async () => {
    setInferenceResult({ loading: true, success: false });

    try {
      const res = await fetch(`/api/v1/graphs/${graphId}/infer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ min_similarity: 0.7, max_results: 20 }),
      });

      const data = await res.json();
      setInferenceResult({ loading: false, success: true, data });
    } catch (e: any) {
      setInferenceResult({ loading: false, success: false, error: e.message });
    }
  }, [graphId]);

  const handleRunClustering = useCallback(async () => {
    setClusterResult({ loading: true, success: false });

    try {
      const res = await fetch(`/api/v1/graphs/${graphId}/cluster`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ min_cluster_size: 2, use_llm_labels: true }),
      });

      const data = await res.json();
      setClusterResult({ loading: false, success: true, data });
    } catch (e: any) {
      setClusterResult({ loading: false, success: false, error: e.message });
    }
  }, [graphId]);

  const handleDiscoverInsights = useCallback(async () => {
    setInsightResult({ loading: true, success: false });

    try {
      const res = await fetch(`/api/v1/graphs/${graphId}/discover-insights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_insights: 10, min_surprise: 0.3 }),
      });

      const data = await res.json();
      setInsightResult({ loading: false, success: true, data });
    } catch (e: any) {
      setInsightResult({ loading: false, success: false, error: e.message });
    }
  }, [graphId]);

  const handleRunInvention = useCallback(async () => {
    setInventionResult({ loading: true, success: false });

    try {
      const res = await fetch(`/api/v1/graphs/${graphId}/invent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_inventions: 3, create_nodes: true }),
      });

      const data = await res.json();
      setInventionResult({ loading: false, success: true, data });
    } catch (e: any) {
      setInventionResult({ loading: false, success: false, error: e.message });
    }
  }, [graphId]);

  // ========== Render Helpers ==========

  const StatusIcon = ({ result }: { result: FeatureResult }) => {
    if (result.loading)
      return <Loader2 className="h-4 w-4 animate-spin text-cyan-400" />;
    if (result.success)
      return <CheckCircle className="h-4 w-4 text-emerald-400" />;
    if (result.error) return <AlertCircle className="h-4 w-4 text-red-400" />;
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-violet-400" />
        <h2 className="text-sm font-semibold text-slate-100">Intelligence Features</h2>
      </div>

      {/* Feature Grid */}
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {/* 1. Batch Upload */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Upload className="h-4 w-4 text-cyan-400" />
              <span className="text-xs font-semibold text-slate-200">
                Batch Upload
              </span>
            </div>
            <StatusIcon result={batchResult} />
          </div>

          <input
            type="file"
            multiple
            onChange={(e) => setSelectedFiles(e.target.files)}
            className="mb-2 w-full text-[10px] text-slate-400 file:mr-2 file:rounded file:border-0 file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:text-slate-300"
          />

          {batchResult.loading && (
            <div className="mb-2">
              <div className="h-1 w-full rounded bg-slate-800">
                <div
                  className="h-1 rounded bg-cyan-500 transition-all"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-500">
                {uploadProgress}%
              </span>
            </div>
          )}

          <button
            onClick={handleBatchUpload}
            disabled={batchResult.loading || !selectedFiles}
            className="w-full rounded-lg bg-cyan-600/20 px-3 py-1.5 text-[10px] font-medium text-cyan-300 hover:bg-cyan-600/30 disabled:opacity-50"
          >
            {batchResult.loading ? "Uploading..." : "Upload Files"}
          </button>

          {batchResult.data && (
            <p className="mt-2 text-[10px] text-emerald-400">
              ✓ {batchResult.data.completed_files} files processed
            </p>
          )}
        </div>

        {/* 2. Cross-doc Inference */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Link2 className="h-4 w-4 text-blue-400" />
              <span className="text-xs font-semibold text-slate-200">
                Cross-doc Inference
              </span>
            </div>
            <StatusIcon result={inferenceResult} />
          </div>

          <p className="mb-3 text-[10px] text-slate-500">
            Find connections between different documents.
          </p>

          <button
            onClick={handleRunInference}
            disabled={inferenceResult.loading}
            className="w-full rounded-lg bg-blue-600/20 px-3 py-1.5 text-[10px] font-medium text-blue-300 hover:bg-blue-600/30 disabled:opacity-50"
          >
            {inferenceResult.loading ? "Analyzing..." : "Run Inference"}
          </button>

          {inferenceResult.data?.inferences && (
            <div className="mt-2 max-h-20 overflow-y-auto">
              {inferenceResult.data.inferences
                .slice(0, 3)
                .map((inf: InferenceLink, i: number) => (
                  <p key={i} className="text-[9px] text-slate-400 truncate">
                    {inf.source.slice(0, 8)}↔{inf.target.slice(0, 8)} (
                    {(inf.similarity * 100).toFixed(0)}%)
                  </p>
                ))}
              {inferenceResult.data.inferences_found > 3 && (
                <p className="text-[9px] text-slate-500">
                  +{inferenceResult.data.inferences_found - 3} more
                </p>
              )}
            </div>
          )}
        </div>

        {/* 3. Semantic Clustering */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-purple-400" />
              <span className="text-xs font-semibold text-slate-200">
                Clustering
              </span>
            </div>
            <StatusIcon result={clusterResult} />
          </div>

          <p className="mb-3 text-[10px] text-slate-500">
            Group related concepts automatically.
          </p>

          <button
            onClick={handleRunClustering}
            disabled={clusterResult.loading}
            className="w-full rounded-lg bg-purple-600/20 px-3 py-1.5 text-[10px] font-medium text-purple-300 hover:bg-purple-600/30 disabled:opacity-50"
          >
            {clusterResult.loading ? "Clustering..." : "Run Clustering"}
          </button>

          {clusterResult.data?.clusters && (
            <div className="mt-2 max-h-20 overflow-y-auto">
              {clusterResult.data.clusters
                .slice(0, 3)
                .map((c: Cluster, i: number) => (
                  <p key={i} className="text-[9px] text-slate-400 truncate">
                    {c.label} ({c.size} nodes)
                  </p>
                ))}
              {clusterResult.data.n_clusters > 3 && (
                <p className="text-[9px] text-slate-500">
                  +{clusterResult.data.n_clusters - 3} more
                </p>
              )}
            </div>
          )}
        </div>

        {/* 4. Hidden Insights */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-400" />
              <span className="text-xs font-semibold text-slate-200">
                Hidden Insights
              </span>
            </div>
            <StatusIcon result={insightResult} />
          </div>

          <p className="mb-3 text-[10px] text-slate-500">
            Discover surprising patterns.
          </p>

          <button
            onClick={handleDiscoverInsights}
            disabled={insightResult.loading}
            className="w-full rounded-lg bg-yellow-600/20 px-3 py-1.5 text-[10px] font-medium text-yellow-300 hover:bg-yellow-600/30 disabled:opacity-50"
          >
            {insightResult.loading ? "Discovering..." : "Discover Insights"}
          </button>

          {insightResult.data?.insights && (
            <div className="mt-2 max-h-20 overflow-y-auto">
              {insightResult.data.insights
                .slice(0, 3)
                .map((ins: Insight, i: number) => (
                  <p key={i} className="text-[9px] text-slate-400 truncate">
                    💡 {ins.title}
                  </p>
                ))}
              {insightResult.data.insights_found > 3 && (
                <p className="text-[9px] text-slate-500">
                  +{insightResult.data.insights_found - 3} more
                </p>
              )}
            </div>
          )}
        </div>

        {/* 5. Image Understanding */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ImageIcon className="h-4 w-4 text-pink-400" />
              <span className="text-xs font-semibold text-slate-200">
                Image Understanding
              </span>
            </div>
          </div>

          <p className="mb-3 text-[10px] text-slate-500">
            Extract meaning from document images.
          </p>

          <p className="text-[9px] text-slate-600 italic">
            Images are auto-processed during batch upload when vision API is
            configured.
          </p>
        </div>

        {/* 6. Self-Inventing */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-semibold text-slate-200">
                Self-Inventing
              </span>
            </div>
            <StatusIcon result={inventionResult} />
          </div>

          <p className="mb-3 text-[10px] text-slate-500">
            Create NEW concepts from existing knowledge.
          </p>

          <button
            onClick={handleRunInvention}
            disabled={inventionResult.loading}
            className="w-full rounded-lg bg-emerald-600/20 px-3 py-1.5 text-[10px] font-medium text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-50"
          >
            {inventionResult.loading ? "Inventing..." : "Run Invention"}
          </button>

          {inventionResult.data?.inventions && (
            <div className="mt-2 max-h-20 overflow-y-auto">
              {inventionResult.data.inventions
                .slice(0, 3)
                .map((inv: Invention, i: number) => (
                  <p key={i} className="text-[9px] text-slate-400 truncate">
                    ✨ {inv.title} ({(inv.confidence * 100).toFixed(0)}%)
                  </p>
                ))}
              {inventionResult.data.inventions_created > 3 && (
                <p className="text-[9px] text-slate-500">
                  +{inventionResult.data.inventions_created - 3} more
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {(batchResult.error ||
        inferenceResult.error ||
        clusterResult.error ||
        insightResult.error ||
        inventionResult.error) && (
        <div className="rounded-lg border border-red-900/50 bg-red-950/20 p-3">
          <p className="text-[10px] text-red-400">
            {batchResult.error ||
              inferenceResult.error ||
              clusterResult.error ||
              insightResult.error ||
              inventionResult.error}
          </p>
        </div>
      )}
    </div>
  );
}
