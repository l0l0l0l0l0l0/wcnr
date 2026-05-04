const API_BASE = '';

let currentPage = 1;
let currentKeyword = '';
let currentPersonIdCard = null;

Auth.requireAuth();

// Init
(function init() {
  Auth.initHeader();

  // Auto-search by id_card_number from URL param (e.g. from alert detail AI badge)
  const urlParams = new URLSearchParams(window.location.search);
  const idCardFromUrl = urlParams.get('id_card_number');
  if (idCardFromUrl) {
    currentKeyword = idCardFromUrl;
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = idCardFromUrl;
  }

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

      // Auto-select person if id_card_number was in URL and matches a result
      const urlParams = new URLSearchParams(window.location.search);
      const idCardFromUrl = urlParams.get('id_card_number');
      if (idCardFromUrl && !currentPersonIdCard) {
        const match = (result.data.items || []).find(p => p.id_card_number === idCardFromUrl);
        if (match) {
          selectPerson(match.id_card_number, match.name || '');
        }
      }
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

  loadArchive(idCard, name);
}

async function loadArchive(idCard, name) {
  const panel = document.getElementById('analysisPanel');
  panel.innerHTML = `
    <div class="analysis-loading">
      <i class="fas fa-robot"></i>
      <div style="text-align:center;">
        <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:4px;">正在加载 ${escapeHtml(name || '')} 的AI档案</div>
        <div style="font-size:13px;color:var(--text-muted);">请稍候...</div>
      </div>
    </div>
  `;

  // Load profile (structured data) first
  let profileData = null;
  try {
    const res = await Auth.authFetch(
      `${API_BASE}/api/ai-portrait/profile?id_card_number=${encodeURIComponent(idCard)}`
    );
    const result = await res.json();
    if (result.success && result.data) {
      profileData = result.data;
      renderArchive(result.data);
    }
  } catch (e) {
    panel.innerHTML = `
      <div class="analysis-placeholder">
        <i class="fas fa-exclamation-triangle" style="color:var(--red);"></i>
        <div style="text-align:center;">
          <div style="font-size:16px;font-weight:600;color:var(--text);margin-bottom:4px;">档案加载失败</div>
          <div style="font-size:13px;">${escapeHtml(e.message)}</div>
        </div>
      </div>
    `;
    return;
  }

  // Then load AI patrol report
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-portrait/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_card_number: idCard })
    });
    const result = await res.json();

    if (result.success && result.data) {
      appendPatrolReport(result.data.analysis);
    } else {
      appendPatrolReportError(result.message || '分析失败');
    }
  } catch (e) {
    appendPatrolReportError(e.message);
  }
}

function renderArchive(data) {
  const panel = document.getElementById('analysisPanel');
  const basic = data.basic_info || {};
  const guardians = data.guardians || [];
  const alertFeedback = data.alert_feedback || [];

  let html = '<div class="archive-scroll">';

  // Header
  html += renderArchiveHeader(basic);

  // Section 1: 个人简介
  html += renderProfileSection(basic, guardians);

  // Section 2: 历史预警反馈信息
  if (alertFeedback.length > 0) {
    html += renderAlertFeedbackSection(alertFeedback);
  }

  // Placeholder for patrol report (will be appended later)
  html += '<div id="patrolReportContainer"></div>';

  html += '</div>';
  panel.innerHTML = html;
}

function renderArchiveHeader(basic) {
  const riskBadge = extractRiskBadgeFromTag(basic.control_category);
  const idCard = basic.id_card_number || '';
  return `
    <div class="archive-header">
      <div class="archive-header-avatar"><i class="fas fa-user"></i></div>
      <div class="archive-header-info">
        <h2>${escapeHtml(basic.name || '未知')} ${riskBadge}</h2>
        <div class="archive-header-meta">
          <span><i class="fas fa-id-card"></i> ${maskIdCard(basic.id_card_number)}</span>
          <span><i class="fas fa-venus-mars"></i> ${escapeHtml(basic.gender || '-')}</span>
          <span><i class="fas fa-birthday-cake"></i> ${escapeHtml(basic.age || '-')}岁</span>
          <span><i class="fas fa-shield-alt"></i> ${escapeHtml(basic.control_category || '-')}</span>
          <span><i class="fas fa-building"></i> ${escapeHtml(basic.police_station || '-')}</span>
        </div>
      </div>
      <a href="/archive-report?id_card_number=${encodeURIComponent(idCard)}" target="_blank" class="btn" style="margin-left:auto;display:inline-flex;align-items:center;gap:6px;padding:8px 14px;background:var(--gov-blue);color:#fff;border-radius:var(--radius);font-size:13px;font-weight:600;text-decoration:none;"
        title="在新标签页打开独立档案报告页"
      >
        <i class="fas fa-file-alt"></i>查看档案报告
      </a>
    </div>
  `;
}

