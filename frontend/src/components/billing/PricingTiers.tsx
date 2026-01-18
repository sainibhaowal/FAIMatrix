"use client";

import React from "react";
import { Check, ArrowRight, Star, Zap, Crown, Loader2 } from "lucide-react";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tokens: "1M",
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
    features: ["10M Token Storage", "2GB Storage", "Unlimited API Keys", "Priority Support", "Advanced Search", "Export Data"],
    color: "amber",
    icon: Crown,
    popular: false,
  },
];

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

interface PricingTiersProps {
  currentPlan: string;
  upgrading: string | null;
  onUpgrade: (planId: string) => void;
}

export function PricingTiers({ currentPlan, upgrading, onUpgrade }: PricingTiersProps) {
  return (
    <div className="grid md:grid-cols-3 gap-6">
      {PLANS.map((plan) => {
        const isCurrent = currentPlan === plan.id;
        const isUpgrade =
          PLANS.findIndex((p) => p.id === currentPlan) <
          PLANS.findIndex((p) => p.id === plan.id);
        const Icon = plan.icon;
        const colors = COLOR_CLASSES[plan.color as keyof typeof COLOR_CLASSES];

        return (
          <div
            key={plan.id}
            className={[
              "relative p-6 rounded-[2rem] border transition-all duration-500 flex flex-col h-full overflow-hidden group",
              isCurrent
                ? "bg-slate-900 border-white/20 shadow-2xl shadow-cyan-500/10"
                : plan.popular
                  ? "bg-gradient-to-br from-purple-950/30 to-slate-900 border-purple-500/30 hover:border-purple-400/50"
                  : "bg-white/[0.02] border-white/5 hover:border-white/10"
            ].join(" ")}
          >
            {/* Glossy background effect */}
            <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2 w-32 h-32 bg-white/5 blur-3xl rounded-full pointer-events-none group-hover:bg-white/10 transition-colors" />
            
            {(plan.popular || isCurrent) && (
              <div className={[
                "absolute -top-1 left-1/2 -translate-x-1/2 px-4 py-1.5 text-[10px] font-black tracking-widest rounded-b-xl shadow-lg",
                isCurrent ? "bg-cyan-500 text-white" : "bg-purple-500 text-white"
              ].join(" ")}>
                {isCurrent ? "ACTIVE" : "POPULAR"}
              </div>
            )}

            <div className="flex items-center gap-4 mb-6">
              <div className={[
                "h-12 w-12 rounded-2xl flex items-center justify-center p-0.5",
                plan.popular ? "bg-gradient-to-br from-purple-500 to-pink-500" : "bg-white/10"
              ].join(" ")}>
                <div className="h-full w-full rounded-[14px] bg-slate-900 flex items-center justify-center">
                  <Icon size={24} className={colors.text} />
                </div>
              </div>
              <div className="font-black text-xl text-white tracking-tight">{plan.name}</div>
            </div>

            <div className="mb-6">
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-black text-white">$</span>
                <span className="text-5xl font-black text-white">{plan.price}</span>
                <span className="text-slate-500 font-bold ml-1">/mo</span>
              </div>
              <div className="text-slate-400 text-xs mt-1 font-medium italic">Neural efficiency at scale</div>
            </div>

            <div className="flex-grow space-y-4 mb-8">
              <div className="flex items-center gap-3">
                 <div className="h-0.5 flex-grow bg-white/5" />
                 <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Key Features</span>
                 <div className="h-0.5 flex-grow bg-white/5" />
              </div>
              <ul className="space-y-3">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className={[
                      "mt-0.5 h-4 w-4 rounded-full flex items-center justify-center flex-shrink-0",
                      isCurrent || plan.popular ? "bg-cyan-500/20" : "bg-white/5"
                    ].join(" ")}>
                      <Check size={10} className={colors.text} strokeWidth={3} />
                    </div>
                    <span className="text-xs text-slate-300 font-medium">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative z-10">
              {isCurrent ? (
                <div className="w-full py-4 px-6 rounded-2xl bg-white/5 border border-white/10 text-slate-400 text-xs font-bold text-center uppercase tracking-widest">
                  Current Deployment
                </div>
              ) : (
                <button
                  onClick={() => onUpgrade(plan.id)}
                  disabled={upgrading !== null}
                  className={[
                    "w-full py-4 px-6 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2 group/btn relative overflow-hidden",
                    plan.popular
                      ? "bg-white text-black hover:bg-cyan-50 scale-[1.02] shadow-xl shadow-purple-500/10"
                      : "bg-slate-800 text-white hover:bg-slate-700 border border-white/5"
                  ].join(" ")}
                >
                  {upgrading === plan.id ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <>
                      {isUpgrade ? "UPGRADE" : "SWITCH PLAN"}
                      <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
