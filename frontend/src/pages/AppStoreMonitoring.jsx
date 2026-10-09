import { useEffect, useState } from "react";
import {
  Smartphone,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { getAppDetections, getBrand, runAppsScan } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import SourceBanner from "../components/SourceBanner";
import ThreatCard from "../components/ThreatCard";

const STORES = [
  { value: "", label: "All Stores" },
  { value: "play", label: "Google Play" },
  { value: "appstore", label: "Apple App Store" },
];

const SEVERITIES = ["ALL", "High", "Medium", "Low", "Safe"];

export default function AppStoreMonitoring() {
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
  const [selectedStore, setSelectedStore] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadData();
  }, [selectedSeverity, selectedStore]);

  async function loadData() {
    try {
      setLoading(true);
      const [bData, dData] = await Promise.all([
        getBrand(),
        getAppDetections({
          verdict: selectedSeverity === "ALL" ? "" : selectedSeverity,
          store: selectedStore,
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
      const res = await runAppsScan();
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
            <Smartphone className="h-6 w-6 text-emerald-400" />
            App Store Monitoring
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Detecting malicious look-alike apps, publisher mismatches, fraudulent loan portals,
            and deceptive icon clones across Google Play and Apple App Store.
          </p>
        </div>

        {canScan && (
          <button
            type="button"
            onClick={handleScan}
            disabled={scanning}
            className="flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-white shadow-lg transition hover:bg-emerald-400 active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${scanning ? "animate-spin" : ""}`} />
            {scanning ? "Scanning Stores..." : "Scan App Stores"}
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
                    ? "bg-emerald-500 text-white shadow"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {/* Store Selector & Search */}
          <div className="flex flex-wrap items-center gap-2.5">
            <select
              value={selectedStore}
              onChange={(e) => setSelectedStore(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
            >
              {STORES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>

            <form onSubmit={handleSearchSubmit} className="relative">
              <input
                type="text"
                placeholder="Search package IDs, titles, developers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-60 rounded-lg border border-slate-700 bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
              />
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
            </form>
          </div>
        </div>

        {/* Threat Stats Bar */}
        <div className="flex items-center justify-between border-t border-slate-800/80 pt-2.5 text-xs text-slate-400">
          <span>
            Showing <strong className="text-slate-200">{detections.length}</strong> applications
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
          <RefreshCw className="mx-auto mb-2 h-6 w-6 animate-spin text-emerald-400" />
          Loading candidate applications...
        </div>
      ) : detections.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-12 text-center">
          <ShieldCheck className="mx-auto h-10 w-10 text-emerald-400 opacity-60 mb-2" />
          <h3 className="font-semibold text-slate-200">No matching app detections</h3>
          <p className="mt-1 text-xs text-slate-400">
            Try adjusting your search filters or click "Scan App Stores" to refresh the catalog.
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
