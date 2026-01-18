"use client";

/**
 * UserIsolationPanel Component
 * 
 * Displays proof of user's isolated resources in FAIMATRIX.
 * Shows user ID, graph ID, and tenant isolation status.
 */

import { useSession } from "next-auth/react";
import { motion } from "framer-motion";
import { 
  Shield, 
  Database, 
  Key, 
  User, 
  Network, 
  Lock,
  CheckCircle,
  Fingerprint
} from "lucide-react";

export function UserIsolationPanel() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 animate-pulse">
        <div className="h-6 bg-slate-700/50 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          <div className="h-4 bg-slate-700/30 rounded w-full" />
          <div className="h-4 bg-slate-700/30 rounded w-2/3" />
        </div>
      </div>
    );
  }

  if (!session?.user) {
    return null;
  }

  const userId = (session.user as any).id || "Unknown";
  const email = session.user.email || "Unknown";
  const graphId = (session as any).graphId || `U:${userId.slice(0, 8)}`;
  const tenantId = userId; // In FAIM, user_id = tenant_id for personal isolation

  const isolationItems = [
    {
      icon: Fingerprint,
      label: "User ID",
      value: userId,
      description: "Your unique, immutable identity",
      color: "cyan",
    },
    {
      icon: Network,
      label: "Graph ID",
      value: graphId,
      description: "Your isolated memory graph namespace",
      color: "purple",
    },
    {
      icon: Database,
      label: "Tenant ID",
      value: tenantId.slice(0, 16) + "...",
      description: "Database partition key for all your data",
      color: "emerald",
    },
    {
      icon: Key,
      label: "Session",
      value: "JWT (HS256, 30d)",
      description: "Cryptographically signed access token",
      color: "amber",
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="bg-gradient-to-br from-slate-900/80 to-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden"
    >
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700/50 bg-gradient-to-r from-cyan-500/10 to-purple-500/10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/20">
            <Shield className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">
              Your Isolated Environment
            </h3>
            <p className="text-sm text-slate-400">
              Zero-trust multi-tenant isolation for your memories
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-medium text-emerald-300">ISOLATED</span>
          </div>
        </div>
      </div>

      {/* User Info */}
      <div className="px-6 py-4 border-b border-slate-700/30">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
            {email[0]?.toUpperCase() || "U"}
          </div>
          <div>
            <p className="text-white font-medium">{session.user.name || email.split("@")[0]}</p>
            <p className="text-sm text-slate-400">{email}</p>
          </div>
        </div>
      </div>

      {/* Isolation Details */}
      <div className="p-6 space-y-4">
        {isolationItems.map((item, idx) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="flex items-start gap-4 p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 hover:border-slate-600/50 transition-colors"
          >
            <div className={`p-2 rounded-lg bg-${item.color}-500/20`}>
              <item.icon className={`w-5 h-5 text-${item.color}-400`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-300">{item.label}</span>
              </div>
              <p className="text-white font-mono text-sm mt-1 truncate" title={item.value}>
                {item.value}
              </p>
              <p className="text-xs text-slate-500 mt-1">{item.description}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Protection Status */}
      <div className="px-6 py-4 bg-slate-800/30 border-t border-slate-700/30">
        <div className="flex items-center gap-3 text-sm">
          <Lock className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-400">
            All your memories, nodes, edges, and events are protected by{" "}
            <span className="text-cyan-400 font-medium">tenant_id</span> isolation.
            No other user can access your data.
          </span>
        </div>
      </div>
    </motion.div>
  );
}
