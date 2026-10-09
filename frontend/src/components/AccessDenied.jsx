import { Lock } from "lucide-react";
import { ROLE_LABELS, useAuth } from "../auth/AuthContext";

export default function AccessDenied({ title = "Permission denied", message }) {
  const { user } = useAuth();
  const roleLabel = ROLE_LABELS[user?.role] || "Unknown";

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-10 text-center">
      <Lock className="mx-auto mb-3 h-9 w-9 text-amber-400" />
      <h2 className="text-base font-semibold text-slate-100">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-xs text-slate-400">
        {message ||
          `Your role (${roleLabel}) does not allow this action. Contact an administrator if you need access.`}
      </p>
    </div>
  );
}
