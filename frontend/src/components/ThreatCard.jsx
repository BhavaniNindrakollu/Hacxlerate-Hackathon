import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileText,
  Copy,
  Check,
} from "lucide-react";
import SeverityBadge from "./SeverityBadge";

export default function ThreatCard({ detection, brand, onQuickTakedown }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const cand = detection.candidate || {};
  const breakdown = detection.breakdown || {};
  const evidence = detection.evidence || [];
  const score = detection.score || 0;
  const verdict = detection.verdict || "Safe";
  const technique = detection.lookalike_technique;

  const isApp = detection.candidate_type === "app";
  const title = cand.name || cand.title || "Unknown Asset";
  const identifier = cand.handle ? `@${cand.handle.replace(/^@/, "")}` : cand.package_id || "";
  const platform = cand.platform || cand.store || detection.candidate_type;
  const candImage = cand.avatar_url || cand.icon_url || "/uploads/neutral_tech.png";
  const brandLogo = brand?.logo_url || "/uploads/paytm_official.png";

  const isOfficial = detection.is_official || verdict === "Official";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-lg backdrop-blur transition-all duration-200 hover:border-slate-700 hover:bg-slate-900/90">
      {/* Header Row */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3.5">
          {/* Candidate Avatar / Icon */}
          <div className="relative">
            <img
              src={candImage}
              alt={title}
              onError={(e) => {
                e.target.src = "/uploads/neutral_tech.png";
              }}
              className="h-13 w-13 rounded-xl border border-slate-700 bg-slate-800 object-cover p-0.5"
            />
            {technique && (
              <span className="absolute -bottom-2 -right-1 rounded bg-red-600 px-1 py-0.2 text-[10px] font-bold uppercase tracking-wider text-white shadow">
                {technique}
              </span>
            )}
          </div>

          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-slate-100">{title}</h3>
              <SeverityBadge verdict={isOfficial ? "Official" : verdict} />
              <span className="rounded bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400 capitalize">
                {platform}
              </span>
            </div>

            <p className="mt-1 font-mono text-xs text-sky-400">{identifier}</p>

            <div className="mt-1 flex flex-wrap gap-x-4 text-xs text-slate-400">
              {cand.developer_name && (
                <span>
                  Dev: <strong className="text-slate-300">{cand.developer_name}</strong>
                </span>
              )}
              {cand.followers_count !== undefined && (
                <span>Followers: {cand.followers_count.toLocaleString()}</span>
              )}
              {cand.downloads_count !== undefined && (
                <span>Downloads: {cand.downloads_count.toLocaleString()}</span>
              )}
              {cand.is_verified && (
                <span className="text-emerald-400 font-medium">✓ Verified</span>
              )}
            </div>
          </div>
        </div>

        {/* Score Radial / Badge */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-xs text-slate-400">Threat Score</div>
            <div
              className={`text-2xl font-black ${
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

      {/* Bio / Description Snippet */}
      {(cand.bio || cand.description) && (
        <div className="mt-3 rounded-lg bg-slate-950/60 p-2.5 text-xs text-slate-300">
          <p className="line-clamp-2 italic">"{cand.bio || cand.description}"</p>
        </div>
      )}

      {/* Side-by-Side Logo Comparison & Score Breakdown */}
      <div className="mt-4 grid grid-cols-1 gap-4 rounded-lg border border-slate-800/80 bg-slate-950/40 p-3.5 sm:grid-cols-2">
        {/* Side-by-side logo */}
        <div className="flex items-center justify-around border-b border-slate-800/60 pb-3 sm:border-b-0 sm:border-r sm:pb-0 sm:pr-3">
          <div className="text-center">
            <span className="text-[11px] text-slate-400">Official Brand</span>
            <div className="mt-1 flex justify-center">
              <img
                src={brandLogo}
                alt="Official"
                className="h-10 w-10 rounded-lg border border-emerald-500/40 object-cover"
              />
            </div>
          </div>

          <div className="flex flex-col items-center px-2">
            <span className="text-[10px] text-slate-400">vs</span>
            <div className="my-0.5 rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
              pHash: {breakdown.logo_hash > 0 ? "Matched" : "No match"}
            </div>
          </div>

          <div className="text-center">
            <span className="text-[11px] text-slate-400">Detected Asset</span>
            <div className="mt-1 flex justify-center">
              <img
                src={candImage}
                alt="Detected"
                className="h-10 w-10 rounded-lg border border-red-500/40 object-cover"
              />
            </div>
          </div>
        </div>

        {/* Signal Breakdown Mini Bar */}
        <div className="flex flex-col justify-center space-y-1.5 text-[11px]">
          <div className="flex justify-between text-slate-400">
            <span>Name Sim (35): <strong className="text-slate-200">{breakdown.name_similarity || 0}</strong></span>
            <span>Technique (15): <strong className="text-slate-200">{breakdown.lookalike_technique || 0}</strong></span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Logo Match (20): <strong className="text-slate-200">{breakdown.logo_hash || 0}</strong></span>
            <span>Publisher (10): <strong className="text-slate-200">{breakdown.publisher_mismatch || 0}</strong></span>
          </div>
          <div className="flex justify-between text-slate-400">
            <span>Bio TF-IDF (10): <strong className="text-slate-200">{breakdown.text_similarity || 0}</strong></span>
            <span>Scam Signals (10): <strong className="text-slate-200">{breakdown.scam_indicators || 0}</strong></span>
          </div>
        </div>
      </div>

      {/* Forensic Evidence Bullets */}
      <div className="mt-3.5 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">
            Forensic Evidence ({evidence.length} signals)
          </span>
          {evidence.length > 2 && (
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 text-[11px] text-sky-400 hover:text-sky-300"
            >
              {expanded ? "Show Less" : "Show All"}
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          )}
        </div>

        <ul className="space-y-1 text-xs">
          {(expanded ? evidence : evidence.slice(0, 2)).map((ev, i) => (
            <li key={i} className="flex items-start gap-2 text-slate-300">
              <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-red-400" />
              <span>{ev}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Action Footer */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800/80 pt-3">
        {cand.profile_url || cand.app_url ? (
          <a
            href={cand.profile_url || cand.app_url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200"
          >
            Open Source <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <span />
        )}

        <div className="flex items-center gap-2">
          {verdict !== "Safe" && !isOfficial && (
            <Link
              to={`/detections/${detection.id}`}
              className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500/20 px-3 py-1.5 text-xs font-medium text-sky-400 hover:bg-sky-500/30"
            >
              <FileText className="h-3.5 w-3.5" />
              Takedown Pack
            </Link>
          )}

          <Link
            to={`/detections/${detection.id}`}
            className="inline-flex items-center gap-1 text-xs font-medium text-slate-300 hover:text-white"
          >
            Details <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
