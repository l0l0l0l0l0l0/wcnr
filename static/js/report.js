let reportDataCache = [];
let reportSummaryCache = null;

async function loadReportStats() {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/report/stats`);
    const result = await res.json();
    if (!result.success) return;

    reportSummaryCache = result.data.summary;
    reportDataCache = result.data.items;
    renderReportCards(reportSummaryCache, reportDataCache);
  } catch (e) {
    console.error('加载报表统计失败:', e);
  }
}

function renderReportCards(summary, items) {
  const grid = document.getElementById('reportGrid');
  if (!grid) return;

  let html = '';

  if (summary) {
    html += `
      <div class="report-card summary">
        <div class="report-card-header">
          <span class="report-card-name">${summary.name}</span>
          <span class="report-card-rank top">#${summary.rank}</span>
        </div>
        <div class="report-card-body">
          <div class="report-stat">
            <div class="report-stat-value">${summary.alerts.toLocaleString()}</div>
            <div class="report-stat-label">预警数量</div>
          </div>
          <div class="report-stat">
            <div class="report-stat-value">${summary.staff}</div>
            <div class="report-stat-label">登录人员</div>
          </div>
          <div class="report-stat">
            <div class="report-stat-value rate">${summary.rate}%</div>
            <div class="report-stat-label">签收率</div>
          </div>
        </div>
      </div>
    `;
  }

  items.forEach(item => {
    html += `
      <div class="report-card" data-name="${item.name}">
        <div class="report-card-header">
          <span class="report-card-name">${item.name}</span>
          <span class="report-card-rank ${item.rank <= 3 ? 'top' : ''}">#${item.rank}</span>
        </div>
        <div class="report-card-body">
          <div class="report-stat">
            <div class="report-stat-value">${item.alerts.toLocaleString()}</div>
            <div class="report-stat-label">预警数量</div>
          </div>
          <div class="report-stat">
            <div class="report-stat-value">${item.staff}</div>
            <div class="report-stat-label">登录人员</div>
          </div>
          <div class="report-stat">
            <div class="report-stat-value rate">${item.rate}%</div>
            <div class="report-stat-label">签收率</div>
          </div>
        </div>
      </div>
    `;
  });

  grid.innerHTML = html;
}

function onReportSearch() {
  const keyword = (document.getElementById('reportSearchInput')?.value || '').trim().toLowerCase();
  if (!keyword) {
    renderReportCards(reportSummaryCache, reportDataCache);
    return;
  }
  const filtered = reportDataCache.filter(item => item.name.toLowerCase().includes(keyword));
  renderReportCards(reportSummaryCache, filtered);
}

// Init
loadReportStats();
