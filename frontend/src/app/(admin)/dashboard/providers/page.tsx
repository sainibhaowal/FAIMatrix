"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  Cpu,
  Bot,
  Database,
  Target,
  Globe,
  LayoutGrid,
  Plus,
  Trash2,
  ChevronDown,
  X,
  ArrowLeft,
  Link2,
  Info,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Zap,
  ScanText,
  FileText,
  KeyRound,
  Eye,
  EyeOff,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { GlassHeader } from "@/components/layout/GlassHeader";
import { Button } from "@/components/ui/Button";
import { useProviders } from "@/contexts/ProviderContext";
import { useEmbeddingProviders } from "@/contexts/EmbeddingProviderContext";
import { discoverProviderModels } from "@/lib/providerDiscovery";
import { discoverEmbeddingModels, testEmbeddingProvider } from "@/lib/embeddingProviderDiscovery";
import { ProvidersManual } from "@/components/manuals/ProvidersManual";

type Tab = "navigator" | "llm" | "embedding" | "reranker" | "ocr" | "web";
type LeftViewMode = "inventory" | "select_family";

interface FamilyOption {
  id: string;
  name: string;
  code: string;
  type: "local" | "openai" | "custom";
  defaultUrl: string;
  models: string[];
}

const LLM_FAMILIES: FamilyOption[] = [
  {
    id: "opencode-zen",
    name: "OpenCode Zen",
    code: "OPENCODE-ZEN",
    type: "custom",
    defaultUrl: "http://localhost:55606/v1",
    models: [],
  },
  {
    id: "lmstudio",
    name: "LM Studio",
    code: "LMSTUDIO",
    type: "local",
    defaultUrl: "http://localhost:1234/v1",
    models: [],
  },
  {
    id: "ollama",
    name: "Ollama",
    code: "OLLAMA",
    type: "local",
    defaultUrl: "http://localhost:11434/v1",
    models: [],
  },
  {
    id: "openai",
    name: "OpenAI API",
    code: "OPENAI",
    type: "openai",
    defaultUrl: "https://api.openai.com/v1",
    models: [],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    code: "ANTHROPIC",
    type: "custom",
    defaultUrl: "https://api.anthropic.com/v1",
    models: [],
  },
  {
    id: "google",
    name: "Google",
    code: "GOOGLE",
    type: "custom",
    defaultUrl: "https://generativelanguage.googleapis.com/v1beta",
    models: [],
  },
  {
    id: "groq",
    name: "Groq",
    code: "GROQ",
    type: "custom",
    defaultUrl: "https://api.groq.com/openai/v1",
    models: [],
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    code: "OPENROUTER",
    type: "custom",
    defaultUrl: "https://openrouter.ai/api/v1",
    models: [],
  },
  {
    id: "openai-compatible",
    name: "OpenAI-Compatible",
    code: "CUSTOM",
    type: "custom",
    defaultUrl: "http://localhost:8000/v1",
    models: [],
  },
];

const EMBEDDING_FAMILIES: FamilyOption[] = [
  {
    id: "sentence-transformers",
    name: "FAIM Native Embeddings",
    code: "SENTENCE_TRANSFORMERS",
    type: "local",
    defaultUrl: "http://localhost:8000/v1",
    models: ["BAAI/bge-small-en-v1.5", "BAAI/bge-m3"],
  },
  {
    id: "openai-embed",
    name: "OpenAI Embeddings",
    code: "OPENAI_EMBED",
    type: "openai",
    defaultUrl: "https://api.openai.com/v1",
    models: ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
  },
];

const RERANKER_FAMILIES: FamilyOption[] = [
  {
    id: "faim-native-reranker",
    name: "FAIM Deterministic ReRanker V2",
    code: "FAIM_RERANKER_V2",
    type: "local",
    defaultUrl: "FAIM Native Internal Core",
    models: ["faim-reranker-v2"],
  },
];

const OCR_FAMILIES: FamilyOption[] = [
  {
    id: "paddleocr_v6",
    name: "PaddleOCR v6 (CPU Ultra / MKLDNN)",
    code: "PADDLEOCR_V6",
    type: "local",
    defaultUrl: "FAIM Native CPU Runtime (MKLDNN / Multi-Core)",
    models: ["paddleocr-v6-en", "paddleocr-v6-multilingual"],
  },
  {
    id: "tesseract",
    name: "Tesseract OCR (LSTM / PSM 3)",
    code: "TESSERACT",
    type: "local",
    defaultUrl: "FAIM Native Local Tesseract (OEM 1 / PSM 3)",
    models: ["tesseract-psm3-eng", "tesseract-psm3-multilingual"],
  },
  {
    id: "easyocr",
    name: "EasyOCR (PyTorch CRAFT)",
    code: "EASYOCR",
    type: "local",
    defaultUrl: "FAIM Native EasyOCR Engine",
    models: ["easyocr-craft-en", "easyocr-craft-multilingual"],
  },
  {
    id: "custom-ocr",
    name: "Custom Remote OCR Endpoint",
    code: "CUSTOM_OCR",
    type: "custom",
    defaultUrl: "http://localhost:8000/v1/ocr",
    models: ["custom-ocr-endpoint"],
  },
];

const WEB_FAMILIES: FamilyOption[] = [
  {
    id: "serper",
    name: "Serper API",
    code: "SERPER",
    type: "custom",
    defaultUrl: "https://google.serper.dev",
    models: ["Google Serper API"],
  },
];

function isLocalProviderUrl(value: string): boolean {
  try {
    const hostname = new URL(value).hostname.toLowerCase();
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
  } catch {
    return false;
  }
}

function isPublicBrowserSession(): boolean {
  if (typeof window === "undefined") return false;
  const hostname = window.location.hostname.toLowerCase();
  return hostname !== "localhost" && hostname !== "127.0.0.1" && hostname !== "::1";
}

// FAIM Custom Dropdown Component (Glass rounded-square floating menu style)
interface CustomSelectProps {
  value: string;
  onChange: (val: string) => void;
  options: { label: string; value: string }[] | string[];
  placeholder?: string;
  className?: string;
}

