"use client";

import React, { useEffect, useState } from 'react';
import { MaturityGauge } from './MaturityGauge';
import { useUserIds } from '@/contexts/UserContext';
import { getSession } from 'next-auth/react';

interface MaturityMetrics {
  fractal_dimension: number;
  compression_ratio: number;
  redundancy: number;
}

export function MaturityDashboard() {
  const [metrics, setMetrics] = useState<MaturityMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const { graphId } = useUserIds();

  useEffect(() => {
    if (!graphId) return;

    const loadMetrics = async () => {
      try {
        const session = await getSession();
        const authHeaders: Record<string, string> = {};
        if (session && (session as any).accessToken) {
          authHeaders["Authorization"] = `Bearer ${(session as any).accessToken}`;
        }

        const res = await fetch(`/api/v1/graphs/${encodeURIComponent(graphId)}/metrics`, {
          headers: authHeaders,
        });
        
        if (res.ok) {
          const data = await res.json();
          setMetrics({
            fractal_dimension: data.fractal_dimension || 0,
            compression_ratio: data.compression_ratio || 0,
            redundancy: data.redundancy || 0,
          });
        }
      } catch (err) {
        console.error("Failed to load maturity metrics:", err);
      } finally {
        setLoading(false);
      }
    };

    loadMetrics();
    const interval = setInterval(loadMetrics, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [graphId]);

  if (loading) return (
    <div className="h-48 flex items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500/20 border-t-cyan-500" />
    </div>
  );

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <MaturityGauge 
        value={metrics?.fractal_dimension || 0} 
        min={0} 
        max={5} 
        label="Fractal Dimension (D)" 
        target={2.5}
        color="#8b5cf6"
      />
      <MaturityGauge 
        value={metrics?.compression_ratio || 1} 
        min={1} 
        max={10} 
        label="Compression Ratio (CR)" 
        unit="x"
        color="#22d3ee"
      />
      <MaturityGauge 
        value={(metrics?.redundancy || 0) * 100} 
        min={0} 
        max={100} 
        label="Redundancy Index (R)" 
        unit="%"
        color="#a855f7"
      />
    </div>
  );
}
