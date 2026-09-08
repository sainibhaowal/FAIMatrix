export type ProfileMode = "strict" | "balanced" | "fast" | "relaxed";
export type PersistMode = "strict" | "relaxed";
export type ModeOperation = "ingest" | "evolve";

type CombinationKey = `${ProfileMode}|${PersistMode}`;

const ALL_SUPPORTED_COMBINATIONS: Record<CombinationKey, true> = {
  "strict|strict": true,
  "strict|relaxed": true,
  "balanced|strict": true,
  "balanced|relaxed": true,
  "fast|strict": true,
  "fast|relaxed": true,
  "relaxed|strict": true,
  "relaxed|relaxed": true,
};

const PROFILE_HELPERS: Record<ProfileMode, string> = {
  strict: "Strict: deterministic and conservative behavior.",
  balanced: "Balanced: bounded acceleration with adaptive safeguards.",
  fast: "Fast: throughput-focused with bounded heuristics.",
  relaxed: "Relaxed: adaptive and more aggressive behavior.",
};

const PERSIST_HELPERS: Record<PersistMode, string> = {
  strict: "Persist strict: wait for required durability steps before success.",
  relaxed:
    "Persist relaxed: commit core write first, secondary steps may complete asynchronously.",
};

export type UiModePolicy = {
  operation: ModeOperation;
  requestedProfile: ProfileMode;
  requestedPersistMode: PersistMode;
  supported: boolean;
  reason?: string;
};

function isProfileMode(value: string): value is ProfileMode {
  return (
    value === "strict" ||
    value === "balanced" ||
    value === "fast" ||
    value === "relaxed"
  );
}

function isPersistMode(value: string): value is PersistMode {
  return value === "strict" || value === "relaxed";
}

function safeProfile(value: string): ProfileMode | null {
  const next = (value || "").trim().toLowerCase();
  return isProfileMode(next) ? next : null;
}

function safePersistMode(value: string): PersistMode | null {
  const next = (value || "").trim().toLowerCase();
  return isPersistMode(next) ? next : null;
}

export function formatModePair(
  profile?: string | null,
  persistMode?: string | null,
): string {
  const p = safeProfile(profile || "");
  const m = safePersistMode(persistMode || "");
  if (!p || !m) return "-";
  return `${p}/${m}`;
}

export function getProfileHelper(profile: string): string {
  const next = safeProfile(profile);
  return next ? PROFILE_HELPERS[next] : "Unknown profile.";
}

export function getPersistHelper(persistMode: string): string {
  const next = safePersistMode(persistMode);
  return next ? PERSIST_HELPERS[next] : "Unknown persist mode.";
}

export function resolveUiModePolicy(
  operation: ModeOperation,
  profile: string,
  persistMode: string,
): UiModePolicy {
  const nextProfile = safeProfile(profile);
  const nextPersistMode = safePersistMode(persistMode);

  if (!nextProfile) {
    return {
      operation,
      requestedProfile: "strict",
      requestedPersistMode: nextPersistMode || "relaxed",
      supported: false,
      reason: `Unsupported profile '${profile}'.`,
    };
  }
  if (!nextPersistMode) {
    return {
      operation,
      requestedProfile: nextProfile,
      requestedPersistMode: "relaxed",
      supported: false,
      reason: `Unsupported persist mode '${persistMode}'.`,
    };
  }

  const key = `${nextProfile}|${nextPersistMode}` as CombinationKey;
  const supported = Boolean(ALL_SUPPORTED_COMBINATIONS[key]);

  return {
    operation,
    requestedProfile: nextProfile,
    requestedPersistMode: nextPersistMode,
    supported,
    reason: supported
      ? undefined
      : `Combination '${key}' is not allowed by policy.`,
  };
}

export function buildEffectiveModeText(
  requestedProfile?: string | null,
  requestedPersistMode?: string | null,
  effectiveProfile?: string | null,
  effectivePersistMode?: string | null,
  durabilityPath?: string | null,
): string {
  const requested = formatModePair(requestedProfile, requestedPersistMode);
  const effective = formatModePair(effectiveProfile, effectivePersistMode);
  const durability = (durabilityPath || "").trim() || "-";
  return `Requested ${requested} -> Effective ${effective} | durability: ${durability}`;
}
