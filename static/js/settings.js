// ─── Settings Page JS ─────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  loadUserInfo();
  loadCategories();
  initNotifications();
  initBankSync();
  initCSVUpload();
  initExport();
  initLogout();
});

// ─── User Info ────────────────────────────────────────────
async function loadUserInfo() {
  try {
    const user = await api('/user/me');
    document.getElementById('acc-username').textContent = user.username;
    document.getElementById('acc-email').textContent = user.email;
  } catch (e) {}
}

// ─── Notifications ────────────────────────────────────────
async function initNotifications() {
  const toggle = document.getElementById('notif-toggle');
  const statusEl = document.getElementById('notif-status');
  const testBtn = document.getElementById('test-notif-btn');

  if (!('Notification' in window) || !('serviceWorker' in navigator)) {
    statusEl.textContent = '⚠️ Push notifications not supported in this browser.';
    toggle.disabled = true;
    return;
  }

  // Load current user preference
  try {
    const user = await api('/user/me');
    toggle.checked = user.notifications_enabled && Notification.permission === 'granted';
  } catch (e) {}

  statusEl.textContent = Notification.permission === 'granted'
    ? '✅ Browser permission granted'
    : Notification.permission === 'denied'
    ? '❌ Permission denied — please allow in browser settings'
    : '⏳ Permission not yet requested';

  toggle.addEventListener('change', async () => {
    if (toggle.checked) {
      await enableNotifications(statusEl, toggle);
    } else {
      await disableNotifications(statusEl, toggle);
    }
  });

  testBtn.addEventListener('click', () => {
    if (Notification.permission !== 'granted') {
      showToast('Please enable notifications first', 'error');
      return;
    }
    new Notification('SpendWise 💰', {
      body: "Have you recorded today's expenses?",
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
    });
    showToast('Test notification sent!', 'success');
  });
}

async function enableNotifications(statusEl, toggle) {
  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {
      statusEl.textContent = '❌ Permission denied';
      toggle.checked = false;
      return;
    }

    const reg = await navigator.serviceWorker.ready;

    // Get VAPID key
    const { public_key } = await api('/push/vapid-public-key');

    let subscription;
    if (public_key) {
      subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
    } else {
      // VAPID not configured — still save preference for local notifications
      subscription = { endpoint: 'local', keys: {} };
    }

    await api('/push/subscribe', 'POST', subscription);
    statusEl.textContent = '✅ Notifications enabled — you\'ll be reminded at 8 PM daily';
    showToast('Notifications enabled!', 'success');

    // Schedule daily local notification via SW
    scheduleDailyReminder();
  } catch (e) {
    showToast('Failed to enable notifications: ' + e.message, 'error');
    toggle.checked = false;
  }
}

async function disableNotifications(statusEl, toggle) {
  try {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) await sub.unsubscribe();
    await api('/push/unsubscribe', 'POST');
    statusEl.textContent = '🔕 Notifications disabled';
    showToast('Notifications disabled', 'info');
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

function scheduleDailyReminder() {
  // Message SW to schedule a daily reminder check
  if (navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'SCHEDULE_REMINDER' });
  }
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}

// ─── Bank Sync ────────────────────────────────────────────
function initBankSync() {
  const syncBtn = document.getElementById('sync-btn');
  const resultEl = document.getElementById('sync-result');

  syncBtn.addEventListener('click', async () => {
    const provider = document.getElementById('bank-provider').value;
    const days = parseInt(document.getElementById('sync-days').value);

    syncBtn.textContent = 'Syncing...';
    syncBtn.disabled = true;
    resultEl.className = 'sync-result hidden';

    try {
      const data = await api('/bank/sync', 'POST', { provider, days });
      resultEl.className = 'sync-result success';
      resultEl.textContent = `✅ Imported ${data.imported} transactions. Skipped ${data.duplicates_skipped} duplicates. Bank balance: ₦${Number(data.bank_balance?.available || 0).toLocaleString()}`;
      showToast(`Synced! ${data.imported} new transactions`, 'success');
    } catch (e) {
      resultEl.className = 'sync-result error';
      resultEl.textContent = '❌ Sync failed: ' + e.message;
      showToast('Sync failed', 'error');
    } finally {
      syncBtn.textContent = 'Sync Now';
      syncBtn.disabled = false;
    }
  });
}