function renderProfileSection(basic, guardians) {
  let html = '<div class="archive-section">';
  html += '<div class="archive-section-title"><i class="fas fa-user-circle"></i>个人简介</div>';

  // Basic info grid
  const baseFields = [
    { label: '姓名', key: 'name' },
    { label: '性别', key: 'gender' },
    { label: '出生日期', key: 'birth_date' },
    { label: '年龄', key: 'age', suffix: '岁' },
    { label: '身份证', key: 'id_card_number' },
    { label: '籍贯', key: 'native_place' },
    { label: '户籍地', key: 'household_address' },
    { label: '居住地', key: 'address' },
    { label: '学历', key: 'education' },
    { label: '学校', key: 'school' },
    { label: '入学时间', key: 'enrollment_date' },
    { label: '离校时间', key: 'graduation_date' },
    { label: '所属分局', key: 'subordinate_bureau' },
    { label: '所属派出所', key: 'police_station' },
    { label: '人员类型标签', key: 'person_type_tag' },
  ];

  html += '<div style="margin-bottom:16px;">';
  html += '<div style="font-size:13px;font-weight:700;color:var(--text-secondary);margin-bottom:10px;">基础信息</div>';
  html += '<div class="info-grid">';
  baseFields.forEach(f => {
    const val = basic[f.key];
    if (val !== null && val !== undefined && val !== '') {
      html += `
        <div class="info-item">
          <span class="info-label">${f.label}:</span>
          <span class="info-value">${escapeHtml(val)}${f.suffix || ''}</span>
        </div>
      `;
    }
  });
  html += '</div></div>';

  // Guardians
  if (guardians.length > 0) {
    html += '<div style="font-size:13px;font-weight:700;color:var(--text-secondary);margin-bottom:10px;">监护人信息</div>';
    html += '<div class="guardian-wrap">';
    guardians.forEach(g => {
      html += `
        <div class="guardian-card">
          <div class="guardian-card-title">${escapeHtml(g.guardian_type || '监护人')}</div>
          ${renderInfoRow('姓名', g.name)}
          ${renderInfoRow('联系方式', g.contact)}
          ${renderInfoRow('身份证', g.id_card_number)}
          ${renderInfoRow('关系', g.relation)}
          ${renderInfoRow('居住地', g.address)}
        </div>
      `;
    });
    html += '</div>';
  }

  // Delivery info
  if (basic.delivery_time || basic.delivery_unit) {
    html += '<div style="margin-top:16px;">';
    html += '<div style="font-size:13px;font-weight:700;color:var(--text-secondary);margin-bottom:10px;">送生信息</div>';
    html += '<div class="info-grid">';
    html += renderInfoGridItem('送生时间', basic.delivery_time);
    html += renderInfoGridItem('送生单位', basic.delivery_unit);
    html += '</div></div>';
  }

  // Other info
  const otherFields = [
    { label: '是否严重不良未成年人', key: 'is_serious_bad_minor' },
    { label: '本人电话', key: 'personal_phone' },
    { label: '监护人电话', key: 'guardian_phone' },
    { label: '不良行为记录', key: 'bad_behavior_records' },
    { label: '飙车炸街行为', key: 'racing_behavior' },
    { label: '综合分析手机号', key: 'analysis_phone' },
    { label: '备注', key: 'remarks' },
  ];
  const hasOther = otherFields.some(f => {
    const v = basic[f.key];
    return v !== null && v !== undefined && v !== '';
  });
  if (hasOther) {
    html += '<div style="margin-top:16px;">';
    html += '<div style="font-size:13px;font-weight:700;color:var(--text-secondary);margin-bottom:10px;">其他信息</div>';
    html += '<div class="info-grid">';
    otherFields.forEach(f => {
      const val = basic[f.key];
      if (val !== null && val !== undefined && val !== '') {
        html += renderInfoGridItem(f.label, val);
      }
    });
    html += '</div></div>';
  }

  html += '</div>';
  return html;
}

