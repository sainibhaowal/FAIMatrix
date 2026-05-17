import { redirect } from "next/navigation";

export default function AdminAlertsPage() {
  redirect("/dashboard/control-plane?section=incidents");
}
