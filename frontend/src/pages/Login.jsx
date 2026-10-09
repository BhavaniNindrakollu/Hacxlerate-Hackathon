import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, Clock, LogIn, RefreshCw, Shield } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login, user, sessionExpired, clearSessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = location.state?.from?.pathname || "/";

  useEffect(() => {
    if (user) navigate(redirectTo, { replace: true });
  }, [user, navigate, redirectTo]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }

    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 font-sans text-slate-100">
      <div className="w-full max-w-md">
        {/* Brand header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-sky-600 to-cyan-400 text-white shadow-lg shadow-sky-500/20">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="mt-3 text-xl font-bold tracking-tight text-white">ImpostorRadar</h1>
          <p className="mt-1 text-xs text-slate-400">
            Digital Risk Protection — Social & App Impersonation Defense
          </p>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-xl">
          <h2 className="text-sm font-semibold text-slate-200">Sign in to your workspace</h2>

          {sessionExpired && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
              <Clock className="h-4 w-4 flex-shrink-0" />
              <span>Your session expired. Please log in again to continue.</span>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-4 space-y-4" noValidate>
            <div>
              <label htmlFor="login-email" className="mb-1 block text-xs font-semibold text-slate-300">
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="login-password" className="mb-1 block text-xs font-semibold text-slate-300">
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-bold text-white shadow transition hover:bg-sky-400 disabled:opacity-50"
            >
              {submitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />}
              {submitting ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="mt-5 border-t border-slate-800 pt-4 text-center text-xs text-slate-400">
            Need an account?{" "}
            <Link
              to="/signup"
              onClick={clearSessionExpired}
              className="font-semibold text-sky-400 hover:text-sky-300"
            >
              Create one
            </Link>
          </p>
        </div>

        <p className="mt-4 text-center text-[11px] text-slate-500">
          Sessions are protected by secure, httpOnly cookies. Unauthorized access is blocked on the
          server side.
        </p>
      </div>
    </div>
  );
}
