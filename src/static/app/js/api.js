/* ════════════════════════════════════════
   API Client & Auth
   ════════════════════════════════════════ */
const BASE = '/api/v1';
const TOKEN_KEY = 'app_token';
const REFRESH_KEY = 'app_refresh_token';
const USER_KEY = 'app_user';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
function setTokens(access, refresh) {
  if (access) localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}
function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}
function isLoggedIn() {
  return !!getToken();
}

async function api(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = 'Bearer ' + token;

  const res = await fetch(BASE + path, { ...options, headers });
  if (res.status === 401 && token) {
    const refreshed = await refreshToken();
    if (refreshed) {
      headers['Authorization'] = 'Bearer ' + getToken();
      return fetch(BASE + path, { ...options, headers });
    }
    clearAuth();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  if (res.status === 204) return null;
  return res.json();
}

async function refreshToken() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return false;
  try {
    const res = await fetch(BASE + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token || refresh);
    return true;
  } catch { return false; }
}

function storeUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}
function getStoredUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
}

function redirectIfNoAuth() {
  if (!isLoggedIn()) { window.location.href = '/login'; return false; }
  return true;
}