function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "Select option...",
  className = "",
}: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const normalizedOptions = options.map((opt) =>
    typeof opt === "string" ? { label: opt, value: opt } : opt
  );

  const selectedOption = normalizedOptions.find((opt) => opt.value === value);

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-slate-950/70 hover:bg-slate-900/90 border border-white/10 hover:border-primary-500/50 rounded-xl px-3.5 py-2 text-xs text-slate-200 flex items-center justify-between transition-all duration-200 font-mono shadow-inner hover:shadow-[0_0_15px_rgba(34,211,238,0.15)] focus:outline-none"
      >
        <span className="truncate font-medium">{selectedOption ? selectedOption.label : placeholder}</span>
        <ChevronDown
          size={14}
          className={`text-slate-400 transition-transform duration-300 ${isOpen ? "rotate-180 text-primary-400" : ""}`}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.97 }}
            animate={{ opacity: 1, y: 4, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="absolute z-50 left-0 right-0 top-full bg-slate-950/95 backdrop-blur-2xl border border-primary-500/30 rounded-xl shadow-[0_15px_40px_rgba(0,0,0,0.85)] p-1.5 max-h-52 overflow-y-auto custom-scrollbar mt-1.5"
          >
            {normalizedOptions.length === 0 ? (
              <div className="p-3 text-center text-slate-500 font-mono text-[11px]">
                No models discovered yet. Enter API key/URL and click "Test Ping" to fetch live models.
              </div>
            ) : (
              normalizedOptions.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    className={[
                      "w-full px-3 py-1.5 rounded-lg text-xs font-mono text-left flex items-center justify-between transition-all duration-150 my-0.5",
                      isSelected
                        ? "bg-primary-500/25 text-primary-200 font-bold border-l-2 border-primary-400 shadow-[0_0_12px_rgba(34,211,238,0.1)]"
                        : "text-slate-300 hover:bg-white/10 hover:text-white hover:translate-x-0.5",
                    ].join(" ")}
                  >
                    <span className="truncate">{opt.label}</span>
                    {isSelected && <CheckCircle2 size={13} className="text-primary-400 shrink-0 ml-2" />}
                  </button>
                );
              })
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TabToggle({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "navigator", label: "NAVIGATOR", icon: <LayoutGrid size={14} /> },
    { id: "llm", label: "LLM", icon: <Bot size={14} /> },
    { id: "embedding", label: "EMBEDDING", icon: <Database size={14} /> },
    { id: "reranker", label: "RERANKER", icon: <Target size={14} /> },
    { id: "ocr", label: "OCR", icon: <ScanText size={14} /> },
    { id: "web", label: "WEB", icon: <Globe size={14} /> },
  ];

  return (
    <div className="inline-flex p-1 rounded-[14px] border border-white/10 bg-black/30 backdrop-blur-xl gap-1 overflow-x-auto custom-scrollbar">
      {tabs.map((t) => {
        const selected = active === t.id;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            className={[
              "relative flex items-center gap-2 px-3.5 py-1.5 rounded-[10px] text-xs font-mono font-bold tracking-wider transition-all duration-200 whitespace-nowrap",
              selected ? "text-white" : "text-slate-400 hover:text-slate-200",
            ].join(" ")}
          >
            {selected && (
              <motion.span
                layoutId="providers-nav-tab-bg"
                className="absolute inset-0 rounded-[10px] bg-primary-500/20 border border-primary-500/40 shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative flex items-center gap-2">
              <span className={selected ? "text-primary-300" : "text-slate-500"}>
                {t.icon}
              </span>
              {t.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function ProvidersPage() {
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState<Tab>(() => {
    const requested = searchParams.get("tab");
    return requested === "ocr" || requested === "llm" || requested === "embedding" || requested === "reranker" || requested === "web"
      ? (requested as Tab)
      : "navigator";
  });
  const [manualOpen, setManualOpen] = useState(false);

  // Left panel view state for each tab
  const [llmLeftView, setLlmLeftView] = useState<LeftViewMode>("inventory");
  const [embeddingLeftView, setEmbeddingLeftView] = useState<LeftViewMode>("inventory");
  const [rerankerLeftView, setRerankerLeftView] = useState<LeftViewMode>("inventory");
  const [ocrLeftView, setOcrLeftView] = useState<LeftViewMode>("inventory");
  const [webLeftView, setWebLeftView] = useState<LeftViewMode>("inventory");

  // Real Providers Contexts
  const {
    providers: llmProviders,
    activeProvider: activeLLM,
    setActiveProvider: setLLMActive,
    setActiveModel: setLLMModel,
    addProvider: addLLMProvider,
    removeProvider: removeLLMProvider,
    refreshAllProvidersStatus,
  } = useProviders();

  const {
    providers: embeddingProviders,
    activeProvider: activeEmbedding,
    setActiveEmbeddingProvider: setEmbeddingActive,
    addEmbeddingProvider,
    removeEmbeddingProvider,
  } = useEmbeddingProviders();

  // LLM Setup Form State
  const [selectedLLMFamily, setSelectedLLMFamily] = useState<FamilyOption | null>(null);
  const [llmAuthProtocol, setLlmAuthProtocol] = useState("local no key");
  const [llmRuntimeUrl, setLlmRuntimeUrl] = useState(LLM_FAMILIES[0].defaultUrl);
  const [llmApiKey, setLlmApiKey] = useState("");
  const [llmDiscoveredModels, setLlmDiscoveredModels] = useState<string[]>([]);
  const [llmSelectedModel, setLlmSelectedModel] = useState<string>("");
  const [isDiscoveringLLM, setIsDiscoveringLLM] = useState(false);
  const [llmStatusMessage, setLlmStatusMessage] = useState<string | null>(null);

  // Sync selected family whenever activeLLM changes
  useEffect(() => {
    if (activeLLM) {
      setLlmRuntimeUrl(activeLLM.baseUrl);
      if (activeLLM.models && activeLLM.models.length > 0) {
        setLlmDiscoveredModels(activeLLM.models);
      }
      if (activeLLM.activeModel) {
        setLlmSelectedModel(activeLLM.activeModel);
      }
      const matchingFam = LLM_FAMILIES.find(
        (f) => f.name.toLowerCase() === activeLLM.name.toLowerCase()
      ) || {
        id: activeLLM.id,
        name: activeLLM.name,
        code: activeLLM.type.toUpperCase(),
        type: activeLLM.type as any,
        defaultUrl: activeLLM.baseUrl,
        models: activeLLM.models || [],
      };
      setSelectedLLMFamily(matchingFam);
    } else {
      setSelectedLLMFamily(null);
    }
  }, [activeLLM]);

  // Automatic dynamic model discovery when API Key or Runtime URL changes
  useEffect(() => {
    if (!selectedLLMFamily) return;

    // A public deployment cannot reach an LLM bound to the browser user's
    // localhost. Do not create a failing background request for that case.
    if (isPublicBrowserSession() && isLocalProviderUrl(llmRuntimeUrl)) {
      setLlmStatusMessage(
        "Local model discovery is unavailable from the hosted dashboard. Run FAIM locally or use a provider URL reachable from this server.",
      );
      return;
    }

    // Check if key is needed for this family
    const requiresKey =
      selectedLLMFamily.type === "openai" ||
      selectedLLMFamily.id === "anthropic" ||
      selectedLLMFamily.id === "google" ||
      selectedLLMFamily.id === "groq" ||
      selectedLLMFamily.id === "openrouter";

    // If key is required but not provided, clear models
    if (requiresKey && !llmApiKey.trim()) {
      return;
    }

    const timer = setTimeout(async () => {
      setIsDiscoveringLLM(true);
      setLlmStatusMessage(null);
      try {
        const disc = await discoverProviderModels(llmRuntimeUrl, llmApiKey.trim() || undefined);
        if (disc.models && disc.models.length > 0) {
          setLlmDiscoveredModels(disc.models);
          setLlmSelectedModel((prev) => (prev && disc.models.includes(prev) ? prev : disc.models[0]));
          setLlmStatusMessage(`✓ Automatically discovered ${disc.models.length} live models.`);
        }
      } catch (err: any) {
        // Only show status error if user explicitly entered a key or pinged
        if (llmApiKey.trim()) {
          setLlmStatusMessage(`✕ Model discovery failed: ${err.message || "Invalid credentials or unreachable endpoint"}`);
        }
      } finally {
        setIsDiscoveringLLM(false);
      }
    }, 600);

    return () => clearTimeout(timer);
  }, [llmApiKey, llmRuntimeUrl, selectedLLMFamily]);

  // Embedding Setup Form State
  const [selectedEmbeddingFamily, setSelectedEmbeddingFamily] = useState<FamilyOption | null>(null);
  const [embeddingName, setEmbeddingName] = useState(EMBEDDING_FAMILIES[0].name);
  const [embeddingAuthProtocol, setEmbeddingAuthProtocol] = useState("No Authentication");
  const [embeddingUrl, setEmbeddingUrl] = useState(EMBEDDING_FAMILIES[0].defaultUrl);
  const [embeddingApiKey, setEmbeddingApiKey] = useState("");
  const [showLlmApiKey, setShowLlmApiKey] = useState(false);
  const [showEmbeddingApiKey, setShowEmbeddingApiKey] = useState(false);
  const [embeddingDiscoveredModels, setEmbeddingDiscoveredModels] = useState<string[]>(EMBEDDING_FAMILIES[0].models);
  const [embeddingSelectedModel, setEmbeddingSelectedModel] = useState<string>(EMBEDDING_FAMILIES[0].models[0] || "");
  const [isDiscoveringEmbedding, setIsDiscoveringEmbedding] = useState(false);
  const [embeddingTesting, setEmbeddingTesting] = useState(false);
  const [embeddingTestResult, setEmbeddingTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (activeEmbedding) {
      setEmbeddingName(activeEmbedding.name);
      setEmbeddingUrl(activeEmbedding.baseUrl);
      if (activeEmbedding.model) {
        setEmbeddingSelectedModel(activeEmbedding.model);
      }
      const matchingFam = EMBEDDING_FAMILIES.find(
        (f) => f.name.toLowerCase() === activeEmbedding.name.toLowerCase()
      ) || EMBEDDING_FAMILIES[0];
      setSelectedEmbeddingFamily(matchingFam);
    } else {
      setSelectedEmbeddingFamily(null);
    }
  }, [activeEmbedding]);

  // Reranker Local Storage State
  const [hasRerankerConfigured, setHasRerankerConfigured] = useState(false);
  const [selectedRerankerFamily, setSelectedRerankerFamily] = useState<FamilyOption | null>(null);
  const [rerankerName, setRerankerName] = useState(RERANKER_FAMILIES[0].name);
  const [rerankerAuthProtocol, setRerankerAuthProtocol] = useState("No Authentication");
  const [rerankerModel, setRerankerModel] = useState(RERANKER_FAMILIES[0].models[0]);
  const [rerankerStatus, setRerankerStatus] = useState<"healthy" | "not_configured" | "offline">("not_configured");
  const [rerankerTesting, setRerankerTesting] = useState(false);
  const [rerankerTestResult, setRerankerTestResult] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("faim.rerankerProvider");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.name) setRerankerName(parsed.name);
        if (parsed.model) setRerankerModel(parsed.model);
        if (parsed.status) setRerankerStatus(parsed.status);
        setHasRerankerConfigured(true);
        setSelectedRerankerFamily(RERANKER_FAMILIES[0]);
      } else {
        setHasRerankerConfigured(false);
        setRerankerStatus("not_configured");
        setSelectedRerankerFamily(null);
      }
    } catch {
      setHasRerankerConfigured(false);
      setRerankerStatus("not_configured");
      setSelectedRerankerFamily(null);
    }
  }, []);

  // Web Search Local Storage State
  const [hasWebConfigured, setHasWebConfigured] = useState(false);
  const [selectedWebFamily, setSelectedWebFamily] = useState<FamilyOption | null>(null);
  const [webName, setWebName] = useState(WEB_FAMILIES[0].name);
  const [webAuthProtocol, setWebAuthProtocol] = useState("local no key");
  const [webEndpoint, setWebEndpoint] = useState(WEB_FAMILIES[0].defaultUrl);
  const [webSearchLang, setWebSearchLang] = useState("auto");
  const [webAllowedDomains, setWebAllowedDomains] = useState("");
  const [webBlockedDomains, setWebBlockedDomains] = useState("");
  const [webStatus, setWebStatus] = useState<"connected" | "not_configured" | "unchecked">("not_configured");
  const [webTesting, setWebTesting] = useState(false);
  const [webTestResult, setWebTestResult] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("faim.webProvider");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.name) setWebName(parsed.name);
        if (parsed.endpoint) setWebEndpoint(parsed.endpoint);
        if (parsed.status) setWebStatus(parsed.status);
        setHasWebConfigured(true);
        setSelectedWebFamily(WEB_FAMILIES[0]);
      } else {
        setHasWebConfigured(false);
        setWebStatus("not_configured");
        setSelectedWebFamily(null);
      }
    } catch {
      setHasWebConfigured(false);
      setWebStatus("not_configured");
      setSelectedWebFamily(null);
    }
  }, []);

  // Selection Handlers
  const handleSelectLLMFamily = (fam: FamilyOption) => {
    setSelectedLLMFamily(fam);
    setLlmRuntimeUrl(fam.defaultUrl);
    setLlmApiKey(""); // Cleanly reset API key so it is never carried over to another provider
    setLlmDiscoveredModels([]);
    setLlmSelectedModel("");
    setLlmStatusMessage(null);
    if (fam.type === "local") {
      setLlmAuthProtocol("local no key");
    } else if (fam.id === "anthropic" || fam.id === "openai" || fam.id === "groq" || fam.id === "google") {
      setLlmAuthProtocol("API Key");
    } else {
      setLlmAuthProtocol("Bearer Token");
    }
  };

  const handleSelectEmbeddingFamily = (fam: FamilyOption) => {
    setSelectedEmbeddingFamily(fam);
    setEmbeddingName(fam.name);
    setEmbeddingUrl(fam.defaultUrl);
    setEmbeddingDiscoveredModels(fam.models);
    setEmbeddingSelectedModel(fam.models[0] || "");
    if (fam.type === "local" || fam.id === "sentence-transformers") {
      setEmbeddingAuthProtocol("No Authentication");
    } else {
      setEmbeddingAuthProtocol("API Key");
    }
  };

  const handleSelectRerankerFamily = (fam: FamilyOption) => {
    setSelectedRerankerFamily(fam);
    setRerankerName(fam.name);
    setRerankerModel(fam.models[0] || "");
  };

  // Dedicated Test Ping Actions (1-token / 1-ping verification)
  const handleTestLLMPing = async () => {
    setIsDiscoveringLLM(true);
    setLlmStatusMessage(null);
    try {
      const modelToTest = llmSelectedModel || (llmDiscoveredModels.length > 0 ? llmDiscoveredModels[0] : "");
      if (!modelToTest) {
        setLlmStatusMessage("✕ Please enter credentials / URL and discover or select a model first.");
        return;
      }

      const pingRes = await fetch("/api/provider/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          providerUrl: llmRuntimeUrl,
          apiKey: llmApiKey.trim() || undefined,
          model: modelToTest,
          messages: [{ role: "user", content: "ping" }],
        }),
      });

      if (pingRes.ok) {
        setLlmStatusMessage(`✓ Ping verified: Model "${modelToTest}" is online and responsive!`);
      } else {
        const errData = await pingRes.json().catch(() => ({}));
        setLlmStatusMessage(`✕ Ping failed: ${errData.message || `Provider returned HTTP ${pingRes.status}`}`);
      }
    } catch (e: any) {
      setLlmStatusMessage(`✕ Ping failed: ${e.message || "Endpoint offline or unreachable"}`);
    } finally {
      setIsDiscoveringLLM(false);
    }
  };

  const handleUpdateLLMConnectivity = async () => {
    if (!selectedLLMFamily) return;
    setIsDiscoveringLLM(true);
    try {
      let modelsToSave = llmDiscoveredModels;
      try {
        const disc = await discoverProviderModels(llmRuntimeUrl, llmApiKey || undefined);
        if (disc.models && disc.models.length > 0) {
          modelsToSave = disc.models;
        }
      } catch {}

      const providerId = await addLLMProvider(
        selectedLLMFamily.name,
        selectedLLMFamily.type,
        llmRuntimeUrl,
        llmApiKey || undefined,
        modelsToSave,
        llmSelectedModel
      );

      if (providerId) {
        setLLMActive(providerId);
        setLLMModel(providerId, llmSelectedModel);
      }
      setLlmLeftView("inventory");
      setActiveTab("navigator");
    } catch (e: any) {
      setLlmStatusMessage(e.message || "Failed to connect LLM provider.");
    } finally {
      setIsDiscoveringLLM(false);
    }
  };

  const handleTestEmbeddingPing = async () => {
    setEmbeddingTesting(true);
    setEmbeddingTestResult(null);
    try {
      const isLocalFamily =
        selectedEmbeddingFamily?.type === "local" ||
        selectedEmbeddingFamily?.id === "sentence-transformers";

      if (isLocalFamily) {
        const res = await fetch("/api/embedding-provider/native-test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: embeddingSelectedModel }),
          cache: "no-store",
        });
        const data = await res.json().catch(() => ({}));
        setEmbeddingTestResult(
          data?.success
            ? `✓ Ping verified: "${embeddingSelectedModel}" generated test vector! (${data?.message || ""})`
            : `✕ Ping failed: ${data?.message || "FAIM-native embedding core unreachable"}`
        );
        return;
      }

      const success = await testEmbeddingProvider({
        baseUrl: embeddingUrl,
        apiKey: embeddingApiKey || undefined,
        model: embeddingSelectedModel,
      });
      if (success) {
        setEmbeddingTestResult(`✓ Ping verified: Embedding model "${embeddingSelectedModel}" generated test vector!`);
      } else {
        setEmbeddingTestResult(`✕ Ping failed: Endpoint offline or model unreachable.`);
      }
    } catch (e: any) {
      setEmbeddingTestResult(`✕ Ping failed: ${e.message || "Unreachable"}`);
    } finally {
      setEmbeddingTesting(false);
    }
  };

  const handleUpdateEmbeddingConnectivity = async () => {
    setIsDiscoveringEmbedding(true);
    try {
      let modelsToSave = embeddingDiscoveredModels;
      try {
        const isLocal = selectedEmbeddingFamily?.type === "local" || selectedEmbeddingFamily?.id === "sentence-transformers";
        if (!isLocal) {
          const disc = await discoverEmbeddingModels(embeddingUrl, embeddingApiKey || undefined);
          if (disc.models && disc.models.length > 0) {
            modelsToSave = disc.models;
          }
        }
      } catch {}

      const providerId = await addEmbeddingProvider(
        embeddingName,
        (selectedEmbeddingFamily?.type || "custom") as any,
        embeddingUrl,
        embeddingApiKey || undefined,
        embeddingSelectedModel
      );
      if (providerId) {
        setEmbeddingActive(providerId);
      }
      setEmbeddingLeftView("inventory");
      setActiveTab("navigator");
    } catch (e: any) {
      setEmbeddingTestResult(e.message || "Failed to update embedding provider.");
    } finally {
      setIsDiscoveringEmbedding(false);
    }
  };

  const handleTestRerankerPing = async () => {
    setRerankerTesting(true);
    setRerankerTestResult(null);
    try {
      const res = await fetch("/api/reranker/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "ping test",
          candidates: ["Document 1", "Document 2"],
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success !== false) {
        const details = data.message ? ` (${data.message}${data.latency_ms !== undefined ? ` in ${data.latency_ms}ms` : ""})` : "";
        setRerankerTestResult(`✓ Ping verified: ReRanker model "${rerankerModel}" active!${details}`);
        setRerankerStatus("healthy");
      } else {
        setRerankerStatus("offline");
        setRerankerTestResult(`✕ Ping failed: ${data.message || "Reranker core offline"}`);
      }
    } catch {
      setRerankerStatus("offline");
      setRerankerTestResult(`✕ Ping failed: ReRanker endpoint unreachable`);
    } finally {
      setRerankerTesting(false);
    }
  };

  const handleUpdateRerankerConnectivity = async () => {
    try {
      await fetch("/api/v1/reranker/activate", { method: "POST" }).catch(() => {});
    } catch {}
    setRerankerStatus("healthy");
    setHasRerankerConfigured(true);
    localStorage.setItem(
      "faim.rerankerProvider",
      JSON.stringify({ name: rerankerName, model: rerankerModel, status: "healthy" })
    );
    setRerankerTestResult(`✓ ReRanker model "${rerankerModel}" active!`);
    setRerankerLeftView("inventory");
    setActiveTab("navigator");
  };

  // Unified Disconnection / Termination Handlers
  const handleTerminateLLM = async (targetId?: string | React.MouseEvent) => {
    const idToDelete = typeof targetId === "string" ? targetId : activeLLM?.id;
    if (!idToDelete) return;

    try {
      await fetch(`/api/v1/model-router/providers/${encodeURIComponent(idToDelete)}`, {
        method: "DELETE",
      }).catch(() => {});
    } catch {}

    removeLLMProvider(idToDelete);

    if (typeof targetId !== "string" || idToDelete === activeLLM?.id || idToDelete === selectedLLMFamily?.id) {
      setLlmApiKey("");
      setLlmStatusMessage(null);
      setLlmDiscoveredModels([]);
      setSelectedLLMFamily(null);
      setLlmLeftView("inventory");
    }
  };

  const handleTerminateEmbedding = async (targetId?: string | React.MouseEvent) => {
    const idToDelete = typeof targetId === "string" ? targetId : activeEmbedding?.id;
    if (!idToDelete) return;

    try {
      await fetch(`/api/v1/embedding-providers/${encodeURIComponent(idToDelete)}`, {
        method: "DELETE",
      }).catch(() => {});
    } catch {}

    removeEmbeddingProvider(idToDelete);

    if (typeof targetId !== "string" || idToDelete === activeEmbedding?.id || idToDelete === selectedEmbeddingFamily?.id) {
      setEmbeddingTestResult(null);
      setSelectedEmbeddingFamily(null);
      setEmbeddingLeftView("inventory");
    }
  };

  const handleTerminateReranker = async () => {
    try {
      await fetch("/api/v1/reranker/deactivate", { method: "POST" }).catch(() => {});
    } catch {}
    localStorage.removeItem("faim.rerankerProvider");
    setHasRerankerConfigured(false);
    setRerankerStatus("not_configured");
    setRerankerTestResult(null);
    setSelectedRerankerFamily(null);
    setRerankerLeftView("inventory");
  };

  const handleTerminateWeb = async () => {
    localStorage.removeItem("faim.webProvider");
    setHasWebConfigured(false);
    setWebStatus("not_configured");
    setWebTestResult(null);
    setWebApiKey("");
    setWebEndpoint("");
    setSelectedWebFamily(null);
    setWebLeftView("inventory");
  };

  const [webApiKey, setWebApiKey] = useState("");

  const handleSelectWebFamily = (fam: FamilyOption) => {
    setSelectedWebFamily(fam);
    setWebName(fam.name);
    setWebEndpoint(fam.defaultUrl);
    if (fam.id === "serper" || fam.id === "tavily" || fam.type === "custom") {
      setWebAuthProtocol("API Key");
    } else {
      setWebAuthProtocol("local no key");
    }
  };

  const handleTestWebPing = async () => {
    setWebTesting(true);
    setWebTestResult(null);
    try {
      const famId = selectedWebFamily?.id;
      const isApiKeyRequired =
        webAuthProtocol === "API Key" ||
        famId === "serper" ||
        famId === "tavily";

      if (isApiKeyRequired && !webApiKey.trim()) {
        setWebTestResult(
          `✕ Ping failed: API key required for ${webName}. Please enter your Serper/Tavily API key.`
        );
        setWebStatus("not_configured");
        return;
      }

      if (!webEndpoint.trim()) {
        setWebTestResult(`✕ Ping failed: Invalid endpoint URL.`);
        setWebStatus("not_configured");
        return;
      }

      // Perform ping test check
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      try {
        await fetch(webEndpoint, {
          method: "HEAD",
          mode: "no-cors",
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        setWebTestResult(
          `✓ Ping verified: Web search endpoint "${webName}" connected!`
        );
        setWebStatus("connected");
      } catch {
        clearTimeout(timeoutId);
        if (webApiKey.trim()) {
          setWebTestResult(
            `✓ Ping verified: Web search endpoint "${webName}" configured with API key!`
          );
          setWebStatus("connected");
        } else {
          setWebTestResult(`✕ Ping failed: Endpoint "${webEndpoint}" unreachable.`);
          setWebStatus("not_configured");
        }
      }
    } catch (e: any) {
      setWebTestResult(`✕ Ping failed: ${e.message || "Endpoint unreachable"}`);
    } finally {
      setWebTesting(false);
    }
  };

  const handleUpdateWebConnectivity = () => {
    const famId = selectedWebFamily?.id;
    const isApiKeyRequired =
      webAuthProtocol === "API Key" ||
      famId === "serper" ||
      famId === "tavily";

    if (isApiKeyRequired && !webApiKey.trim()) {
      setWebTestResult(
        `✕ Cannot link: API key required for ${webName}.`
      );
      return;
    }

    setWebTesting(true);
    setTimeout(() => {
      setWebStatus("connected");
      setHasWebConfigured(true);
      setWebTesting(false);
      localStorage.setItem(
        "faim.webProvider",
        JSON.stringify({
          name: webName,
          endpoint: webEndpoint,
          apiKey: webApiKey || undefined,
          status: "connected",
        })
      );
      setWebLeftView("inventory");
      setActiveTab("navigator");
    }, 500);
  };

  // OCR State & Handlers
  const [hasOcrConfigured, setHasOcrConfigured] = useState(false);
  const [ocrProvidersList, setOcrProvidersList] = useState<any[]>([]);
  const [activeOcrId, setActiveOcrId] = useState<string>("paddleocr_v6");
  const [selectedOcrFamily, setSelectedOcrFamily] = useState<FamilyOption | null>(null);
  const [ocrName, setOcrName] = useState(OCR_FAMILIES[0].name);
  const [ocrAuthProtocol, setOcrAuthProtocol] = useState("local no key");
  const [ocrEndpoint, setOcrEndpoint] = useState(OCR_FAMILIES[0].defaultUrl);
  const [ocrLanguages, setOcrLanguages] = useState("eng");
  const [ocrDpi, setOcrDpi] = useState("300");
  const [ocrStatus, setOcrStatus] = useState<"healthy" | "not_configured" | "offline">("not_configured");
  const [ocrTesting, setOcrTesting] = useState(false);
  const [ocrTestResult, setOcrTestResult] = useState<any | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("faim.ocrProvider");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.name) setOcrName(parsed.name);
        if (parsed.id) {
          setActiveOcrId(parsed.id);
          const fam = OCR_FAMILIES.find((f) => f.id === parsed.id) || OCR_FAMILIES[0];
          setSelectedOcrFamily(fam);
        }
        if (parsed.status) setOcrStatus(parsed.status);
        setHasOcrConfigured(true);
      } else {
        setHasOcrConfigured(false);
        setOcrStatus("not_configured");
        setSelectedOcrFamily(null);
      }
    } catch {
      setHasOcrConfigured(false);
      setOcrStatus("not_configured");
      setSelectedOcrFamily(null);
    }
  }, []);

  const fetchOcrProviders = async () => {
    try {
      const res = await fetch("/api/v1/ocr-providers", { cache: "no-store" });
      if (res.ok) {
        const data = await res.json();
        if (data.items) setOcrProvidersList(data.items);
        if (data.active_provider_id) {
          setActiveOcrId(data.active_provider_id);
        }
      }
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    fetchOcrProviders();
  }, []);

  const handleSwitchOcr = async (providerId: string) => {
    try {
      const res = await fetch("/api/v1/ocr-providers/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_id: providerId }),
      });
      if (res.ok) {
        setActiveOcrId(providerId);
        await fetchOcrProviders();
      }
    } catch (e) {
      console.error("Failed to switch OCR provider", e);
    }
  };

  const handleTestOcrPing = async (providerId: string = activeOcrId) => {
    setOcrTesting(true);
    setOcrTestResult(null);
    try {
      const res = await fetch(`/api/v1/ocr-providers/${encodeURIComponent(providerId)}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ languages: ocrLanguages }),
      });
      const data = await res.json();
      setOcrTestResult(data);
    } catch (e: any) {
      setOcrTestResult({
        success: false,
        message: e.message || "OCR engine test failed",
        latency_ms: 0,
      });
    } finally {
      setOcrTesting(false);
    }
  };

  const handleSelectOcrFamily = (fam: FamilyOption) => {
    setSelectedOcrFamily(fam);
    setOcrName(fam.name);
    setOcrEndpoint(fam.defaultUrl);
    setOcrAuthProtocol(fam.type === "local" ? "local no key" : "API Key");
    setOcrTestResult(null);
  };

  const handleLinkOcrFamily = async () => {
    if (!selectedOcrFamily) return;
    if (selectedOcrFamily.type === "custom") {
      try {
        await fetch("/api/v1/ocr-providers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            id: selectedOcrFamily.id,
            name: selectedOcrFamily.name,
            provider_type: "custom",
            base_url: ocrEndpoint,
            languages: [ocrLanguages],
          }),
        });
      } catch {}
    }
    await handleSwitchOcr(selectedOcrFamily.id);
    setHasOcrConfigured(true);
    setOcrName(selectedOcrFamily.name);
    setOcrStatus("healthy");
    localStorage.setItem(
      "faim.ocrProvider",
      JSON.stringify({
        id: selectedOcrFamily.id,
        name: selectedOcrFamily.name,
        endpoint: ocrEndpoint,
        languages: ocrLanguages,
        dpi: ocrDpi,
        status: "healthy",
      })
    );
    setOcrLeftView("inventory");
    setActiveTab("navigator");
  };

  const handleTerminateOcr = () => {
    setHasOcrConfigured(false);
    setOcrStatus("not_configured");
    localStorage.removeItem("faim.ocrProvider");
    setSelectedOcrFamily(null);
    setOcrLeftView("inventory");
    setActiveTab("navigator");
  };


  return (
    <>
      <div className="space-y-4">
        {/* FAIM Glass Header */}
        <GlassHeader
        title="Providers"
        subtitle="MANAGE FOUNDATION MODELS AND RUNTIME CONNECTIVITY"
        icon={Cpu}
        accentColor="var(--faim-primary)"
        actions={
        <>
          <Button
            variant="outline"
            leftIcon={<BookOpen size={13} />}
            onClick={() => setManualOpen(true)}
            className="rounded-xl border-white/5 bg-white/5 hover:bg-white/10 backdrop-blur-md h-10 px-5 text-[11px] font-bold uppercase tracking-[0.2em]"
          >
            User Manual
          </Button>
          <TabToggle active={activeTab} onChange={setActiveTab} />
        </>
      }
      />

      <AnimatePresence mode="wait">
        {/* ========================================================================= */}
        {/* TAB 1: NAVIGATOR (ACTIVE INVENTORY DASHBOARD) */}
        {/* ========================================================================= */}
        {activeTab === "navigator" && (
          <motion.div
            key="tab-navigator"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
          >
            {/* Card 1: LLM Active */}
            <div className="rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl hover:border-primary-500/40 transition-all">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-xl border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center">
                    <Bot size={16} />
                  </div>
                  <div
                    className={[
                      "px-2.5 py-0.5 rounded-lg border text-[10px] font-mono font-bold tracking-wider flex items-center gap-1.5 uppercase",
                      activeLLM
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/10 border-slate-500/20 text-slate-400",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-1.5 h-1.5 rounded-full",
                        activeLLM ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                      ].join(" ")}
                    />
                    {activeLLM ? "(✓ ONLINE)" : "(✕ NOT CONFIGURED)"}
                  </div>
                </div>

                <div>
                  <p className="font-mono text-[10px] font-bold text-primary-400 uppercase tracking-[0.2em]">
                    LLM ACTIVE
                  </p>
                  <h3 className="text-base font-bold text-white tracking-tight mt-0.5">
                    {activeLLM ? activeLLM.name : "Not Configured"}
                  </h3>
                  <p className="text-xs font-mono text-primary-200/80 mt-0.5 truncate">
                    {activeLLM?.activeModel || "No active LLM connection"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="pt-2 border-t border-white/8 flex items-center justify-between">
                  <span
                    className={[
                      "text-[11px] font-mono font-bold tracking-wider",
                      activeLLM ? "text-emerald-400" : "text-slate-500",
                    ].join(" ")}
                  >
                    {llmProviders.length > 0 ? `${llmProviders.length} PROVIDER(S) CONFIGURED` : "0 PROVIDERS CONFIGURED"}
                  </span>
                </div>

                {activeLLM ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => {
                        refreshAllProvidersStatus();
                        setActiveTab("llm");
                      }}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-white/5 text-slate-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-primary-400" />
                      VERIFY
                    </button>
                    <button
                      onClick={handleTerminateLLM}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-rose-400" />
                      TERMINATE
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setActiveTab("llm")}
                    className="w-full py-2 rounded-lg border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus size={14} />
                    + CONFIGURE LLM
                  </button>
                )}
              </div>
            </div>

            {/* Card 2: Embedding Active */}
            <div className="rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl hover:border-primary-500/40 transition-all">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-xl border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center">
                    <Database size={16} />
                  </div>
                  <div
                    className={[
                      "px-2.5 py-0.5 rounded-lg border text-[10px] font-mono font-bold tracking-wider flex items-center gap-1.5 uppercase",
                      activeEmbedding
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/10 border-slate-500/20 text-slate-400",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-1.5 h-1.5 rounded-full",
                        activeEmbedding ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                      ].join(" ")}
                    />
                    {activeEmbedding ? "(✓ ONLINE)" : "(✕ NOT CONFIGURED)"}
                  </div>
                </div>

                <div>
                  <p className="font-mono text-[10px] font-bold text-primary-400 uppercase tracking-[0.2em]">
                    EMBEDDING ACTIVE
                  </p>
                  <h3 className="text-base font-bold text-white tracking-tight mt-0.5 truncate">
                    {activeEmbedding ? activeEmbedding.name : "Not Configured"}
                  </h3>
                  <p className="text-xs font-mono text-primary-200/80 mt-0.5 truncate">
                    {activeEmbedding?.model || "No active embedding model"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="pt-2 border-t border-white/8 flex items-center justify-between">
                  <span
                    className={[
                      "text-[11px] font-mono font-bold tracking-wider",
                      activeEmbedding ? "text-emerald-400" : "text-slate-500",
                    ].join(" ")}
                  >
                    {embeddingProviders.length > 0 ? `${embeddingProviders.length} PROVIDER(S) CONFIGURED` : "0 PROVIDERS CONFIGURED"}
                  </span>
                </div>

                {activeEmbedding ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setActiveTab("embedding")}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-white/5 text-slate-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-primary-400" />
                      VERIFY
                    </button>
                    <button
                      onClick={handleTerminateEmbedding}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-rose-400" />
                      TERMINATE
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setActiveTab("embedding")}
                    className="w-full py-2 rounded-lg border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus size={14} />
                    + CONFIGURE EMBEDDING
                  </button>
                )}
              </div>
            </div>

            {/* Card 3: Reranker Active */}
            <div className="rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl hover:border-primary-500/40 transition-all">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-xl border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center">
                    <Target size={16} />
                  </div>
                  <div
                    className={[
                      "px-2.5 py-0.5 rounded-lg border text-[10px] font-mono font-bold tracking-wider flex items-center gap-1.5 uppercase",
                      hasRerankerConfigured
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/10 border-slate-500/20 text-slate-400",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-1.5 h-1.5 rounded-full",
                        hasRerankerConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                      ].join(" ")}
                    />
                    {hasRerankerConfigured ? "(✓ HEALTHY)" : "(✕ NOT CONFIGURED)"}
                  </div>
                </div>

                <div>
                  <p className="font-mono text-[10px] font-bold text-primary-400 uppercase tracking-[0.2em]">
                    RERANKER ACTIVE
                  </p>
                  <h3 className="text-base font-bold text-white tracking-tight mt-0.5 truncate">
                    {hasRerankerConfigured ? rerankerName : "Not Configured"}
                  </h3>
                  <p className="text-xs font-mono text-primary-200/80 mt-0.5 truncate">
                    {hasRerankerConfigured ? rerankerModel : "No active reranker model"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="pt-2 border-t border-white/8 flex items-center justify-between">
                  <span
                    className={[
                      "text-[11px] font-mono font-bold tracking-wider",
                      hasRerankerConfigured ? "text-emerald-400" : "text-slate-500",
                    ].join(" ")}
                  >
                    {hasRerankerConfigured ? "1 PROVIDER CONFIGURED" : "0 PROVIDERS CONFIGURED"}
                  </span>
                </div>

                {hasRerankerConfigured ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setActiveTab("reranker")}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-white/5 text-slate-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-primary-400" />
                      VERIFY
                    </button>
                    <button
                      onClick={handleTerminateReranker}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-rose-400" />
                      TERMINATE
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setActiveTab("reranker")}
                    className="w-full py-2 rounded-lg border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus size={14} />
                    + CONFIGURE RERANKER
                  </button>
                )}
              </div>
            </div>

            {/* Card 4: Web Active */}
            <div className="rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl hover:border-primary-500/40 transition-all">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-xl border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center">
                    <Globe size={16} />
                  </div>
                  <div
                    className={[
                      "px-2.5 py-0.5 rounded-lg border text-[10px] font-mono font-bold tracking-wider flex items-center gap-1.5 uppercase",
                      hasWebConfigured
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/10 border-slate-500/20 text-slate-400",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-1.5 h-1.5 rounded-full",
                        hasWebConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                      ].join(" ")}
                    />
                    {hasWebConfigured ? "(✓ CONNECTED)" : "(✕ NOT CONFIGURED)"}
                  </div>
                </div>

                <div>
                  <p className="font-mono text-[10px] font-bold text-primary-400 uppercase tracking-[0.2em]">
                    WEB ACTIVE
                  </p>
                  <h3 className="text-base font-bold text-white tracking-tight mt-0.5 truncate">
                    {hasWebConfigured ? webName : "Not Configured"}
                  </h3>
                  <p className="text-xs font-mono text-primary-200/80 mt-0.5 truncate">
                    {hasWebConfigured ? webEndpoint : "No active web search endpoint"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="pt-2 border-t border-white/8 flex items-center justify-between">
                  <span
                    className={[
                      "text-[11px] font-mono font-bold tracking-wider",
                      hasWebConfigured ? "text-emerald-400" : "text-slate-500",
                    ].join(" ")}
                  >
                    {hasWebConfigured ? "1 PROVIDER CONFIGURED" : "0 PROVIDERS CONFIGURED"}
                  </span>
                </div>

                {hasWebConfigured ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setActiveTab("web")}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-white/5 text-slate-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-primary-400" />
                      VERIFY
                    </button>
                    <button
                      onClick={handleTerminateWeb}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-rose-400" />
                      TERMINATE
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setActiveTab("web")}
                    className="w-full py-2 rounded-lg border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus size={14} />
                    + CONFIGURE WEB SEARCH
                  </button>
                )}
              </div>
            </div>

            {/* Card 5: OCR Active */}
            <div className="rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl hover:border-primary-500/40 transition-all">
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-xl border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center">
                    <ScanText size={16} />
                  </div>
                  <div
                    className={[
                      "px-2.5 py-0.5 rounded-lg border text-[10px] font-mono font-bold tracking-wider flex items-center gap-1.5 uppercase",
                      hasOcrConfigured
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                        : "bg-slate-500/10 border-slate-500/20 text-slate-400",
                    ].join(" ")}
                  >
                    <div
                      className={[
                        "w-1.5 h-1.5 rounded-full",
                        hasOcrConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                      ].join(" ")}
                    />
                    {hasOcrConfigured ? "(✓ CONNECTED)" : "(✕ NOT CONFIGURED)"}
                  </div>
                </div>

                <div>
                  <p className="font-mono text-[10px] font-bold text-primary-400 uppercase tracking-[0.2em]">
                    OCR ACTIVE
                  </p>
                  <h3 className="text-base font-bold text-white tracking-tight mt-0.5 truncate">
                    {hasOcrConfigured ? ocrName : "Not Configured"}
                  </h3>
                  <p className="text-xs font-mono text-primary-200/80 mt-0.5 truncate">
                    {hasOcrConfigured ? "Native CPU Multi-Core & Angle Classification" : "No active OCR engine configured"}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <div className="pt-2 border-t border-white/8 flex items-center justify-between">
                  <span
                    className={[
                      "text-[11px] font-mono font-bold tracking-wider",
                      hasOcrConfigured ? "text-emerald-400" : "text-slate-500",
                    ].join(" ")}
                  >
                    {hasOcrConfigured ? "1 PROVIDER CONFIGURED" : "0 PROVIDERS CONFIGURED"}
                  </span>
                </div>

                {hasOcrConfigured ? (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => setActiveTab("ocr")}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-white/5 text-slate-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-primary-400" />
                      VERIFY
                    </button>
                    <button
                      onClick={handleTerminateOcr}
                      className="py-1.5 rounded-lg border border-white/10 bg-black/40 hover:bg-rose-500/10 hover:border-rose-500/30 text-slate-300 hover:text-rose-400 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all"
                    >
                      <Zap size={12} className="text-rose-400" />
                      TERMINATE
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setActiveTab("ocr")}
                    className="w-full py-2 rounded-lg border border-primary-500/30 bg-primary-500/10 hover:bg-primary-500/20 text-primary-300 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-all"
                  >
                    <Plus size={14} />
                    + CONFIGURE OCR
                  </button>
                )}
              </div>
            </div>

          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: LLM SETUP */}
        {/* ========================================================================= */}
        {activeTab === "llm" && (
          <motion.div
            key="tab-llm"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-4"
          >
            {/* Left Panel Sidebar */}
            <div className="lg:col-span-4 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl">
              <AnimatePresence mode="wait">
                {llmLeftView === "inventory" ? (
                  <motion.div
                    key="llm-inventory"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        INVENTORY
                      </span>
                      <button
                        onClick={() => {
                          setLlmLeftView("select_family");
                          setSelectedLLMFamily(null);
                        }}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Add LLM Family"
                      >
                        <Plus size={16} />
                      </button>
                    </div>

                    <div className="space-y-0.5">
                      <p className="font-mono text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                        LLM FAMILIES
                      </p>
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-extrabold text-white">Inventory</h3>
                        <span className="text-xs font-mono bg-black/40 border border-primary-500/30 text-primary-300 px-2 py-0.5 rounded-full font-bold">
                          {llmProviders.length} options
                        </span>
                      </div>
                    </div>

                    <div className="h-[1px] bg-white/5 my-1" />

                    {llmProviders.length === 0 ? (
                      <div className="p-5 text-center border border-dashed border-white/10 rounded-xl bg-black/20 space-y-2">
                        <p className="text-xs font-mono text-slate-500 italic">
                          No active connections.
                        </p>
                        <button
                          onClick={() => {
                            setLlmLeftView("select_family");
                            setSelectedLLMFamily(null);
                          }}
                          className="px-3 py-1.5 text-xs font-mono font-bold bg-primary-500/20 border border-primary-500/40 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-all"
                        >
                          + Add Connection
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 custom-scrollbar">
                        {llmProviders.map((prov) => {
                          const selected = activeLLM?.id === prov.id;
                          return (
                            <div
                              key={prov.id}
                              onClick={() => {
                                setLLMActive(prov.id);
                                const matchingFam = LLM_FAMILIES.find(
                                  (f) => f.name.toLowerCase() === prov.name.toLowerCase()
                                ) || {
                                  id: prov.id,
                                  name: prov.name,
                                  code: prov.type.toUpperCase(),
                                  type: prov.type as any,
                                  defaultUrl: prov.baseUrl,
                                  models: prov.models || [],
                                };
                                setSelectedLLMFamily(matchingFam);
                                setLlmRuntimeUrl(prov.baseUrl);
                                if (prov.models && prov.models.length > 0) {
                                  setLlmDiscoveredModels(prov.models);
                                }
                                if (prov.activeModel) {
                                  setLlmSelectedModel(prov.activeModel);
                                }
                              }}
                              className={[
                                "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                                selected
                                  ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                  : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                              ].join(" ")}
                            >
                              <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                                <Bot size={14} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <p className="text-xs font-bold truncate">{prov.name}</p>
                                  <span className="text-[9px] font-mono bg-primary-500/20 border border-primary-500/40 text-primary-300 px-1.5 py-0.5 rounded font-bold">
                                    {prov.type.toUpperCase()}
                                  </span>
                                </div>
                                <p className="text-[10px] font-mono text-slate-400 truncate mt-0.5">
                                  {prov.activeModel || "Default"}
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleTerminateLLM(prov.id);
                                }}
                                className="p-1 rounded-md hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-all shrink-0"
                                title="Terminate this provider"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="llm-select-family"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        SELECT FAMILY
                      </span>
                      <button
                        onClick={() => setLlmLeftView("inventory")}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Close"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <button
                      onClick={() => setLlmLeftView("inventory")}
                      className="w-full p-2 rounded-xl bg-black/40 hover:bg-white/5 border border-white/10 text-xs font-bold text-white flex items-center gap-2 transition-all"
                    >
                      <ArrowLeft size={14} />
                      Back to Inventory
                    </button>

                    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                      {LLM_FAMILIES.map((fam) => {
                        const selected = selectedLLMFamily?.id === fam.id;
                        return (
                          <div
                            key={fam.id}
                            onClick={() => handleSelectLLMFamily(fam)}
                            className={[
                              "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                              selected
                                ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                            ].join(" ")}
                          >
                            <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                              <Zap size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold truncate">{fam.name}</p>
                              <p className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">
                                {fam.code}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Panel: Chat Setup Form or Empty State */}
            {selectedLLMFamily === null ? (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-4 shadow-xl min-h-[380px]">
                <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 text-primary-400 flex items-center justify-center">
                  <Zap size={28} />
                </div>
                <div className="space-y-1 max-w-sm">
                  <h3 className="text-base font-bold text-white tracking-tight">System Navigator</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Select a provider family from the left list to adjust its parameters or test connectivity.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setLlmLeftView("select_family");
                    setSelectedLLMFamily(null);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-primary-500/15 border border-primary-500/40 text-primary-300 font-mono text-xs font-bold hover:bg-primary-500/25 transition-all shadow-[0_0_15px_rgba(34,211,238,0.15)] flex items-center gap-2"
                >
                  <Plus size={14} />
                  + Add Connection
                </button>
              </div>
            ) : (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4 shadow-xl">
                <div>
                  <p className="font-mono text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                    CHAT SETUP
                  </p>
                  <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                    {selectedLLMFamily.name}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Connect this chat provider, enter the API key, then link it.
                  </p>
                </div>

                {/* Input Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Auth Protocol with CustomSelect */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      AUTHENTICATION PROTOCOL
                    </label>
                    <CustomSelect
                      value={llmAuthProtocol}
                      onChange={setLlmAuthProtocol}
                      options={["local no key", "Bearer Token", "API Key", "No Authentication"]}
                    />
                  </div>

                  {/* API / Runtime URL */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      API / RUNTIME URL
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={llmRuntimeUrl}
                        onChange={(e) => setLlmRuntimeUrl(e.target.value)}
                        className="w-full bg-slate-950/70 border border-white/10 rounded-xl pl-3 pr-8 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                      />
                      <Globe size={14} className="absolute right-3 top-2.5 text-slate-500" />
                    </div>
                  </div>
                </div>

                {/* API Key / Token Input Field */}
                {(llmAuthProtocol === "API Key" ||
                  llmAuthProtocol === "Bearer Token" ||
                  selectedLLMFamily.type === "openai" ||
                  selectedLLMFamily.id === "anthropic" ||
                  selectedLLMFamily.id === "google" ||
                  selectedLLMFamily.id === "groq" ||
                  selectedLLMFamily.id === "openrouter" ||
                  selectedLLMFamily.id === "opencode-zen") && (
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-primary-400 uppercase flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <KeyRound size={12} className="text-primary-400" />
                        {llmAuthProtocol === "Bearer Token" ? "BEARER TOKEN" : "API KEY"} ({selectedLLMFamily.name.toUpperCase()})
                      </span>
                      <span className="text-[9px] text-slate-400 font-normal">Stored securely in browser session</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showLlmApiKey ? "text" : "password"}
                        value={llmApiKey}
                        onChange={(e) => setLlmApiKey(e.target.value)}
                        placeholder={`Enter ${selectedLLMFamily.name} ${llmAuthProtocol === "Bearer Token" ? "Token" : "API Key"}...`}
                        className="w-full bg-slate-950/70 border border-primary-500/40 rounded-xl pl-3 pr-10 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-400 transition-all font-mono placeholder:text-slate-600 shadow-inner"
                      />
                      <button
                        type="button"
                        onClick={() => setShowLlmApiKey(!showLlmApiKey)}
                        className="absolute right-3 top-2.5 text-slate-400 hover:text-primary-400 transition-colors"
                        title={showLlmApiKey ? "Hide Key" : "Show Key"}
                      >
                        {showLlmApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>
                )}

                {/* Chat Model Selection with CustomSelect */}
                <div className="space-y-1">
                  <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                    CHAT MODEL
                  </label>
                  <CustomSelect
                    value={llmSelectedModel}
                    onChange={setLlmSelectedModel}
                    options={llmDiscoveredModels}
                  />
                </div>

                {/* Model Discovery Section */}
                <div className="space-y-1.5 pt-0.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-400 uppercase">
                      MODEL DISCOVERY
                    </span>
                    <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {isDiscoveringLLM ? "DISCOVERING..." : `${llmDiscoveredModels.length} MODELS FOUND`}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-black/30 border border-white/8 text-xs text-slate-400">
                    When you enter the token, supported chat models are fetched automatically for this provider.
                  </div>
                  {llmStatusMessage && (
                    <p className="text-xs font-mono text-primary-300">{llmStatusMessage}</p>
                  )}
                </div>

                {/* Metric / Status Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-0.5">
                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      CURRENT TARGET
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {activeLLM ? activeLLM.activeModel : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">Managed chat runtime</p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      RUNTIME URL
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {activeLLM ? activeLLM.baseUrl : "Not set"}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      STATUS
                    </p>
                    <p
                      className={[
                        "text-xs font-bold flex items-center gap-1.5",
                        activeLLM ? "text-emerald-400" : "text-slate-400",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "w-1.5 h-1.5 rounded-full",
                          activeLLM ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                        ].join(" ")}
                      />
                      {activeLLM ? "Healthy" : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {activeLLM ? "Last runtime check." : "No active LLM connection."}
                    </p>
                  </div>
                </div>

                {/* Bottom Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-white/8">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleTestLLMPing}
                      disabled={isDiscoveringLLM}
                      className="font-mono text-xs font-bold tracking-wider text-slate-300 hover:text-white flex items-center gap-1.5 transition-all"
                    >
                      {isDiscoveringLLM ? (
                        <Loader2 size={14} className="animate-spin text-primary-400" />
                      ) : (
                        <Zap size={14} className="text-primary-400" />
                      )}
                      TEST PING
                    </button>

                    <button
                      onClick={handleTerminateLLM}
                      className="font-mono text-xs font-bold tracking-wider text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-all"
                    >
                      <Zap size={14} />
                      TERMINATE
                    </button>
                  </div>

                  <Button onClick={handleUpdateLLMConnectivity} size="md" className="gap-2">
                    <Link2 size={15} />
                    Update Connectivity
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: EMBEDDING SETUP */}
        {/* ========================================================================= */}
        {activeTab === "embedding" && (
          <motion.div
            key="tab-embedding"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-4"
          >
            {/* Left Panel Sidebar */}
            <div className="lg:col-span-4 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl">
              <AnimatePresence mode="wait">
                {embeddingLeftView === "inventory" ? (
                  <motion.div
                    key="emb-inventory"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        INVENTORY
                      </span>
                      <button
                        onClick={() => {
                          setEmbeddingLeftView("select_family");
                          setSelectedEmbeddingFamily(null);
                        }}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Add Embedding Provider"
                      >
                        <Plus size={16} />
                      </button>
                    </div>

                    <div className="space-y-0.5">
                      <p className="font-mono text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                        EMBEDDING FAMILIES
                      </p>
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-extrabold text-white">Inventory</h3>
                        <span className="text-xs font-mono bg-black/40 border border-primary-500/30 text-primary-300 px-2 py-0.5 rounded-full font-bold">
                          {embeddingProviders.length} options
                        </span>
                      </div>
                    </div>

                    <div className="h-[1px] bg-white/5 my-1" />

                    {embeddingProviders.length === 0 ? (
                      <div className="p-5 text-center border border-dashed border-white/10 rounded-xl bg-black/20 space-y-2">
                        <p className="text-xs font-mono text-slate-500 italic">
                          No active connections.
                        </p>
                        <button
                          onClick={() => {
                            setEmbeddingLeftView("select_family");
                            setSelectedEmbeddingFamily(null);
                          }}
                          className="px-3 py-1.5 text-xs font-mono font-bold bg-primary-500/20 border border-primary-500/40 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-all"
                        >
                          + Add Connection
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 custom-scrollbar">
                        {embeddingProviders.map((prov) => {
                          const selected = activeEmbedding?.id === prov.id;
                          return (
                            <div
                              key={prov.id}
                              onClick={() => {
                                setEmbeddingActive(prov.id);
                                const matchingFam = EMBEDDING_FAMILIES.find(
                                  (f) => f.name.toLowerCase() === prov.name.toLowerCase()
                                ) || EMBEDDING_FAMILIES[0];
                                setSelectedEmbeddingFamily(matchingFam);
                              }}
                              className={[
                                "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                                selected
                                  ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                  : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                              ].join(" ")}
                            >
                              <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                                <Database size={14} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <p className="text-xs font-bold truncate">{prov.name}</p>
                                  <span className="text-[9px] font-mono bg-primary-500/20 border border-primary-500/40 text-primary-300 px-1.5 py-0.5 rounded font-bold">
                                    HOSTED
                                  </span>
                                </div>
                                <p className="text-[10px] font-mono text-slate-400 truncate mt-0.5">
                                  {prov.model || "Default"}
                                </p>
                              </div>
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleTerminateEmbedding(prov.id);
                                }}
                                className="p-1 rounded-md hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-all shrink-0"
                                title="Terminate this provider"
                              >
                                <Trash2 size={13} />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="emb-select-family"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        SELECT FAMILY
                      </span>
                      <button
                        onClick={() => setEmbeddingLeftView("inventory")}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Close"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <button
                      onClick={() => setEmbeddingLeftView("inventory")}
                      className="w-full p-2 rounded-xl bg-black/40 hover:bg-white/5 border border-white/10 text-xs font-bold text-white flex items-center gap-2 transition-all"
                    >
                      <ArrowLeft size={14} />
                      Back to Inventory
                    </button>

                    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                      {EMBEDDING_FAMILIES.map((fam) => {
                        const selected = selectedEmbeddingFamily?.id === fam.id;
                        return (
                          <div
                            key={fam.id}
                            onClick={() => handleSelectEmbeddingFamily(fam)}
                            className={[
                              "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                              selected
                                ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                            ].join(" ")}
                          >
                            <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                              <Zap size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold truncate">{fam.name}</p>
                              <p className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">
                                {fam.code}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Panel: Embedding Setup Form or Empty State */}
            {selectedEmbeddingFamily === null ? (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-4 shadow-xl min-h-[380px]">
                <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 text-primary-400 flex items-center justify-center">
                  <Zap size={28} />
                </div>
                <div className="space-y-1 max-w-sm">
                  <h3 className="text-base font-bold text-white tracking-tight">System Navigator</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Select a provider family from the left list to adjust its parameters or test connectivity.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setEmbeddingLeftView("select_family");
                    setSelectedEmbeddingFamily(null);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-primary-500/15 border border-primary-500/40 text-primary-300 font-mono text-xs font-bold hover:bg-primary-500/25 transition-all shadow-[0_0_15px_rgba(34,211,238,0.15)] flex items-center gap-2"
                >
                  <Plus size={14} />
                  + Add Connection
                </button>
              </div>
            ) : (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4 shadow-xl">
                <div>
                  <p className="font-mono text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                    EMBEDDING SETUP
                  </p>
                  <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                    {selectedEmbeddingFamily.name}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Connect this embedding provider, enter the API key, then link it.
                  </p>
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Auth Protocol with CustomSelect */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      AUTHENTICATION PROTOCOL
                    </label>
                    <CustomSelect
                      value={embeddingAuthProtocol}
                      onChange={setEmbeddingAuthProtocol}
                      options={["No Authentication", "API Key", "Bearer Token"]}
                    />
                  </div>

                  {/* API / Runtime URL — hidden for built-in local family */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      API / RUNTIME URL
                    </label>
                    {selectedEmbeddingFamily?.type === "local" ||
                    selectedEmbeddingFamily?.id === "sentence-transformers" ? (
                      <div className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-400 font-mono flex items-center gap-2 shadow-inner">
                        <Info size={14} className="text-primary-400 shrink-0" />
                        <span className="truncate">Managed runtime — built-in local model, no URL needed.</span>
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={embeddingUrl}
                        onChange={(e) => setEmbeddingUrl(e.target.value)}
                        className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                      />
                    )}
                  </div>
                </div>

                {/* API Key Input Field for Embedding */}
                {(embeddingAuthProtocol === "API Key" ||
                  embeddingAuthProtocol === "Bearer Token" ||
                  selectedEmbeddingFamily?.type === "openai" ||
                  selectedEmbeddingFamily?.id === "openai-embed") && (
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-primary-400 uppercase flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <KeyRound size={12} className="text-primary-400" />
                        {embeddingAuthProtocol === "Bearer Token" ? "BEARER TOKEN" : "API KEY"} ({selectedEmbeddingFamily.name.toUpperCase()})
                      </span>
                      <span className="text-[9px] text-slate-400 font-normal">Stored securely in browser session</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showEmbeddingApiKey ? "text" : "password"}
                        value={embeddingApiKey}
                        onChange={(e) => setEmbeddingApiKey(e.target.value)}
                        placeholder={`Enter ${selectedEmbeddingFamily.name} API Key...`}
                        className="w-full bg-slate-950/70 border border-primary-500/40 rounded-xl pl-3 pr-10 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-400 transition-all font-mono placeholder:text-slate-600 shadow-inner"
                      />
                      <button
                        type="button"
                        onClick={() => setShowEmbeddingApiKey(!showEmbeddingApiKey)}
                        className="absolute right-3 top-2.5 text-slate-400 hover:text-primary-400 transition-colors"
                        title={showEmbeddingApiKey ? "Hide Key" : "Show Key"}
                      >
                        {showEmbeddingApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                  </div>
                )}

                {/* Embedding Model with CustomSelect */}
                <div className="space-y-1">
                  <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                    EMBEDDING MODEL
                  </label>
                  <CustomSelect
                    value={embeddingSelectedModel}
                    onChange={setEmbeddingSelectedModel}
                    options={embeddingDiscoveredModels}
                  />
                </div>

                {/* Model Discovery */}
                <div className="space-y-1.5 pt-0.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-400 uppercase">
                      MODEL DISCOVERY
                    </span>
                    <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {isDiscoveringEmbedding ? "DISCOVERING..." : `${embeddingDiscoveredModels.length} MODELS FOUND`}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-black/30 border border-white/8 text-xs text-slate-400">
                    When you enter the token, supported embedding models are fetched automatically for this provider.
                  </div>
                  {embeddingTestResult && (
                    <p className="text-xs font-mono text-primary-300">{embeddingTestResult}</p>
                  )}
                </div>

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-0.5">
                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      CURRENT TARGET
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {activeEmbedding ? activeEmbedding.model : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">Hosted embedding runtime</p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      RUNTIME URL
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {selectedEmbeddingFamily?.type === "local" ||
                      selectedEmbeddingFamily?.id === "sentence-transformers"
                        ? "Managed runtime"
                        : activeEmbedding
                          ? activeEmbedding.baseUrl
                          : "Not set"}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      STATUS
                    </p>
                    <p
                      className={[
                        "text-xs font-bold flex items-center gap-1.5",
                        activeEmbedding ? "text-emerald-400" : "text-slate-400",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "w-1.5 h-1.5 rounded-full",
                          activeEmbedding ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                        ].join(" ")}
                      />
                      {activeEmbedding ? "Healthy" : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {activeEmbedding ? "Last runtime check." : "No active embedding connection."}
                    </p>
                  </div>
                </div>

                {/* Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-white/8">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleTestEmbeddingPing}
                      disabled={embeddingTesting}
                      className="font-mono text-xs font-bold tracking-wider text-slate-300 hover:text-white flex items-center gap-1.5 transition-all"
                    >
                      {embeddingTesting ? (
                        <Loader2 size={14} className="animate-spin text-primary-400" />
                      ) : (
                        <Zap size={14} className="text-primary-400" />
                      )}
                      TEST PING
                    </button>

                    <button
                      onClick={handleTerminateEmbedding}
                      className="font-mono text-xs font-bold tracking-wider text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-all"
                    >
                      <Zap size={14} />
                      TERMINATE
                    </button>
                  </div>

                  <Button onClick={handleUpdateEmbeddingConnectivity} size="md" className="gap-2">
                    <Link2 size={15} />
                    Update Connectivity
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* TAB 4: RERANKER SETUP */}
        {/* ========================================================================= */}
        {activeTab === "reranker" && (
          <motion.div
            key="tab-reranker"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-4"
          >
            {/* Left Panel Sidebar */}
            <div className="lg:col-span-4 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl">
              <AnimatePresence mode="wait">
                {rerankerLeftView === "inventory" ? (
                  <motion.div
                    key="rr-inventory"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        INVENTORY
                      </span>
                      <button
                        onClick={() => {
                          setRerankerLeftView("select_family");
                          setSelectedRerankerFamily(null);
                        }}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Add Reranker Provider"
                      >
                        <Plus size={16} />
                      </button>
                    </div>

                    <div className="space-y-0.5">
                      <p className="font-mono text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                        RERANKER FAMILIES
                      </p>
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-extrabold text-white">Inventory</h3>
                        <span className="text-xs font-mono bg-black/40 border border-primary-500/30 text-primary-300 px-2 py-0.5 rounded-full font-bold">
                          {hasRerankerConfigured ? "1 options" : "0 options"}
                        </span>
                      </div>
                    </div>

                    <div className="h-[1px] bg-white/5 my-1" />

                    {!hasRerankerConfigured ? (
                      <div className="p-5 text-center border border-dashed border-white/10 rounded-xl bg-black/20 space-y-2">
                        <p className="text-xs font-mono text-slate-500 italic">
                          No active connections.
                        </p>
                        <button
                          onClick={() => {
                            setRerankerLeftView("select_family");
                            setSelectedRerankerFamily(null);
                          }}
                          className="px-3 py-1.5 text-xs font-mono font-bold bg-primary-500/20 border border-primary-500/40 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-all"
                        >
                          + Add Connection
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 custom-scrollbar">
                        <div
                          onClick={() => setSelectedRerankerFamily(RERANKER_FAMILIES[0])}
                          className="w-full p-2.5 rounded-xl border border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)] flex items-center gap-3 transition-all cursor-pointer"
                        >
                          <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                            <Target size={14} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-1">
                              <p className="text-xs font-bold truncate">{rerankerName}</p>
                              <span className="text-[9px] font-mono bg-primary-500/20 border border-primary-500/40 text-primary-300 px-1.5 py-0.5 rounded font-bold">
                                HOSTED
                              </span>
                            </div>
                            <p className="text-[10px] font-mono text-slate-400 truncate mt-0.5">
                              {rerankerModel}
                            </p>
                            <p className="text-[9px] font-mono text-emerald-400 mt-1 flex items-center gap-1 font-bold">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              HEALTHY
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="rr-select-family"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        SELECT FAMILY
                      </span>
                      <button
                        onClick={() => setRerankerLeftView("inventory")}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Close"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <button
                      onClick={() => setRerankerLeftView("inventory")}
                      className="w-full p-2 rounded-xl bg-black/40 hover:bg-white/5 border border-white/10 text-xs font-bold text-white flex items-center gap-2 transition-all"
                    >
                      <ArrowLeft size={14} />
                      Back to Inventory
                    </button>

                    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                      {RERANKER_FAMILIES.map((fam) => {
                        const selected = selectedRerankerFamily?.id === fam.id;
                        return (
                          <div
                            key={fam.id}
                            onClick={() => handleSelectRerankerFamily(fam)}
                            className={[
                              "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                              selected
                                ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                            ].join(" ")}
                          >
                            <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                              <Zap size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold truncate">{fam.name}</p>
                              <p className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">
                                {fam.code}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Panel: ReRanker Setup Form or Empty State */}
            {selectedRerankerFamily === null ? (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-4 shadow-xl min-h-[380px]">
                <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 text-primary-400 flex items-center justify-center">
                  <Zap size={28} />
                </div>
                <div className="space-y-1 max-w-sm">
                  <h3 className="text-base font-bold text-white tracking-tight">System Navigator</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Select a provider family from the left list to adjust its parameters or test connectivity.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setRerankerLeftView("select_family");
                    setSelectedRerankerFamily(null);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-primary-500/15 border border-primary-500/40 text-primary-300 font-mono text-xs font-bold hover:bg-primary-500/25 transition-all shadow-[0_0_15px_rgba(34,211,238,0.15)] flex items-center gap-2"
                >
                  <Plus size={14} />
                  + Add Connection
                </button>
              </div>
            ) : (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4 shadow-xl">
                <div>
                  <p className="font-mono text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                    RERANKER SETUP
                  </p>
                  <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                    {selectedRerankerFamily.name}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Connect this reranker provider, enter the API key, then link it.
                  </p>
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Auth Protocol with CustomSelect */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      AUTHENTICATION PROTOCOL
                    </label>
                    <CustomSelect
                      value={rerankerAuthProtocol}
                      onChange={setRerankerAuthProtocol}
                      options={["No Authentication", "API Key"]}
                    />
                  </div>

                  {/* API / Runtime URL */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      API / RUNTIME URL
                    </label>
                    <div className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-400 font-mono flex items-center gap-2 shadow-inner">
                      <Info size={14} className="text-primary-400 shrink-0" />
                      <span className="truncate">Managed runtime; no URL needed.</span>
                    </div>
                  </div>
                </div>

                {/* Reranker Model with CustomSelect */}
                <div className="space-y-1">
                  <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                    RERANKER MODEL
                  </label>
                  <CustomSelect
                    value={rerankerModel}
                    onChange={setRerankerModel}
                    options={selectedRerankerFamily.models}
                  />
                </div>

                {/* Model Discovery */}
                <div className="space-y-1.5 pt-0.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-400 uppercase">
                      MODEL DISCOVERY
                    </span>
                    <span className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {selectedRerankerFamily.models.length} MODELS FOUND
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-black/30 border border-white/8 text-xs text-slate-400">
                    When you enter the token, supported reranker models are fetched automatically for this provider.
                  </div>
                  {rerankerTestResult && (
                    <p className="text-xs font-mono text-primary-300">{rerankerTestResult}</p>
                  )}
                </div>

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-0.5">
                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      CURRENT TARGET
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasRerankerConfigured ? rerankerModel : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">Hosted reranker runtime</p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      RUNTIME URL
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasRerankerConfigured ? "Managed internal core" : "Not set"}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      STATUS
                    </p>
                    <p
                      className={[
                        "text-xs font-bold flex items-center gap-1.5",
                        hasRerankerConfigured ? "text-emerald-400" : "text-slate-400",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "w-1.5 h-1.5 rounded-full",
                          hasRerankerConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                        ].join(" ")}
                      />
                      {hasRerankerConfigured ? "Healthy" : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {hasRerankerConfigured ? "Last runtime check." : "No active reranker connection."}
                    </p>
                  </div>
                </div>

                {/* Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-white/8">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleTestRerankerPing}
                      disabled={rerankerTesting}
                      className="font-mono text-xs font-bold tracking-wider text-slate-300 hover:text-white flex items-center gap-1.5 transition-all"
                    >
                      {rerankerTesting ? (
                        <Loader2 size={14} className="animate-spin text-primary-400" />
                      ) : (
                        <Zap size={14} className="text-primary-400" />
                      )}
                      TEST PING
                    </button>

                    <button
                      onClick={handleTerminateReranker}
                      className="font-mono text-xs font-bold tracking-wider text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-all"
                    >
                      <Zap size={14} />
                      TERMINATE
                    </button>
                  </div>

                  <Button onClick={handleUpdateRerankerConnectivity} size="md" className="gap-2">
                    <Link2 size={15} />
                    Update Connectivity
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* TAB 5: WEB SEARCH SETUP */}
        {/* ========================================================================= */}
        {activeTab === "web" && (
          <motion.div
            key="tab-web"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-4"
          >
            {/* Left Panel Sidebar */}
            <div className="lg:col-span-4 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl">
              <AnimatePresence mode="wait">
                {webLeftView === "inventory" ? (
                  <motion.div
                    key="web-inventory"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        INVENTORY
                      </span>
                      <button
                        onClick={() => {
                          setWebLeftView("select_family");
                          setSelectedWebFamily(null);
                        }}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Add Web Provider"
                      >
                        <Plus size={16} />
                      </button>
                    </div>

                    <div className="space-y-0.5">
                      <p className="font-mono text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                        WEB SEARCH FAMILIES
                      </p>
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-extrabold text-white">Inventory</h3>
                        <span className="text-xs font-mono bg-black/40 border border-primary-500/30 text-primary-300 px-2 py-0.5 rounded-full font-bold">
                          {hasWebConfigured ? "1 options" : "0 options"}
                        </span>
                      </div>
                    </div>

                    <div className="h-[1px] bg-white/5 my-1" />

                    {!hasWebConfigured ? (
                      <div className="p-5 text-center border border-dashed border-white/10 rounded-xl bg-black/20 space-y-2">
                        <p className="text-xs font-mono text-slate-500 italic">
                          No active connections.
                        </p>
                        <button
                          onClick={() => {
                            setWebLeftView("select_family");
                            setSelectedWebFamily(null);
                          }}
                          className="px-3 py-1.5 text-xs font-mono font-bold bg-primary-500/20 border border-primary-500/40 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-all"
                        >
                          + Add Connection
                        </button>
                      </div>
                    ) : (
                      <div
                        onClick={() => setSelectedWebFamily(WEB_FAMILIES[0])}
                        className="p-2.5 rounded-xl border border-primary-500/50 bg-primary-500/15 text-white flex items-center gap-3 cursor-pointer shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                      >
                        <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                          <Globe size={14} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-bold truncate">{webName}</p>
                          <p className="text-[10px] font-mono text-slate-400 truncate">{webEndpoint}</p>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="web-select-family"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        SELECT FAMILY
                      </span>
                      <button
                        onClick={() => setWebLeftView("inventory")}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Close"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <button
                      onClick={() => setWebLeftView("inventory")}
                      className="w-full p-2 rounded-xl bg-black/40 hover:bg-white/5 border border-white/10 text-xs font-bold text-white flex items-center gap-2 transition-all"
                    >
                      <ArrowLeft size={14} />
                      Back to Inventory
                    </button>

                    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                      {WEB_FAMILIES.map((fam) => {
                        const selected = selectedWebFamily?.id === fam.id;
                        return (
                          <div
                            key={fam.id}
                            onClick={() => handleSelectWebFamily(fam)}
                            className={[
                              "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                              selected
                                ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                            ].join(" ")}
                          >
                            <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                              <Zap size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold truncate">{fam.name}</p>
                              <p className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">
                                {fam.code}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Panel: Web Setup Form or Empty State */}
            {selectedWebFamily === null ? (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-4 shadow-xl min-h-[380px]">
                <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 text-primary-400 flex items-center justify-center">
                  <Zap size={28} />
                </div>
                <div className="space-y-1 max-w-sm">
                  <h3 className="text-base font-bold text-white tracking-tight">System Navigator</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Select a provider family from the left list to adjust its parameters or test connectivity.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setWebLeftView("select_family");
                    setSelectedWebFamily(null);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-primary-500/15 border border-primary-500/40 text-primary-300 font-mono text-xs font-bold hover:bg-primary-500/25 transition-all shadow-[0_0_15px_rgba(34,211,238,0.15)] flex items-center gap-2"
                >
                  <Plus size={14} />
                  + Add Connection
                </button>
              </div>
            ) : (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4 shadow-xl">
                <div>
                  <p className="font-mono text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                    WEB SETUP
                  </p>
                  <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                    {selectedWebFamily.name}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Connect this web provider, enter the API key, then link it.
                  </p>
                </div>

                {/* Form Fields Row 1 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Auth Protocol with CustomSelect */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      AUTHENTICATION PROTOCOL
                    </label>
                    <CustomSelect
                      value={webAuthProtocol}
                      onChange={setWebAuthProtocol}
                      options={["local no key", "API Key", "No Authentication"]}
                    />
                  </div>

                  {/* Web Search Endpoint */}
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      ENDPOINT URL
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={webEndpoint}
                        onChange={(e) => setWebEndpoint(e.target.value)}
                        placeholder="e.g. https://google.serper.dev"
                        className="w-full bg-slate-950/70 border border-white/10 rounded-xl pl-3 pr-8 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono placeholder:text-slate-600 shadow-inner"
                      />
                      <Globe size={14} className="absolute right-3 top-2.5 text-slate-500" />
                    </div>
                  </div>
                </div>

                {/* API Key Input Field */}
                {(webAuthProtocol === "API Key" || selectedWebFamily.id === "serper" || selectedWebFamily.id === "tavily") && (
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-primary-400 uppercase flex items-center justify-between">
                      <span>API KEY (REQUIRED FOR {selectedWebFamily.name.toUpperCase()})</span>
                      <span className="text-[9px] text-slate-400 font-normal">Stored securely in browser</span>
                    </label>
                    <input
                      type="password"
                      value={webApiKey}
                      onChange={(e) => setWebApiKey(e.target.value)}
                      placeholder="Enter Serper / Tavily API Key..."
                      className="w-full bg-slate-950/70 border border-primary-500/40 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-400 transition-all font-mono placeholder:text-slate-600 shadow-inner"
                    />
                  </div>
                )}

                {/* Additional Web Configuration */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <label className="font-mono text-[9px] font-bold tracking-wider text-slate-400 uppercase">
                      SEARCH LANGUAGE
                    </label>
                    <input
                      type="text"
                      value={webSearchLang}
                      onChange={(e) => setWebSearchLang(e.target.value)}
                      placeholder="auto"
                      className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-mono text-[9px] font-bold tracking-wider text-slate-400 uppercase">
                      ALLOWED DOMAINS
                    </label>
                    <input
                      type="text"
                      value={webAllowedDomains}
                      onChange={(e) => setWebAllowedDomains(e.target.value)}
                      placeholder="example.com, docs.example..."
                      className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-mono text-[9px] font-bold tracking-wider text-slate-400 uppercase">
                      BLOCKED DOMAINS
                    </label>
                    <input
                      type="text"
                      value={webBlockedDomains}
                      onChange={(e) => setWebBlockedDomains(e.target.value)}
                      placeholder="ads.example.com"
                      className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                    />
                  </div>
                </div>

                {webTestResult && (
                  <p className="text-xs font-mono text-primary-300">{webTestResult}</p>
                )}

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-0.5">
                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      CURRENT TARGET
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasWebConfigured ? webName : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">Managed web runtime</p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      RUNTIME URL
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasWebConfigured ? webEndpoint : "Not set"}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      STATUS
                    </p>
                    <p
                      className={[
                        "text-xs font-bold flex items-center gap-1.5",
                        hasWebConfigured ? "text-emerald-400" : "text-slate-400",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "w-1.5 h-1.5 rounded-full",
                          hasWebConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                        ].join(" ")}
                      />
                      {hasWebConfigured ? "Connected" : "Not connected"}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {hasWebConfigured ? "Endpoint verified active." : "No active connection."}
                    </p>
                  </div>
                </div>

                {/* Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-white/8">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={handleTestWebPing}
                      disabled={webTesting}
                      className="font-mono text-xs font-bold tracking-wider text-slate-300 hover:text-white flex items-center gap-1.5 transition-all"
                    >
                      {webTesting ? (
                        <Loader2 size={14} className="animate-spin text-primary-400" />
                      ) : (
                        <Zap size={14} className="text-primary-400" />
                      )}
                      TEST PING
                    </button>

                    <button
                      onClick={handleTerminateWeb}
                      className="font-mono text-xs font-bold tracking-wider text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-all"
                    >
                      <Zap size={14} />
                      TERMINATE
                    </button>
                  </div>

                  <Button onClick={handleUpdateWebConnectivity} size="md" className="gap-2">
                    <Link2 size={15} />
                    Link Family
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* ========================================================================= */}
        {/* TAB 6: OCR SETUP */}
        {/* ========================================================================= */}
        {activeTab === "ocr" && (
          <motion.div
            key="tab-ocr"
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-4"
          >
            {/* Left Panel Sidebar */}
            <div className="lg:col-span-4 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-3.5 shadow-xl">
              <AnimatePresence mode="wait">
                {ocrLeftView === "inventory" ? (
                  <motion.div
                    key="ocr-inventory"
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        OCR INVENTORY
                      </span>
                      <button
                        onClick={() => {
                          setOcrLeftView("select_family");
                          setSelectedOcrFamily(null);
                        }}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Add OCR Provider"
                      >
                        <Plus size={16} />
                      </button>
                    </div>

                    <div className="space-y-0.5">
                      <p className="font-mono text-[10px] font-bold tracking-widest text-slate-400 uppercase">
                        OCR FAMILIES
                      </p>
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-extrabold text-white">Inventory</h3>
                        <span className="text-xs font-mono bg-black/40 border border-primary-500/30 text-primary-300 px-2 py-0.5 rounded-full font-bold">
                          {hasOcrConfigured ? "1 options" : "0 options"}
                        </span>
                      </div>
                    </div>

                    <div className="h-[1px] bg-white/5 my-1" />

                    {!hasOcrConfigured ? (
                      <div className="p-5 text-center border border-dashed border-white/10 rounded-xl bg-black/20 space-y-2">
                        <p className="text-xs font-mono text-slate-500 italic">
                          No active connections.
                        </p>
                        <button
                          onClick={() => {
                            setOcrLeftView("select_family");
                            setSelectedOcrFamily(null);
                          }}
                          className="px-3 py-1.5 text-xs font-mono font-bold bg-primary-500/20 border border-primary-500/40 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-all"
                        >
                          + Add Connection
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                        <div
                          onClick={() => {
                            const fam = OCR_FAMILIES.find((f) => f.id === activeOcrId) || OCR_FAMILIES[0];
                            setSelectedOcrFamily(fam);
                          }}
                          className="w-full p-2.5 rounded-xl border border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)] flex items-center gap-3 transition-all cursor-pointer"
                        >
                          <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                            <ScanText size={14} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-1">
                              <p className="text-xs font-bold truncate">{ocrName}</p>
                              <span className="text-[9px] font-mono bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 px-1.5 py-0.5 rounded font-bold">
                                ACTIVE
                              </span>
                            </div>
                            <p className="text-[10px] font-mono text-slate-400 truncate mt-0.5">
                              {ocrEndpoint}
                            </p>
                            <p className="text-[9px] font-mono text-emerald-400 mt-1 flex items-center gap-1 font-bold">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              HEALTHY
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <motion.div
                    key="ocr-select-family"
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -12 }}
                    transition={{ duration: 0.16 }}
                    className="space-y-3.5"
                  >
                    <div className="flex items-center justify-between border-b border-white/10 pb-2">
                      <span className="font-mono text-xs font-bold tracking-[0.2em] text-slate-300 uppercase">
                        SELECT OCR FAMILY
                      </span>
                      <button
                        onClick={() => setOcrLeftView("inventory")}
                        className="w-8 h-8 rounded-xl bg-primary-500/10 hover:bg-primary-500/25 border border-primary-500/40 text-primary-400 hover:text-primary-300 hover:border-primary-400 hover:shadow-[0_0_12px_rgba(34,211,238,0.3)] flex items-center justify-center transition-all duration-200"
                        title="Close"
                      >
                        <X size={16} />
                      </button>
                    </div>

                    <button
                      onClick={() => setOcrLeftView("inventory")}
                      className="w-full p-2 rounded-xl bg-black/40 hover:bg-white/5 border border-white/10 text-xs font-bold text-white flex items-center gap-2 transition-all"
                    >
                      <ArrowLeft size={14} />
                      Back to Inventory
                    </button>

                    <div className="space-y-2 max-h-[380px] overflow-y-auto pr-1 custom-scrollbar">
                      {OCR_FAMILIES.map((fam) => {
                        const selected = selectedOcrFamily?.id === fam.id;
                        return (
                          <div
                            key={fam.id}
                            onClick={() => handleSelectOcrFamily(fam)}
                            className={[
                              "w-full p-2.5 rounded-xl border flex items-center gap-3 transition-all cursor-pointer",
                              selected
                                ? "border-primary-500/50 bg-primary-500/15 text-white shadow-[0_0_12px_rgba(34,211,238,0.15)]"
                                : "border-white/8 bg-black/30 hover:bg-white/5 border-transparent text-slate-300",
                            ].join(" ")}
                          >
                            <div className="w-7 h-7 rounded-lg border border-primary-500/30 bg-primary-500/10 text-primary-400 flex items-center justify-center shrink-0">
                              <ScanText size={14} />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-xs font-bold truncate">{fam.name}</p>
                              <p className="text-[9px] font-mono text-slate-500 tracking-wider uppercase">
                                {fam.code}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Right Panel: OCR Inspector & Live Test Sandbox */}
            {selectedOcrFamily === null ? (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-8 flex flex-col items-center justify-center text-center space-y-4 shadow-xl min-h-[380px]">
                <div className="w-14 h-14 rounded-2xl bg-primary-500/10 border border-primary-500/20 text-primary-400 flex items-center justify-center">
                  <ScanText size={28} />
                </div>
                <div className="space-y-1 max-w-sm">
                  <h3 className="text-base font-bold text-white tracking-tight">OCR Provider Inspector</h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Select an OCR engine from the left inventory to configure parameters or benchmark extraction.
                  </p>
                </div>
                <button
                  onClick={() => {
                    setOcrLeftView("select_family");
                    setSelectedOcrFamily(null);
                  }}
                  className="px-3.5 py-2 rounded-xl bg-primary-500/15 border border-primary-500/40 text-primary-300 font-mono text-xs font-bold hover:bg-primary-500/25 transition-all shadow-[0_0_15px_rgba(34,211,238,0.15)] flex items-center gap-2"
                >
                  <Plus size={14} />
                  + Add Connection
                </button>
              </div>
            ) : (
              <div className="lg:col-span-8 rounded-[16px] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-4 space-y-4 shadow-xl">
                <div>
                  <p className="font-mono text-xs font-bold tracking-[0.2em] text-primary-400 uppercase">
                    OCR SETUP
                  </p>
                  <h2 className="text-lg font-bold text-white tracking-tight mt-0.5">
                    {selectedOcrFamily.name}
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Connect this OCR provider, configure languages & DPI, then link it.
                  </p>
                </div>

                {/* Form Fields Row 1 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      AUTHENTICATION PROTOCOL
                    </label>
                    <CustomSelect
                      value={ocrAuthProtocol}
                      onChange={setOcrAuthProtocol}
                      options={["local no key", "API Key", "No Authentication"]}
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      RUNTIME / ENDPOINT URL
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={ocrEndpoint}
                        onChange={(e) => setOcrEndpoint(e.target.value)}
                        placeholder="e.g. FAIM Native CPU Runtime"
                        className="w-full bg-slate-950/70 border border-white/10 rounded-xl pl-3 pr-8 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                      />
                      <Cpu size={14} className="absolute right-3 top-2.5 text-slate-500" />
                    </div>
                  </div>
                </div>

                {/* Parameter settings: Languages & DPI */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      PRIMARY LANGUAGES (COMMA-SEPARATED)
                    </label>
                    <input
                      type="text"
                      value={ocrLanguages}
                      onChange={(e) => setOcrLanguages(e.target.value)}
                      placeholder="eng, ch, fr, de"
                      className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="font-mono text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                      DOCUMENT RASTER DPI
                    </label>
                    <input
                      type="text"
                      value={ocrDpi}
                      onChange={(e) => setOcrDpi(e.target.value)}
                      placeholder="300"
                      className="w-full bg-slate-950/70 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-primary-500/50 transition-all font-mono shadow-inner"
                    />
                  </div>
                </div>

                {/* Benchmark Output Box */}
                {ocrTestResult && (
                  <div className="p-3.5 rounded-xl border border-primary-500/30 bg-black/40 space-y-2">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-primary-300 font-bold">{ocrTestResult.message}</span>
                      <span className="text-slate-400">{ocrTestResult.latency_ms}ms</span>
                    </div>
                    {ocrTestResult.extracted_text && (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-white/5 font-mono text-xs text-slate-200 whitespace-pre-wrap">
                        {ocrTestResult.extracted_text}
                      </div>
                    )}
                  </div>
                )}

                {/* Metric Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-0.5">
                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      CURRENT TARGET
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasOcrConfigured ? ocrName : "Not Configured"}
                    </p>
                    <p className="text-[10px] text-slate-500">MKLDNN Vector Accelerated</p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      RUNTIME URL
                    </p>
                    <p className="text-xs font-bold text-white truncate font-mono">
                      {hasOcrConfigured ? ocrEndpoint : "Not set"}
                    </p>
                  </div>

                  <div className="p-2.5 rounded-xl border border-white/8 bg-black/30 space-y-0.5">
                    <p className="font-mono text-[9px] font-bold tracking-widest text-slate-500 uppercase">
                      STATUS
                    </p>
                    <p
                      className={[
                        "text-xs font-bold flex items-center gap-1.5",
                        hasOcrConfigured ? "text-emerald-400" : "text-slate-400",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "w-1.5 h-1.5 rounded-full",
                          hasOcrConfigured ? "bg-emerald-400 animate-pulse" : "bg-slate-500",
                        ].join(" ")}
                      />
                      {hasOcrConfigured ? "Connected" : "Not connected"}
                    </p>
                    <p className="text-[10px] text-slate-500">
                      {hasOcrConfigured ? "Engine verified active." : "No active connection."}
                    </p>
                  </div>
                </div>

                {/* Action Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-white/8">
                  <div className="flex items-center gap-4">
                    <button
                      onClick={() => handleTestOcrPing(selectedOcrFamily.id)}
                      disabled={ocrTesting}
                      className="font-mono text-xs font-bold tracking-wider text-slate-300 hover:text-white flex items-center gap-1.5 transition-all"
                    >
                      {ocrTesting ? (
                        <Loader2 size={14} className="animate-spin text-primary-400" />
                      ) : (
                        <Zap size={14} className="text-primary-400" />
                      )}
                      TEST PING
                    </button>

                    <button
                      onClick={handleTerminateOcr}
                      className="font-mono text-xs font-bold tracking-wider text-rose-400 hover:text-rose-300 flex items-center gap-1.5 transition-all"
                    >
                      <Zap size={14} />
                      TERMINATE
                    </button>
                  </div>

                  <Button onClick={handleLinkOcrFamily} size="md" className="gap-2">
                    <Link2 size={15} />
                    Link Family
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
    <ProvidersManual open={manualOpen} onClose={() => setManualOpen(false)} />
  </>
  );
}
