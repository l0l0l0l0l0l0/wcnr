let currentPage = 1;
let currentPerPage = 20;
let totalPages = 1;

/* ===== DATE RANGE PICKER ===== */
const calState = {
  year: new Date().getFullYear(),
  month: new Date().getMonth(),
  rangeStart: null,
  rangeEnd: null,
  selecting: false,
  popup: null,
};

function formatCalDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function openCalendar(anchorEl) {
  if (calState.popup) { closeCalendar(); }

  const popup = document.createElement('div');
  popup.className = 'calendar-popup';
  calState.popup = popup;
  calState.anchorEl = anchorEl;

  renderCalendar();
  document.body.appendChild(popup);
  positionCalendar();

  const onScrollResize = () => positionCalendar();
  window.addEventListener('scroll', onScrollResize, true);
  window.addEventListener('resize', onScrollResize);
  popup._cleanupScroll = () => {
    window.removeEventListener('scroll', onScrollResize, true);
    window.removeEventListener('resize', onScrollResize);
  };

  // Calendar only closes via confirm button
  popup._cleanupClick = () => {};
}

function positionCalendar() {
  const popup = calState.popup;
  const anchor = calState.anchorEl;
  if (!popup || !anchor) return;

  const rect = anchor.closest('.date-range-wrap').getBoundingClientRect();
  const popW = popup.offsetWidth;
  const viewW = window.innerWidth;
  const viewH = window.innerHeight;

  let left = rect.left;
  let top = rect.bottom + 4;

  if (left + popW > viewW - 8) left = viewW - popW - 8;
  if (left < 8) left = 8;

  const popH = popup.offsetHeight;
  if (top + popH > viewH - 8) top = rect.top - popH - 4;

  popup.style.left = left + 'px';
  popup.style.top = top + 'px';
}

function closeCalendar() {
  if (!calState.popup) return;
  calState.popup._cleanupClick?.();
  calState.popup._cleanupScroll?.();
  calState.popup.remove();
  calState.popup = null;
  calState.anchorEl = null;
}

function renderCalendar() {
  const popup = calState.popup;
  if (!popup) return;

  const { year, month, rangeStart, rangeEnd } = calState;
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startWeekday = firstDay.getDay();
  const daysInMonth = lastDay.getDate();

  const prevLast = new Date(year, month, 0).getDate();

  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

  let html = `
    <div class="cal-header">
      <button class="cal-nav" onclick="calNav(-1)"><i class="fas fa-chevron-left"></i></button>
      <span class="cal-header-title">${year}年${month + 1}月</span>
      <button class="cal-nav" onclick="calNav(1)"><i class="fas fa-chevron-right"></i></button>
    </div>
    <div class="cal-weekdays">
      ${weekdays.map(w => `<div class="cal-weekday">${w}</div>`).join('')}
    </div>
    <div class="cal-days">`;

  const today = new Date();
  const todayStr = formatCalDate(today);

  for (let i = 0; i < startWeekday; i++) {
    const d = prevLast - startWeekday + 1 + i;
    html += `<div class="cal-day other-month" data-date="">${d}</div>`;
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    let cls = 'cal-day';
    if (dateStr === todayStr) cls += ' today';
    if (rangeStart && dateStr === formatCalDate(rangeStart)) {
      cls += rangeEnd ? ' range-start' : ' selected';
    }
    if (rangeEnd && dateStr === formatCalDate(rangeEnd)) cls += ' range-end';
    if (rangeStart && rangeEnd) {
      const dt = new Date(year, month, d);
      if (dt > rangeStart && dt < rangeEnd) cls += ' in-range';
    }
    html += `<div class="${cls}" data-date="${dateStr}" onclick="pickDate('${dateStr}')">${d}</div>`;
  }

  const totalCells = startWeekday + daysInMonth;
  const remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  for (let i = 1; i <= remaining; i++) {
    html += `<div class="cal-day other-month" data-date="">${i}</div>`;
  }

  html += `</div>
    <div class="cal-footer">
      <div class="cal-shortcuts">
        <button class="cal-shortcut" onclick="calShortcut('today')">今天</button>
        <button class="cal-shortcut" onclick="calShortcut('week')">本周</button>
        <button class="cal-shortcut" onclick="calShortcut('month')">本月</button>
      </div>
      <button class="cal-confirm-btn${(!calState.rangeStart || !calState.rangeEnd) ? ' disabled' : ''}" ${(!calState.rangeStart || !calState.rangeEnd) ? 'disabled' : ''} onclick="confirmDateRange()">确定</button>
    </div>`;

  popup.innerHTML = html;
}

