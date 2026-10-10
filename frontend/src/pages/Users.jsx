import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ScrollText,
  ShieldCheck,
  UserCog,
} from "lucide-react";
import { getAuditLog, getUsers, updateUser } from "../api/client";
import { ROLE_BADGE_STYLES, ROLE_LABELS, useAuth } from "../auth/AuthContext";
import AccessDenied from "../components/AccessDenied";

const ROLES = ["administrator", "analyst", "viewer"];

export default function Users() {
  const { user: currentUser, can, refresh } = useAuth();
  const [users, setUsers] = useState([]);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState(null);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [usersData, auditData] = await Promise.all([getUsers(), getAuditLog()]);
      setUsers(usersData.items || []);
      setAudit(auditData.items || []);
    } catch (err) {
      setError(err.message || "Failed to load user administration data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (can("manage_users")) loadData();
  }, [can, loadData]);

  if (!can("manage_users")) {
    return (
      <AccessDenied
        title="Administrator access required"
        message="User management and the audit log are only available to administrators."
      />
    );
  }

  async function handleUpdate(target, changes) {
    setBusyUserId(target.id);
    setMessage(null);
    setError(null);
    try {
      await updateUser(target.id, changes);
      setMessage(`Updated ${target.email}.`);
      if (currentUser && target.id === currentUser.id) {
        // A role change to the current user changes their permissions immediately.
        await refresh();
      }
      await loadData();
    } catch (err) {
      setError(err.message || "Failed to update user.");
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow">
        <h1 className="flex items-center gap-2 text-xl font-bold text-white">
          <UserCog className="h-6 w-6 text-sky-400" />
          User & Role Management
        </h1>
        <p className="mt-1 text-xs text-slate-400">
          Assign roles, disable accounts, and review the security audit log. The last active
          administrator cannot be demoted or disabled.
        </p>
      </div>

      {message && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          <span>{message}</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex h-48 items-center justify-center text-slate-400">
          <RefreshCw className="mr-2 h-5 w-5 animate-spin text-sky-400" />
          Loading users...
        </div>
      ) : (
        <>
          {/* Users table (tablet/desktop) */}
          <div className="hidden overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60 shadow sm:block">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Role</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {users.map((u) => {
                  const isSelf = currentUser && u.id === currentUser.id;
                  const busy = busyUserId === u.id;
                  return (
                    <tr key={u.id} className="hover:bg-slate-900">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold text-sky-300">
                            {(u.full_name || u.email).slice(0, 2).toUpperCase()}
                          </span>
                          <div>
                            <p className="font-semibold text-slate-100">
                              {u.full_name || "—"} {isSelf && <span className="text-[10px] text-sky-400">(you)</span>}
                            </p>
                            <p className="text-slate-400">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={u.role}
                          disabled={busy}
                          onChange={(e) => handleUpdate(u, { role: e.target.value })}
                          className={`rounded-md border bg-slate-950 px-2 py-1.5 text-xs font-semibold focus:outline-none disabled:opacity-50 ${ROLE_BADGE_STYLES[u.role] || ""}`}
                        >
                          {ROLES.map((r) => (
                            <option key={r} value={r}>
                              {ROLE_LABELS[r]}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                            u.is_active
                              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                              : "border-red-500/40 bg-red-500/10 text-red-300"
                          }`}
                        >
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() =>
                            handleUpdate(u, { role: u.role, is_active: !u.is_active })
                          }
                          className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                        >
                          {busy ? "Saving..." : u.is_active ? "Disable" : "Enable"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Users stacked cards (mobile) */}
          <div className="space-y-3 sm:hidden">
            {users.map((u) => {
              const isSelf = currentUser && u.id === currentUser.id;
              const busy = busyUserId === u.id;
              return (
                <div key={u.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-slate-800 text-[11px] font-bold text-sky-300">
                      {(u.full_name || u.email).slice(0, 2).toUpperCase()}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-100">
                        {u.full_name || "—"} {isSelf && <span className="text-[10px] text-sky-400">(you)</span>}
                      </p>
                      <p className="truncate text-slate-400">{u.email}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <select
                      value={u.role}
                      disabled={busy}
                      onChange={(e) => handleUpdate(u, { role: e.target.value })}
                      className={`rounded-md border bg-slate-950 px-2 py-1.5 text-xs font-semibold focus:outline-none disabled:opacity-50 ${ROLE_BADGE_STYLES[u.role] || ""}`}
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABELS[r]}
                        </option>
                      ))}
                    </select>
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                        u.is_active
                          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                          : "border-red-500/40 bg-red-500/10 text-red-300"
                      }`}
                    >
                      {u.is_active ? "Active" : "Disabled"}
                    </span>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        handleUpdate(u, { role: u.role, is_active: !u.is_active })
                      }
                      className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700 disabled:opacity-50"
                    >
                      {busy ? "Saving..." : u.is_active ? "Disable" : "Enable"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Audit log */}
          <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow">
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-4 py-3">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                <ScrollText className="h-4 w-4 text-sky-400" />
                Security Audit Log (latest 100 events)
              </h2>
              <button
                type="button"
                onClick={loadData}
                className="flex items-center gap-1.5 rounded-md bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-200 hover:bg-slate-700"
              >
                <RefreshCw className="h-3 w-3" />
                Refresh
              </button>
            </div>
            {audit.length === 0 ? (
              <p className="px-4 py-6 text-center text-xs text-slate-500">No audit events yet.</p>
            ) : (
              <ul className="max-h-96 divide-y divide-slate-800/70 overflow-y-auto">
                {audit.map((row) => (
                  <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-xs">
                    <div className="flex items-center gap-2.5">
                      <ShieldCheck className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" />
                      <span className="font-mono font-semibold text-sky-300">{row.action}</span>
                      {row.detail && <span className="text-slate-400">{row.detail}</span>}
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-slate-500">
                      {row.ip_address && <span className="font-mono">{row.ip_address}</span>}
                      <span>{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
