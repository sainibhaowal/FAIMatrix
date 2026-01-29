"use client";

/**
 * FAIMATRIX - Email Verification Page
 *
 * Handles email verification token from URL.
 */

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, CheckCircle, XCircle, Mail } from "lucide-react";

function VerifyContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"verifying" | "success" | "error">(
    "verifying",
  );
  const [message, setMessage] = useState("Verifying your email...");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided.");
      return;
    }

    const verifyEmail = async () => {
      try {
        const res = await fetch("/api/v1/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        const data = await res.json();

        if (res.ok && data.success) {
          setStatus("success");
          setMessage(data.message || "Email verified successfully!");
          // Redirect to login after 3 seconds
          setTimeout(() => router.push("/auth/login"), 3000);
        } else {
          setStatus("error");
          setMessage(
            data.detail || "Verification failed. The link may be expired.",
          );
        }
      } catch (err) {
        setStatus("error");
        setMessage("Network error. Please try again.");
      }
    };

    verifyEmail();
  }, [token, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 px-4">
      {/* Background effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 to-blue-500 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-lg">F</span>
            </div>
            <span className="text-xl font-bold text-white">Faimatrix</span>
          </Link>
        </div>

        {/* Status Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl text-center">
          {status === "verifying" && (
            <>
              <div className="w-16 h-16 mx-auto mb-4 bg-cyan-500/20 rounded-full flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Verifying Email
              </h1>
              <p className="text-slate-400">{message}</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="w-16 h-16 mx-auto mb-4 bg-emerald-500/20 rounded-full flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-emerald-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Email Verified!
              </h1>
              <p className="text-slate-400 mb-6">{message}</p>
              <p className="text-slate-500 text-sm">Redirecting to login...</p>
            </>
          )}

          {status === "error" && (
            <>
              <div className="w-16 h-16 mx-auto mb-4 bg-red-500/20 rounded-full flex items-center justify-center">
                <XCircle className="w-8 h-8 text-red-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Verification Failed
              </h1>
              <p className="text-slate-400 mb-6">{message}</p>
              <Link
                href="/auth/login"
                className="inline-block px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-xl text-white font-semibold hover:shadow-lg hover:shadow-cyan-500/25 transition-all"
              >
                Go to Login
              </Link>
            </>
          )}
        </div>

        {/* Security note */}
        <p className="text-center text-slate-500 text-xs mt-6">
          🔒 Secured email verification
        </p>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
