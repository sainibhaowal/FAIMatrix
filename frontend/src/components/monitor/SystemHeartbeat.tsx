"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Heart, 
  Activity, 
  Database, 
  GitMerge, 
  Lightbulb, 
  LayoutGrid, 
  Search, 
  Eye, 
  AlertCircle,
  Bell,
  RefreshCw
} from "lucide-react";

interface SystemEvent {
  event: string;
  data: any;
  ts: number;
}

export default function SystemHeartbeat() {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [isLive, setIsLive] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let eventSource: EventSource | null = null;

    const connect = async () => {
      try {
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        const token = (session as any)?.accessToken;
        
        // Construct authenticated URL
        const url = new URL("/api/v1/stream", window.location.origin);
        if (token) url.searchParams.append("token", token);
        
        eventSource = new EventSource(url.toString());

        eventSource.onopen = () => {
          setIsLive(true);
        };

        // Use a buffer to batch events and avoid excessive re-renders
        let buffer: SystemEvent[] = [];
        const flushBuffer = () => {
          if (buffer.length === 0) return;
          setEvents(prev => [...prev, ...buffer].slice(-50));
          buffer = [];
        };

        const interval = setInterval(flushBuffer, 300);

        const handleEvent = (e: MessageEvent, eventName: string) => {
          try {
            const data = JSON.parse(e.data);
            const newEvent: SystemEvent = {
              event: eventName,
              data,
              ts: data.ts || Date.now() / 1000
            };
            
            buffer.push(newEvent);
          } catch (err) {
            console.error("Failed to parse SSE event:", err);
          }
        };

        // Subscriptions
        const eventTypes = [
          "fig_delta", "evolution", "invention", 
          "cluster_updated", "inference_found", "insight_discovered",
          "toast", "error"
        ];

        eventTypes.forEach(type => {
          eventSource?.addEventListener(type, (e) => handleEvent(e as MessageEvent, type));
        });

        eventSource.onerror = (e) => {
          console.error("SSE Connection failed:", e);
          setIsLive(false);
          // Optional: Retry logic could be added here
        };

        return () => {
          clearInterval(interval);
          if (eventSource) eventSource.close();
        };
      } catch (err) {
        console.error("Failed to initialize SSE connection:", err);
      }
    };

    const cleanup = connect();

    return () => {
      cleanup.then(fn => fn && fn());
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const getEventMeta = (event: string) => {
    switch (event) {
      case "fig_delta": return { color: "text-blue-400", icon: <Database className="h-3 w-3" />, label: "NODE" };
      case "evolution": return { color: "text-emerald-400", icon: <GitMerge className="h-3 w-3" />, label: "EVO" };
      case "invention": return { color: "text-amber-400", icon: <Lightbulb className="h-3 w-3" />, label: "INV" };
      case "cluster_updated": return { color: "text-violet-400", icon: <LayoutGrid className="h-3 w-3" />, label: "CLUST" };
      case "inference_found": return { color: "text-cyan-400", icon: <Search className="h-3 w-3" />, label: "INF" };
      case "insight_discovered": return { color: "text-pink-400", icon: <Eye className="h-3 w-3" />, label: "INSIGHT" };
      case "error": return { color: "text-rose-400", icon: <AlertCircle className="h-3 w-3" />, label: "ERROR" };
      case "toast": return { color: "text-slate-400", icon: <Bell className="h-3 w-3" />, label: "SYS" };
      default: return { color: "text-slate-500", icon: <Activity className="h-3 w-3" />, label: "EVENT" };
    }
  };

  const formatData = (event: string, data: any) => {
    if (event === "fig_delta") {
      const added = data.delta?.nodes_added?.length || 0;
      return added > 0 ? `Integrated ${added} new node(s)` : "Graph topology updated";
    }
    if (event === "evolution") {
      return `${data.type?.toUpperCase()}: ${data.data?.details || "Action recorded"}`;
    }
    if (event === "cluster_updated") {
      return `Clustered ${data.cards?.clusters?.length || 0} concept groups`;
    }
    if (event === "inference_found") {
      return `Semantic link discovered between concepts`;
    }
    if (event === "insight_discovered") {
      return `New pattern detected: ${data.insights?.[0]?.title || "Detail unknown"}`;
    }
    return data.message || data.details || JSON.stringify(data).slice(0, 50);
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Heart className={`h-4 w-4 ${isLive ? "text-rose-500 animate-pulse" : "text-slate-600"}`} />
          <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
            System Heartbeat
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-emerald-500" : "bg-rose-500"}`} />
          <span className="text-[10px] text-slate-500 font-mono">{isLive ? "STREAMING" : "OFFLINE"}</span>
        </div>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-[10px] space-y-2 scrollbar-hide"
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-2">
            <RefreshCw className="h-5 w-5 animate-spin opacity-20" />
            <p className="animate-pulse">Awaiting system pulse...</p>
          </div>
        ) : (
          events.map((ev, i) => {
            const meta = getEventMeta(ev.event);
            return (
              <div key={i} className="flex items-start gap-3 border-l border-slate-800 pl-3 pb-1 group animate-in slide-in-from-left-1 duration-300">
                <span className="text-slate-600 shrink-0 tabular-nums">
                  {new Date(ev.ts * 1000).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className={`flex items-center gap-1.5 shrink-0 w-16 ${meta.color} font-bold`}>
                  {meta.icon}
                  <small className="uppercase">{meta.label}</small>
                </span>
                <span className="text-slate-400 group-hover:text-slate-200 transition-colors">
                  {formatData(ev.event, ev.data)}
                </span>
              </div>
            );
          })
        )}
      </div>

      <div className="px-4 py-1.5 bg-slate-900/40 border-t border-slate-800/50 flex justify-between items-center text-[9px] text-slate-600 font-mono italic">
        <span>CORE_BUS_v4.diag</span>
        <span>LATENCY: OPTIMIZED</span>
      </div>
    </div>
  );
}
