"use client";

import React, { useEffect, useState } from "react";
import { CreditCard, Check, ArrowRight, Star, Zap, Crown, Sparkles } from "lucide-react";
import { getSession } from "next-auth/react";

interface UsageData {
    plan: string;
    tokens_used: number;
    tokens_max: number;
    storage_used_mb: number;
    storage_max_mb: number;
    price_monthly: number;
}

const PLANS = [
    {
        id: "free",
        name: "Free",
        price: 0,
        tokens: "1M",
        tokensNum: 1_000_000,
        storage: "100MB",
        storageMb: 100,
        features: ["1M Token Storage", "100MB Storage", "1 API Key", "Community Support"],
        color: "cyan",
        icon: Zap,
        popular: false,
    },
    {
        id: "starter",
        name: "Starter",
        price: 9,
        tokens: "3M",
        tokensNum: 3_000_000,
        storage: "500MB",
        storageMb: 500,
        features: ["3M Token Storage", "500MB Storage", "Unlimited API Keys", "Priority Support"],
        color: "purple",
        icon: Star,
        popular: true,
    },
    {
        id: "pro",
        name: "Pro",
        price: 15,
        tokens: "10M",
        tokensNum: 10_000_000,
        storage: "2GB",
        storageMb: 2000,
        features: ["10M Token Storage", "2GB Storage", "Unlimited API Keys", "Priority Support", "Advanced Search", "Export Data"],
        color: "amber",
        icon: Crown,
        popular: false,
    },
];

// Tailwind classes must be statically analyzable - can't use template strings
const COLOR_CLASSES = {
    cyan: {
        bg: "bg-cyan-500/20",
        bgActive: "bg-cyan-900/20",
        border: "border-cyan-500/50",
        ring: "ring-cyan-500/30",
        text: "text-cyan-400",
        token: "bg-cyan-500/10 border-cyan-500/20",
        btn: "bg-cyan-500 hover:bg-cyan-400",
    },
    purple: {
        bg: "bg-purple-500/20",
        bgActive: "bg-purple-900/20",
        border: "border-purple-500/50",
        ring: "ring-purple-500/30",
        text: "text-purple-400",
        token: "bg-purple-500/10 border-purple-500/20",
        btn: "bg-purple-500 hover:bg-purple-400",
    },
    amber: {
        bg: "bg-amber-500/20",
        bgActive: "bg-amber-900/20",
        border: "border-amber-500/50",
        ring: "ring-amber-500/30",
        text: "text-amber-400",
        token: "bg-amber-500/10 border-amber-500/20",
        btn: "bg-amber-500 hover:bg-amber-400",
    },
};

