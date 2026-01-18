"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";

type ConsentPreferences = {
  essential: boolean; // Always true
  analytics: boolean;
  marketing: boolean;
};

const CONSENT_KEY = "faim_cookie_consent";
const CONSENT_PREFS_KEY = "faim_cookie_preferences";

export default function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [preferences, setPreferences] = useState<ConsentPreferences>({
    essential: true,
    analytics: true,
    marketing: false,
  });

  useEffect(() => {
    // Check if user has already consented
    const consent = localStorage.getItem(CONSENT_KEY);
    if (!consent) {
      // Delay showing the banner for better UX
      const timer = setTimeout(() => setIsVisible(true), 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const saveConsent = (prefs: ConsentPreferences) => {
    // Save consent timestamp and preferences
    const consentData = {
      timestamp: new Date().toISOString(),
      version: "1.0",
      preferences: prefs,
    };
    localStorage.setItem(CONSENT_KEY, JSON.stringify(consentData));
    localStorage.setItem(CONSENT_PREFS_KEY, JSON.stringify(prefs));

    // Apply preferences (in production, this would enable/disable scripts)
    applyConsentPreferences(prefs);

    setIsVisible(false);
  };

  const applyConsentPreferences = (prefs: ConsentPreferences) => {
    // In production, this would:
    // - Enable/disable Google Analytics
    // - Enable/disable marketing pixels
    // - Set appropriate cookies

    if (prefs.analytics) {
      // Enable analytics scripts here
    } else {
      // Disable analytics scripts here
    }

    if (prefs.marketing) {
      // Enable marketing scripts here
    } else {
      // Disable marketing scripts here
    }
  };

  const handleAcceptAll = () => {
    const allEnabled: ConsentPreferences = {
      essential: true,
      analytics: true,
      marketing: true,
    };
    setPreferences(allEnabled);
    saveConsent(allEnabled);
  };

  const handleDeclineNonEssential = () => {
    const essentialOnly: ConsentPreferences = {
      essential: true,
      analytics: false,
      marketing: false,
    };
    setPreferences(essentialOnly);
    saveConsent(essentialOnly);
  };

  const handleSavePreferences = () => {
    saveConsent(preferences);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ y: 100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 100, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className="fixed bottom-4 left-4 right-4 md:left-auto md:right-6 md:max-w-lg z-50"
        >
          <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl shadow-slate-950/50 overflow-hidden">
            {/* Header */}
            <div className="p-6">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shrink-0">
                  <svg
                    className="w-5 h-5 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                </div>

                <div className="flex-1">
                  <h3 className="text-white font-semibold mb-2">
                    Cookie Preferences
                  </h3>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    We use cookies to enhance your experience and analyze site
                    traffic. See our{" "}
                    <Link
                      href="/privacy"
                      className="text-cyan-400 hover:underline"
                    >
                      Privacy Policy
                    </Link>
                    .
                  </p>
                </div>
              </div>

              {/* Cookie Categories (Expandable) */}
              <AnimatePresence>
                {showDetails && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-6 space-y-4"
                  >
                    {/* Essential */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl">
                      <div>
                        <p className="text-white font-medium text-sm">
                          Essential
                        </p>
                        <p className="text-slate-500 text-xs">
                          Required for the site to function
                        </p>
                      </div>
                      <div className="w-12 h-6 bg-cyan-500 rounded-full flex items-center justify-end px-1">
                        <div className="w-4 h-4 bg-white rounded-full" />
                      </div>
                    </div>

                    {/* Analytics */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl">
                      <div>
                        <p className="text-white font-medium text-sm">
                          Analytics
                        </p>
                        <p className="text-slate-500 text-xs">
                          Help us improve our service
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          setPreferences({
                            ...preferences,
                            analytics: !preferences.analytics,
                          })
                        }
                        className={`w-12 h-6 rounded-full flex items-center px-1 transition-colors ${
                          preferences.analytics
                            ? "bg-cyan-500 justify-end"
                            : "bg-slate-600 justify-start"
                        }`}
                      >
                        <div className="w-4 h-4 bg-white rounded-full" />
                      </button>
                    </div>

                    {/* Marketing */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl">
                      <div>
                        <p className="text-white font-medium text-sm">
                          Marketing
                        </p>
                        <p className="text-slate-500 text-xs">
                          Personalized ads and content
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          setPreferences({
                            ...preferences,
                            marketing: !preferences.marketing,
                          })
                        }
                        className={`w-12 h-6 rounded-full flex items-center px-1 transition-colors ${
                          preferences.marketing
                            ? "bg-cyan-500 justify-end"
                            : "bg-slate-600 justify-start"
                        }`}
                      >
                        <div className="w-4 h-4 bg-white rounded-full" />
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Actions */}
            <div className="p-4 pt-0 flex flex-wrap items-center gap-3">
              {showDetails ? (
                <>
                  <button
                    onClick={handleSavePreferences}
                    className="flex-1 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg text-white text-sm font-medium hover:scale-105 transition-transform"
                  >
                    Save Preferences
                  </button>
                  <button
                    onClick={() => setShowDetails(false)}
                    className="px-4 py-2.5 bg-slate-800 rounded-lg text-slate-300 text-sm font-medium hover:bg-slate-700 transition-colors"
                  >
                    Back
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleAcceptAll}
                    className="flex-1 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg text-white text-sm font-medium hover:scale-105 transition-transform"
                  >
                    Accept All
                  </button>
                  <button
                    onClick={handleDeclineNonEssential}
                    className="px-4 py-2.5 bg-slate-800 rounded-lg text-slate-300 text-sm font-medium hover:bg-slate-700 transition-colors"
                  >
                    Essential Only
                  </button>
                  <button
                    onClick={() => setShowDetails(true)}
                    className="px-4 py-2.5 text-slate-400 text-sm hover:text-white transition-colors"
                  >
                    Customize
                  </button>
                </>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
