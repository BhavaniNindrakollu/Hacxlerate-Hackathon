import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { ROLE_BADGE_STYLES, ROLE_LABELS, useAuth } from "../auth/AuthContext";

export default function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (!user) return null;

  const roleLabel = ROLE_LABELS[user.role] || user.role;
  const roleStyle = ROLE_BADGE_STYLES[user.role] || ROLE_BADGE_STYLES.viewer;

  async function handleLogout() {
    setBusy(true);
    try {
      await logout();
    } finally {
      setBusy(false);
      setOpen(false);
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-900/80 px-2.5 py-1.5 text-xs text-slate-200 transition hover:bg-slate-800"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-sky-500/20 text-sky-300">
          <UserRound className="h-3.5 w-3.5" />
        </span>
        <span className="hidden max-w-[120px] truncate font-semibold sm:inline">
          {user.full_name || user.email}
        </span>
        <span className={`hidden rounded-full border px-1.5 py-0.5 text-[10px] font-semibold sm:inline ${roleStyle}`}>
          {roleLabel}
        </span>
        <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 z-[60] mt-2 w-64 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
          <div className="border-b border-slate-800 p-4">
            <p className="truncate text-sm font-semibold text-slate-100">
              {user.full_name || "User"}
            </p>
            <p className="mt-0.5 truncate text-xs text-slate-400">{user.email}</p>
            <span className={`mt-2 inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${roleStyle}`}>
              <ShieldCheck className="h-3 w-3" />
              {roleLabel}
            </span>
          </div>

          <div className="p-2">
            <button
              type="button"
              onClick={handleLogout}
              disabled={busy}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-semibold text-red-300 transition hover:bg-red-500/10 disabled:opacity-50"
            >
              <LogOut className="h-3.5 w-3.5" />
              {busy ? "Logging out..." : "Log out"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
