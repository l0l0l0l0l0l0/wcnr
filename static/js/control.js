let controlCurrentPage = 1;
let controlCurrentPerPage = 20;
let controlTotalPages = 1;
let controlSelectedIds = new Set();

async function loadControlStats() {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/stats`);
    const result = await res.json();
    if (!result.success) return;
    const d = result.data;
    const statEls = document.querySelectorAll('#controlStatsWrap .stat-compact-value[data-count]');
    if (statEls[0]) statEls[0].dataset.count = d.total;
    if (statEls[1]) statEls[1].dataset.count = d.controlling;
    if (statEls[2]) statEls[2].dataset.count = d.pending;
    if (statEls[3]) statEls[3].dataset.count = d.revoked;
    if (statEls[4]) statEls[4].dataset.count = d.today_new;
    animateNumbers();
  } catch (e) {
    console.error('加载布控统计失败:', e);
  }
}

async function loadControls(page = 1, perPage = 20) {
  try {
    const library = document.getElementById('ctrlFilterLibrary')?.value || '';
    const status = document.getElementById('ctrlFilterStatus')?.value || '';
    const keyword = document.getElementById('ctrlFilterKeyword')?.value || '';
    const address = document.getElementById('ctrlFilterAddress')?.value || '';
    const photo = document.getElementById('ctrlFilterPhoto')?.value || '';

    const params = new URLSearchParams({ page: String(page), per_page: String(perPage) });
    if (library) params.append('library', library);
    if (status) params.append('status', status);
    if (keyword) params.append('keyword', keyword);
    if (address) params.append('address', address);
    if (photo) params.append('photo', photo);

    const res = await Auth.authFetch(`${API_BASE}/api/controls?${params}`);
    const result = await res.json();
    if (!result.success) return;

    const { items, total, pages } = result.data;
    controlCurrentPage = page;
    controlCurrentPerPage = perPage;
    controlTotalPages = pages;
    controlSelectedIds.clear();
    updateBatchButtons();

    renderControlTable(items);
    const countEl = document.getElementById('controlTotalCount');
    if (countEl) countEl.textContent = total.toLocaleString();
    renderPagination('controlPagination', page, pages, 'goToControlPage');
  } catch (e) {
    console.error('加载布控列表失败:', e);
  }
}

function renderControlTable(data) {
  const tbody = document.getElementById('controlTableBody');
  if (!tbody) return;
  tbody.innerHTML = data.map((item, idx) => {
    const status = controlStatusConfig[item.control_status] || controlStatusConfig['布控中'];
    const isSelected = controlSelectedIds.has(item.control_id) ? 'selected' : '';
    return `
      <tr class="${isSelected}" data-id="${item.control_id}">
        <td><input type="checkbox" class="ctrl-row-checkbox" ${controlSelectedIds.has(item.control_id) ? 'checked' : ''} onchange="toggleRowSelect('${item.control_id}')"></td>
        <td><div class="control-photo">${item.photo_url ? `<img src="${API_BASE}/proxy-pic?url=${encodeURIComponent(item.photo_url)}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" onerror="this.outerHTML='<i class=fas-fa-user></i>'">` : '<i class="fas fa-user"></i>'}</div></td>
        <td><strong>${item.name}</strong></td>
        <td>${item.id_card}</td>
        <td>${item.gender || '--'}</td>
        <td>${item.age || '--'}</td>
        <td>${item.ethnicity || '--'}</td>
        <td>${item.control_library}</td>
        <td><span class="ctrl-status ${status.class}">${status.text}</span></td>
        <td>${item.latest_alert_time}</td>
        <td>${item.sub_bureau}</td>
        <td>${item.police_station}</td>
        <td>${item.community}</td>
        <td>${item.alias}</td>
        <td>${item.phone}</td>
        <td>${item.household_address}</td>
        <td>${item.current_address}</td>
        <td>
          <div class="ctrl-actions">
            <i class="fas fa-eye" title="查看" onclick="alert('查看详情: ${item.name}')"></i>
            <i class="fas fa-pen" title="编辑" onclick="alert('编辑: ${item.name}')"></i>
            <i class="fas fa-ban ${item.control_status === '已撤控' ? 'delete' : ''}" title="撤控" onclick="revokeSingle('${item.control_id}')"></i>
            <i class="fas fa-trash delete" title="删除" onclick="deleteSingle('${item.control_id}')"></i>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function goToControlPage(page) {
  if (page < 1 || page > controlTotalPages || page === controlCurrentPage) return;
  loadControls(page, controlCurrentPerPage);
}

function onControlPageSizeChange(size) {
  controlCurrentPerPage = parseInt(size);
  loadControls(1, controlCurrentPerPage);
}

function jumpToControlPage(page) {
  const p = parseInt(page);
  if (isNaN(p) || p < 1) return;
  goToControlPage(Math.min(p, controlTotalPages));
}

function onControlSearch() {
  loadControls(1, controlCurrentPerPage);
}

function onControlReset() {
  document.getElementById('ctrlFilterLibrary').value = '';
  document.getElementById('ctrlFilterStatus').value = '';
  document.getElementById('ctrlFilterKeyword').value = '';
  document.getElementById('ctrlFilterAddress').value = '';
  document.getElementById('ctrlFilterNumberType').value = '';
  document.getElementById('ctrlFilterPhoto').value = '';
  loadControls(1, controlCurrentPerPage);
}

function toggleSelectAll() {
  const checkbox = document.getElementById('selectAllCheckbox');
  const rows = document.querySelectorAll('#controlTableBody tr');
  rows.forEach(row => {
    const id = row.dataset.id;
    const cb = row.querySelector('.ctrl-row-checkbox');
    if (checkbox.checked) {
      controlSelectedIds.add(id);
      if (cb) cb.checked = true;
      row.classList.add('selected');
    } else {
      controlSelectedIds.delete(id);
      if (cb) cb.checked = false;
      row.classList.remove('selected');
    }
  });
  updateBatchButtons();
}

function toggleRowSelect(id) {
  const row = document.querySelector(`#controlTableBody tr[data-id="${id}"]`);
  if (controlSelectedIds.has(id)) {
    controlSelectedIds.delete(id);
    if (row) row.classList.remove('selected');
  } else {
    controlSelectedIds.add(id);
    if (row) row.classList.add('selected');
  }
  updateBatchButtons();
}

function updateBatchButtons() {
  const revokeBtn = document.getElementById('btnBatchRevoke');
  const deleteBtn = document.getElementById('btnBatchDelete');
  const hasSelection = controlSelectedIds.size > 0;
  if (revokeBtn) revokeBtn.disabled = !hasSelection;
  if (deleteBtn) deleteBtn.disabled = !hasSelection;
}

async function onBatchRevoke() {
  if (controlSelectedIds.size === 0) return;
  const reason = prompt(`确定要撤控选中的 ${controlSelectedIds.size} 条记录吗？请输入原因（可选）：`);
  if (reason === null) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/batch_revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: Array.from(controlSelectedIds), reason })
    });
    const result = await res.json();
    alert(result.message);
    if (result.success) {
      loadControlStats();
      loadControls(controlCurrentPage, controlCurrentPerPage);
    }
  } catch (e) {
    console.error('批量撤控失败:', e);
    alert('批量撤控失败');
  }
}

