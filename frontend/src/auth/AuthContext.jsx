import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .getMe()
      .then((me) => {
        if (active) setUser(me);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setInitializing(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    function onSessionExpired() {
      setUser((prev) => {
        if (prev) setSessionExpired(true);
        return null;
      });
    }
    window.addEventListener("ir:session-expired", onSessionExpired);
    return () => window.removeEventListener("ir:session-expired", onSessionExpired);
  }, []);

  const login = useCallback(async (email, password) => {
    const me = await api.login(email, password);
    setSessionExpired(false);
    setUser(me);
    return me;
  }, []);

  const signup = useCallback(async (payload) => {
    const me = await api.signup(payload);
    setSessionExpired(false);
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      setSessionExpired(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    const me = await api.getMe();
    setUser(me);
    return me;
  }, []);

  const clearSessionExpired = useCallback(() => setSessionExpired(false), []);

  const value = useMemo(() => {
    const can = (permission) => Boolean(user?.permissions?.[permission]);
    return { user, initializing, sessionExpired, login, signup, logout, refresh, can, clearSessionExpired };
  }, [user, initializing, sessionExpired, login, signup, logout, refresh, clearSessionExpired]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export const ROLE_LABELS = {
  administrator: "Administrator",
  analyst: "Analyst",
  viewer: "Viewer",
};

export const ROLE_BADGE_STYLES = {
  administrator: "bg-rose-500/15 text-rose-300 border-rose-500/40",
  analyst: "bg-sky-500/15 text-sky-300 border-sky-500/40",
  viewer: "bg-slate-500/15 text-slate-300 border-slate-500/40",
};
