import { ControlCenterConsole } from "@/components/control-center/ControlCenterConsole";

export default function ControlPlanePage({
  searchParams,
}: {
  searchParams?: { section?: string };
}) {
  return <ControlCenterConsole initialSection={searchParams?.section} />;
}
