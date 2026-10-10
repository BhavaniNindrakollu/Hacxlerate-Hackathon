import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ShieldAlert,
  ArrowLeft,
  Download,
  Copy,
  Check,
  ExternalLink,
  FileText,
  AlertTriangle,
  Building2,
  RefreshCw,
  CheckCircle2,
  Lock,
} from "lucide-react";
import {
  getDetection,
  getTakedownText,
  getTakedownPdfUrl,
  mediaUrl,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import SeverityBadge from "../components/SeverityBadge";

export default function DetectionDetail() {
  const { id } = useParams();
  const { can } = useAuth();
  const canTakedown = can("generate_takedown");

  const [detection, setDetection] = useState(null);
  const [takedownText, setTakedownText] = useState("");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadDetail();
  }, [id]);

  async function loadDetail() {
    try {
      setLoading(true);
      const dData = await getDetection(id);
      setDetection(dData);
      if (canTakedown) {
        const tData = await getTakedownText(id).catch(() => ({ text: "" }));
        setTakedownText(tData.text || "");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function handleCopyNotice() {
    if (!takedownText) return;
    navigator.clipboard.writeText(takedownText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <RefreshCw className="mr-2 h-5 w-5 animate-spin text-sky-400" />
        Loading incident dossier...
      </div>
    );
  }

  if (!detection) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-12 text-center text-slate-300">
        <p>Detection #{id} was not found.</p>
        <Link to="/social" className="mt-4 inline-block text-xs text-sky-400 underline">
          Return to Social Monitoring
        </Link>
      </div>
    );
  }

  const cand = detection.candidate || {};
  const brand = detection.brand || {};
  const breakdown = detection.breakdown || {};
  const evidence = detection.evidence || [];
  const score = detection.score || 0;
  const verdict = detection.verdict || "Safe";
  const technique = detection.lookalike_technique;
  const isApp = detection.candidate_type === "app";

  const brandLogo = mediaUrl(brand.logo_url || "/uploads/paytm_official.png");
  const candImage = mediaUrl(cand.avatar_url || cand.icon_url || "/uploads/neutral_tech.png");

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Navigation & Status */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Link
          to={isApp ? "/apps" : "/social"}
          className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {isApp ? "App Store Feed" : "Social Feed"}
        </Link>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Incident #{id}</span>
          <SeverityBadge verdict={verdict} />
        </div>
      </div>

      {/* Incident Header Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <img
              src={candImage}
              alt=""
              onError={(e) => {
                e.target.src = mediaUrl("/uploads/neutral_tech.png");
              }}
              className="h-16 w-16 rounded-xl border border-slate-700 bg-slate-950 object-cover p-1 shadow"
            />
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl font-bold text-white">
                  {cand.name || cand.title || "Infringing Entity"}
                </h1>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-300 capitalize">
                  {cand.platform || cand.store || detection.candidate_type}
                </span>
                {technique && (
                  <span className="rounded bg-red-600/30 border border-red-500/40 px-2 py-0.5 text-xs font-bold text-red-300 font-mono uppercase">
                    [{technique}]
                  </span>
                )}
              </div>

              <p className="mt-1 font-mono text-sm text-sky-400">
                {cand.handle ? `@${cand.handle.replace(/^@/, "")}` : cand.package_id}
              </p>

              {cand.developer_name && (
                <p className="mt-0.5 text-xs text-slate-400">
                  Publisher: <strong className="text-slate-200">{cand.developer_name}</strong>
                </p>
              )}
            </div>
          </div>

          {/* Threat Metric */}
          <div className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-950 px-5 py-3 text-right">
            <div>
              <div className="text-xs text-slate-400 font-medium">Composite Threat Index</div>
              <div
                className={`text-3xl font-black ${
                  score >= 75
                    ? "text-red-400"
                    : score >= 50
                    ? "text-amber-400"
                    : score >= 30
                    ? "text-yellow-400"
                    : "text-emerald-400"
                }`}
              >
                {score}
                <span className="text-xs font-normal text-slate-400">/100</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Visual Comparison & Forensic Signals */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Side-by-Side Comparison */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">
            Side-by-Side Asset Forensic Match
          </h2>

          <div className="grid grid-cols-2 gap-4 rounded-lg bg-slate-950 p-4 border border-slate-800/80">
            {/* Authorized */}
            <div className="text-center space-y-2 border-r border-slate-800 pr-2">
              <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                OFFICIAL ASSET
              </span>
              <div className="flex justify-center">
                <img
                  src={brandLogo}
                  alt="Official"
                  className="h-16 w-16 rounded-xl border-2 border-emerald-500/40 object-cover shadow"
                />
              </div>
              <p className="text-xs font-bold text-slate-200">{brand.company_name}</p>
              <p className="text-[11px] text-slate-400">Authorized Entity</p>
            </div>

            {/* Candidate */}
            <div className="text-center space-y-2 pl-2">
              <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
                INFRINGING ENTITY
              </span>
              <div className="flex justify-center">
                <img
                  src={candImage}
                  alt="Candidate"
                  className="h-16 w-16 rounded-xl border-2 border-red-500/40 object-cover shadow"
                />
              </div>
              <p className="text-xs font-bold text-slate-200 truncate">
                {cand.name || cand.title}
              </p>
              <p className="text-[11px] text-slate-400 font-mono truncate">
                {cand.handle ? `@${cand.handle.replace(/^@/, "")}` : cand.package_id}
              </p>
            </div>
          </div>

          {/* Description / Bio Text */}
          <div className="rounded-lg bg-slate-950 p-3 text-xs border border-slate-800/80">
            <span className="font-semibold text-slate-400">Candidate Text Content:</span>
            <p className="mt-1 text-slate-300 italic">
              "{cand.bio || cand.description || "No bio description provided."}"
            </p>
          </div>
        </div>

        {/* Threat Score Breakdown Bars */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">
            Weighted Signal Breakdown
          </h2>

          <div className="space-y-3 text-xs">
            {/* Name Similarity (35) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Name Lexical Match (Max 35)</span>
                <span className="font-bold">{breakdown.name_similarity || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-sky-500"
                  style={{ width: `${((breakdown.name_similarity || 0) / 35) * 100}%` }}
                />
              </div>
            </div>

            {/* Lookalike Technique (15) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Look-alike Technique: {technique || "None"} (Max 15)</span>
                <span className="font-bold">{breakdown.lookalike_technique || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-purple-500"
                  style={{ width: `${((breakdown.lookalike_technique || 0) / 15) * 100}%` }}
                />
              </div>
            </div>

            {/* Logo Hash (20) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Logo Perceptual Hash Match (Max 20)</span>
                <span className="font-bold">{breakdown.logo_hash || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-red-500"
                  style={{ width: `${((breakdown.logo_hash || 0) / 20) * 100}%` }}
                />
              </div>
            </div>

            {/* Bio TF-IDF (10) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Bio / Description TF-IDF Cosine (Max 10)</span>
                <span className="font-bold">{breakdown.text_similarity || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-amber-500"
                  style={{ width: `${((breakdown.text_similarity || 0) / 10) * 100}%` }}
                />
              </div>
            </div>

            {/* Publisher Mismatch (10) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Publisher / Authorization Mismatch (Max 10)</span>
                <span className="font-bold">{breakdown.publisher_mismatch || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-orange-500"
                  style={{ width: `${((breakdown.publisher_mismatch || 0) / 10) * 100}%` }}
                />
              </div>
            </div>

            {/* Scam Indicators (10) */}
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Scam & Phishing Bait Triggers (Max 10)</span>
                <span className="font-bold">{breakdown.scam_indicators || 0} pts</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-2 rounded-full bg-rose-500"
                  style={{ width: `${((breakdown.scam_indicators || 0) / 10) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Forensic Evidence Timeline */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-200">
          Forensic Evidence Log ({evidence.length} items)
        </h2>
        <div className="space-y-2">
          {evidence.map((ev, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 rounded-lg border border-slate-800/80 bg-slate-950 p-3 text-xs text-slate-300"
            >
              <span className="mt-0.5 rounded-full bg-red-500/20 p-1 text-red-400">
                <AlertTriangle className="h-3.5 w-3.5" />
              </span>
              <span>{ev}</span>
            </div>
          ))}
        </div>
      </div>

      {/* One-Click Takedown Pack */}
      {canTakedown ? (
        <div className="rounded-xl border border-sky-500/30 bg-slate-900/80 p-6 space-y-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-sky-400" />
              One-Click Takedown Pack
            </h2>
            <p className="mt-1 text-xs text-slate-400">
              Ready-to-send impersonation report with forensic evidence, official asset references,
              and platform-tailored wording.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleCopyNotice}
              className="flex items-center gap-1.5 rounded-lg bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700 active:scale-95"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  Copied to Clipboard!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy Notice Text
                </>
              )}
            </button>

            <a
              href={getTakedownPdfUrl(id)}
              download={`takedown_case_${id}.pdf`}
              className="flex items-center gap-1.5 rounded-lg bg-sky-500 px-4 py-2 text-xs font-bold text-white shadow hover:bg-sky-400 active:scale-95"
            >
              <Download className="h-3.5 w-3.5" />
              Download Dossier (PDF)
            </a>
          </div>
        </div>

        {/* Text Area with Takedown Copy */}
        <div className="relative">
          <textarea
            readOnly
            value={takedownText}
            rows={14}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-300 leading-relaxed focus:outline-none"
          />
        </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 rounded-xl border border-slate-700 bg-slate-900/60 p-5 text-sm text-slate-300">
          <Lock className="h-5 w-5 flex-shrink-0 text-slate-400" />
          <span>
            Generating takedown packs requires the Analyst or Administrator role.
            Your role can inspect this dossier but cannot generate or download
            takedown reports.
          </span>
        </div>
      )}
    </div>
  );
}