function calNav(dir) {
  calState.month += dir;
  if (calState.month < 0) { calState.month = 11; calState.year--; }
  if (calState.month > 11) { calState.month = 0; calState.year++; }
  renderCalendar();
}

function pickDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  if (!calState.selecting || (calState.rangeStart && calState.rangeEnd)) {
    calState.rangeStart = d;
    calState.rangeEnd = null;
    calState.selecting = true;
  } else {
    if (d < calState.rangeStart) {
      calState.rangeEnd = calState.rangeStart;
      calState.rangeStart = d;
    } else {
      calState.rangeEnd = d;
    }
    calState.selecting = false;
  }
  renderCalendar();
}

function calShortcut(type) {
  const today = new Date();
  if (type === 'today') {
    calState.rangeStart = today;
    calState.rangeEnd = new Date(today);
  } else if (type === 'week') {
    const day = today.getDay();
    calState.rangeStart = new Date(today);
    calState.rangeStart.setDate(today.getDate() - (day === 0 ? 6 : day - 1));
    calState.rangeEnd = new Date(calState.rangeStart);
    calState.rangeEnd.setDate(calState.rangeStart.getDate() + 6);
  } else if (type === 'month') {
    calState.rangeStart = new Date(today.getFullYear(), today.getMonth(), 1);
    calState.rangeEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  }
  calState.selecting = false;
  calState.year = calState.rangeStart.getFullYear();
  calState.month = calState.rangeStart.getMonth();
  renderCalendar();
}

function confirmDateRange() {
  const dateStart = document.getElementById('dateStart');
  const dateEnd = document.getElementById('dateEnd');
  if (calState.rangeStart) {
    dateStart.value = formatCalDate(calState.rangeStart);
  }
  if (calState.rangeEnd) {
    dateEnd.value = formatCalDate(calState.rangeEnd);
  } else if (calState.rangeStart) {
    dateEnd.value = formatCalDate(calState.rangeStart);
  }
  closeCalendar();
}

/* ===== TIME PERIOD ===== */
function initTimePeriod() {
  const hourStart = document.getElementById('hourStart');
  const hourEnd = document.getElementById('hourEnd');
  const minuteStart = document.getElementById('minuteStart');
  const minuteEnd = document.getElementById('minuteEnd');

  hourStart.innerHTML = '<option value="">起始时</option>';
  hourEnd.innerHTML = '<option value="">结束时</option>';
  for (let i = 0; i < 24; i++) {
    const val = String(i).padStart(2, '0');
    hourStart.innerHTML += `<option value="${val}">${val}时</option>`;
    hourEnd.innerHTML += `<option value="${val}">${val}时</option>`;
  }

  minuteStart.innerHTML = '<option value="">起始分</option>';
  minuteEnd.innerHTML = '<option value="">结束分</option>';
  for (let i = 0; i < 60; i += 5) {
    const val = String(i).padStart(2, '0');
    minuteStart.innerHTML += `<option value="${val}">${val}分</option>`;
    minuteEnd.innerHTML += `<option value="${val}">${val}分</option>`;
  }
}

function onTimePeriodChange() {
  const val = document.getElementById('timePeriod').value;
  const wrap = document.getElementById('timeRangeWrap');
  const hourGroup = document.getElementById('hourRangeGroup');
  const minuteGroup = document.getElementById('minuteRangeGroup');

  if (!val) {
    wrap.style.display = 'none';
    hourGroup.style.display = 'none';
    minuteGroup.style.display = 'none';
    return;
  }

  wrap.style.display = 'flex';
  if (val === 'hour') {
    hourGroup.style.display = 'flex';
    minuteGroup.style.display = 'none';
  } else {
    hourGroup.style.display = 'none';
    minuteGroup.style.display = 'flex';
  }
}

