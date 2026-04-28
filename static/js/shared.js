const API_BASE = '';

Auth.requireAuth();

// User dropdown
function toggleUserDropdown() {
  const dd = document.getElementById('userDropdown');
  dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', (e) => {
  if (!e.target.closest('.user-menu')) {
    const dd = document.getElementById('userDropdown');
    if (dd) dd.style.display = 'none';
  }
});

Auth.initHeader();

// Set active nav item based on data-page attribute
(function setActiveNav() {
  const page = document.body.dataset.page;
  if (!page) return;
  document.querySelectorAll('#topNav .nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.nav === page);
  });
})();

// Status configs
const statusConfig = {
  '待签收': { class: 'pending-sign', text: '待签收' },
  '待反馈': { class: 'pending-feedback', text: '待反馈' },
  '已反馈': { class: 'feedback-done', text: '已反馈' },
  '已签收': { class: 'signed', text: '已签收' }
};

const controlStatusConfig = {
  '布控中': { class: 'controlling', text: '布控中' },
  '待审批': { class: 'pending', text: '待审批' },
  '已撤控': { class: 'revoked', text: '已撤控' }
};

function animateNumbers() {
  document.querySelectorAll('.stat-compact-value[data-count]').forEach(el => {
    const target = parseInt(el.dataset.count);
    const duration = 1500;
    const start = performance.now();

    function update(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(target * eased);
      el.textContent = current.toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(update);
  });
}

function proxyUrl(url) {
  if (!url) return '';
  return `${API_BASE}/proxy-pic?url=${encodeURIComponent(url)}`;
}

function renderPagination(containerId, current, total, goToPageFn) {
  const container = document.getElementById(containerId);
  if (!container || total <= 1) {
    if (container) container.innerHTML = '';
    return;
  }

  let html = '';
  html += `<button class="page-btn ${current === 1 ? 'disabled' : ''}" onclick="${goToPageFn}(${current - 1})" ${current === 1 ? 'disabled' : ''}><i class="fas fa-chevron-left"></i></button>`;

  const delta = 2;
  let start = Math.max(1, current - delta);
  let end = Math.min(total, current + delta);

  if (current <= delta + 1) {
    end = Math.min(total, 5);
  } else if (current >= total - delta) {
    start = Math.max(1, total - 4);
  }

  if (start > 1) {
    html += `<button class="page-btn ${1 === current ? 'active' : ''}" onclick="${goToPageFn}(1)">1</button>`;
    if (start > 2) html += `<span class="page-info">...</span>`;
  }

  for (let i = start; i <= end; i++) {
    html += `<button class="page-btn ${i === current ? 'active' : ''}" onclick="${goToPageFn}(${i})">${i}</button>`;
  }

  if (end < total) {
    if (end < total - 1) html += `<span class="page-info">...</span>`;
    html += `<button class="page-btn ${total === current ? 'active' : ''}" onclick="${goToPageFn}(${total})">${total}</button>`;
  }

  html += `<button class="page-btn ${current === total ? 'disabled' : ''}" onclick="${goToPageFn}(${current + 1})" ${current === total ? 'disabled' : ''}><i class="fas fa-chevron-right"></i></button>`;

  container.innerHTML = html;
}
