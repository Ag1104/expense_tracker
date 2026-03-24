let currentPage = 1;
let totalPages = 1;
let searchTimeout;

async function loadTransactions(page = 1) {
  currentPage = page;
  const month = document.getElementById('filter-month').value;
  const year = document.getElementById('filter-year').value;
  const type = document.getElementById('filter-type').value;
  const search = document.getElementById('search-input').value.toLowerCase();

  const params = new URLSearchParams({ page, per_page: 20 });
  if (month) params.set('month', month);
  if (year) params.set('year', year);
  if (type) params.set('type', type);

  const wrap = document.getElementById('txn-list-wrap');
  wrap.innerHTML = '<div class="skeleton" style="height:60px;margin-bottom:8px;"></div>'.repeat(5);

  try {
    const data = await api(`/transactions?${params}`);
    totalPages = data.pages;
    let txns = data.transactions;

    // Client-side search filter
    if (search) {
      txns = txns.filter(t =>
        (t.description || '').toLowerCase().includes(search) ||
        (t.category?.name || '').toLowerCase().includes(search)
      );
    }

    document.getElementById('txn-count-label').textContent = data.total;
    renderTransactions(txns);
    renderPagination(data.current_page, data.pages);
  } catch (e) {
    wrap.innerHTML = `<div class="empty-state"><p>Failed to load transactions</p></div>`;
    showToast('Failed to load transactions', 'error');
  }
}

function renderTransactions(txns) {
  const wrap = document.getElementById('txn-list-wrap');
  wrap.innerHTML = '';

  if (!txns.length) {
    wrap.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>No transactions found</p></div>';
    return;
  }

  txns.forEach(txn => wrap.appendChild(buildTxnItem(txn, true)));
}

function renderPagination(current, total) {
  const pg = document.getElementById('pagination');
  pg.innerHTML = '';
  if (total <= 1) return;

  const mkBtn = (label, page, active = false) => {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (active ? ' active' : '');
    btn.textContent = label;
    if (page) btn.addEventListener('click', () => loadTransactions(page));
    else btn.disabled = true;
    return btn;
  };

  if (current > 1) pg.appendChild(mkBtn('‹', current - 1));

  const start = Math.max(1, current - 2);
  const end = Math.min(total, current + 2);
  for (let i = start; i <= end; i++) {
    pg.appendChild(mkBtn(i, i, i === current));
  }

  if (current < total) pg.appendChild(mkBtn('›', current + 1));
}

function onTransactionChange() { loadTransactions(currentPage); }

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Set current filters
  const now = new Date();
  document.getElementById('filter-year').value = now.getFullYear();

  loadTransactions();

  document.getElementById('filter-month')?.addEventListener('change', () => loadTransactions(1));
  document.getElementById('filter-year')?.addEventListener('change', () => loadTransactions(1));
  document.getElementById('filter-type')?.addEventListener('change', () => loadTransactions(1));

  document.getElementById('search-input')?.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadTransactions(1), 400);
  });

  document.getElementById('add-txn-btn')?.addEventListener('click', () => {
    openAddModal(() => loadTransactions(currentPage));
  });

  document.getElementById('export-btn')?.addEventListener('click', () => {
    const month = document.getElementById('filter-month').value;
    const year = document.getElementById('filter-year').value;
    const params = new URLSearchParams({ year });
    if (month) params.set('month', month);
    window.location.href = `/export/csv?${params}`;
  });
});
