import { useEffect, useState } from "react";
import {
  Building2,
  Upload,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Save,
  Globe,
  Smartphone,
  Lock,
} from "lucide-react";
import { getBrand, saveBrand, uploadLogo, loadDemoBrand } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import ConfirmDialog from "../components/ConfirmDialog";

const PLATFORMS = [
  "twitter",
  "instagram",
  "youtube",
  "facebook",
  "telegram",
  "linkedin",
];

const STORES = ["play", "appstore"];

export default function BrandProfile() {
  const { can } = useAuth();
  const canEdit = can("modify_brand");

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [demoConfirmOpen, setDemoConfirmOpen] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const [companyName, setCompanyName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [keywordsInput, setKeywordsInput] = useState("");
  const [socialAccounts, setSocialAccounts] = useState([]);
  const [officialApps, setOfficialApps] = useState([]);

  useEffect(() => {
    fetchProfile();
  }, []);

  async function fetchProfile() {
    setLoading(true);
    try {
      const data = await getBrand();
      if (data) {
        populateForm(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function populateForm(data) {
    setCompanyName(data.company_name || "");
    setLogoUrl(data.logo_url || "");
    setKeywordsInput((data.keywords || []).join(", "));
    setSocialAccounts(data.social_accounts || []);
    setOfficialApps(data.official_apps || []);
  }

  async function handleLoadDemo(overwrite = false) {
    setDemoLoading(true);
    setError(null);
    setMessage(null);
    try {
      const data = await loadDemoBrand(overwrite);
      populateForm(data);
      setMessage("Demo Brand 'Paytm' loaded successfully! All official assets populated.");
    } catch (err) {
      if (err.status === 409) {
        setDemoConfirmOpen(true);
      } else {
        setError(err.message || "Failed to load demo brand");
      }
    } finally {
      setDemoLoading(false);
    }
  }

  async function handleLogoUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setError("Logo image size must be under 5MB");
      return;
    }

    try {
      const res = await uploadLogo(file);
      setLogoUrl(res.logo_url);
      setMessage("Logo uploaded and updated successfully!");
    } catch (err) {
      setError(err.message || "Failed to upload logo");
    } finally {
      e.target.value = "";
    }
  }

  function addSocial() {
    setSocialAccounts([...socialAccounts, { platform: "twitter", handle: "" }]);
  }

  function updateSocial(index, field, value) {
    const updated = [...socialAccounts];
    updated[index][field] = value;
    setSocialAccounts(updated);
  }

  function removeSocial(index) {
    setSocialAccounts(socialAccounts.filter((_, i) => i !== index));
  }

  function addApp() {
    setOfficialApps([
      ...officialApps,
      { store: "play", package_id: "", developer_name: "" },
    ]);
  }

  function updateApp(index, field, value) {
    const updated = [...officialApps];
    updated[index][field] = value;
    setOfficialApps(updated);
  }

  function removeApp(index) {
    setOfficialApps(officialApps.filter((_, i) => i !== index));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!companyName.trim()) {
      setError("Company Name is required (min 2 characters)");
      return;
    }

    setSaving(true);
    setError(null);
    setMessage(null);

    const keywords = keywordsInput
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);

    const payload = {
      company_name: companyName.trim(),
      keywords,
      social_accounts: socialAccounts.map((s) => ({
        platform: s.platform,
        handle: s.handle.trim(),
      })),
      official_apps: officialApps.map((a) => ({
        store: a.store,
        package_id: a.package_id.trim(),
        developer_name: a.developer_name.trim(),
      })),
    };

    try {
      const res = await saveBrand(payload);
      populateForm(res);
      setMessage("Brand Profile saved! Monitoring engine will use this profile.");
    } catch (err) {
      setError(err.message || "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Top Banner & Quick Demo Action */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-sky-500/30 bg-sky-500/10 p-5">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Building2 className="h-6 w-6 text-sky-400" />
            Brand Profile & Asset Registry
          </h1>
          <p className="mt-1 text-sm text-slate-300">
            Define authorized brand assets. Official handles and package IDs are
            excluded from threats BEFORE scoring to eliminate false positives.
          </p>
        </div>

        {canEdit && (
          <button
            type="button"
            onClick={() => handleLoadDemo(false)}
            disabled={demoLoading}
            className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:bg-sky-400 active:scale-95 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            {demoLoading ? "Loading Demo..." : "Load Demo Brand (Paytm)"}
          </button>
        )}
      </div>

      {/* Read-only notice for viewers */}
      {!canEdit && (
        <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 p-3.5 text-sm text-slate-300">
          <Lock className="h-4 w-4 flex-shrink-0 text-slate-400" />
          <span>
            Read-only access: your role can view the brand profile and official
            asset allowlists but cannot modify them.
          </span>
        </div>
      )}

      {/* Notifications */}
      {message && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-sm text-emerald-300">
          <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-sm text-red-300">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-slate-400">Loading brand profile...</div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <fieldset disabled={!canEdit} className="space-y-6 min-w-0">
          {/* General Information & Logo */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-5">
            <h2 className="text-base font-semibold text-slate-200">
              1. Brand Identity & Official Logo
            </h2>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
              <div className="sm:col-span-2 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Company Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Paytm"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    Used as the benchmark for name similarity and look-alike detection.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Brand Keywords & Core Offerings (comma separated)
                  </label>
                  <input
                    type="text"
                    value={keywordsInput}
                    onChange={(e) => setKeywordsInput(e.target.value)}
                    placeholder="e.g. wallet, payments, upi, soundbox, fastag, bank"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    Used to compute TF-IDF cosine similarity against bios and app descriptions.
                  </p>
                </div>
              </div>

              {/* Logo Box */}
              <div className="flex flex-col items-center justify-center rounded-lg border border-slate-800 bg-slate-950 p-4 text-center">
                <span className="text-xs font-semibold text-slate-300 mb-2">
                  Official Logo
                </span>
                {logoUrl ? (
                  <img
                    src={logoUrl}
                    alt="Brand Logo"
                    className="h-20 w-20 rounded-lg border border-slate-700 bg-slate-900 object-cover p-1 shadow"
                  />
                ) : (
                  <div className="flex h-20 w-20 items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-900 text-slate-500">
                    No Logo
                  </div>
                )}
                <label className="mt-3 flex cursor-pointer items-center gap-1.5 rounded-md bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700">
                  <Upload className="h-3.5 w-3.5" />
                  Upload Image
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/svg+xml"
                    onChange={handleLogoUpload}
                    className="hidden"
                  />
                </label>
                <span className="mt-1 text-[10px] text-slate-500">PNG, JPG, SVG up to 5MB</span>
              </div>
            </div>
          </div>

          {/* Official Social Accounts */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
                  <Globe className="h-4 w-4 text-sky-400" />
                  2. Official Social Media Handles (Allowlist)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  These accounts will NEVER be flagged as threats during scans.
                </p>
              </div>

              <button
                type="button"
                onClick={addSocial}
                className="flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-sky-400 hover:bg-slate-700"
              >
                <Plus className="h-3.5 w-3.5" /> Add Social
              </button>
            </div>

            {socialAccounts.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No official social accounts registered yet.
              </p>
            ) : (
              <div className="space-y-2.5">
                {socialAccounts.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-wrap items-center gap-2.5 rounded-lg bg-slate-950 p-2.5 border border-slate-800/80"
                  >
                    <select
                      value={item.platform}
                      onChange={(e) => updateSocial(idx, "platform", e.target.value)}
                      className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {PLATFORMS.map((p) => (
                        <option key={p} value={p}>
                          {p.toUpperCase()}
                        </option>
                      ))}
                    </select>

                    <div className="relative flex-1 min-w-[200px]">
                      <span className="absolute inset-y-0 left-2.5 flex items-center text-xs text-slate-500">
                        @
                      </span>
                      <input
                        type="text"
                        placeholder="official_handle"
                        value={item.handle.replace(/^@/, "")}
                        onChange={(e) => updateSocial(idx, "handle", e.target.value)}
                        className="w-full rounded-md border border-slate-700 bg-slate-900 pl-6 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none"
                      />
                    </div>

                    <button
                      type="button"
                      onClick={() => removeSocial(idx)}
                      className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Official App Store Assets */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-sky-400" />
                  3. Official App Store Applications (Allowlist)
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Apps matching package IDs or authorized developer names will be excluded.
                </p>
              </div>

              <button
                type="button"
                onClick={addApp}
                className="flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-sky-400 hover:bg-slate-700"
              >
                <Plus className="h-3.5 w-3.5" /> Add App
              </button>
            </div>

            {officialApps.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No official apps registered yet.
              </p>
            ) : (
              <div className="space-y-2.5">
                {officialApps.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-wrap items-center gap-2.5 rounded-lg bg-slate-950 p-2.5 border border-slate-800/80"
                  >
                    <select
                      value={item.store}
                      onChange={(e) => updateApp(idx, "store", e.target.value)}
                      className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      {STORES.map((s) => (
                        <option key={s} value={s}>
                          {s === "play" ? "Google Play" : "Apple App Store"}
                        </option>
                      ))}
                    </select>

                    <input
                      type="text"
                      placeholder="Package ID (e.g. net.one97.paytm)"
                      value={item.package_id}
                      onChange={(e) => updateApp(idx, "package_id", e.target.value)}
                      className="flex-1 min-w-[180px] rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none"
                    />

                    <input
                      type="text"
                      placeholder="Official Developer (e.g. One97 Communications Ltd.)"
                      value={item.developer_name}
                      onChange={(e) => updateApp(idx, "developer_name", e.target.value)}
                      className="flex-1 min-w-[200px] rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none"
                    />

                    <button
                      type="button"
                      onClick={() => removeApp(idx)}
                      className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || !canEdit}
              className="flex items-center gap-2 rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white shadow hover:bg-sky-400 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {saving ? "Saving Profile..." : "Save Brand Profile"}
            </button>
          </div>
          </fieldset>
        </form>
      )}

      {/* Demo overwrite confirmation */}
      <ConfirmDialog
        open={demoConfirmOpen}
        title="Replace the existing brand profile?"
        icon={AlertCircle}
        danger
        busy={demoLoading}
        confirmLabel="Replace with Demo Data"
        onCancel={() => setDemoConfirmOpen(false)}
        onConfirm={async () => {
          await handleLoadDemo(true);
          setDemoConfirmOpen(false);
        }}
      >
        <p>
          A custom brand profile already exists. Loading the demo brand will
          replace the current brand profile and its official asset allowlists
          (social handles and app allowlist entries).
        </p>
        <p className="mt-2 text-slate-400">
          Detection history, scan runs, uploaded logos, and user accounts will
          not be changed.
        </p>
      </ConfirmDialog>
    </div>
  );
}