function initDatePickers() {
  const dateStart = document.getElementById('dateStart');
  const dateEnd = document.getElementById('dateEnd');
  const dateIcon = document.getElementById('dateIcon');

  dateStart.addEventListener('click', () => openCalendar(dateStart));
  dateEnd.addEventListener('click', () => openCalendar(dateEnd));
  dateIcon.addEventListener('click', () => openCalendar(dateStart));

  document.getElementById('timePeriod').addEventListener('change', onTimePeriodChange);
  initTimePeriod();

  const today = formatCalDate(new Date());
  dateStart.value = today;
  dateEnd.value = today;
  calState.rangeStart = new Date();
  calState.rangeEnd = new Date();
}

async function loadStats() {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/stats`);
    const result = await res.json();
    if (!result.success) return;

    const d = result.data;
    const statEls = document.querySelectorAll('.stat-compact-value[data-count]');
    if (statEls[0]) statEls[0].dataset.count = d.history_total;
    if (statEls[1]) statEls[1].dataset.count = d.today_total;
    if (statEls[2]) statEls[2].dataset.count = d.pending_sign;
    if (statEls[3]) statEls[3].dataset.count = d.pending_feedback;
    if (statEls[4]) statEls[4].dataset.count = d.feedback_done;

    animateNumbers();
  } catch (e) {
    console.error('加载统计数据失败:', e);
  }
}

async function loadAlerts(page = 1, perPage = 20) {
  try {
    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    const keyword = document.querySelector('.filter-input[placeholder="证件/车牌号"]')?.value;
    const status = document.querySelector('.filter-select option:checked')?.textContent;
    if (keyword) params.append('keyword', keyword);
    if (status && status !== '全部') params.append('status', status);

    const res = await Auth.authFetch(`${API_BASE}/api/alerts?${params}`);
    const result = await res.json();
    if (!result.success) return;

    const { items, total, pages } = result.data;
    currentPage = page;
    currentPerPage = perPage;
    totalPages = pages;

    renderCards(items);
    updateResultCount(total);
    renderPagination('pagination', page, pages, 'goToPage');
    setTimeout(() => animateCards(), 50);
  } catch (e) {
    console.error('加载预警列表失败:', e);
  }
}

function renderCards(data) {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = data.map(item => {
    const sim = typeof item.similarity === 'number' ? item.similarity : 0;
    const simClass = sim >= 95 ? 'high' : sim >= 90 ? 'mid' : 'low';
    const status = statusConfig[item.status] || statusConfig['待签收'];

    const isClickable = item.status === '待签收' || item.status === '待反馈' || item.status === '已反馈';

    // 抓拍图：优先使用 bkg_url，其次使用 face_pic_url
    const snapSrcRaw = item.bkg_url || item.face_pic_url || '';
    const snapSrc = snapSrcRaw ? `/proxy-pic?url=${encodeURIComponent(snapSrcRaw)}` : '';
    // 人脸图：优先使用 face_pic_url，其次使用 person_face_url 作为备选
    const faceSrcRaw = item.face_pic_url || item.person_face_url || '';
    const faceSrc = faceSrcRaw ? `/proxy-pic?url=${encodeURIComponent(faceSrcRaw)}` : '';

    return `
      <div class="person-card" onclick="openAlertDetail(${item.db_id})">
        <div class="card-images">
          <div class="img-snap" onclick="event.stopPropagation();window.open('${snapSrc}','_blank')">
            ${snapSrc ? `<img src="${snapSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-camera\\'></i><span>抓拍图</span>'">` : '<i class="fas fa-camera"></i><span>抓拍图</span>'}
          </div>
          <div class="img-face" onclick="event.stopPropagation();window.open('${faceSrc}','_blank')">
            ${faceSrc ? `<img src="${faceSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i><span>人脸图</span>'">` : '<i class="fas fa-user"></i><span>人脸图</span>'}
          </div>
          <div class="similarity-badge ${simClass}">${sim}%</div>
        </div>
        <div class="card-body">
          <div class="person-name-row">
            <span class="person-name">${item.name}</span>
            <span class="person-id">${item.person_id_card || ''}</span>
          </div>
          <div class="info-row"><i class="far fa-clock"></i><span>${item.time}</span></div>
          <div class="info-row"><i class="fas fa-map-marker-alt"></i><span>${item.location}</span></div>
          <div class="card-divider"></div>
          <div class="card-footer">
            <span class="tag tag-person">${item.person_tag || '重点人员'}</span>
            <span class="status-badge ${status.class} ${isClickable ? 'clickable' : ''}"
                  onclick="${isClickable ? `event.stopPropagation();openAlertModal(${item.db_id},'${item.status}')` : ''}">${status.text}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function animateCards() {
  const cards = document.querySelectorAll('.person-card');
  cards.forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px) scale(0.97)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1)';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0) scale(1)';
    }, i * 45);
  });
}

