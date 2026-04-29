const API_BASE = '';

let currentPage = 1;
let currentKeyword = '';
let currentPersonIdCard = null;

Auth.requireAuth();

// Init
(function init() {
  Auth.initHeader();
  loadPersons();
})();

function onSearch() {
  const kw = document.getElementById('searchInput').value.trim();
  currentKeyword = kw;
  currentPage = 1;
  loadPersons();
}

function goToPersonPage(page) {
  currentPage = page;
  loadPersons();
}

async function loadPersons() {
  const listEl = document.getElementById('personList');
  listEl.innerHTML = '<div class="analysis-loading" style="padding:20px;"><i class="fas fa-spinner"></i><span>加载中...</span></div>';

  try {
    const res = await Auth.authFetch(
      `${API_BASE}/api/ai-portrait/persons?page=${currentPage}&per_page=20&keyword=${encodeURIComponent(currentKeyword)}`
    );
    const result = await res.json();
    if (result.success && result.data) {
      renderPersonList(result.data);
      renderPagination('pagination', result.data.page, result.data.pages, 'goToPersonPage');
    } else {
      listEl.innerHTML = '<div class="analysis-placeholder" style="padding:20px;"><span>加载失败</span></div>';
    }
  } catch (e) {
    listEl.innerHTML = '<div class="analysis-placeholder" style="padding:20px;"><span>请求异常</span></div>';
  }
}

function renderPersonList(data) {
  const listEl = document.getElementById('personList');
  const items = data.items || [];

  if (items.length === 0) {
    listEl.innerHTML = `
      <div class="analysis-placeholder" style="padding:20px;">
        <i class="fas fa-inbox"></i>
        <span>未找到匹配人员</span>
      </div>`;
    return;
  }

  let html = '';
  items.forEach(p => {
    const activeClass = currentPersonIdCard === p.id_card_number ? 'active' : '';
    const tagClass = getTagClass(p.control_category);
    html += `
      <div class="person-card ${activeClass}" onclick="selectPerson('${p.id_card_number}', '${escapeHtml(p.name || '')}')">
        <div class="person-avatar"><i class="fas fa-user"></i></div>
        <div class="person-info">
          <div class="person-name">${escapeHtml(p.name || '未知')}</div>
          <div class="person-meta">
            <span>${maskIdCard(p.id_card_number)}</span>
            <span class="person-tag ${tagClass}">${escapeHtml(p.control_category || '一般')}</span>
          </div>
          <div class="person-meta">
            <span>${escapeHtml(p.police_station || '')}</span>
            <span>${escapeHtml(p.gender || '')}</span>
            <span>${escapeHtml(p.age || '')}岁</span>
          </div>
        </div>
      </div>
    `;
  });
  listEl.innerHTML = html;
}

function selectPerson(idCard, name) {
  currentPersonIdCard = idCard;

  // Update active state
  document.querySelectorAll('.person-card').forEach(el => el.classList.remove('active'));
  const cards = document.querySelectorAll('.person-card');
  cards.forEach(el => {
    if (el.getAttribute('onclick') && el.getAttribute('onclick').includes(`'${idCard}'`)) {
      el.classList.add('active');
    }
  });

  analyzePerson(idCard, name);
}

async function analyzePerson(idCard, name) {
  const panel = document.getElementById('analysisPanel');
  panel.innerHTML = `
    <div class="analysis-loading">
      <i class="fas fa-robot"></i>
      <div style="text-align:center;">
        <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:4px;">正在分析 ${escapeHtml(name || '')}</div>
        <div style="font-size:13px;color:var(--text-muted);">AI 正在聚合多表数据并生成画像，请稍候...</div>
      </div>
    </div>
  `;

  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-portrait/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_card_number: idCard })
    });
    const result = await res.json();

    if (result.success && result.data) {
      renderAnalysis(result.data);
    } else {
      panel.innerHTML = `
        <div class="analysis-placeholder">
          <i class="fas fa-exclamation-triangle" style="color:var(--orange);"></i>
          <div style="text-align:center;">
            <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:4px;">分析失败</div>
            <div style="font-size:13px;">${escapeHtml(result.message || '未知错误')}</div>
          </div>
        </div>
      `;
    }
  } catch (e) {
    panel.innerHTML = `
      <div class="analysis-placeholder">
        <i class="fas fa-exclamation-triangle" style="color:var(--red);"></i>
        <div style="text-align:center;">
          <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:4px;">请求异常</div>
          <div style="font-size:13px;">${escapeHtml(e.message)}</div>
        </div>
      </div>
    `;
  }
}

