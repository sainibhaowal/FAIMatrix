"use client";

import { FeaturePageLayout } from "@/components";

const icon = (
  <svg
    viewBox="0 0 24 24"
    className="w-12 h-12"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    <path d="M9 12l2 2 4-4" />
  </svg>
);

const benefits = [
  "Deterministic UUIDv5 mapping (Mathematical Identity)",
  "No-Fragmentation architecture across sessions",
  "Transactional 'Hard Purge' on account deletion",
  "Zero-Trust backend session verification",
  "Automated rate-limiting and brute-force protection",
  "100% data isolation via tenant-id scoping",
];

export default function SecurityPage() {
  return (
    <FeaturePageLayout
      title="Deterministic Security"
      subtitle="Mathematical identity anchoring with absolute data purges. Your privacy is enforced by laws of logic."
      gradient="from-green-500 to-emerald-500"
      icon={icon}
      benefits={benefits}
    >
      <h2 className="text-2xl font-bold text-white mb-4">Privacy by Design</h2>
      <p className="text-slate-400 mb-6">
        FAIM-Native is built from the ground up with the philosophy that
        security shouldn&apos;t just be an add-on - it should be a mathematical
        certainty. Our deterministic identity architecture ensures that your
        presence in the system is uniquely yours, anchored by your verified
        email.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        Mathematical Identity Anchoring
      </h3>
      <p className="text-slate-400 mb-6">
        Unlike systems that use random, auto-incrementing IDs, FAIM uses
        deterministic UUIDv5 hashes. This means your User ID, Tenant ID, and
        Graph ID are calculated from your email. This ensures absolute
        consistency across signups and prevents identity fragments or duplicate
        accounts.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        The Absolute Hard Purge
      </h3>
      <p className="text-slate-400 mb-6">
        When you decide to delete your account, we don&apos;t just
        &quot;flag&quot; it as deleted. We execute a transactional hard purge of
        the entire database. Every node, edge, event, and snapshot associated
        with your Identity is wiped across PostgreSQL and our Vector Indices.
        Zero residue remains.
      </p>

      <h3 className="text-xl font-semibold text-white mb-3">
        Zero-Trust Authorization
      </h3>
      <p className="text-slate-400">
        Our backend middleware never trusts user-provided IDs. Access to any
        piece of data requires a cryptographically signed JWT. The backend
        calculates your Identity ID itself from the verified session, making it
        impossible to spoof another user&apos;s data even if their ID is known.
      </p>
    </FeaturePageLayout>
  );
}
