let lineChart, pieChart, barChart;

async function loadDashboard() {
  const month = document.getElementById('filter-month').value;
  const year = document.getElementById('filter-year').value;

  const params = new URLSearchParams({ year });
  if (month) params.set('month', month);

  try {
    const data = await api(`/dashboard/data?${params}`);
    renderSummary(data.summary);
    renderLineChart(data.daily_data);
    renderPieChart(data.category_data);
    renderBarChart(data.monthly_data, year);
    renderRecentTransactions(data.recent_transactions);
  } catch (e) {
    showToast('Failed to load dashboard', 'error');
  }
}

function renderSummary(s) {
  document.getElementById('total-credit').textContent = formatCurrency(s.total_credit);
  document.getElementById('total-debit').textContent = formatCurrency(s.total_debit);
  document.getElementById('total-balance').textContent = formatCurrency(s.balance);
  document.getElementById('txn-count').textContent = s.transaction_count;

  const balEl = document.getElementById('total-balance');
  balEl.style.color = s.balance >= 0 ? 'var(--green)' : 'var(--red)';
}

function renderLineChart(dailyData) {
  const ctx = document.getElementById('line-chart').getContext('2d');
  if (lineChart) lineChart.destroy();

  const labels = dailyData.map(d => {
    const date = new Date(d.date);
    return date.toLocaleDateString('en-NG', { month: 'short', day: 'numeric' });
  });

  lineChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Credit',
          data: dailyData.map(d => d.credit),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.08)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
        },
        {
          label: 'Debit',
          data: dailyData.map(d => d.debit),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.08)',
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 3,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111520',
          borderColor: '#1e2840',
          borderWidth: 1,
          titleColor: '#8892b0',
          bodyColor: '#e8eaf6',
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.raw)}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#1e2840' },
          ticks: { color: '#4a5568', maxTicksLimit: 10, font: { size: 11 } }
        },
        y: {
          grid: { color: '#1e2840' },
          ticks: {
            color: '#4a5568',
            font: { size: 11 },
            callback: v => '₦' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v)
          }
        }
      }
    }
  });
}

function renderPieChart(categoryData) {
  const ctx = document.getElementById('pie-chart').getContext('2d');
  if (pieChart) pieChart.destroy();

  const legendEl = document.getElementById('pie-legend');

  if (!categoryData.length) {
    legendEl.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No expenses recorded</p>';
    return;
  }

  pieChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: categoryData.map(c => c.name),
      datasets: [{
        data: categoryData.map(c => c.amount),
        backgroundColor: categoryData.map(c => c.color + 'cc'),
        borderColor: categoryData.map(c => c.color),
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      cutout: '60%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111520',
          borderColor: '#1e2840',
          borderWidth: 1,
          callbacks: {
            label: (ctx) => ` ${ctx.label}: ${formatCurrency(ctx.raw)}`
          }
        }
      }
    }
  });

  // Build legend
  legendEl.innerHTML = '';
  categoryData.slice(0, 8).forEach(cat => {
    const item = document.createElement('div');
    item.className = 'pie-legend-item';
    item.innerHTML = `<span class="pie-legend-dot" style="background:${cat.color}"></span>${cat.icon} ${cat.name}`;
    legendEl.appendChild(item);
  });
}

function renderBarChart(monthlyData, year) {
  const ctx = document.getElementById('bar-chart').getContext('2d');
  if (barChart) barChart.destroy();
  document.getElementById('bar-year').textContent = year;

  barChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthlyData.map(m => m.label),
      datasets: [
        {
          label: 'Credit',
          data: monthlyData.map(m => m.credit),
          backgroundColor: 'rgba(34,197,94,0.6)',
          borderColor: '#22c55e',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'Debit',
          data: monthlyData.map(m => m.debit),
          backgroundColor: 'rgba(239,68,68,0.6)',
          borderColor: '#ef4444',
          borderWidth: 1,
          borderRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { labels: { color: '#8892b0', font: { size: 12 } } },
        tooltip: {
          backgroundColor: '#111520',
          borderColor: '#1e2840',
          borderWidth: 1,
          callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${formatCurrency(ctx.raw)}` }
        }
      },
      scales: {
        x: { grid: { color: '#1e2840' }, ticks: { color: '#4a5568', font: { size: 11 } } },
        y: {
          grid: { color: '#1e2840' },
          ticks: {
            color: '#4a5568', font: { size: 11 },
            callback: v => '₦' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v)
          }
        }
      }
    }
  });
}

function renderRecentTransactions(txns) {
  const list = document.getElementById('recent-list');
  list.innerHTML = '';
  if (!txns.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-icon">💸</div><p>No transactions yet. Add your first one!</p></div>';
    return;
  }
  txns.forEach(txn => list.appendChild(buildTxnItem(txn, true)));
}

function onTransactionChange() { loadDashboard(); }

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();

  document.getElementById('filter-month')?.addEventListener('change', loadDashboard);
  document.getElementById('filter-year')?.addEventListener('change', loadDashboard);

  document.getElementById('add-txn-btn')?.addEventListener('click', () => {
    openAddModal(() => loadDashboard());
  });

  // Set current month/year
  const now = new Date();
  const monthSel = document.getElementById('filter-month');
  const yearSel = document.getElementById('filter-year');
  if (monthSel) monthSel.value = now.getMonth() + 1;
  if (yearSel) yearSel.value = now.getFullYear();
  loadDashboard();
});