function renderAnalysis(data) {
  const panel = document.getElementById('analysisPanel');
  const summary = data.person_summary || {};
  const analysisText = data.analysis || '';

  const riskBadge = extractRiskBadge(analysisText);
  const sections = parseAnalysisSections(analysisText);

  let sectionsHtml = '';
  sections.forEach(sec => {
    sectionsHtml += `
      <div class="analysis-section">
        <div class="analysis-section-title"><i class="fas fa-chevron-right"></i>${escapeHtml(sec.title)}</div>
        <div class="analysis-section-body">${formatText(sec.content)}</div>
      </div>
    `;
  });

  panel.innerHTML = `
    <div class="analysis-result">
      <div class="analysis-header">
        <div class="analysis-header-avatar"><i class="fas fa-user"></i></div>
        <div class="analysis-header-info">
          <h2>${escapeHtml(summary.name || '未知')} ${riskBadge}</h2>
          <div class="analysis-header-meta">
            <span><i class="fas fa-id-card"></i> ${maskIdCard(summary.id_card_number)}</span>
            <span><i class="fas fa-venus-mars"></i> ${escapeHtml(summary.gender || '-')}</span>
            <span><i class="fas fa-birthday-cake"></i> ${escapeHtml(summary.age || '-')}岁</span>
            <span><i class="fas fa-shield-alt"></i> ${escapeHtml(summary.control_category || '-')}</span>
            <span><i class="fas fa-building"></i> ${escapeHtml(summary.police_station || '-')}</span>
          </div>
        </div>
      </div>
      ${sectionsHtml}
    </div>
  `;
}

function extractRiskBadge(text) {
  if (/风险等级[：:]\s*高/.test(text) || /高\s*风险/.test(text)) {
    return '<span class="risk-badge high"><i class="fas fa-exclamation-circle"></i>高风险</span>';
  }
  if (/风险等级[：:]\s*中/.test(text) || /中\s*风险/.test(text)) {
    return '<span class="risk-badge medium"><i class="fas fa-exclamation-triangle"></i>中风险</span>';
  }
  if (/风险等级[：:]\s*低/.test(text) || /低\s*风险/.test(text)) {
    return '<span class="risk-badge low"><i class="fas fa-check-circle"></i>低风险</span>';
  }
  return '';
}

function parseAnalysisSections(text) {
  const sections = [];
  const lines = text.split('\n');
  let currentTitle = '';
  let currentContent = [];

  const sectionRegex = /^(\d+[\.．、]|\*\*|##?\s*)\s*(.+)$/;

  lines.forEach(line => {
    const match = line.match(sectionRegex);
    if (match) {
      if (currentTitle) {
        sections.push({ title: currentTitle, content: currentContent.join('\n').trim() });
      }
      currentTitle = match[2].trim();
      currentContent = [];
    } else {
      currentContent.push(line);
    }
  });

  if (currentTitle) {
    sections.push({ title: currentTitle, content: currentContent.join('\n').trim() });
  }

  if (sections.length === 0) {
    sections.push({ title: '分析报告', content: text.trim() });
  }

  return sections;
}

function formatText(text) {
  if (!text) return '';
  return escapeHtml(text)
    .replace(/\n/g, '<br>')
    .replace(/(-\s+)/g, '&bull; ');
}

function getTagClass(category) {
  if (!category) return 'blue';
  const c = category.toString();
  if (c.includes('重点') || c.includes('高危')) return 'red';
  if (c.includes('一般')) return 'orange';
  if (c.includes('已撤')) return 'green';
  return 'blue';
}

function maskIdCard(idCard) {
  if (!idCard || idCard.length !== 18) return idCard || '';
  return idCard.substring(0, 6) + '********' + idCard.substring(14);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