function renderInfoRow(label, value) {
  if (!value) return '';
  return `
    <div class="info-item">
      <span class="info-label">${label}:</span>
      <span class="info-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderInfoGridItem(label, value) {
  if (!value) return '';
  return `
    <div class="info-item">
      <span class="info-label">${label}:</span>
      <span class="info-value">${escapeHtml(value)}</span>
    </div>
  `;
}

function renderAlertFeedbackSection(records) {
  let html = '<div class="archive-section">';
  html += '<div class="archive-section-title"><i class="fas fa-history"></i>历史预警反馈信息</div>';
  html += '<div class="alert-feedback-list">';
  records.forEach(r => {
    html += `
      <div class="alert-feedback-item">
        <div class="alert-feedback-time">${escapeHtml(r.time || '')}</div>
        <div class="alert-feedback-row">
          <span class="label">地点:</span>
          <span class="value">${escapeHtml(r.location || '')}</span>
        </div>
        <div class="alert-feedback-row">
          <span class="label">情况:</span>
          <span class="value">${escapeHtml(r.situation || '')}</span>
        </div>
        <div class="alert-feedback-row">
          <span class="label">处理:</span>
          <span class="value">${escapeHtml(r.handling || '')}</span>
        </div>
      </div>
    `;
  });
  html += '</div></div>';
  return html;
}

function appendPatrolReport(analysisText) {
  const container = document.getElementById('patrolReportContainer');
  if (!container) return;
  container.innerHTML = renderPatrolReport(analysisText);
}

function appendPatrolReportError(message) {
  const container = document.getElementById('patrolReportContainer');
  if (!container) return;
  container.innerHTML = `
    <div class="archive-section">
      <div class="archive-section-title"><i class="fas fa-file-alt"></i>巡逻防范报告</div>
      <div style="color:var(--text-muted);font-size:13px;padding:20px;text-align:center;">
        <i class="fas fa-exclamation-triangle" style="color:var(--orange);margin-bottom:8px;display:block;font-size:20px;"></i>
        报告加载失败: ${escapeHtml(message)}
      </div>
    </div>
  `;
}

function renderPatrolReport(text) {
  const sections = parsePatrolReport(text);

  let html = '<div class="archive-section">';
  html += '<div class="archive-section-title"><i class="fas fa-file-alt"></i>巡逻防范报告</div>';

  if (sections.length === 0) {
    html += `<div class="report-section-body">${formatText(text)}</div>`;
  } else {
    sections.forEach(sec => {
      html += `
        <div class="report-section">
          <div class="report-section-title"><i class="fas fa-chevron-right"></i>${escapeHtml(sec.title)}</div>
          <div class="report-section-body">${formatText(sec.content)}</div>
        </div>
      `;
    });
  }

  html += '</div>';
  return html;
}

function parsePatrolReport(text) {
  const sections = [];
  const lines = text.split('\n');
  let currentTitle = '';
  let currentContent = [];

  // Match: 一、xxx  二、xxx  ...  五、xxx  or  结论
  const sectionRegex = /^([一二三四五]|[①②③④⑤]|结论)[、．.\s]+(.+)$/;

  lines.forEach(line => {
    const match = line.match(sectionRegex);
    if (match) {
      if (currentTitle) {
        sections.push({ title: currentTitle, content: currentContent.join('\n').trim() });
      }
      currentTitle = line.trim();
      currentContent = [];
    } else {
      currentContent.push(line);
    }
  });

  if (currentTitle) {
    sections.push({ title: currentTitle, content: currentContent.join('\n').trim() });
  }

  if (sections.length === 0) {
    sections.push({ title: '巡逻防范报告', content: text.trim() });
  }

  return sections;
}

function extractRiskBadgeFromTag(category) {
  if (!category) return '';
  const c = category.toString();
  if (c.includes('重点') || c.includes('高危')) {
    return '<span class="risk-badge high"><i class="fas fa-exclamation-circle"></i>高风险</span>';
  }
  if (c.includes('一般')) {
    return '<span class="risk-badge medium"><i class="fas fa-exclamation-triangle"></i>中风险</span>';
  }
  if (c.includes('已撤')) {
    return '<span class="risk-badge low"><i class="fas fa-check-circle"></i>低风险</span>';
  }
  return '';
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