async function onBatchDelete() {
  if (controlSelectedIds.size === 0) return;
  if (!confirm(`确定要删除选中的 ${controlSelectedIds.size} 条记录吗？此操作不可恢复！`)) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/batch_delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: Array.from(controlSelectedIds) })
    });
    const result = await res.json();
    alert(result.message);
    if (result.success) {
      loadControlStats();
      loadControls(1, controlCurrentPerPage);
    }
  } catch (e) {
    console.error('批量删除失败:', e);
    alert('批量删除失败');
  }
}

async function revokeSingle(control_id) {
  const reason = prompt('请输入撤控原因（可选）：');
  if (reason === null) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/batch_revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [control_id], reason })
    });
    const result = await res.json();
    alert(result.message);
    if (result.success) {
      loadControlStats();
      loadControls(controlCurrentPage, controlCurrentPerPage);
    }
  } catch (e) {
    console.error('撤控失败:', e);
  }
}

async function deleteSingle(control_id) {
  if (!confirm('确定要删除该记录吗？此操作不可恢复！')) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/batch_delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: [control_id] })
    });
    const result = await res.json();
    alert(result.message);
    if (result.success) {
      loadControlStats();
      loadControls(controlCurrentPage, controlCurrentPerPage);
    }
  } catch (e) {
    console.error('删除失败:', e);
  }
}

function onImport() {
  const input = prompt('请粘贴 JSON 格式数据（支持对象或数组）：');
  if (!input) return;
  try {
    let data = JSON.parse(input);
    if (!Array.isArray(data)) data = [data];
    Auth.authFetch(`${API_BASE}/api/control/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: data })
    })
    .then(r => r.json())
    .then(result => {
      alert(result.message);
      if (result.success) {
        loadControlStats();
        loadControls(1, controlCurrentPerPage);
      }
    });
  } catch (e) {
    alert('JSON 格式错误，请检查输入');
  }
}

async function loadTodayControls() {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/control/today`);
    const result = await res.json();
    if (!result.success) return;
    const tbody = document.getElementById('controlTableBody');
    if (!tbody) return;
    controlSelectedIds.clear();
    updateBatchButtons();
    if (result.data.length === 0) {
      tbody.innerHTML = '<tr><td colspan="18" style="text-align:center;padding:40px;color:var(--text-muted);">今日暂无预警布控人员</td></tr>';
    } else {
      renderControlTable(result.data.map((item, idx) => ({ ...item, control_id: item.control_id || `tmp-${idx}` })));
    }
    const countEl = document.getElementById('controlTotalCount');
    if (countEl) countEl.textContent = result.data.length.toLocaleString();
    renderPagination('controlPagination', 1, 1, 'goToControlPage');
  } catch (e) {
    console.error('加载今日预警失败:', e);
  }
}

// Init
loadControlStats();
loadControls(1, 20);