function updateResultCount(total) {
  const countEl = document.querySelector('.results-count .highlight');
  if (countEl) countEl.textContent = total.toLocaleString();
}

function goToPage(page) {
  if (page < 1 || page > totalPages || page === currentPage) return;
  loadAlerts(page, currentPerPage);
}

function onPageSizeChange(size) {
  currentPerPage = parseInt(size);
  loadAlerts(1, currentPerPage);
}

function jumpToPage(page) {
  const p = parseInt(page);
  if (isNaN(p) || p < 1) return;
  goToPage(Math.min(p, totalPages));
}

// Init
initDatePickers();
loadStats();
loadAlerts(1, 20);

// Overlay click to close
document.getElementById('alertModalOverlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeAlertModal();
});

// Detail modal overlay click to close
document.getElementById('alertDetailOverlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) closeAlertDetail();
});

/* ===== ALERT PROCESS MODAL ===== */
let currentAlertDbId = null;
let currentAlertStatus = null;

async function openAlertModal(dbId, status) {
  currentAlertDbId = dbId;
  currentAlertStatus = status;

  const overlay = document.getElementById('alertModalOverlay');

  // Reset form state
  document.getElementById('signForm').style.display = 'none';
  document.getElementById('feedbackForm').style.display = 'none';
  document.getElementById('modalHistory').style.display = 'none';
  document.getElementById('alertModalFooter').style.display = '';
  document.getElementById('alertModalSubmitBtn').disabled = true;

  overlay.classList.add('show');

  try {
    const res = await Auth.authFetch(`${API_BASE}/api/alerts/${dbId}/detail`);
    const result = await res.json();
    if (!result.success) { alert('获取预警详情失败'); closeAlertModal(); return; }

    const d = result.data;

    // Images
    const snapSrc = d.bkg_url ? `/proxy-pic?url=${encodeURIComponent(d.bkg_url)}` : '';
    const faceSrc = d.face_pic_url ? `/proxy-pic?url=${encodeURIComponent(d.face_pic_url)}` : '';
    document.getElementById('modalSnapImg').innerHTML = snapSrc
      ? `<img src="${snapSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;">`
      : '<i class="fas fa-camera"></i><span>抓拍图</span>';
    document.getElementById('modalFaceImg').innerHTML = faceSrc
      ? `<img src="${faceSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;">`
      : '<i class="fas fa-user"></i><span>人脸图</span>';

    // Info fields
    document.getElementById('modalName').textContent = d.name || '--';
    document.getElementById('modalIdCard').textContent = d.person_id_card || '--';
    document.getElementById('modalTime').textContent = d.time || '--';
    document.getElementById('modalLocation').textContent = d.location || '--';
    document.getElementById('modalCameraCode').textContent = d.camera_index_code || '--';
    document.getElementById('modalSimilarity').textContent = (d.similarity || 0) + '%';

    const statusConf = statusConfig[d.status] || statusConfig['待签收'];
    const statusSpan = document.getElementById('modalStatus');
    statusSpan.textContent = statusConf.text;
    statusSpan.className = 'status-badge ' + statusConf.class;

    // Show appropriate form based on status
    const user = Auth.getUser();
    const handlerName = user ? (user.real_name || user.username) : '--';

    if (d.is_processed === 0) {
      document.getElementById('alertModalTitle').textContent = '签收预警';
      document.getElementById('signForm').style.display = '';
      document.getElementById('signHandler').value = handlerName;
      document.getElementById('signRemark').value = '';
      document.getElementById('alertModalSubmitBtn').textContent = '确认签收';
      document.getElementById('alertModalSubmitBtn').disabled = false;
    } else if (d.is_processed === 1) {
      document.getElementById('alertModalTitle').textContent = '反馈预警';
      document.getElementById('feedbackForm').style.display = '';
      document.getElementById('feedbackHandler').value = handlerName;
      document.getElementById('feedbackContent').value = '';
      document.getElementById('alertModalSubmitBtn').textContent = '提交反馈';
      document.getElementById('alertModalSubmitBtn').disabled = false;
    } else if (d.is_processed === 2) {
      document.getElementById('alertModalTitle').textContent = '再次反馈';
      document.getElementById('feedbackForm').style.display = '';
      document.getElementById('feedbackHandler').value = handlerName;
      document.getElementById('feedbackContent').value = '';
      document.getElementById('alertModalSubmitBtn').textContent = '再次反馈';
      document.getElementById('alertModalSubmitBtn').disabled = false;
    } else {
      document.getElementById('alertModalTitle').textContent = '预警详情';
      document.getElementById('alertModalFooter').style.display = 'none';
    }

    // Show history if logs exist
    if (d.logs && d.logs.length > 0) {
      document.getElementById('modalHistory').style.display = '';
      document.getElementById('modalHistoryList').innerHTML = d.logs.map(log => {
        const actionLabel = log.action === 'sign' ? '签收' : '反馈';
        const detail = log.remark || log.feedback_content || '';
        return `<div class="history-item">
          <span class="history-action">${actionLabel}</span>
          <span>${log.handler_name || '--'}</span>
          ${detail ? '<span>' + detail + '</span>' : ''}
          <span class="history-time">${log.created_at}</span>
        </div>`;
      }).join('');
    }

  } catch (e) {
    console.error('加载预警详情失败:', e);
    alert('加载预警详情失败');
    closeAlertModal();
  }
}

