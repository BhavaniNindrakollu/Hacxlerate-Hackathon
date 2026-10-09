import { AlertCircle, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

export default function SourceBanner({
  status,
  message,
  onRefresh,
  loading = false,
}) {
  if (status !== "unavailable") {
    return null;
  }

  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
      <div className="flex items-center gap-2.5">
        <AlertCircle className="h-5 w-5 flex-shrink-0 text-amber-400" />
        <div>
          <span className="font-semibold text-amber-300">
            Source unavailable, showing cached/sample data
          </span>
          {message && (
            <p className="text-xs text-amber-300/80 mt-0.5">{message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Link
          to="/settings"
          className="text-xs font-medium text-amber-300 underline underline-offset-2 hover:text-white"
        >
          Check Connector Status
        </Link>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-1 rounded bg-amber-500/20 px-2.5 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-500/30 disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