// ─── CSV Upload ───────────────────────────────────────────
function initCSVUpload() {
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('csv-file-input');
  const resultEl = document.getElementById('csv-result');

  zone.addEventListener('click', () => fileInput.click());

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.style.borderColor = 'var(--accent)';
    zone.style.background = 'var(--accent-glow)';
  });

  zone.addEventListener('dragleave', () => {
    zone.style.borderColor = '';
    zone.style.background = '';
  });

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.style.borderColor = '';
    zone.style.background = '';
    const file = e.dataTransfer.files[0];
    if (file) uploadCSV(file, resultEl);
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) uploadCSV(fileInput.files[0], resultEl);
  });
}

async function uploadCSV(file, resultEl) {
  if (!file.name.endsWith('.csv')) {
    showToast('Please upload a CSV file', 'error');
    return;
  }

  const zone = document.getElementById('upload-zone');
  zone.querySelector('p').textContent = `Uploading ${file.name}...`;
  resultEl.className = 'sync-result hidden';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/upload/csv', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    resultEl.className = 'sync-result success';
    resultEl.textContent = `✅ Imported ${data.imported} transactions. Skipped ${data.duplicates_skipped} duplicates.`;
    showToast(`CSV imported! ${data.imported} transactions added`, 'success');
  } catch (e) {
    resultEl.className = 'sync-result error';
    resultEl.textContent = '❌ Import failed: ' + e.message;
    showToast('Import failed', 'error');
  } finally {
    zone.querySelector('p').textContent = 'Drag & drop CSV or click to browse';
    document.getElementById('csv-file-input').value = '';
  }
}

// ─── Categories ───────────────────────────────────────────
async function loadCategories() {
  const listEl = document.getElementById('categories-list');
  try {
    const cats = await getCategories(true);
    listEl.innerHTML = '';
    cats.forEach(cat => {
      const item = document.createElement('div');
      item.className = 'cat-item';
      item.innerHTML = `
        <span class="cat-color-dot" style="background:${cat.color}"></span>
        <span style="font-size:16px">${cat.icon}</span>
        <span class="cat-name">${cat.name}</span>
      `;
      listEl.appendChild(item);
    });
  } catch (e) {
    listEl.innerHTML = '<p style="color:var(--text-muted);font-size:13px">Failed to load categories</p>';
  }
}

document.getElementById('add-cat-btn')?.addEventListener('click', async () => {
  const name = document.getElementById('new-cat-name').value.trim();
  const icon = document.getElementById('new-cat-icon').value.trim() || '📦';
  const color = document.getElementById('new-cat-color').value;

  if (!name) { showToast('Category name required', 'error'); return; }

  try {
    await api('/categories', 'POST', { name, icon, color });
    document.getElementById('new-cat-name').value = '';
    document.getElementById('new-cat-icon').value = '';
    await loadCategories();
    showToast('Category added!', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
});

// ─── Export ───────────────────────────────────────────────
function initExport() {
  document.getElementById('export-btn')?.addEventListener('click', () => {
    const month = document.getElementById('export-month').value;
    const year = document.getElementById('export-year').value;
    const params = new URLSearchParams({ year });
    if (month) params.set('month', month);
    window.location.href = `/export/csv?${params}`;
  });
}

// ─── Logout ───────────────────────────────────────────────
function initLogout() {
  document.getElementById('logout-btn')?.addEventListener('click', async () => {
    try {
      await api('/logout', 'POST');
      window.location.href = '/login';
    } catch (e) {
      window.location.href = '/login';
    }
  });
}
