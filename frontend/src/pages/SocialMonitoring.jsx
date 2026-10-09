import { useEffect, useState } from "react";
import {
  Globe,
  RefreshCw,
  Search,
  Filter,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { getBrand, getSocialDetections, runSocialScan } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import SourceBanner from "../components/SourceBanner";
import ThreatCard from "../components/ThreatCard";

const PLATFORMS = [
  { value: "", label: "All Platforms" },
  { value: "twitter", label: "Twitter / X" },
  { value: "instagram", label: "Instagram" },
  { value: "telegram", label: "Telegram" },
  { value: "facebook", label: "Facebook" },
  { value: "youtube", label: "YouTube" },
  { value: "linkedin", label: "LinkedIn" },
];

const SEVERITIES = ["ALL", "High", "Medium", "Low", "Safe"];

export default function SocialMonitoring() {
  const { can } = useAuth();
  const canScan = can("scan");

  const [brand, setBrand] = useState(null);
  const [detections, setDetections] = useState([]);
  const [sourceStatus, setSourceStatus] = useState("ok");
  const [sourceMessage, setSourceMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  // Filters
  const [selectedSeverity, setSelectedSeverity] = useState("ALL");
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadData();
  }, [selectedSeverity, selectedPlatform]);

  async function loadData() {
    try {
      setLoading(true);
      const [bData, dData] = await Promise.all([
        getBrand(),
        getSocialDetections({
          verdict: selectedSeverity === "ALL" ? "" : selectedSeverity,
          platform: selectedPlatform,
          search: searchQuery,
        }),
      ]);
      setBrand(bData);
      setDetections(dData.items || []);
      setSourceStatus(dData.source_status || "ok");
      setSourceMessage(dData.source_message);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    setScanning(true);
    try {
      const res = await runSocialScan();
      setSourceStatus(res.source_status);
      setSourceMessage(res.source_message);
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setScanning(false);
    }
  }

  function handleSearchSubmit(e) {
    e.preventDefault();
    loadData();
  }

  const highThreatsCount = detections.filter((d) => d.verdict === "High").length;
  const mediumThreatsCount = detections.filter((d) => d.verdict === "Medium").length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Globe className="h-6 w-6 text-sky-400" />
            Social Media Monitoring
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Scanning candidate profiles across Twitter, Instagram, Telegram, YouTube & Facebook
            against official brand handles.
          </p>
        </div>

        {canScan && (
          <button
            type="button"
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-xs font-bold text-white shadow-lg transition hover:bg-sky-400 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${scanning ? "animate-spin" : ""}`} />
            {scanning ? "Scanning Feeds..." : "Scan Social Profiles"}
          </button>
        )}
      </div>

      {/* Resilience Source Unavailable Banner */}
      <SourceBanner
        status={sourceStatus}
        message={sourceMessage}
        onRefresh={canScan ? handleScan : undefined}
        loading={scanning}
      />

      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Severity Pills */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-400 mr-1">Severity:</span>
            {SEVERITIES.map((sev) => (
              <button
                key={sev}
                type="button"
                onClick={() => setSelectedSeverity(sev)}
                className={`rounded-lg px-3 py-1 text-xs font-medium transition ${
                  selectedSeverity === sev
                    ? "bg-sky-500 text-white shadow"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {/* Platform Selector & Search */}
          <div className="flex flex-wrap items-center gap-2.5">
            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
            >
              {PLATFORMS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>

            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                placeholder="Search handles, names, bio..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-56 rounded-lg border border-slate-700 bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
              />
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
            </form>
          </div>
        </div>

        {/* Threat Stats Bar */}
        <div className="flex items-center justify-between border-t border-slate-800/80 pt-2.5 text-xs text-slate-400">
          <span>
            Showing <strong className="text-slate-200">{detections.length}</strong> profiles
          </span>
          <div className="flex gap-4">
            <span className="text-red-400">
              ● High Threats: <strong>{highThreatsCount}</strong>
            </span>
            <span className="text-amber-400">
              ● Medium: <strong>{mediumThreatsCount}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* Detections List */}
      {loading ? (
        <div className="py-16 text-center text-slate-400">
          <RefreshCw className="mx-auto mb-2 h-6 w-6 animate-spin text-sky-400" />
          Loading candidate profiles...
        </div>
      ) : detections.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
          <ShieldCheck className="mx-auto h-10 w-10 text-emerald-400 opacity-60 mb-2" />
          <h3 className="font-semibold text-slate-200">No matching detections</h3>
          <p className="mt-1 text-xs text-slate-400">
            Try adjusting your search filters or click "Scan Social Profiles" to run a scan.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {detections.map((d) => (
            <ThreatCard key={d.id} detection={d} brand={brand} />
          ))}
        </div>
      )}
    </div>
  );
}
