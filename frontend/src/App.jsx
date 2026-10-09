import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import {
  Radar,
  Building2,
  Globe,
  Smartphone,
  FlaskConical,
  Settings as SettingsIcon,
  Shield,
  Users as UsersIcon,
  RefreshCw,
} from "lucide-react";
import { useAuth } from "./auth/AuthContext";
import UserMenu from "./components/UserMenu";
import BrandProfile from "./pages/BrandProfile.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import SocialMonitoring from "./pages/SocialMonitoring.jsx";
import AppStoreMonitoring from "./pages/AppStoreMonitoring.jsx";
import LookalikeLab from "./pages/LookalikeLab.jsx";
import DetectionDetail from "./pages/DetectionDetail.jsx";
import Settings from "./pages/Settings.jsx";
import Users from "./pages/Users.jsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";

const NAV = [
  { to: "/", label: "Trust Radar", icon: Radar },
  { to: "/brand", label: "Brand Profile", icon: Building2 },
  { to: "/social", label: "Social Feeds", icon: Globe },
  { to: "/apps", label: "App Stores", icon: Smartphone },
  { to: "/lab", label: "Look-alike Lab", icon: FlaskConical },
  { to: "/settings", label: "Settings", icon: SettingsIcon, allowed: (can) => can("scan") || can("manage_sources") },
  { to: "/users", label: "Users", icon: UsersIcon, allowed: (can) => can("manage_users") },
];

function FullPageLoader({ label }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
      <RefreshCw className="mr-2 h-5 w-5 animate-spin text-sky-400" />
      {label}
    </div>
  );
}

function ProtectedLayout() {
  const { user, initializing, can } = useAuth();
  const location = useLocation();

  if (initializing) {
    return <FullPageLoader label="Restoring your session..." />;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const visibleNav = NAV.filter((item) => !item.allowed || item.allowed(can));

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 font-sans text-slate-100 selection:bg-sky-500 selection:text-white">
      {/* Top Header Navbar */}
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          {/* Brand Logo & Title */}
          <NavLink to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-400 text-white shadow-md shadow-sky-500/20">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5 text-base font-bold tracking-tight text-white">
                <span>ImpostorRadar</span>
                <span className="rounded bg-sky-500/20 px-1.5 py-0.2 text-[10px] font-bold text-sky-400">
                  DRP
                </span>
              </div>
              <p className="text-[10px] tracking-wide text-slate-400">
                Social & App Impersonation Defense
              </p>
            </div>
          </NavLink>

          {/* Nav Links */}
          <nav className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
            {visibleNav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 rounded-lg px-3 py-2 transition-all ${
                      isActive
                        ? "border border-sky-500/30 bg-sky-500/15 text-sky-400 shadow-sm"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`
                  }
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* User Menu */}
          <UserMenu />
        </div>
      </header>

      {/* Main Page Area */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-4 text-center text-xs text-slate-500">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4">
          <span>
            ImpostorRadar — Digital Risk Protection platform built for Kampus.VC Challenge.
          </span>
          <span className="text-slate-400">
            Python + FastAPI + SQLite • React + Vite + Tailwind
          </span>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/brand" element={<BrandProfile />} />
        <Route path="/social" element={<SocialMonitoring />} />
        <Route path="/apps" element={<AppStoreMonitoring />} />
        <Route path="/lab" element={<LookalikeLab />} />
        <Route path="/detections/:id" element={<DetectionDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/users" element={<Users />} />
        <Route
          path="*"
          element={
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center text-slate-400">
              Page not found.{" "}
              <NavLink to="/" className="text-sky-400 underline">
                Return home
              </NavLink>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
