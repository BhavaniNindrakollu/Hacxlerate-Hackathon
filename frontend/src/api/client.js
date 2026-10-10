/**
 * ImpostorRadar API client.
 *
 * - Every request sends session cookies (credentials: "include").
 * - Non-GET requests attach the X-CSRF-Token header read from the ir_csrf cookie
 *   (double-submit CSRF protection enforced by the backend).
 * - A 401 on a non-auth endpoint dispatches "ir:session-expired" so the AuthContext
 *   can drop the user and send them to the login page.
 */

const BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

// A deployed SPA without VITE_API_URL silently sends API calls to itself.
if (!BASE_URL && !/^(localhost|127\.0\.0\.1|\[::1\])$/.test(window.location.hostname)) {
  console.error(
    "[ImpostorRadar] VITE_API_URL is not set — API requests will go to this site and fail. " +
      "Add VITE_API_URL (the backend origin, no trailing slash) in the Vercel dashboard and redeploy."
  );
}

/**
 * Resolve a backend media path (e.g. "/uploads/logo.png") against the API base.
 * Same-origin deployments pass "" so the path stays relative; split deployments
 * (Vercel frontend + Render backend) need the absolute backend origin.
 */
export function mediaUrl(path) {
  if (!path || /^https?:\/\//i.test(path)) return path;
  return `${BASE_URL}${path}`;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

async function request(path, { method = "GET", body, formData } = {}) {
  const headers = {};

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCookie("ir_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      credentials: "include",
      headers,
      body: formData !== undefined ? formData : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Network error. Check that the backend server is running.", 0);
  }

  if (!res.ok) {
    let detail = null;
    try {
      const payload = await res.json();
      if (payload.detail) detail = payload.detail;
      else if (payload.message) detail = payload.message;
    } catch {
      // response body was not JSON — the request likely never reached the API
      // (wrong/absent VITE_API_URL, or the backend is down)
    }
    if (detail === null) {
      const origin = BASE_URL || window.location.origin;
      if (res.status === 404) {
        detail = `The API was not found at ${origin}. Check that VITE_API_URL points to the running backend (no trailing slash) and that the backend is deployed.`;
      } else if (res.status === 502 || res.status === 503) {
        detail = `The backend at ${origin} is unavailable (HTTP ${res.status}). It may be starting or crashed — check the Render logs.`;
      } else {
        detail = `Request failed (HTTP ${res.status})`;
      }
    }
    const error = new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
    if (res.status === 401 && !path.startsWith("/api/auth/")) {
      window.dispatchEvent(new Event("ir:session-expired"));
    }
    throw error;
  }

  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

// --- Authentication ---

export function signup(payload) {
  return request("/api/auth/signup", { method: "POST", body: payload });
}

export function login(email, password) {
  return request("/api/auth/login", { method: "POST", body: { email, password } });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function getMe() {
  return request("/api/auth/me");
}

// --- Brand Profile ---

export function getBrand() {
  return request("/api/brand");
}

export function saveBrand(brandData) {
  return request("/api/brand", { method: "POST", body: brandData });
}

export function uploadLogo(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/api/brand/upload-logo", { method: "POST", formData });
}

export function loadDemoBrand(confirmOverwrite = false) {
  const suffix = confirmOverwrite ? "?confirm_overwrite=true" : "";
  return request(`/api/brand/demo${suffix}`, { method: "POST" });
}

// --- Scans & Monitoring ---

export function runSocialScan() {
  return request("/api/scan/social", { method: "POST" });
}

export function getSocialDetections(params = {}) {
  const query = new URLSearchParams();
  if (params.verdict) query.set("verdict", params.verdict);
  if (params.platform) query.set("platform", params.platform);
  if (params.search) query.set("search", params.search);
  return request(`/api/detections/social?${query.toString()}`);
}

export function runAppsScan() {
  return request("/api/scan/apps", { method: "POST" });
}

export function getAppDetections(params = {}) {
  const query = new URLSearchParams();
  if (params.verdict) query.set("verdict", params.verdict);
  if (params.store) query.set("store", params.store);
  if (params.search) query.set("search", params.search);
  return request(`/api/detections/apps?${query.toString()}`);
}

// --- Detection Detail & History ---

export function getDetection(id) {
  return request(`/api/detections/${id}`);
}

export function deleteDetection(id) {
  return request(`/api/detections/${id}`, { method: "DELETE" });
}

export function deleteDetectionHistory(confirmation, createBackup) {
  return request("/api/detections/history", {
    method: "DELETE",
    body: { confirmation, create_backup: createBackup },
  });
}

// --- Look-alike Lab ---

export function generateLookalikes(name) {
  return request("/api/lookalike/generate", { method: "POST", body: { name } });
}

// --- Takedown Pack ---

export function getTakedownText(id) {
  return request(`/api/takedown/${id}/text`);
}

export function getTakedownPdfUrl(id) {
  return `${BASE_URL}/api/takedown/${id}/pdf`;
}

// --- Dashboard ---

export function getDashboardStats() {
  return request("/api/dashboard/stats");
}

// --- Sources & Settings ---

export function getSourcesStatus() {
  return request("/api/sources");
}

export function toggleSources(flags) {
  return request("/api/sources/toggle", { method: "POST", body: flags });
}

// --- User Administration (administrator only) ---

export function getUsers() {
  return request("/api/users");
}

export function updateUser(userId, payload) {
  return request(`/api/users/${userId}`, { method: "PATCH", body: payload });
}

export function getAuditLog() {
  return request("/api/audit");
}
