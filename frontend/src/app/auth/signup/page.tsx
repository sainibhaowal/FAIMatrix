"use client";

import { useState, Suspense } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Loader2,
  Mail,
  Lock,
  User,
  ArrowRight,
  ChevronLeft,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Logo from "@/components/brand/Logo";

function SignupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Client-side validation
    if (name.trim().length < 2) {
      setError("Name must be at least 2 characters");
      return;
    }
    if (!validateEmail(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/otp/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, mode: "signup" }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setStep("code");
      } else {
        setError(data.detail || "Failed to send code");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await signIn("credentials", {
        email,
        code,
        full_name: name, // Pass name to verify endpoint
        redirect: false,
        callbackUrl,
      });

      if (result?.error) {
        setError("Invalid verification code");
      } else if (result?.ok) {
        router.push(callbackUrl);
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020617] relative overflow-hidden">
      {/* Dynamic Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 rounded-full blur-[120px] animate-pulse" />
        <div
          className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-cyan-600/10 rounded-full blur-[120px] animate-pulse"
          style={{ animationDelay: "2s" }}
        />
      </div>

      <div className="relative z-10 w-full max-w-md px-6 py-12">
        {/* Logo Section */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-10"
        >
          <div className="flex justify-center mb-4">
            <Logo size="large" px={100} />
          </div>
          <h2 className="text-white text-3xl font-bold tracking-tight">
            FAIM<span className="text-cyan-400">ATRIX</span>
          </h2>
          <p className="text-slate-500 text-sm mt-1 tracking-widest uppercase">
            Fractal AI Memory
          </p>
        </motion.div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="bg-slate-900/50 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 shadow-2xl shadow-cyan-500/5"
        >
          <AnimatePresence mode="wait">
            {step === "email" ? (
              <motion.div
                key="signup-email"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="mb-8">
                  <h1 className="text-2xl font-bold text-white mb-2">
                    Create Account
                  </h1>
                  <p className="text-slate-400 text-sm">
                    Join the next generation of AI management.
                  </p>
                </div>

                <form onSubmit={handleRequestOtp} className="space-y-6">
                  {/* Name Field */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 ml-1">
                      Full Name
                    </label>
                    <div className="relative group">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl opacity-0 group-focus-within:opacity-20 transition duration-300" />
                      <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="John Doe"
                        required
                        className="relative w-full pl-12 pr-4 py-4 bg-slate-800/40 border border-white/5 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-all text-sm"
                      />
                    </div>
                  </div>

                  {/* Email Field */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 ml-1">
                      Email Address
                    </label>
                    <div className="relative group">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl opacity-0 group-focus-within:opacity-20 transition duration-300" />
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        required
                        className="relative w-full pl-12 pr-4 py-4 bg-slate-800/40 border border-white/5 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-all text-sm"
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 p-3 rounded-lg flex items-center gap-2"
                    >
                      <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                      {error}
                    </motion.div>
                  )}

                  <button
                    type="submit"
                    disabled={loading || !email}
                    className="w-full group relative py-4 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl text-white font-bold text-sm tracking-wide overflow-hidden shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="absolute inset-0 bg-white/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                    <span className="relative flex items-center justify-center gap-2">
                      {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <>
                          Join Now
                          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </span>
                  </button>
                </form>

                <div className="mt-8 pt-6 border-t border-white/5 text-center">
                  <p className="text-slate-500 text-sm">
                    Already have an account?{" "}
                    <Link
                      href="/auth/login"
                      className="text-cyan-400 font-semibold hover:text-cyan-300 transition-colors"
                    >
                      Sign In
                    </Link>
                  </p>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="signup-code"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="mb-8">
                  <button
                    onClick={() => setStep("email")}
                    className="flex items-center gap-1 text-slate-500 hover:text-white transition-colors text-xs mb-4 group"
                  >
                    <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                    Back
                  </button>
                  <h1 className="text-2xl font-bold text-white mb-2">
                    Verify Email
                  </h1>
                  <p className="text-slate-400 text-sm">
                    Verification code sent to{" "}
                    <span className="text-cyan-400 font-medium">{email}</span>
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 ml-1">
                      Code
                    </label>
                    <div className="relative group">
                      <div className="absolute -inset-0.5 bg-gradient-to-r from-cyan-400 to-purple-500 rounded-xl opacity-0 group-focus-within:opacity-20 transition duration-300" />
                      <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-cyan-400 transition-colors" />
                      <input
                        type="text"
                        value={code}
                        onChange={(e) => setCode(e.target.value)}
                        placeholder="000 000"
                        required
                        maxLength={6}
                        className="relative w-full pl-12 pr-4 py-4 bg-slate-800/40 border border-white/5 rounded-xl text-white placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 transition-all text-center text-lg tracking-[0.5em] font-mono"
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 p-3 rounded-lg"
                    >
                      {error}
                    </motion.div>
                  )}

                  <button
                    type="submit"
                    disabled={loading || code.length < 6}
                    className="w-full group relative py-4 bg-gradient-to-r from-cyan-500 to-blue-600 rounded-xl text-white font-bold text-sm tracking-wide overflow-hidden shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <span className="relative flex items-center justify-center gap-2">
                      {loading ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <>
                          Complete Registration
                          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </span>
                  </button>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#020617]">
          <Loader2 className="w-10 h-10 animate-spin text-cyan-500" />
        </div>
      }
    >
      <SignupContent />
    </Suspense>
  );
}
