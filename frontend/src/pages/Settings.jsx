import { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  AlertTriangle,
  RefreshCw,
  Globe,
  Smartphone,
  Trash2,
  Sparkles,
  CheckCircle2,
  Sliders,
  ShieldCheck,
  DatabaseBackup,
} from "lucide-react";
import {
  getSourcesStatus,
  toggleSources,
  loadDemoBrand,
  runSocialScan,
  runAppsScan,
  deleteDetectionHistory,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AccessDenied from "../components/AccessDenied";
import ConfirmDialog from "../components/ConfirmDialog";

const DELETE_PHRASE = "DELETE_DETECTION_HISTORY";

export default function Settings() {
  const { can } = useAuth();

  const [sources, setSources] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  // Delete-history dialog state
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePhrase, setDeletePhrase] = useState("");
  const [createBackup, setCreateBackup] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState(null);

  // Demo overwrite confirmation state
  const [demoConfirmOpen, setDemoConfirmOpen] = useState(false);

  const canManageSources = can("manage_sources");
  const canScan = can("scan");
  const canDeleteHistory = can("delete_history");
  const pageVisible = canManageSources || canScan;

  useEffect(() => {
    if (pageVisible) fetchStatus();
  }, [pageVisible]);

  if (!pageVisible) {
    return (
      <AccessDenied
        title="Settings unavailable for your role"
        message="Source simulation controls and maintenance actions require the Analyst or Administrator role. Viewers have read-only access to dashboards and detections."
      />
    );
  }

  async function fetchStatus() {
    try {
      setLoading(true);
      const data = await getSourcesStatus();
      setSources(data);
    } catch (err) {
      setError(err.message || "Failed to load connector status.");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(key, currentValue) {
    setUpdating(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await toggleSources({ [key]: !currentValue });
      setSources(updated);
      setMessage(
        `Source simulation updated: ${key} is now ${!currentValue ? "ENABLED (simulated outage)" : "DISABLED (normal)"}`
      );
    } catch (err) {
      setError(err.message || "Failed to update source simulation.");
    } finally {
      setUpdating(false);
    }
  }

  async function handleReloadDemo(confirmOverwrite = false) {
    setUpdating(true);
    setMessage(null);
    setError(null);
    try {
      await loadDemoBrand(confirmOverwrite);
      if (canScan) {
        await runSocialScan();
        await runAppsScan();
      }
      setMessage("Demo Brand 'Paytm' reloaded. Detection history was preserved; scans refreshed.");
      setDemoConfirmOpen(false);
    } catch (err) {
      if (err.status === 409 && !confirmOverwrite) {
        setDemoConfirmOpen(true);
      } else {
        setError(err.message || "Failed to reload the demo brand.");
      }
    } finally {
      setUpdating(false);
    }
  }

  function openDeleteDialog() {
    setDeletePhrase("");
    setCreateBackup(true);
    setDeleteResult(null);
    setDeleteOpen(true);
  }

  async function handleConfirmDelete() {
    setDeleting(true);
    setMessage(null);
    setError(null);
    try {
      const result = await deleteDetectionHistory(deletePhrase, createBackup);
      setDeleteResult(result);
      setDeleteOpen(false);
      setMessage(result.message || "Detection history deleted.");
    } catch (err) {
      setError(err.message || "Failed to delete detection history.");
      setDeleteOpen(false);
    } finally {
      setDeleting(false);
    }
  }

  if (loading && !sources) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <RefreshCw className="mr-2 h-5 w-5 animate-spin text-sky-400" />
        Checking connector diagnostics...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
        <h1 className="flex items-center gap-2 text-xl font-bold text-white">
          <SettingsIcon className="h-6 w-6 text-sky-400" />
          Settings & Source Resilience Controls
        </h1>
        <p className="mt-1 text-xs text-slate-300">
          Manage connector health, inspect fallback pipelines, and run maintenance operations.
          Destructive actions are administrator-only and always ask for explicit confirmation.
        </p>
      </div>

      {message && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-300">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {deleteResult && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-4 text-xs text-slate-300">
          <p className="flex items-center gap-2 font-semibold text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
            History deletion report
          </p>
          <ul className="mt-2 space-y-1 text-slate-400">
            <li>Deleted detections: <strong className="text-slate-200">{deleteResult.deleted_detections}</strong></li>
            <li>Deleted scan runs: <strong className="text-slate-200">{deleteResult.deleted_scan_runs}</strong></li>
            <li>Remaining brand profiles: <strong className="text-slate-200">{deleteResult.remaining_brands}</strong></li>
            <li>Remaining official assets: <strong className="text-slate-200">{deleteResult.remaining_official_assets}</strong></li>
            <li>Remaining user accounts: <strong className="text-slate-200">{deleteResult.remaining_users}</strong></li>
          </ul>
          {deleteResult.backups?.length > 0 && (
            <p className="mt-2 flex items-center gap-1.5 text-slate-400">
              <DatabaseBackup className="h-3.5 w-3.5 text-sky-400" />
              Backups written: {deleteResult.backups.join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Connectors Status Cards (admin-only controls) */}
      <div className="space-y-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Sliders className="h-4 w-4 text-sky-400" />
          Data Source Health & Fault Tolerance Toggles
        </h2>

        {!canManageSources && (
          <p className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-400">
            Source simulation toggles are visible to everyone but can only be changed by an
            administrator.
          </p>
        )}

        {/* Social Connector Card */}
        <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-sky-500/10 p-2.5 text-sky-400">
                <Globe className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-200">
                  Social Monitoring Pipeline (social_sample & live connector)
                </h3>
                <p className="text-xs text-slate-400">
                  Streams candidate social accounts across Twitter, Instagram, Telegram & YouTube.
                </p>
              </div>
            </div>

            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                sources?.social?.status === "ok"
                  ? "border border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : "border border-amber-500/30 bg-amber-500/15 text-amber-400"
              }`}
            >
              {sources?.social?.status === "ok" ? "● OPERATIONAL" : "● UNAVAILABLE (CACHED)"}
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <div className="text-xs text-slate-300">
              <span className="font-semibold">Simulate Source Outage:</span>
              <p className="mt-0.5 text-[11px] text-slate-400">
                Simulates network outage. Demonstrates that scans never crash and a friendly banner appears.
              </p>
            </div>

            <label
              className={`relative inline-flex items-center ${canManageSources ? "cursor-pointer" : "cursor-not-allowed opacity-50"}`}
            >
              <input
                type="checkbox"
                checked={sources?.simulate_social_unavailable || false}
                onChange={() =>
                  handleToggle("simulate_social_unavailable", sources?.simulate_social_unavailable)
                }
                disabled={updating || !canManageSources}
                className="peer sr-only"
              />
              <div className="peer h-6 w-11 rounded-full bg-slate-800 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-slate-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-amber-500 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none" />
            </label>
          </div>
        </div>

        {/* App Store Connector Card */}
        <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-400">
                <Smartphone className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-200">
                  App Store Pipeline (appstore_sample & live connector)
                </h3>
                <p className="text-xs text-slate-400">
                  Streams candidate app store listings across Google Play Store & Apple App Store.
                </p>
              </div>
            </div>

            <span
              className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                sources?.apps?.status === "ok"
                  ? "border border-emerald-500/30 bg-emerald-500/15 text-emerald-400"
                  : "border border-amber-500/30 bg-amber-500/15 text-amber-400"
              }`}
            >
              {sources?.apps?.status === "ok" ? "● OPERATIONAL" : "● UNAVAILABLE (CACHED)"}
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950 p-3.5">
            <div className="text-xs text-slate-300">
              <span className="font-semibold">Simulate Source Outage:</span>
              <p className="mt-0.5 text-[11px] text-slate-400">
                Simulates App Store API rate-limiting or downtime. UI shows a friendly banner.
              </p>
            </div>

            <label
              className={`relative inline-flex items-center ${canManageSources ? "cursor-pointer" : "cursor-not-allowed opacity-50"}`}
            >
              <input
                type="checkbox"
                checked={sources?.simulate_apps_unavailable || false}
                onChange={() =>
                  handleToggle("simulate_apps_unavailable", sources?.simulate_apps_unavailable)
                }
                disabled={updating || !canManageSources}
                className="peer sr-only"
              />
              <div className="peer h-6 w-11 rounded-full bg-slate-800 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-slate-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-amber-500 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none" />
            </label>
          </div>
        </div>
      </div>

      {/* Demo Controls */}
      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
        <h2 className="text-sm font-semibold text-slate-200">Demo Management</h2>
        <p className="text-xs text-slate-400">
          Reloading the demo brand replaces only the brand profile and official allowlist. It never
          deletes detection history, uploaded logos, or user accounts.
        </p>

        <button
          type="button"
          onClick={() => handleReloadDemo(false)}
          disabled={updating}
          className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2.5 text-xs font-bold text-white shadow hover:bg-sky-400 disabled:opacity-50"
        >
          <Sparkles className="h-4 w-4" />
          {updating ? "Working..." : "Reload Demo Brand & Refresh All Scans"}
        </button>
      </div>

      {/* Danger Zone: admin only */}
      {canDeleteHistory ? (
        <div className="space-y-4 rounded-xl border border-red-500/30 bg-red-500/5 p-5 shadow">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-red-300">
            <Trash2 className="h-4 w-4" />
            Danger Zone — Detection History
          </h2>
          <p className="text-xs text-slate-400">
            Deletes <strong className="text-slate-200">detection records and scan runs only</strong>.
            Brand profiles, official assets, uploaded logos, and user accounts are preserved. You can
            optionally write backup files before anything is removed.
          </p>

          <button
            type="button"
            onClick={openDeleteDialog}
            disabled={updating}
            className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2.5 text-xs font-semibold text-red-300 hover:bg-red-500/20 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" />
            Delete Detection History…
          </button>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <p className="text-xs text-slate-400">
            Detection-history deletion is restricted to administrators. Your role can view and export
            detections from the monitoring pages.
          </p>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={deleteOpen}
        title="Delete detection history?"
        danger
        busy={deleting}
        confirmLabel={deleting ? "Deleting..." : "Delete History"}
        confirmDisabled={deletePhrase.trim() !== DELETE_PHRASE}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
      >
        <div className="space-y-3 text-xs">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-300">
            <p className="font-semibold">This permanently deletes:</p>
            <ul className="mt-1 list-disc pl-5">
              <li>All detection records (social + app store)</li>
              <li>All scan runs and their source status history</li>
            </ul>
          </div>
          <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-emerald-300">
            <p className="font-semibold">This does NOT delete:</p>
            <ul className="mt-1 list-disc pl-5">
              <li>Brand profiles and official allowlists</li>
              <li>Uploaded logos and official assets</li>
              <li>User accounts and roles</li>
            </ul>
          </div>

          <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-slate-700 bg-slate-950 p-3">
            <input
              type="checkbox"
              checked={createBackup}
              onChange={(e) => setCreateBackup(e.target.checked)}
              className="mt-0.5 rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
            />
            <span className="text-slate-300">
              Write backup files first (JSON export + SQLite snapshot into the backups/ folder)
            </span>
          </label>

          <div>
            <label className="mb-1 block text-slate-300">
              Type <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-sky-300">{DELETE_PHRASE}</code> to confirm
            </label>
            <input
              type="text"
              value={deletePhrase}
              onChange={(e) => setDeletePhrase(e.target.value)}
              placeholder={DELETE_PHRASE}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100 placeholder-slate-600 focus:border-red-500 focus:outline-none"
            />
          </div>
        </div>
      </ConfirmDialog>

      {/* Demo overwrite confirmation dialog */}
      <ConfirmDialog
        open={demoConfirmOpen}
        title="Replace the existing brand profile?"
        busy={updating}
        confirmLabel="Load Demo Brand"
        onCancel={() => setDemoConfirmOpen(false)}
        onConfirm={() => handleReloadDemo(true)}
      >
        <p className="text-xs text-slate-300">
          A custom brand profile already exists. Loading the demo will replace its name, keywords,
          and official allowlist with Paytm's. Detection history, uploaded logos, and user accounts
          are NOT deleted.
        </p>
      </ConfirmDialog>
    </div>
  );
}
