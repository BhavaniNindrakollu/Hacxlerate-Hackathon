import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Radar,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Building2,
  ExternalLink,
  Smartphone,
  Globe,
  FlaskConical,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getDashboardStats, runSocialScan, runAppsScan, mediaUrl } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import SeverityBadge from "../components/SeverityBadge";

const SEVERITY_COLORS = {
  High: "#ef4444",
  Medium: "#f59e0b",
  Low: "#eab308",
  Safe: "#10b981",
};

export default function Dashboard() {
  const { can } = useAuth();
  const canScan = can("scan");

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  async function fetchStats() {
    try {
      setLoading(true);
      const data = await getDashboardStats();
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunFullScan() {
    setScanning(true);
    try {
      await Promise.all([runSocialScan(), runAppsScan()]);
      await fetchStats();
    } catch (err) {
      console.error(err);
    } finally {
      setScanning(false);
    }
  }

  if (loading && !stats) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <RefreshCw className="mr-2 h-5 w-5 animate-spin text-sky-400" />
        Loading Trust Radar metrics...
      </div>
    );
  }

  const brand = stats?.brand || {};
  const exposureScore = stats?.brand_exposure_score || 0;
  const severityCounts = stats?.severity_counts || { High: 0, Medium: 0, Low: 0, Safe: 0 };

  const pieData = [
    { name: "High", value: severityCounts.High, color: SEVERITY_COLORS.High },
    { name: "Medium", value: severityCounts.Medium, color: SEVERITY_COLORS.Medium },
    { name: "Low", value: severityCounts.Low, color: SEVERITY_COLORS.Low },
    { name: "Safe", value: severityCounts.Safe, color: SEVERITY_COLORS.Safe },
  ].filter((d) => d.value > 0);

  const platformData = stats?.platforms || [];
  const techniqueData = (stats?.techniques || []).slice(0, 6);
  const recentThreats = stats?.recent_threats || [];

  return (
    <div className="space-y-6">
      {/* Brand Header & Threat Index Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-xl backdrop-blur">
        <div className="flex items-center gap-4">
          <img
            src={mediaUrl(brand.logo_url || "/uploads/paytm_official.png")}
            alt={brand.company_name || "Brand"}
            onError={(e) => {
              e.target.src = mediaUrl("/uploads/neutral_tech.png");
            }}
            className="h-14 w-14 rounded-xl border border-slate-700 bg-slate-950 object-cover p-1 shadow"
          />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">
                {brand.company_name || "Paytm"}
              </h1>
              <span className="rounded bg-sky-500/20 px-2 py-0.5 text-xs font-semibold text-sky-400">
                ACTIVE MONITORING
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {(brand.keywords || []).slice(0, 5).join(" • ") || "wallet • upi • soundbox • payments"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/brand"
            className="rounded-lg border border-slate-700 bg-slate-800/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
          >
            Configure Assets
          </Link>

          {canScan && (
            <button
              type="button"
              onClick={handleRunFullScan}
              disabled={scanning}
              className="flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-xs font-bold text-white shadow-lg transition hover:bg-sky-400 active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${scanning ? "animate-spin" : ""}`} />
              {scanning ? "Scanning Feeds..." : "Run Full Scan"}
            </button>
          )}
        </div>
      </div>

      {/* Trust Radar Key Metrics Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {/* Brand Exposure Score */}
        <div className="rounded-xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-5 shadow">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Brand Exposure Score</span>
            <Radar className="h-4 w-4 text-sky-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-3xl font-black ${
                exposureScore >= 70
                  ? "text-red-400"
                  : exposureScore >= 40
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            >
              {exposureScore}
            </span>
            <span className="text-xs text-slate-400">/100</span>
          </div>
          <div className="mt-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
            {exposureScore >= 70 ? (
              <span className="text-red-400">● Critical Threat Exposure</span>
            ) : exposureScore >= 40 ? (
              <span className="text-amber-400">● Elevated Risk Exposure</span>
            ) : (
              <span className="text-emerald-400">● Low Risk Profile</span>
            )}
          </div>
        </div>

        {/* Total Monitored */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <div className="text-xs text-slate-400">Total Monitored Candidates</div>
          <div className="mt-2 text-3xl font-black text-slate-100">
            {stats?.total_monitored || 0}
          </div>
          <div className="mt-2 text-[11px] text-slate-400">
            Social profiles & App stores synced
          </div>
        </div>

        {/* High Severity Threats */}
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-5 shadow">
          <div className="flex items-center justify-between text-xs text-red-400">
            <span>High Severity</span>
            <ShieldAlert className="h-4 w-4 text-red-400" />
          </div>
          <div className="mt-2 text-3xl font-black text-red-400">
            {severityCounts.High}
          </div>
          <div className="mt-2 text-[11px] text-red-400/80">
            Immediate takedown recommended
          </div>
        </div>

        {/* Medium Threats */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5 shadow">
          <div className="flex items-center justify-between text-xs text-amber-400">
            <span>Medium Severity</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-3xl font-black text-amber-400">
            {severityCounts.Medium}
          </div>
          <div className="mt-2 text-[11px] text-amber-400/80">
            Suspicious look-alikes & resellers
          </div>
        </div>

        {/* Safe / Excluded Assets */}
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5 shadow">
          <div className="flex items-center justify-between text-xs text-emerald-400">
            <span>Safe / Official</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-3xl font-black text-emerald-400">
            {severityCounts.Safe}
          </div>
          <div className="mt-2 text-[11px] text-emerald-400/80">
            Allowlisted or benign compounds
          </div>
        </div>
      </div>

      {/* Analytics Charts Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Severity Distribution Donut */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <h2 className="text-sm font-semibold text-slate-200">
            Threat Severity Breakdown
          </h2>
          <div className="mt-4 h-52 flex items-center justify-center">
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-slate-500">No detection data</p>
            )}
          </div>
          <div className="mt-2 flex justify-around text-xs text-slate-300">
            {pieData.map((d) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                <span>{d.name}: {d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Platform Threats Distribution */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <h2 className="text-sm font-semibold text-slate-200">
            Threats by Channel / Store
          </h2>
          <div className="mt-4 h-52">
            {platformData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={platformData}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="threats" name="Active Threats" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="total" name="Total Synced" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                No platform data
              </div>
            )}
          </div>
          <p className="mt-2 text-center text-[11px] text-slate-500">
            Comparison of threats detected versus total monitored assets
          </p>
        </div>

        {/* Top Look-alike Techniques */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
          <h2 className="text-sm font-semibold text-slate-200">
            Top Look-alike Techniques Detected
          </h2>
          <div className="mt-4 h-52">
            {techniqueData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={techniqueData} layout="vertical">
                  <XAxis type="number" stroke="#64748b" fontSize={10} />
                  <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={10} width={80} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      borderColor: "#334155",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="count" name="Incidents" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-slate-500">
                No technique breakdown
              </div>
            )}
          </div>
          <p className="mt-2 text-center text-[11px] text-slate-500">
            Frequencies of character swaps, homoglyphs, spacing & added words
          </p>
        </div>
      </div>

      {/* Quick Access Channels & Recent Threats */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quick Launch Cards */}
        <div className="space-y-4">
          <Link
            to="/social"
            className="group block rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-sky-500/50 hover:bg-slate-900"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-sky-500/10 p-2.5 text-sky-400 group-hover:bg-sky-500/20">
                  <Globe className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200 text-sm">
                    Social Media Monitoring
                  </h3>
                  <p className="text-xs text-slate-400">
                    Scan candidate profiles across Twitter, Instagram, YouTube
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-sky-400" />
            </div>
          </Link>

          <Link
            to="/apps"
            className="group block rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-sky-500/50 hover:bg-slate-900"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-400 group-hover:bg-emerald-500/20">
                  <Smartphone className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200 text-sm">
                    App Store Monitoring
                  </h3>
                  <p className="text-xs text-slate-400">
                    Detect copycat apps, publisher mismatches, and loan traps
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-emerald-400" />
            </div>
          </Link>

          <Link
            to="/lab"
            className="group block rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-purple-500/50 hover:bg-slate-900"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-purple-500/10 p-2.5 text-purple-400 group-hover:bg-purple-500/20">
                  <FlaskConical className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-200 text-sm">
                    Look-alike Lab
                  </h3>
                  <p className="text-xs text-slate-400">
                    Simulate typosquatting, homoglyphs, and cross-reference feeds
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-purple-400" />
            </div>
          </Link>
        </div>

        {/* Recent High Threats Feed */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-red-400" />
              Highest Priority Incident Feed
            </h2>
            <span className="text-xs text-slate-500">Live Scored Queue</span>
          </div>

          {recentThreats.length === 0 ? (
            <p className="py-8 text-center text-xs text-slate-500">
              No high risk detections recorded.
            </p>
          ) : (
            <div className="mt-3 divide-y divide-slate-800/60">
              {recentThreats.map((t) => {
                const cand = t.candidate || {};
                return (
                  <div
                    key={t.id}
                    className="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <div className="flex items-center gap-3">
                      <img
                        src={mediaUrl(cand.avatar_url || cand.icon_url || "/uploads/neutral_tech.png")}
                        alt=""
                        onError={(e) => {
                          e.target.src = mediaUrl("/uploads/neutral_tech.png");
                        }}
                        className="h-10 w-10 rounded-lg border border-slate-700 bg-slate-950 object-cover p-0.5"
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-slate-100">
                            {cand.name || cand.title || "Unknown"}
                          </span>
                          <SeverityBadge verdict={t.verdict} />
                          {t.lookalike_technique && (
                            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-amber-300 font-mono">
                              [{t.lookalike_technique}]
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 font-mono">
                          {cand.handle ? `@${cand.handle.replace(/^@/, "")}` : cand.package_id}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-xs font-black text-red-400">
                        {t.score}/100
                      </span>
                      <Link
                        to={`/detections/${t.id}`}
                        className="rounded bg-slate-800 px-2.5 py-1 text-xs font-semibold text-sky-400 hover:bg-slate-700"
                      >
                        Dossier →
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