export default function BillingPage() {
    const [loading, setLoading] = useState(false);
    const [upgrading, setUpgrading] = useState<string | null>(null);
    const [projectId, setProjectId] = useState<string | null>(null);
    const [usage, setUsage] = useState<UsageData | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isLive, setIsLive] = useState(false); // SSE connection status

    // Initial load and SSE connection
    useEffect(() => {
        let eventSource: EventSource | null = null;

        async function init() {
            try {
                const session = await getSession();
                const token = (session as any)?.accessToken;

                // In dev mode, API works without token
                const headers: Record<string, string> = {};
                if (token) {
                    headers["Authorization"] = `Bearer ${token}`;
                }

                // Fetch user project to get plan
                const resOrgs = await fetch("/api/v1/orgs", { headers });
                const orgs = await resOrgs.json();

                if (!Array.isArray(orgs) || orgs.length === 0) {
                    setError("No organization found");
                    return;
                }

                const resProjs = await fetch(`/api/v1/projects?org_id=${orgs[0].id}`, { headers });
                const projs = await resProjs.json();

                if (!Array.isArray(projs) || projs.length === 0) {
                    setError("No project found");
                    return;
                }

                const project = projs[0];
                setProjectId(project.id);

                // Get token limit from PLANS array based on current plan
                const currentPlanDef = PLANS.find(p => p.id === project.plan) || PLANS[0];
                const planLimits = project.plan_limits || {};

                setUsage({
                    plan: project.plan || "free",
                    tokens_used: planLimits.tokens_used || 0,
                    tokens_max: planLimits.tokens_max || currentPlanDef.tokensNum,
                    storage_used_mb: 0,
                    storage_max_mb: planLimits.storage_mb_max || currentPlanDef.storageMb,
                    price_monthly: currentPlanDef.price,
                });

                // Connect to SSE for real-time usage updates
                connectSSE(project.id);

            } catch (e: any) {
                console.error(e);
                setError(e.message || "Failed to load billing info");
            }
        }

        function connectSSE(projId: string) {
            try {
                eventSource = new EventSource(`/api/v1/usage/stream?project_id=${projId}`);

                eventSource.onopen = () => {
                    console.log("[SSE] Connected to usage stream");
                    setIsLive(true);
                };

                eventSource.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        console.log("[SSE] Received:", message);

                        if (message.type === "initial" || message.type === "usage_update") {
                            const data = message.data;
                            if (data && typeof data.tokens_used === "number") {
                                setUsage(prev => prev ? {
                                    ...prev,
                                    tokens_used: data.tokens_used,
                                    tokens_max: data.tokens_max || prev.tokens_max,
                                } : prev);
                            }
                        }
                    } catch (e) {
                        console.warn("[SSE] Parse error:", e);
                    }
                };

                eventSource.onerror = (e) => {
                    console.warn("[SSE] Connection error:", e);
                    setIsLive(false);
                    // Reconnect after 5 seconds
                    setTimeout(() => {
                        if (projId) connectSSE(projId);
                    }, 5000);
                };

            } catch (e) {
                console.warn("[SSE] Failed to connect:", e);
            }
        }

        init();

        // Cleanup on unmount
        return () => {
            if (eventSource) {
                eventSource.close();
            }
        };
    }, []);

    const handleUpgrade = async (planId: string) => {
        if (!projectId || planId === "free") return;

        setUpgrading(planId);
        try {
            const session = await getSession();
            const token = (session as any)?.accessToken;

            const headers: Record<string, string> = {
                "Content-Type": "application/json"
            };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch("/api/billing/checkout", {
                method: "POST",
                headers,
                body: JSON.stringify({
                    project_id: projectId,
                    plan: planId,
                    success_url: window.location.origin + "/billing?success=true",
                    cancel_url: window.location.origin + "/billing?canceled=true"
                })
            });

            const data = await res.json();

            if (data.checkout_url) {
                window.location.href = data.checkout_url;
            } else if (data.detail) {
                alert(data.detail);
            } else {
                alert("Checkout failed: " + JSON.stringify(data));
            }
        } catch (err: any) {
            alert(err.message || "Error starting checkout");
        } finally {
            setUpgrading(null);
        }
    };

    const handleManage = async () => {
        if (!projectId) return;
        setLoading(true);
        try {
            const session = await getSession();
            const token = (session as any)?.accessToken;

            const headers: Record<string, string> = {
                "Content-Type": "application/json"
            };
            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const res = await fetch(`/api/billing/portal/${projectId}?return_url=${encodeURIComponent(window.location.href)}`, {
                method: "POST",
                headers,
            });

            const data = await res.json();
            if (data.portal_url) {
                window.location.href = data.portal_url;
            } else {
                alert("Portal failed: " + (data.detail || "Unknown error"));
            }
        } catch (err) {
            alert("Error opening billing portal");
        } finally {
            setLoading(false);
        }
    };

    const currentPlan = usage?.plan || "free";
    const tokensUsedPercent = usage ? Math.min(100, (usage.tokens_used / usage.tokens_max) * 100) : 0;

    return (
        <div className="space-y-6 max-w-4xl mx-auto">
            {/* Header */}
            <header className="text-center">
                <h1 className="text-xl font-bold text-slate-100 flex items-center justify-center gap-2">
                    <Sparkles className="text-purple-400" size={20} />
                    FAIM Lab Plans
                </h1>
                <p className="mt-1 text-sm text-slate-400">Simple, transparent pricing. Pay for what you need.</p>
            </header>

            {/* Current Usage Card */}
            {usage && (
                <div className="bg-slate-900/60 border border-slate-700/50 rounded-2xl p-5">
                    <div className="flex items-center justify-between mb-3">
                        <div>
                            <span className="text-xs text-slate-500 uppercase tracking-wider">Current Plan</span>
                            <div className="text-lg font-bold text-slate-100 capitalize">{currentPlan}</div>
                        </div>
                        {currentPlan !== "free" && (
                            <button
                                onClick={handleManage}
                                disabled={loading}
                                className="px-3 py-1.5 text-xs rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition-all"
                            >
                                {loading ? "Loading..." : "Manage Subscription"}
                            </button>
                        )}
                    </div>

                    {/* Token Usage Bar */}
                    <div className="space-y-1">
                        <div className="flex justify-between text-xs text-slate-400">
                            <span className="flex items-center gap-1.5">
                                Token Usage
                                {isLive && (
                                    <span className="flex items-center gap-1 text-green-400">
                                        <span className="relative flex h-2 w-2">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                                        </span>
                                        <span className="text-[10px]">LIVE</span>
                                    </span>
                                )}
                            </span>
                            <span>{(usage.tokens_used / 1_000_000).toFixed(2)}M / {(usage.tokens_max / 1_000_000).toFixed(0)}M</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className={`h-full transition-all duration-500 ${tokensUsedPercent > 90 ? 'bg-red-500' :
                                    tokensUsedPercent > 70 ? 'bg-yellow-500' :
                                        'bg-gradient-to-r from-cyan-500 to-purple-500'
                                    }`}
                                style={{ width: `${tokensUsedPercent}%` }}
                            />
                        </div>
                        {tokensUsedPercent > 80 && (
                            <p className="text-xs text-yellow-400 mt-1">
                                ⚠️ You're running low on tokens. Consider upgrading!
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="bg-red-900/30 border border-red-500/50 rounded-xl p-4 text-center text-red-300 text-sm">
                    {error}
                </div>
            )}

            {/* Plan Cards */}
            <div className="grid md:grid-cols-3 gap-4">
                {PLANS.map((plan) => {
                    const isCurrent = currentPlan === plan.id;
                    const isUpgrade = PLANS.findIndex(p => p.id === currentPlan) < PLANS.findIndex(p => p.id === plan.id);
                    const Icon = plan.icon;

                    const colors = COLOR_CLASSES[plan.color as keyof typeof COLOR_CLASSES];

                    return (
                        <div
                            key={plan.id}
                            className={`relative p-5 rounded-2xl border transition-all ${isCurrent
                                ? `${colors.bgActive} ${colors.border} ring-2 ${colors.ring}`
                                : plan.popular
                                    ? 'bg-gradient-to-b from-purple-900/30 to-slate-900/40 border-purple-500/40 hover:border-purple-400/60'
                                    : 'bg-slate-900/40 border-slate-700/50 hover:border-slate-600/50'
                                }`}
                        >
                            {/* Popular Badge */}
                            {plan.popular && !isCurrent && (
                                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-purple-500 text-white text-[10px] font-bold rounded-full">
                                    MOST POPULAR
                                </div>
                            )}

                            {/* Current Badge */}
                            {isCurrent && (
                                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-cyan-500 text-white text-[10px] font-bold rounded-full">
                                    CURRENT PLAN
                                </div>
                            )}

                            {/* Plan Icon & Name */}
                            <div className="flex items-center gap-2 mb-3">
                                <div className={`p-2 rounded-lg ${colors.bg}`}>
                                    <Icon size={16} className={colors.text} />
                                </div>
                                <span className="text-sm font-semibold text-slate-200">{plan.name}</span>
                            </div>

                            {/* Price */}
                            <div className="mb-4">
                                <span className="text-3xl font-bold text-white">
                                    {plan.price === 0 ? "Free" : `$${plan.price}`}
                                </span>
                                {plan.price > 0 && (
                                    <span className="text-sm text-slate-500">/month</span>
                                )}
                            </div>

                            {/* Token Highlight */}
                            <div className={`mb-4 py-2 px-3 rounded-lg ${colors.token}`}>
                                <span className={`text-lg font-bold ${colors.text}`}>{plan.tokens}</span>
                                <span className="text-sm text-slate-400 ml-1">tokens</span>
                            </div>

                            {/* Features */}
                            <ul className="space-y-2 mb-5">
                                {plan.features.map((feature, i) => (
                                    <li key={i} className="flex items-center gap-2 text-xs text-slate-300">
                                        <Check size={12} className={`${colors.text} flex-shrink-0`} />
                                        {feature}
                                    </li>
                                ))}
                            </ul>

                            {/* Action Button */}
                            {isCurrent ? (
                                <div className="py-2 px-4 rounded-lg bg-slate-700/50 text-slate-400 text-xs text-center">
                                    Current Plan
                                </div>
                            ) : isUpgrade ? (
                                <button
                                    onClick={() => handleUpgrade(plan.id)}
                                    disabled={upgrading !== null || !projectId}
                                    className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-all flex items-center justify-center gap-2 ${plan.popular
                                        ? 'bg-white text-black hover:bg-white/90'
                                        : `${colors.btn} text-white`
                                        }`}
                                >
                                    {upgrading === plan.id ? (
                                        "Processing..."
                                    ) : (
                                        <>
                                            Upgrade to {plan.name}
                                            <ArrowRight size={14} />
                                        </>
                                    )}
                                </button>
                            ) : (
                                <div className="py-2 px-4 rounded-lg bg-slate-700/30 text-slate-500 text-xs text-center">
                                    Downgrade via Portal
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* FAQ / Info */}
            <div className="text-center pt-4 border-t border-slate-800">
                <p className="text-xs text-slate-500">
                    All plans include your permanent Universe ID and API access.
                    <br />
                    Need more? Contact us at <a href="mailto:support@faim.dev" className="text-cyan-400 hover:underline">support@faim.dev</a>
                </p>
            </div>
        </div>
    );
}
