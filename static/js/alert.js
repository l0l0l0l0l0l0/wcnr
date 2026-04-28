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

  const onClickOutside = (e) => {
    if (!popup.contains(e.target) && e.target !== document.getElementById('dateStart') && e.target !== document.getElementById('dateEnd') && e.target !== document.getElementById('dateIcon')) {
      closeCalendar();
    }
  };
  setTimeout(() => document.addEventListener('click', onClickOutside), 0);
  popup._cleanupClick = () => document.removeEventListener('click', onClickOutside);
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
      <button class="cal-confirm-btn" onclick="confirmDateRange()">确定</button>
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

    const snapSrc = proxyUrl(item.bkg_url || item.face_pic_url);
    const faceSrc = proxyUrl(item.person_face_url || item.face_pic_url);

    return `
      <div class="person-card">
        <div class="card-images">
          <div class="img-snap" onclick="window.open('${snapSrc}','_blank')">
            ${snapSrc ? `<img src="${snapSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-camera\\'></i><span>抓拍图</span>'">` : '<i class="fas fa-camera"></i><span>抓拍图</span>'}
          </div>
          <div class="img-face" onclick="window.open('${faceSrc}','_blank')">
            ${faceSrc ? `<img src="${faceSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none';this.parentElement.innerHTML='<i class=\\'fas fa-user\\'></i><span>人脸图</span>'">` : '<i class="fas fa-user"></i><span>人脸图</span>'}
          </div>
          <div class="similarity-badge ${simClass}">${sim}%</div>
        </div>
        <div class="card-body">
          <div class="person-name-row">
            <span class="person-name">${item.name}</span>
            <span class="person-id">尾号${item.id_tail || '****'}</span>
          </div>
          <div class="info-row"><i class="far fa-clock"></i><span>${item.time}</span></div>
          <div class="info-row"><i class="fas fa-map-marker-alt"></i><span>${item.location}</span></div>
          <div class="card-divider"></div>
          <div class="card-footer">
            <span class="tag tag-person">${item.person_tag || '重点人员'}</span>
            <span class="status-badge ${status.class}">${status.text}</span>
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
