import { AlertTriangle, RefreshCw, X } from "lucide-react";

export default function ConfirmDialog({
  open,
  title,
  icon,
  children,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  confirmDisabled = false,
  onConfirm,
  onCancel,
}) {
  if (!open) return null;

  const Icon = icon || AlertTriangle;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={() => {
        if (!busy) onCancel();
      }}
    >
      <div
        className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span
              className={`rounded-lg p-2.5 ${
                danger ? "bg-red-500/15 text-red-400" : "bg-amber-500/15 text-amber-400"
              }`}
            >
              <Icon className="h-5 w-5" />
            </span>
            <h2 className="text-base font-bold text-white">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300 disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 space-y-4 text-sm text-slate-300">{children}</div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy || confirmDisabled}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold text-white shadow disabled:opacity-50 ${
              danger ? "bg-red-600 hover:bg-red-500" : "bg-sky-500 hover:bg-sky-400"
            }`}
          >
            {busy && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
