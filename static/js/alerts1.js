let currentPage = 1;
let currentPerPage = 20;
let totalPages = 1;

async function loadStats() {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/stats`);
    const result = await res.json();
    if (!result.success) return;

    const d = result.data;
    const statEls = document.querySelectorAll('.stat-compact-value[data-count]');
    if (statEls[0]) statEls[0].dataset.count = d.history_total;
    if (statEls[1]) statEls[1].dataset.count = d.today_total;
    if (statEls[2]) statEls[2].dataset.count = d.pending;
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
    renderPagination('pagination', page, pages, 'gotoPage');
    setTimeout(() => animateCards(), 50);
  } catch (e) {
    console.error('加载预警列表失败:', e);
  }
}

function renderCards(data) {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = data.map(item => {
    // 后端已返回百分比值（如 95.5），直接使用
    const sim = typeof item.similarity === 'number' ? item.similarity : 0;
    const simClass = sim >= 95 ? 'high' : sim >= 90 ? 'mid' : 'low';
    const status = statusConfig[item.status] || statusConfig['待签收'];

    // 使用代理服务器请求图片，解决跨域问题
    // 抓拍图：优先使用 bkg_url（背景图），其次使用 face_pic_url（人脸图）
    const snapSrcRaw = item.bkg_url || item.face_pic_url || '';
    const snapSrc = snapSrcRaw ? `/proxy-pic?url=${encodeURIComponent(snapSrcRaw)}` : '';
    // 人脸图：优先使用 face_pic_url（卡口抓拍的人脸图），其次使用 person_face_url（人员登记的人脸图）作为备选
    const faceSrcRaw = item.face_pic_url || item.person_face_url || '';
    const faceSrc = faceSrcRaw ? `/proxy-pic?url=${encodeURIComponent(faceSrcRaw)}` : '';

    return `
      <div class="person-card">
        <div class="card-images">
          <div class="img-snap" onclick="window.open('${snapSrc}', '_blank')">
            ${snapSrc ? `<img src="${snapSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none'">` : ''}
          </div>
          <div class="img-face" onclick="window.open('${faceSrc}', '_blank')">
            ${faceSrc ? `<img src="${faceSrc}" style="width:100%;height:100%;object-fit:cover;border-radius:6px;" onerror="this.style.display='none'">` : ''}
          </div>
          <div class="similarity-badge ${simClass}">${sim}</div>
        </div>
        <div class="card-body">
          <div class="person-name-row">
            <span class="person-name">${item.name}</span>
            <span class="person-id">尾号${item.id_tail || '****'}</span>
          </div>
          <div class="info-row"><i class="far fa-clock"></i><span>${item.time}</span></div>
          <div class="info-row"><i class="far fa-map-marker-alt"></i><span>${item.location}</span></div>
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

function gotoPage(page) {
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
  gotoPage(Math.min(p, totalPages));
}

// Init
loadStats();
loadAlerts(1, 20);