function closeAlertModal() {
  document.getElementById('alertModalOverlay').classList.remove('show');
  currentAlertDbId = null;
  currentAlertStatus = null;
  document.getElementById('alertModalFooter').style.display = '';
}

async function submitAlertProcess() {
  if (!currentAlertDbId) return;

  const btn = document.getElementById('alertModalSubmitBtn');
  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = '处理中...';

  try {
    let url, body;

    if (currentAlertStatus === '待签收') {
      url = `${API_BASE}/api/alerts/${currentAlertDbId}/sign`;
      body = JSON.stringify({ remark: document.getElementById('signRemark').value.trim() || null });
    } else {
      const content = document.getElementById('feedbackContent').value.trim();
      if (!content) {
        alert('请输入反馈内容');
        btn.disabled = false;
        btn.textContent = originalText;
        return;
      }
      url = `${API_BASE}/api/alerts/${currentAlertDbId}/feedback`;
      body = JSON.stringify({ feedback_content: content });
    }

    const res = await Auth.authFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body
    });
    const result = await res.json();

    if (result.success) {
      closeAlertModal();
      loadAlerts(currentPage, currentPerPage);
      loadStats();
    } else {
      alert(result.message || '操作失败');
      btn.disabled = false;
      btn.textContent = originalText;
    }
  } catch (e) {
    console.error('提交失败:', e);
    alert('提交失败');
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

/* ===== ALERT DETAIL MODAL ===== */
let currentDetailDbId = null;

function switchDetailImageTab(tab) {
  document.querySelectorAll('.detail-image-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.detail-image-tab[data-tab="${tab}"]`).classList.add('active');
}

function switchDetailRightTab(tab) {
  document.querySelectorAll('.detail-right-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.detail-right-tab[data-tab="${tab}"]`).classList.add('active');
  document.querySelectorAll('.detail-tab-pane').forEach(p => p.classList.remove('active'));
  const paneMap = { basic: 'detailTabBasic', flow: 'detailTabFlow', history: 'detailTabHistory' };
  document.getElementById(paneMap[tab]).classList.add('active');
}

async function openAlertDetail(dbId) {
  currentDetailDbId = dbId;
  const overlay = document.getElementById('alertDetailOverlay');

  // Reset to basic tab
  switchDetailRightTab('basic');
  document.querySelectorAll('.detail-image-tab').forEach(t => t.classList.remove('active'));
  document.querySelector('.detail-image-tab[data-tab="face"]').classList.add('active');

  overlay.classList.add('show');

  try {
    const res = await Auth.authFetch(`${API_BASE}/api/alerts/${dbId}/detail`);
    const result = await res.json();
    if (!result.success) { alert('获取预警详情失败'); closeAlertDetail(); return; }

    const d = result.data;

    // Images
    const snapSrc = d.bkg_url ? `/proxy-pic?url=${encodeURIComponent(d.bkg_url)}` : '';
    const faceSrc = d.face_pic_url ? `/proxy-pic?url=${encodeURIComponent(d.face_pic_url)}` : '';
    const personFaceSrc = d.person_face_url ? `/proxy-pic?url=${encodeURIComponent(d.person_face_url)}` : '';

    document.getElementById('detailSnapImg').innerHTML = snapSrc
      ? `<img src="${snapSrc}" style="width:100%;height:100%;object-fit:cover;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-camera\\'></i><span>抓拍图片</span>'">`
      : '<i class="fas fa-camera"></i><span>抓拍图片</span>';
    document.getElementById('detailFaceImg').innerHTML = (faceSrc || personFaceSrc)
      ? `<img src="${faceSrc || personFaceSrc}" style="width:100%;height:100%;object-fit:cover;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i><span>库对比图</span>'">`
      : '<i class="fas fa-user"></i><span>库对比图</span>';

    // Basic info
    const sim = typeof d.similarity === 'number' ? d.similarity : 0;
    document.getElementById('detailSimilarity').textContent = sim + '%';
    document.getElementById('detailLib').textContent = d.control_lib || '--';
    document.getElementById('detailName').textContent = d.name || '--';
    document.getElementById('detailIdCard').innerHTML = (d.person_id_card || '--') +
      (d.person_id_card ? ' <span class="detail-ai-badge">AI</span>' : '');
    document.getElementById('detailGender').textContent = d.gender || '--';

    const tags = d.person_tag ? d.person_tag.split(/[,，、]/).filter(Boolean) : [];
    document.getElementById('detailTags').innerHTML = tags.length > 0
      ? tags.map(t => `<span class="detail-tag">${t.trim()}</span>`).join('')
      : '--';
    document.getElementById('detailTime').textContent = d.time || '--';
    document.getElementById('detailSnapTime').textContent = d.snap_time || d.time || '--';
    document.getElementById('detailLocation').textContent = d.location || '--';

    // Map
    const mapContainer = document.getElementById('detailMapContainer');
    if (d.location) {
      mapContainer.innerHTML = `<iframe src="https://map.baidu.com/search/${encodeURIComponent(d.location)}" title="地图"></iframe>`;
    } else {
      mapContainer.innerHTML = '<div class="detail-map-placeholder"><i class="fas fa-map-marked-alt"></i><span>暂无位置信息</span></div>';
    }

    // Flow timeline
    const flowContainer = document.getElementById('detailFlowTimeline');
    let flowHtml = '';

    // Add feedback entries from logs
    if (d.logs && d.logs.length > 0) {
      d.logs.forEach(log => {
        const isFeedback = log.action === 'feedback';
        const dotClass = isFeedback ? 'success' : '';
        const actionLabel = log.action === 'sign' ? '签收' : '反馈';
        const statusHtml = isFeedback ? ' <span class="detail-timeline-status">已完成</span>' : '';
        flowHtml += `
          <div class="detail-timeline-item">
            <div class="detail-timeline-dot ${dotClass}"></div>
            <div class="detail-timeline-title">
              <span>${actionLabel}</span>
              <span class="detail-timeline-time">${log.created_at || ''}</span>
              ${statusHtml}
            </div>
            <div class="detail-timeline-content">
              ${log.handler_name ? `<div class="detail-timeline-row"><div class="detail-timeline-label">${actionLabel}人：</div><div class="detail-timeline-value">${log.handler_name}</div></div>` : ''}
              ${log.created_at ? `<div class="detail-timeline-row"><div class="detail-timeline-label">${actionLabel}时间：</div><div class="detail-timeline-value">${log.created_at}</div></div>` : ''}
              ${log.remark ? `<div class="detail-timeline-row"><div class="detail-timeline-label">备注：</div><div class="detail-timeline-value">${log.remark}</div></div>` : ''}
              ${log.feedback_content ? `<div class="detail-timeline-row"><div class="detail-timeline-label">反馈内容：</div><div class="detail-timeline-value">${log.feedback_content}</div></div>` : ''}
            </div>
          </div>`;
      });
    }

    // Always add the initial alert entry at the bottom
    flowHtml += `
      <div class="detail-timeline-item">
        <div class="detail-timeline-dot warning"></div>
        <div class="detail-timeline-title"><span>预警</span></div>
        <div class="detail-timeline-content">
          <div class="detail-timeline-row"><div class="detail-timeline-label">预警时间：</div><div class="detail-timeline-value">${d.time || '--'}</div></div>
          <div class="detail-timeline-row"><div class="detail-timeline-label">抓拍时间：</div><div class="detail-timeline-value">${d.snap_time || d.time || '--'}</div></div>
          <div class="detail-timeline-row"><div class="detail-timeline-label">抓拍地点：</div><div class="detail-timeline-value">${d.location || '--'}</div></div>
        </div>
      </div>`;

    flowContainer.innerHTML = flowHtml;

    // History timeline
    const historyContainer = document.getElementById('detailHistoryTimeline');
    if (d.history && d.history.length > 0) {
      historyContainer.innerHTML = d.history.map(h => {
        const hSnapSrc = h.bkg_url ? `/proxy-pic?url=${encodeURIComponent(h.bkg_url)}` : '';
        const hFaceSrc = h.face_pic_url ? `/proxy-pic?url=${encodeURIComponent(h.face_pic_url)}` : '';
        return `
          <div class="detail-history-item">
            <div class="detail-history-dot"></div>
            <div class="detail-history-body">
              <div class="detail-history-image-wrap">
                <div class="detail-history-time-badge">${h.time || '--'}</div>
                <div class="detail-history-main-image">
                  ${hSnapSrc ? `<img src="${hSnapSrc}" onerror="this.style.display='none';this.parentElement.textContent='抓拍图'">` : '抓拍图'}
                </div>
                <div class="detail-history-location">${h.location || ''}</div>
              </div>
              <div class="detail-history-info">
                <div class="detail-history-result">处置结果：${h.result || '--'}</div>
                <div class="detail-history-detail">${h.detail || ''}</div>
              </div>
            </div>
          </div>`;
      }).join('');
    } else {
      historyContainer.innerHTML = '<div class="detail-history-empty">暂无历史预警</div>';
    }

  } catch (e) {
    console.error('加载预警详情失败:', e);
    alert('加载预警详情失败');
    closeAlertDetail();
  }
}

function closeAlertDetail() {
  document.getElementById('alertDetailOverlay').classList.remove('show');
  currentDetailDbId = null;
}

function handleSecondaryAlert() {
  if (!currentDetailDbId) return;
  alert('二次预警功能开发中');
}
