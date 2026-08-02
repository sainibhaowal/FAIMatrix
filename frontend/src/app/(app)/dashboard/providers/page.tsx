"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  Cpu,
  Plus,
  Trash2,
  CheckCircle,
  AlertCircle,
  Loader,
  Radio,
  Copy,
  Check,
  Download,
  ChevronDown,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Button } from "@/components/ui/Button";
import { useProviders } from "@/contexts/ProviderContext";
import { discoverProviderModels } from "@/lib/providerDiscovery";
import { providerReasoningCapability } from "@/lib/providers";

function ModelDropdown({
  models,
  value,
  onChange,
}: {
  models: string[];
  value: string;
  onChange: (model: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const [vendor, ...rest] = value.split("/");
  const displayName = rest.length > 0 ? rest.join("/") : vendor;
  const displayVendor = rest.length > 0 ? vendor : null;

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg border border-white/10 bg-black/40 hover:border-white/20 hover:bg-white/5 transition-all group"
      >
        <div className="flex items-center gap-2 min-w-0">
          {displayVendor && (
            <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest bg-slate-800/60 px-1.5 py-0.5 rounded flex-shrink-0">
              {displayVendor}
            </span>
          )}
          <span className="text-sm text-slate-200 font-medium truncate">
            {displayName}
          </span>
        </div>
        <ChevronDown
          size={14}
          className={`flex-shrink-0 text-slate-500 group-hover:text-slate-300 transition-all duration-200 ${open ? "rotate-180 text-primary-400" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.97 }}
            transition={{ duration: 0.12 }}
            className="absolute z-50 left-0 right-0 top-full mt-1.5 rounded-xl border border-white/10 bg-slate-900/95 backdrop-blur-xl shadow-2xl overflow-hidden"
          >
            <div className="max-h-[200px] overflow-y-auto p-1 space-y-0.5 custom-scrollbar">
              {models.map((m) => {
                const [v, ...r] = m.split("/");
                const mName = r.length > 0 ? r.join("/") : v;
                const mVendor = r.length > 0 ? v : null;
                const active = m === value;
                return (
                  <button
                    key={m}
                    type="button"
                    onClick={() => {
                      onChange(m);
                      setOpen(false);
                    }}
                    className={[
                      "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left transition-all duration-150",
                      active
                        ? "bg-primary-500/15 border border-primary-500/30 text-primary-200"
                        : "hover:bg-white/[0.06] border border-transparent text-slate-300",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-2 h-2 rounded-full flex-shrink-0",
                        active
                          ? "bg-primary-400 shadow-[0_0_6px_rgba(34,211,238,0.5)]"
                          : "bg-slate-700",
                      ].join(" ")}
                    />
                    {mVendor && (
                      <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest bg-slate-800/60 px-1.5 py-0.5 rounded flex-shrink-0">
                        {mVendor}
                      </span>
                    )}
                    <span className="text-[13px] font-medium truncate">
                      {mName}
                    </span>
                    {active && (
                      <Check
                        size={12}
                        className="ml-auto flex-shrink-0 text-primary-400"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ProvidersPage() {
  const {
    providers,
    activeProvider,
    isLoading,
    error,
    addProvider,
    removeProvider,
    setActiveProvider,
    setActiveModel,
    discoverModels,
  } = useProviders();

  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    type: "local" as "local" | "openai" | "custom",
    baseUrl: "",
    apiKey: "",
  });
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [formStep, setFormStep] = useState<"config" | "models">("config");
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Step 1: Test Connection & Fetch Models
  const handleTestConnection = useCallback(async () => {
    setFormError(null);
    setFormLoading(true);
    setDiscoveredModels([]);
    setSelectedModel("");

    if (!formData.baseUrl.trim()) {
      setFormError("Base URL is required");
      setFormLoading(false);
      return;
    }

    try {
      const { models } = await discoverProviderModels(
        formData.baseUrl,
        formData.apiKey || undefined,
      );
      setDiscoveredModels(models);

      if (models.length > 0) {
        setSelectedModel(models[0]);
        setFormStep("models");
      } else {
        setFormError("No models found from provider");
      }
    } catch (e: any) {
      setFormError(e.message || "Failed to discover models");
    } finally {
      setFormLoading(false);
    }
  }, [formData.baseUrl, formData.apiKey]);

  // Step 2: Add Provider with selected model
  const handleAddProvider = useCallback(async () => {
    setFormError(null);
    setFormLoading(true);

    if (!formData.name.trim()) {
      setFormError("Provider name is required");
      setFormLoading(false);
      return;
    }

    if (!selectedModel) {
      setFormError("A model must be selected");
      setFormLoading(false);
      return;
    }

    try {
      const id = await addProvider(
        formData.name,
        formData.type,
        formData.baseUrl,
        formData.apiKey || undefined,
        discoveredModels,
        selectedModel,
      );

      if (id) {
        setFormData({ name: "", type: "local", baseUrl: "", apiKey: "" });
        setDiscoveredModels([]);
        setSelectedModel("");
        setFormStep("config");
        setShowAddForm(false);
      } else {
        setFormError("Failed to add provider. Check the URL and try again.");
      }
    } finally {
      setFormLoading(false);
    }
  }, [addProvider, discoveredModels, formData, selectedModel]);

  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedId(url);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleRefreshModels = useCallback(
    async (providerId: string) => {
      await discoverModels(providerId);
    },
    [discoverModels],
  );

  const closeForm = () => {
    setShowAddForm(false);
    setFormStep("config");
    setFormData({ name: "", type: "local", baseUrl: "", apiKey: "" });
    setDiscoveredModels([]);
    setSelectedModel("");
    setFormError(null);
  };

  return (
    <div className="relative space-y-6 pb-8 text-slate-100 px-1">
      <div className="faim-grid" />

      <GlassHeader
        title="LLM Providers"
        subtitle="Universal AI endpoint management"
        icon={Cpu}
        actions={
          <Button
            size="sm"
            variant="primary"
            leftIcon={<Plus size={14} />}
            onClick={() => setShowAddForm(true)}
          >
            Add Provider
          </Button>
        }
      />

      {/* Top Metric Strip (Domain Studio MetricTile style) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "ACTIVE PROVIDER",
            value: activeProvider?.name || "None",
            icon: <Cpu size={16} />,
            accent: "#06b6d4",
          },
          {
            label: "ACTIVE MODEL",
            value: activeProvider?.activeModel || "—",
            icon: <CheckCircle size={16} />,
            accent: "#10b981",
          },
          {
            label: "TOTAL PROVIDERS",
            value: `${providers.length}`,
            icon: <Radio size={16} />,
            accent: "#f59e0b",
          },
          {
            label: "CONNECTION STATUS",
            value:
              activeProvider?.status === "online"
                ? "Online"
                : activeProvider
                  ? "Checking..."
                  : "Offline",
            icon: <AlertCircle size={16} />,
            accent: activeProvider?.status === "online" ? "#10b981" : "#8b5cf6",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="relative overflow-hidden rounded-[14px] border border-white/10 bg-[rgba(10,16,28,0.75)] backdrop-blur-xl pl-4 pr-3.5 py-3.5 shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]"
          >
            <span
              className="pointer-events-none absolute left-0 top-0 h-full w-[2px]"
              style={{ background: stat.accent }}
            />
            <div className="flex items-center justify-between mb-1.5">
              <p className="font-mono text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                {stat.label}
              </p>
              <div className="opacity-40">{stat.icon}</div>
            </div>
            <p className="text-[18px] font-semibold tracking-tight text-white truncate">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Error Alert */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-[14px] border border-rose-500/20 bg-rose-500/5 px-4 py-3 flex items-center gap-3 backdrop-blur-md"
        >
          <AlertCircle size={16} className="text-rose-500 flex-shrink-0" />
          <p className="text-sm text-rose-500">{error}</p>
        </motion.div>
      )}

      {/* Main Section Shell (Clean Frosted Glass Style) */}
      <section className="relative overflow-hidden rounded-[18px] border border-white/10 bg-[rgba(10,16,28,0.75)] backdrop-blur-2xl shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] p-6 space-y-5">
        <div className="relative border-b border-white/8 pb-4 flex items-center justify-between">
          <div>
            <p className="font-mono text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-400">
              UNIVERSAL AI ENDPOINT MANAGEMENT
            </p>
            <h2 className="mt-1 text-base font-semibold tracking-tight text-white">
              Configured Providers
            </h2>
          </div>
          <Button
            size="sm"
            leftIcon={<Plus size={14} />}
            onClick={() => setShowAddForm(true)}
          >
            Add Provider
          </Button>
        </div>

        {providers.length === 0 ? (
          <div className="relative rounded-[14px] border border-dashed border-white/10 p-12 flex flex-col items-center gap-4 text-center bg-white/[0.01]">
            <Cpu size={32} className="text-slate-500 opacity-40" />
            <div>
              <h3 className="text-sm font-bold text-slate-300 mb-2">
                No providers configured
              </h3>
              <p className="text-xs text-slate-500 max-w-md mb-4 leading-relaxed">
                Add your first LLM provider (LM Studio local server, OpenAI, or
                any OpenAI-compatible endpoint) to start querying.
              </p>
              <Button
                size="sm"
                leftIcon={<Plus size={14} />}
                onClick={() => setShowAddForm(true)}
              >
                Add Provider
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 relative">
            {providers.map((provider) => (
              <motion.div
                key={provider.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-[14px] border border-white/8 bg-white/[0.03] p-4 space-y-4 shadow-[0_4px_20px_rgba(0,0,0,0.2)]"
              >
                {(() => {
                  const reasoning = providerReasoningCapability(provider);
                  return reasoning.supported ? (
                    <div className="flex justify-end">
                      <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-cyan-200">
                        Reasoning {reasoning.confidence}
                      </span>
                    </div>
                  ) : null;
                })()}
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-sm font-bold text-white truncate">
                        {provider.name}
                      </h3>
                      {provider.isActive && (
                        <span className="inline-block px-2 py-1 rounded-lg bg-primary-500/20 border border-primary-500/30 text-[10px] font-bold text-primary-300 uppercase tracking-wider whitespace-nowrap">
                          Active
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] text-slate-500 uppercase tracking-widest mb-2">
                      {provider.type === "local"
                        ? "Local Server"
                        : provider.type === "openai"
                          ? "OpenAI"
                          : "Custom Endpoint"}
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div className="flex-shrink-0">
                    {provider.status === "online" ? (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-[9px] font-bold text-emerald-400 uppercase tracking-wider">
                          Online
                        </span>
                      </div>
                    ) : provider.status === "offline" ? (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-rose-500/10 border border-rose-500/20">
                        <div className="w-2 h-2 rounded-full bg-rose-500" />
                        <span className="text-[9px] font-bold text-rose-400 uppercase tracking-wider">
                          Offline
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-500/10 border border-slate-500/20">
                        <Loader size={10} className="animate-spin" />
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">
                          Check
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* URL */}
                <div className="space-y-1.5">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    Base URL
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="text-[11px] font-mono text-slate-400 bg-black/30 px-2 py-1.5 rounded border border-slate-700/50 flex-1 truncate">
                      {provider.baseUrl}
                    </code>
                    <button
                      onClick={() => handleCopyUrl(provider.baseUrl)}
                      className="p-1.5 rounded hover:bg-white/10 transition-colors"
                      title="Copy URL"
                    >
                      {copiedId === provider.baseUrl ? (
                        <Check size={14} className="text-emerald-400" />
                      ) : (
                        <Copy
                          size={14}
                          className="text-slate-500 hover:text-slate-300"
                        />
                      )}
                    </button>
                  </div>
                </div>

                {/* Models */}
                {provider.models.length > 0 ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        Models ({provider.models.length})
                      </p>
                      <button
                        onClick={() => handleRefreshModels(provider.id)}
                        className="text-[9px] text-primary-400 hover:text-primary-300 uppercase tracking-widest font-bold transition-colors"
                      >
                        Refresh
                      </button>
                    </div>
                    <ModelDropdown
                      models={provider.models}
                      value={provider.activeModel}
                      onChange={(m) => setActiveModel(provider.id, m)}
                    />
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <AlertCircle size={14} />
                    <span className="text-[11px]">
                      No models discovered. Check connection.
                    </span>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-slate-700/50">
                  {!provider.isActive && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => setActiveProvider(provider.id)}
                    >
                      Set Active
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-rose-500/30 text-rose-500 hover:bg-rose-500/5 flex-1"
                    leftIcon={<Trash2 size={12} />}
                    onClick={() => removeProvider(provider.id)}
                  >
                    Delete
                  </Button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Add Provider Modal - Step 1 & 2 */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={() => !formLoading && closeForm()}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="max-w-md w-full bg-[rgba(10,16,28,0.92)] backdrop-blur-2xl border border-white/10 rounded-[18px] p-6 shadow-[0_24px_80px_rgba(0,0,0,0.6)] relative overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {formStep === "config" && (
                <>
                  <h2 className="text-xl font-bold text-white mb-1">
                    Add LLM Provider
                  </h2>
                  <p className="text-sm text-slate-400 mb-6">
                    Step 1 of 2: Configure provider and test connection
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                        Provider Name
                      </label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) =>
                          setFormData({ ...formData, name: e.target.value })
                        }
                        placeholder="e.g., My LM Studio"
                        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-primary-500/50"
                        disabled={formLoading}
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                        Provider Type
                      </label>
                      <div className="flex gap-2">
                        {["local", "openai", "custom"].map((t) => (
                          <label key={t} className="flex-1 cursor-pointer">
                            <input
                              type="radio"
                              name="type"
                              value={t}
                              checked={formData.type === t}
                              onChange={(e) =>
                                setFormData({
                                  ...formData,
                                  type: e.target.value as
                                    | "local"
                                    | "openai"
                                    | "custom",
                                })
                              }
                              disabled={formLoading}
                              className="sr-only"
                            />
                            <div
                              className={`px-3 py-2 rounded-lg border text-center text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer ${
                                formData.type === t
                                  ? "bg-primary-500/20 border-primary-500/50 text-primary-300"
                                  : "bg-white/5 border-white/10 text-slate-400 hover:bg-white/10"
                              }`}
                            >
                              {t === "local"
                                ? "Local"
                                : t === "openai"
                                  ? "OpenAI"
                                  : "Custom"}
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                        Base URL
                      </label>
                      <input
                        type="text"
                        value={formData.baseUrl}
                        onChange={(e) =>
                          setFormData({ ...formData, baseUrl: e.target.value })
                        }
                        placeholder={
                          formData.type === "local"
                            ? "http://localhost:1234"
                            : formData.type === "openai"
                              ? "https://api.openai.com/v1"
                              : "https://your-endpoint.com/v1"
                        }
                        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-primary-500/50"
                        disabled={formLoading}
                      />
                      {formData.type === "local" && (
                        <p className="text-[9px] text-slate-500 mt-1.5">
                          Tip: If running in Docker, use{" "}
                          <code className="font-mono">
                            http://host.docker.internal:1234
                          </code>
                        </p>
                      )}
                    </div>

                    {(formData.type === "openai" ||
                      formData.type === "custom") && (
                      <div>
                        <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                          API Key {formData.type === "custom" && "(Optional)"}
                        </label>
                        <input
                          type="password"
                          value={formData.apiKey}
                          onChange={(e) =>
                            setFormData({ ...formData, apiKey: e.target.value })
                          }
                          placeholder="sk-... or leave empty"
                          className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-primary-500/50"
                          disabled={formLoading}
                        />
                      </div>
                    )}

                    {formError && (
                      <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20">
                        <AlertCircle
                          size={14}
                          className="text-rose-500 flex-shrink-0 mt-0.5"
                        />
                        <span className="text-[11px] text-rose-500">
                          {formError}
                        </span>
                      </div>
                    )}

                    <div className="flex gap-3 pt-4">
                      <Button
                        className="flex-1"
                        variant="primary"
                        size="md"
                        onClick={handleTestConnection}
                        disabled={formLoading || !formData.baseUrl.trim()}
                        leftIcon={
                          formLoading ? (
                            <Loader size={14} className="animate-spin" />
                          ) : (
                            <Download size={14} />
                          )
                        }
                      >
                        {formLoading ? "Testing..." : "Test Connection"}
                      </Button>
                      <Button
                        className="flex-1"
                        variant="outline"
                        size="md"
                        onClick={closeForm}
                        disabled={formLoading}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </>
              )}

              {formStep === "models" && (
                <>
                  {/* Header */}
                  <div className="flex items-center gap-3 mb-1">
                    <div className="w-8 h-8 rounded-lg bg-primary-500/20 border border-primary-500/30 flex items-center justify-center flex-shrink-0">
                      <CheckCircle size={16} className="text-primary-400" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-white leading-tight">
                        Select Model
                      </h2>
                      <p className="text-[10px] text-primary-400 font-semibold uppercase tracking-widest">
                        {discoveredModels.length} models found
                      </p>
                    </div>
                  </div>

                  <p className="text-xs text-slate-500 mb-4">
                    Step 2 of 2 — Pick the default model for{" "}
                    <span className="text-slate-300 font-semibold">
                      {formData.name || "this provider"}
                    </span>
                  </p>

                  {/* Model Cards */}
                  <div className="space-y-1.5 max-h-[260px] overflow-y-auto pr-1 custom-scrollbar mb-4">
                    {discoveredModels.map((m) => {
                      const isSelected = selectedModel === m;
                      const [vendor, ...rest] = m.split("/");
                      const modelName =
                        rest.length > 0 ? rest.join("/") : vendor;
                      const vendorLabel = rest.length > 0 ? vendor : null;

                      return (
                        <button
                          key={m}
                          onClick={() => setSelectedModel(m)}
                          disabled={formLoading}
                          className={[
                            "w-full text-left px-3 py-2.5 rounded-xl border transition-all duration-200 flex items-center gap-3 group",
                            isSelected
                              ? "bg-primary-500/15 border-primary-500/40 shadow-[0_0_12px_rgba(34,211,238,0.1)]"
                              : "bg-white/[0.03] border-white/[0.06] hover:bg-white/[0.07] hover:border-white/10",
                          ].join(" ")}
                        >
                          {/* Selection indicator */}
                          <div
                            className={[
                              "w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all",
                              isSelected
                                ? "border-primary-400 bg-primary-400"
                                : "border-slate-600 group-hover:border-slate-400",
                            ].join(" ")}
                          >
                            {isSelected && (
                              <div className="w-1.5 h-1.5 rounded-full bg-slate-900" />
                            )}
                          </div>

                          {/* Model info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-baseline gap-2">
                              <span
                                className={[
                                  "text-[13px] font-semibold truncate",
                                  isSelected
                                    ? "text-primary-200"
                                    : "text-slate-200",
                                ].join(" ")}
                              >
                                {modelName}
                              </span>
                            </div>
                            {vendorLabel && (
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                                {vendorLabel}
                              </span>
                            )}
                          </div>

                          {isSelected && (
                            <span className="text-[9px] font-bold text-primary-400 uppercase tracking-widest flex-shrink-0">
                              Selected
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>

                  {formError && (
                    <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 mb-4">
                      <AlertCircle
                        size={14}
                        className="text-rose-500 flex-shrink-0 mt-0.5"
                      />
                      <span className="text-[11px] text-rose-500">
                        {formError}
                      </span>
                    </div>
                  )}

                  <div className="flex gap-3">
                    <Button
                      className="flex-1"
                      variant="primary"
                      size="md"
                      onClick={handleAddProvider}
                      disabled={
                        formLoading || !formData.name.trim() || !selectedModel
                      }
                      leftIcon={
                        formLoading ? (
                          <Loader size={14} className="animate-spin" />
                        ) : (
                          <Plus size={14} />
                        )
                      }
                    >
                      {formLoading ? "Adding..." : "Add Provider"}
                    </Button>
                    <Button
                      variant="outline"
                      size="md"
                      onClick={() => {
                        setFormStep("config");
                        setFormError(null);
                      }}
                      disabled={formLoading}
                    >
                      Back
                    </Button>
                  </div>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
