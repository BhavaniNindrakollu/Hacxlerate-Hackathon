import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FlaskConical,
  Search,
  Sparkles,
  Copy,
  Check,
  ShieldAlert,
  ArrowRight,
  Filter,
  Lock,
} from "lucide-react";
import { generateLookalikes, getBrand } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import SeverityBadge from "../components/SeverityBadge";

const TECHNIQUES = [
  { value: "ALL", label: "All Techniques" },
  { value: "swap", label: "Swaps & Transpositions" },
  { value: "homoglyph", label: "Homoglyphs (Cyrillic)" },
  { value: "leetspeak", label: "Leetspeak (0, 1, rn)" },
  { value: "spacing", label: "Spacing Tricks" },
  { value: "punctuation", label: "Punctuation" },
  { value: "added-word", label: "Added Bait Words" },
];

export default function LookalikeLab() {
  const { can } = useAuth();
  const canSimulate = can("scan");

  const [inputName, setInputName] = useState("Paytm");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterTech, setFilterTech] = useState("ALL");
  const [onlyMatched, setOnlyMatched] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);

  useEffect(() => {
    initLab();
  }, []);

  async function initLab() {
    try {
      const b = await getBrand();
      const initialName = b?.company_name || "Paytm";
      setInputName(initialName);
      if (canSimulate) runGenerate(initialName);
    } catch {
      if (canSimulate) runGenerate("Paytm");
    }
  }

  async function runGenerate(name) {
    if (!name || name.trim().length < 2) return;
    setLoading(true);
    try {
      const res = await generateLookalikes(name.trim());
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function handleFormSubmit(e) {
    e.preventDefault();
    runGenerate(inputName);
  }

  function handleCopy(text, idx) {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  }

  const variants = data?.variants || [];
  const filteredVariants = variants.filter((v) => {
    if (filterTech !== "ALL" && v.technique !== filterTech) return false;
    if (onlyMatched && !v.exists_in_monitored) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-purple-500/30 bg-purple-500/10 p-5 shadow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <FlaskConical className="h-6 w-6 text-purple-400" />
              Look-alike Lab
            </h1>
            <p className="mt-1 text-xs text-slate-300">
              Generate permutations across typos, character swaps, Cyrillic homoglyphs,
              leetspeak, and bait keywords. Cross-referenced in real time with actively
              scanned threat feeds.
            </p>
          </div>

          {canSimulate ? (
            <form onSubmit={handleFormSubmit} className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
              <div className="relative">
                <input
                  type="text"
                  value={inputName}
                  onChange={(e) => setInputName(e.target.value)}
                  placeholder="Enter Brand Name..."
                  className="w-full rounded-lg border border-purple-500/40 bg-slate-950 px-3.5 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-purple-400 focus:outline-none sm:w-56"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-purple-500 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {loading ? "Generating..." : "Simulate Variants"}
              </button>
            </form>
          ) : (
            <span className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3.5 py-2 text-xs text-slate-300">
              <Lock className="h-3.5 w-3.5 text-slate-400" />
              Simulation requires the Analyst or Administrator role.
            </span>
          )}
        </div>
      </div>

      {/* Metrics & Filter Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-400">Technique:</span>
            {TECHNIQUES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setFilterTech(t.value)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                  filterTech === t.value
                    ? "bg-purple-600 text-white shadow"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={onlyMatched}
              onChange={(e) => setOnlyMatched(e.target.checked)}
              className="rounded border-slate-700 bg-slate-800 text-purple-600 focus:ring-0"
            />
            <span>Show Only Active Matches ({data?.matches_found || 0})</span>
          </label>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-2 text-xs text-slate-400">
          <span>
            Simulated for Brand: <strong className="text-purple-300">{data?.brand_name}</strong>
          </span>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <span>
              Total Variants: <strong className="text-slate-200">{data?.total_variants || 0}</strong>
            </span>
            <span className="text-red-400">
              🔥 Matched in Feeds: <strong>{data?.matches_found || 0}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Variants Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-400">
          <FlaskConical className="mx-auto mb-2 h-7 w-7 animate-pulse text-purple-400" />
          Simulating permutation algorithms...
        </div>
      ) : filteredVariants.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center text-slate-400 text-xs">
          {!canSimulate && !data
            ? "Variant simulation is available to Analyst and Administrator roles. Ask an analyst to run a simulation to populate this view."
            : "No variants matching the current filter."}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filteredVariants.map((v, idx) => {
            const isMatch = v.exists_in_monitored;
            const matchInfo = v.matched_candidate;

            return (
              <div
                key={idx}
                className={`rounded-xl border p-4 transition ${
                  isMatch
                    ? "border-red-500/50 bg-red-950/20 shadow-lg shadow-red-950/20"
                    : "border-slate-800 bg-slate-900/50 hover:border-slate-700"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="break-all font-mono text-sm font-bold text-slate-100">
                      {v.variant}
                    </span>
                    <div className="mt-1 flex items-center gap-1.5">
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-medium text-slate-300 uppercase">
                        {v.technique}
                      </span>
                      {isMatch && (
                        <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                          🔥 MATCHED IN FEED
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleCopy(v.variant, idx)}
                    className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
                    title="Copy variant"
                  >
                    {copiedIndex === idx ? (
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>

                {/* Match Information Card */}
                {isMatch && matchInfo && (
                  <div className="mt-3 rounded-lg border border-red-500/30 bg-slate-950/60 p-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-300 font-medium capitalize">
                        {matchInfo.platform} Candidate
                      </span>
                      <SeverityBadge verdict={matchInfo.verdict} />
                    </div>
                    <p className="mt-1 font-mono text-[11px] text-slate-400 truncate">
                      {matchInfo.handle ? `@${matchInfo.handle}` : matchInfo.name}
                    </p>
                    <div className="mt-2 flex items-center justify-between border-t border-slate-800/80 pt-1.5">
                      <span className="text-red-400 font-bold">
                        Threat: {matchInfo.score}/100
                      </span>
                      <Link
                        to={`/detections/${matchInfo.detection_id}`}
                        className="flex items-center gap-1 text-[11px] font-semibold text-sky-400 hover:text-sky-300"
                      >
                        Inspect Dossier <ArrowRight className="h-3 w-3" />
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
