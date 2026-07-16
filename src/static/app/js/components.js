/* ════════════════════════════════════════
   Shared UI Components
   ════════════════════════════════════════ */

/* ── Toast ── */
function showToast(msg, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = 'toast toast-' + type;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => { el.remove(); if (container.children.length === 0) container.remove(); }, 3500);
}

/* ── Bottom Nav ── */
function buildBottomNav(current) {
  return `
  <nav class="bottom-nav">
    <button class="bottom-nav-item ${current === 'discovery' ? 'active' : ''}" onclick="location.href='/app'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
      Discover
    </button>
    <button class="bottom-nav-item ${current === 'matches' ? 'active' : ''}" onclick="location.href='/app/matches.html'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      Chat
    </button>
    <button class="bottom-nav-item ${current === 'profile' ? 'active' : ''}" onclick="location.href='/app/profile.html'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      Profile
    </button>
    <button class="bottom-nav-item ${current === 'settings' ? 'active' : ''}" onclick="location.href='/app/settings.html'">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      Settings
    </button>
  </nav>`;
}

/* ── App Shell ── */
function renderPage(title, content, currentTab) {
  const nav = buildBottomNav(currentTab);
  document.getElementById('app').innerHTML = `
    <div class="app-container">
      <div class="app-header">
        <span class="app-header-title">${title}</span>
      </div>
      <div class="app-content">${content}</div>
      ${nav}
    </div>`;
}

/* ── Loading / Empty ── */
function loadingHTML(msg = 'Loading...') {
  return `<div class="loading-overlay"><div class="spinner"></div><span>${msg}</span></div>`;
}

function emptyHTML(icon, title, msg, actionHTML = '') {
  return `
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <h3>${title}</h3>
      <p>${msg}</p>
      ${actionHTML}
    </div>`;
}

/* ── Time formatters ── */
function timeAgo(dateStr) {
  const now = new Date();
  const date = new Date(dateStr);
  const sec = Math.floor((now - date) / 1000);
  if (sec < 60) return 'just now';
  if (sec < 3600) return Math.floor(sec / 60) + 'm ago';
  if (sec < 86400) return Math.floor(sec / 3600) + 'h ago';
  if (sec < 604800) return Math.floor(sec / 86400) + 'd ago';
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function formatChatTime(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

/* ── Photo gallery dots ── */
function renderPhotoDots(count, active) {
  let html = '<div class="photo-dots">';
  for (let i = 0; i < count; i++) {
    html += `<div class="photo-dot ${i === active ? 'active' : ''}"></div>`;
  }
  html += '</div>';
  return html;
}
