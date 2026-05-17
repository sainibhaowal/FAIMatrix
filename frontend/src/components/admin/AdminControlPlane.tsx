"use client";

import { ControlCenterConsole } from "@/components/control-center/ControlCenterConsole";

type AdminView = "overview" | "alerts";

export function AdminControlPlane({ view }: { view: AdminView }) {
  return (
    <ControlCenterConsole
      initialSection={view === "alerts" ? "incidents" : "overview"}
    />
  );
}
