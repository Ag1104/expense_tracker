// ─── Formatting Helpers ───────────────────────────────────
function formatCurrency(amount, currency = '₦') {
  return currency + Number(amount).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-NG', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ─── Toast Notifications ──────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── API Helper ───────────────────────────────────────────
async function api(url, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ─── Modal Manager ────────────────────────────────────────
const Modal = {
  el: null,
  open(id) {
    const el = document.getElementById(id || 'txn-modal-overlay');
    if (el) { el.classList.add('open'); this.el = el; }
  },
  close() {
    document.querySelectorAll('.modal-overlay.open').forEach(el => el.classList.remove('open'));
  }
};

// ─── Categories Cache ─────────────────────────────────────
let _categoriesCache = null;
async function getCategories(force = false) {
  if (_categoriesCache && !force) return _categoriesCache;
  _categoriesCache = await api('/categories');
  return _categoriesCache;
}

function populateCategorySelect(selectEl, selectedId = null) {
  getCategories().then(cats => {
    selectEl.innerHTML = '<option value="">Select category...</option>';
    cats.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat.id;
      opt.textContent = `${cat.icon} ${cat.name}`;
      if (selectedId && cat.id == selectedId) opt.selected = true;
      selectEl.appendChild(opt);
    });
  });
}

// ─── Transaction Item Builder ─────────────────────────────
function buildTxnItem(txn, actions = true) {
  const div = document.createElement('div');
  div.className = 'txn-item';
  div.dataset.id = txn.id;

  const color = txn.category?.color || '#D3D3D3';
  const icon = txn.category?.icon || '📦';
  const amtClass = txn.type === 'credit' ? 'credit' : 'debit';
  const sign = txn.type === 'credit' ? '+' : '-';

  div.innerHTML = `
    <div class="txn-cat-icon" style="background:${hexToRgba(color, 0.15)};">${icon}</div>
    <div class="txn-info">
      <div class="txn-desc">${txn.description || txn.category?.name || 'Transaction'}</div>
      <div class="txn-meta">
        ${txn.category?.name || 'Uncategorized'} · ${txn.date_display}
        <span class="source-badge ${txn.source}">${txn.source.replace('_',' ')}</span>
      </div>
    </div>
    <div class="txn-amount ${amtClass}">${sign}${formatCurrency(txn.amount)}</div>
    ${actions ? `
    <div class="txn-actions">
      <button class="txn-action-btn edit" title="Edit">✏️</button>
      <button class="txn-action-btn delete" title="Delete">🗑</button>
    </div>` : ''}
  `;

  if (actions) {
    div.querySelector('.edit')?.addEventListener('click', () => openEditModal(txn));
    div.querySelector('.delete')?.addEventListener('click', () => confirmDelete(txn.id, div));
  }
  return div;
}

function hexToRgba(hex, alpha = 1) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ─── Delete Confirm ───────────────────────────────────────
async function confirmDelete(id, el) {
  if (!confirm('Delete this transaction?')) return;
  try {
    await api(`/transactions/${id}`, 'DELETE');
    el.style.opacity = '0';
    el.style.transform = 'translateX(-20px)';
    el.style.transition = 'all 0.3s ease';
    setTimeout(() => el.remove(), 300);
    showToast('Transaction deleted', 'success');
    if (typeof onTransactionChange === 'function') onTransactionChange();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

// ─── Mobile Nav ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const hamburger = document.getElementById('nav-hamburger');
  const overlay = document.getElementById('nav-overlay');
  const nav = document.querySelector('.app-nav');

  hamburger?.addEventListener('click', () => {
    nav.classList.toggle('open');
    overlay.classList.toggle('open');
  });
  overlay?.addEventListener('click', () => {
    nav.classList.remove('open');
    overlay.classList.remove('open');
  });

  // Greeting
  const greetEl = document.getElementById('greeting-time');
  if (greetEl) {
    const h = new Date().getHours();
    greetEl.textContent = h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening';
  }

  // Close modal buttons
  document.getElementById('modal-close')?.addEventListener('click', Modal.close);
  document.getElementById('cancel-btn')?.addEventListener('click', Modal.close);
  document.getElementById('txn-modal-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) Modal.close();
  });

  // Register service worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service-worker.js')
      .catch(err => console.warn('SW registration failed:', err));
  }
});

// ─── Global Modal for Adding/Editing Transactions ─────────
let _txnSaveCallback = null;

function openAddModal(callback) {
  _txnSaveCallback = callback;
  document.getElementById('modal-title').textContent = 'Add Transaction';
  document.getElementById('edit-txn-id').value = '';
  document.getElementById('txn-amount').value = '';
  document.getElementById('txn-description').value = '';
  document.getElementById('txn-date').value = new Date().toISOString().split('T')[0];
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.type-btn[data-type="debit"]').classList.add('active');
  populateCategorySelect(document.getElementById('txn-category'));
  Modal.open('txn-modal-overlay');
}

function openEditModal(txn) {
  document.getElementById('modal-title').textContent = 'Edit Transaction';
  document.getElementById('edit-txn-id').value = txn.id;
  document.getElementById('txn-amount').value = txn.amount;
  document.getElementById('txn-description').value = txn.description || '';
  document.getElementById('txn-date').value = txn.date.split(' ')[0];
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.type-btn[data-type="${txn.type}"]`).classList.add('active');
  populateCategorySelect(document.getElementById('txn-category'), txn.category_id);
  Modal.open('txn-modal-overlay');
}

// Type button toggle
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  document.getElementById('save-txn-btn')?.addEventListener('click', async () => {
    const id = document.getElementById('edit-txn-id').value;
    const amount = document.getElementById('txn-amount').value;
    const type = document.querySelector('.type-btn.active')?.dataset.type;
    const category_id = document.getElementById('txn-category').value || null;
    const description = document.getElementById('txn-description').value;
    const date = document.getElementById('txn-date').value;

    if (!amount || !type) return showToast('Amount and type are required', 'error');

    try {
      const btn = document.getElementById('save-txn-btn');
      btn.textContent = 'Saving...'; btn.disabled = true;

      let result;
      if (id) {
        result = await api(`/transactions/${id}`, 'PUT', { amount, type, category_id, description, date });
      } else {
        result = await api('/transactions', 'POST', { amount, type, category_id, description, date });
      }

      Modal.close();
      showToast(id ? 'Transaction updated!' : 'Transaction added!', 'success');
      if (typeof _txnSaveCallback === 'function') _txnSaveCallback(result);
      if (typeof onTransactionChange === 'function') onTransactionChange();
      btn.textContent = 'Save Transaction'; btn.disabled = false;
    } catch (e) {
      showToast(e.message, 'error');
      document.getElementById('save-txn-btn').textContent = 'Save Transaction';
      document.getElementById('save-txn-btn').disabled = false;
    }
  });
});
